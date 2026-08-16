# AI Collaboration Orchestrator

## Pipeline
1. Gemini audits research/evidence against `input.md`.
2. Claude reconciles Gemini's audit with the source material and produces the
   final production package.

The original design had a third OpenAI/GPT stage; it was dropped for billing
reasons (see root `CLAUDE.md`). Restoring it means adding an `openai()`
function to `ai_collaboration.py` and the `OPENAI_API_KEY` secret/guard back
into the workflow.

## Required environment variables
- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`

Optional model variables:
- `GEMINI_MODEL`
- `CLAUDE_MODEL`

## Run
```bash
python orchestrator/ai_collaboration.py input.md
```

Outputs are written to `artifacts/`.

## Important
API keys must never be committed to GitHub. Use local environment variables or repository/CI secrets.
