# 3-AI Collaboration Orchestrator

## Pipeline
1. Gemini audits research/evidence.
2. Claude reviews and reconciles Gemini + source material.
3. GPT produces the final production package.

## Required environment variables
- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

Optional model variables:
- `GEMINI_MODEL`
- `CLAUDE_MODEL`
- `OPENAI_MODEL`

## Run
```bash
python orchestrator/ai_collaboration.py input.md
```

Outputs are written to `artifacts/`.

## Important
API keys must never be committed to GitHub. Use local environment variables or repository/CI secrets.
