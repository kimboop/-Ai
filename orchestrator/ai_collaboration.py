#!/usr/bin/env python3
"""Two-model collaboration runner: Gemini -> Claude.

Input: a UTF-8 markdown/text file.
Output: artifacts/01-gemini-research.md and artifacts/02-final-package.md.
Secrets are supplied only through environment variables.
"""
import json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)

INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input.md"
if not INPUT.exists():
    raise SystemExit(f"Input file not found: {INPUT}")
source = INPUT.read_text(encoding="utf-8")


def post(url, headers, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={**headers, "Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def gemini(text):
    key = os.environ["GEMINI_API_KEY"]
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    data = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                {"x-goog-api-key": key},
                {"contents":[{"parts":[{"text": text}]}]})
    return data["candidates"][0]["content"]["parts"][0]["text"]


def claude(text):
    key = os.environ["ANTHROPIC_API_KEY"]
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    data = post("https://api.anthropic.com/v1/messages",
                {"x-api-key": key, "anthropic-version":"2023-06-01"},
                {"model":model,"max_tokens":12000,"messages":[{"role":"user","content":text}]})
    return "\n".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")

base = f"""You are one member of a two-AI production team.\n\nSOURCE MATERIAL:\n{source}\n\nDo not invent facts. Separate FACT / FORECAST / TARGET / INTERPRETATION. Flag anything needing fresh web verification. Return actionable production-ready output."""

gemini_report = gemini(base + "\n\nROLE: GEMINI — research and evidence auditor. Find contradictions, missing verification points, and source-quality problems. Produce a structured fact-check report.")
(Path(OUT / "01-gemini-research.md")).write_text(gemini_report, encoding="utf-8")

final = claude(base + f"\n\nGEMINI REPORT:\n{gemini_report}\n\nROLE: CLAUDE — senior editor and final orchestrator. Reconcile the source with Gemini's report, identify exact corrections, narrative risks, and legal/copyright risks, then produce the final production package. Keep verified facts intact, resolve conflicts conservatively, label uncertainty, and output: (1) corrected production plan, (2) final script, (3) scene-by-scene visual instructions, (4) B-roll/real-vs-AI list, (5) graphics specs, (6) SRT draft, (7) thumbnail/title options, (8) description, (9) final QC checklist. Do not claim a source was verified unless the supplied reports support it.")
(Path(OUT / "02-final-package.md")).write_text(final, encoding="utf-8")
print("DONE: artifacts/02-final-package.md")
