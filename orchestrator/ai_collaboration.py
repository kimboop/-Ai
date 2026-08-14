#!/usr/bin/env python3
"""Three-model collaboration runner: Gemini -> Claude -> OpenAI.

Input: a UTF-8 markdown/text file.
Output: artifacts/collaboration-final.md and per-agent reports.
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


def openai(text):
    key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL", "gpt-5")
    data = post("https://api.openai.com/v1/responses",
                {"Authorization":f"Bearer {key}"},
                {"model":model,"input":text})
    return data.get("output_text", "")

base = f"""You are one member of a three-AI production team.\n\nSOURCE MATERIAL:\n{source}\n\nDo not invent facts. Separate FACT / FORECAST / TARGET / INTERPRETATION. Flag anything needing fresh web verification. Return actionable production-ready output."""

gemini_report = gemini(base + "\n\nROLE: GEMINI — research and evidence auditor. Find contradictions, missing verification points, and source-quality problems. Produce a structured fact-check report.")
(Path(OUT / "01-gemini-research.md")).write_text(gemini_report, encoding="utf-8")

claude_report = claude(base + f"\n\nGEMINI REPORT:\n{gemini_report}\n\nROLE: CLAUDE — senior editor/reviewer. Reconcile the source with Gemini's report. Identify exact corrections, narrative risks, legal/copyright risks, and give a corrected production plan.")
(Path(OUT / "02-claude-review.md")).write_text(claude_report, encoding="utf-8")

final = openai(base + f"\n\nGEMINI REPORT:\n{gemini_report}\n\nCLAUDE REVIEW:\n{claude_report}\n\nROLE: GPT — final orchestrator. Produce the final production package. Keep verified facts intact, resolve conflicts conservatively, label uncertainty, and output: (1) final script, (2) scene-by-scene visual instructions, (3) B-roll/real-vs-AI list, (4) graphics specs, (5) SRT draft, (6) thumbnail/title options, (7) description, (8) final QC checklist. Do not claim a source was verified unless the supplied reports support it.")
(Path(OUT / "03-final-package.md")).write_text(final, encoding="utf-8")
print("DONE: artifacts/03-final-package.md")
