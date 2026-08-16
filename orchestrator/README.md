# AI Collaboration Orchestrator (Instagram Reels)

## Pipeline
1. **Claude (lead)** authors the full Reels production package from the source
   material and flags anything it can't verify itself with
   `[VERIFY-GEMINI: ...]` markers.
2. **Gemini (support)** resolves only those flagged markers via research and
   runs a final QC pass. It does not rewrite Claude's creative/structural
   choices.

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
