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


def gemini(text):
    key = os.environ["GEMINI_API_KEY"]
    models = gemini_models()
    for i, model in enumerate(models):
        try:
            data = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        {"x-goog-api-key": key},
                        {"contents":[{"parts":[{"text": text}]}]})
        except urllib.error.HTTPError as e:
            if e.code not in FALLBACK_STATUS or i == len(models) - 1:
                raise
            reason = e.code
        except (TimeoutError, urllib.error.URLError) as e:
            if i == len(models) - 1:
                raise
            reason = type(e).__name__
        else:
            print(f"Gemini stage served by {model}")
            return data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"::warning::Gemini model {model} unavailable ({reason}), falling back to {models[i + 1]}")


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

gemini_report = gemini(base + "\n\nROLE: GEMINI — research and evidence auditor. Find contradictions, missing verification points, and source-quality problems. Produce a structured fact-check report.")
(Path(OUT / "01-gemini-research.md")).write_text(gemini_report, encoding="utf-8")

final = claude(base + f"\n\nGEMINI REPORT:\n{gemini_report}\n\nROLE: CLAUDE — senior editor and final orchestrator. Reconcile the source with Gemini's report, identify exact corrections, narrative risks, and legal/copyright risks, then produce the final production package. Keep verified facts intact, resolve conflicts conservatively, label uncertainty, and output: (1) corrected production plan, (2) final script, (3) scene-by-scene visual instructions, (4) B-roll/real-vs-AI list, (5) graphics specs, (6) SRT draft, (7) thumbnail/title options, (8) description, (9) final QC checklist. Do not claim a source was verified unless the supplied reports support it.")
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
    print(f"::warning::ChatGPT stage failed, Claude package kept: {e}")
    sys.exit(0)
(Path(OUT / "03-chatgpt-distribution.md")).write_text(distribution, encoding="utf-8")
print("DONE: artifacts/03-chatgpt-distribution.md")
