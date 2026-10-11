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

## Test without hitting the real APIs
`orchestrator/test_mock.py` mocks `claude()`/`gemini()`/`post()` so the retry
logic, response parsing, and both the success and Gemini-failure-fallback
paths through `run()` can be checked without network access or burning API
quota:
```bash
python orchestrator/test_mock.py -v
```
This also runs automatically as a CI step before the real API call.

## Important
API keys must never be committed to GitHub. Use local environment variables or repository/CI secrets.
