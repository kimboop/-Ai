#!/usr/bin/env python3
"""Two-model collaboration runner: Claude (lead) -> Gemini (support).

Claude authors the full Instagram Reels production package and flags
anything it cannot verify itself with `[VERIFY-GEMINI: ...]` markers.
Gemini's only job is to resolve those markers and run a QC pass -- it does
not rewrite Claude's creative/structural choices.

Input: a UTF-8 markdown/text file.
Output: artifacts/01-claude-lead-draft.md and artifacts/02-final-reels-package.md.
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


def post(url, headers, payload, retries=4, backoff=10):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={**headers, "Content-Type":"application/json"}, method="POST")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                print(f"{url} returned {e.code}, retrying in {wait}s (attempt {attempt + 1}/{retries})")
                time.sleep(wait)
                continue
            raise


def claude(text):
    key = os.environ["ANTHROPIC_API_KEY"]
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
    data = post("https://api.anthropic.com/v1/messages",
                {"x-api-key": key, "anthropic-version":"2023-06-01"},
                {"model":model,"max_tokens":12000,"messages":[{"role":"user","content":text}]})
    return "\n".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")


def gemini(text):
    key = os.environ["GEMINI_API_KEY"]
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    data = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                {"x-goog-api-key": key},
                {"contents":[{"parts":[{"text": text}]}]})
    return data["candidates"][0]["content"]["parts"][0]["text"]

base = f"""You are one member of a two-AI Instagram Reels production team.\n\nSOURCE MATERIAL:\n{source}\n\nDo not invent facts. Separate FACT / FORECAST / TARGET / INTERPRETATION. Flag anything needing fresh web verification. Target output: a single Instagram Reel, vertical 9:16, runtime under 90 seconds unless the source material specifies otherwise. Return actionable, production-ready output."""

claude_draft = claude(base + "\n\nROLE: CLAUDE — lead producer and primary author. You own the creative and structural output. Produce the full Reels production package: (1) hook (first 1-3 seconds), (2) full timestamped script/voiceover, (3) shot-by-shot list (shot #, script line, vertical-framing visual direction, on-screen text, duration), (4) caption draft, (5) hashtag set (broad/niche/branded), (6) trending-audio style guidance, (7) cover-frame suggestion, (8) on-screen text/caption-burn-in timing specs, (9) CTA, (10) QC checklist. For anything you cannot verify yourself — live trending-audio names, current hashtag performance, fresh facts/statistics, competitor benchmarks — do not guess. Insert an explicit `[VERIFY-GEMINI: <what is needed>]` marker instead of a value. This draft is the primary deliverable; Gemini will only fill in what you flag, not rewrite it.")
(Path(OUT / "01-claude-lead-draft.md")).write_text(claude_draft, encoding="utf-8")

final = gemini(base + f"\n\nCLAUDE'S DRAFT:\n{claude_draft}\n\nROLE: GEMINI — support researcher. Do not rewrite Claude's creative or structural choices. Find every `[VERIFY-GEMINI: ...]` marker in the draft and replace it with a researched, sourced answer — or, if it truly cannot be verified without live web access, say so plainly and note it as a pre-publish TODO instead of fabricating a value. Then run a final QC pass: confirm FACT/FORECAST/TARGET/INTERPRETATION labeling is consistent, flag any copyright/music-licensing or Instagram community-guideline risk, and confirm the hashtags/caption stay consistent with the script. Return the complete final Reels production package with every marker resolved, plus a short 'QC & Supplement Notes' section summarizing what you filled in and any remaining risk.")
(Path(OUT / "02-final-reels-package.md")).write_text(final, encoding="utf-8")
print("DONE: artifacts/02-final-reels-package.md")
