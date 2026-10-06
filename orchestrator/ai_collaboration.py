#!/usr/bin/env python3
"""Multi-model collaboration runner: Gemini -> Claude -> (optional) ChatGPT.

Input: a UTF-8 markdown/text file.
Output: artifacts/01-gemini-research.md, artifacts/02-final-package.md and,
when OPENAI_API_KEY is set, artifacts/03-chatgpt-distribution.md.
Secrets are supplied only through environment variables.
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)

INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input.md"
if not INPUT.exists():
    raise SystemExit(f"Input file not found: {INPUT}")
source = INPUT.read_text(encoding="utf-8")


RETRYABLE_STATUS = (429, 500, 502, 503, 504)


def post(url, headers, payload, retries=4, backoff=10, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={**headers, "Content-Type":"application/json"}, method="POST")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE_STATUS or attempt == retries - 1:
                raise
            reason = e.code
        # Slow model responses surface as read timeouts or dropped connections,
        # not HTTP errors; they're just as transient, so retry them too.
        except (TimeoutError, urllib.error.URLError) as e:
            if attempt == retries - 1:
                raise
            reason = type(e).__name__
        wait = backoff * (2 ** attempt)
        print(f"{url} failed ({reason}), retrying in {wait}s (attempt {attempt + 1}/{retries})")
        time.sleep(wait)


# Status codes that mean "this model can't serve us right now" rather than
# "the request itself is wrong": worth trying a different model for. 404
# covers a retired or misspelled model ID; 400/401/403 (bad key, bad
# payload) would fail identically on every model, so they still fail fast.
FALLBACK_STATUS = RETRYABLE_STATUS + (404,)


def gemini_models():
    primary = os.getenv("GEMINI_MODEL") or "gemini-3.6-flash"
    fallbacks = os.getenv("GEMINI_FALLBACK_MODELS") or "gemini-3.5-flash,gemini-3.5-flash-lite"
    models = [primary] + [m.strip() for m in fallbacks.split(",") if m.strip()]
    return list(dict.fromkeys(models))  # dedupe, keep order


def grounding_enabled():
    return os.getenv("GEMINI_GROUNDING", "true").strip().lower() not in ("0", "false", "no", "off")


def gemini_sources(candidate):
    """Render the URLs Google Search actually returned for this answer.

    Without this, the report only has whatever sources the model chooses to
    mention in prose, which can't be told apart from remembered (or invented)
    ones. These come from the API's groundingMetadata, not from the model.
    """
    meta = candidate.get("groundingMetadata") or {}
    queries = meta.get("webSearchQueries") or []
    chunks = [c["web"] for c in meta.get("groundingChunks") or [] if c.get("web", {}).get("uri")]
    if not chunks:
        return "\n\n---\n## Search grounding\nNo web sources were returned for this report. Treat every claim in it as UNVERIFIED.\n"
    lines = ["", "", "---", "## Search grounding (from Google Search, not model-written)"]
    if queries:
        lines.append("Queries: " + " | ".join(queries))
    lines += [f"{n}. [{c.get('title') or c['uri']}]({c['uri']})" for n, c in enumerate(chunks, 1)]
    return "\n".join(lines) + "\n"


def error_detail(e):
    return e.read().decode(errors="replace")[:500] if isinstance(e, urllib.error.HTTPError) else ""


def gemini_chain(text, grounded):
    """Try each model in turn; return (model, first candidate)."""
    key = os.environ["GEMINI_API_KEY"]
    models = gemini_models()
    payload = {"contents":[{"parts":[{"text": text}]}]}
    if grounded:
        # Lets Gemini run live Google searches instead of answering from
        # training data, which is what a fact-check stage is for.
        payload["tools"] = [{"google_search": {}}]
    for i, model in enumerate(models):
        try:
            data = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        {"x-goog-api-key": key},
                        payload)
        except urllib.error.HTTPError as e:
            if e.code not in FALLBACK_STATUS or i == len(models) - 1:
                raise
            reason = e.code
        except (TimeoutError, urllib.error.URLError) as e:
            if i == len(models) - 1:
                raise
            reason = type(e).__name__
        else:
            return model, data["candidates"][0]
        print(f"::warning::Gemini model {model} unavailable ({reason}), falling back to {models[i + 1]}")


def candidate_text(candidate):
    # Grounded answers can come back split across several text parts.
    return "".join(p.get("text", "") for p in candidate["content"]["parts"])


def gemini(text):
    if grounding_enabled():
        try:
            model, candidate = gemini_chain(text, grounded=True)
        except (urllib.error.HTTPError, TimeoutError, urllib.error.URLError) as e:
            # Search grounding has its own, much smaller free-tier quota: on
            # 2026-10-06 every model 429'd with it on while the same models
            # answered fine without it. A fact-check without search beats no
            # pipeline run, as long as the report says loudly that it's unverified.
            print(f"::warning::Grounded Gemini call failed on every model ({e} {error_detail(e)}".rstrip() + "); retrying without search")
            model, candidate = gemini_chain(text, grounded=False)
            print(f"Gemini stage served by {model} (search grounding FAILED, report marked UNVERIFIED)")
            return candidate_text(candidate) + (
                "\n\n---\n## Search grounding\nSearch grounding was unavailable for this run "
                f"({e}), so this report was written without web search. Treat every claim in it as UNVERIFIED.\n")
        print(f"Gemini stage served by {model} (search grounding on)")
        return candidate_text(candidate) + gemini_sources(candidate)
    model, candidate = gemini_chain(text, grounded=False)
    print(f"Gemini stage served by {model} (search grounding off)")
    return candidate_text(candidate)


def claude(text):
    key = os.environ["ANTHROPIC_API_KEY"]
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    data = post("https://api.anthropic.com/v1/messages",
                {"x-api-key": key, "anthropic-version":"2023-06-01"},
                {"model":model,"max_tokens":12000,"messages":[{"role":"user","content":text}]})
    return "\n".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")

def chatgpt(text):
    key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL") or "gpt-5"
    data = post("https://api.openai.com/v1/responses",
                {"Authorization": f"Bearer {key}"},
                {"model": model, "input": text})
    return "\n".join(c.get("text", "") for item in data.get("output", []) if item.get("type") == "message"
                     for c in item.get("content", []) if c.get("type") == "output_text")

base = f"""You are one member of a multi-AI production team.\n\nSOURCE MATERIAL:\n{source}\n\nDo not invent facts. Separate FACT / FORECAST / TARGET / INTERPRETATION. Flag anything needing fresh web verification. Return actionable production-ready output."""

gemini_report = gemini(base + "\n\nROLE: GEMINI — research and evidence auditor. Find contradictions, missing verification points, and source-quality problems. Produce a structured fact-check report. Use web search to check every factual claim and every number against current sources; for each one, state the source (publisher and date) you found it in, and mark it UNVERIFIED if search turned up nothing. Never present a number from memory as verified.")
(Path(OUT / "01-gemini-research.md")).write_text(gemini_report, encoding="utf-8")

final = claude(base + f"\n\nGEMINI REPORT:\n{gemini_report}\n\nROLE: CLAUDE — senior editor and final orchestrator. Reconcile the source with Gemini's report, identify exact corrections, narrative risks, and legal/copyright risks, then produce the final production package. Keep verified facts intact, resolve conflicts conservatively, label uncertainty, and output: (1) corrected production plan, (2) final script, (3) scene-by-scene visual instructions, (4) B-roll/real-vs-AI list, (5) graphics specs, (6) SRT draft, (7) thumbnail/title options, (8) description, (9) final QC checklist. Do not claim a source was verified unless the supplied reports support it. The 'Search grounding' section at the end of Gemini's report lists the web sources Google Search actually returned; treat a claim as verified only if it can be traced to one of those sources, and cite them in the description where facts are stated.")
(Path(OUT / "02-final-package.md")).write_text(final, encoding="utf-8")
print("DONE: artifacts/02-final-package.md")

# ChatGPT stage is opt-in: it was removed once over billing, so a missing key
# or a failed call must never cost us the Claude package written above.
if not os.getenv("OPENAI_API_KEY"):
    print("SKIP: OPENAI_API_KEY not set, ChatGPT stage skipped")
    sys.exit(0)
try:
    distribution = chatgpt(base + f"\n\nFINAL PACKAGE (from Claude):\n{final}\n\nROLE: CHATGPT — distribution and monetization strategist plus independent red-team reviewer. Do not change verified facts or add new claims. Output: (1) red-team review: any factual, legal or tone problems still left in the final package, each with the exact fix; (2) hook variants for the first 0-3 seconds (5 options); (3) platform-specific packaging for YouTube long-form, YouTube Shorts, Instagram Reels and TikTok — title, caption, hashtags, pinned comment and CTA for each; (4) thumbnail text A/B pairs; (5) upload checklist and best posting times with reasoning labeled as INTERPRETATION.")
except Exception as e:  # noqa: BLE001 - optional stage, report and keep Claude's output
    # OpenAI's 429 covers both rate limits and an unfunded account
    # ("insufficient_quota"); only the response body tells them apart.
    print(f"::warning::ChatGPT stage failed, Claude package kept: {e} {error_detail(e)}".rstrip())
    sys.exit(0)
(Path(OUT / "03-chatgpt-distribution.md")).write_text(distribution, encoding="utf-8")
print("DONE: artifacts/03-chatgpt-distribution.md")
