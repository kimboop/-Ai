# AI Collaboration Orchestrator

## Pipeline
1. Gemini audits research/evidence against `input.md`.
2. Claude reconciles Gemini's audit with the source material and produces the
   final production package.
3. ChatGPT (optional) red-teams the final package and writes platform-specific
   distribution copy (hooks, titles, captions, CTAs) to
   `artifacts/03-chatgpt-distribution.md`. Skipped when `OPENAI_API_KEY` is
   unset; a failure here only logs a warning and never discards stage 2.

## Required environment variables
- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`

Optional:
- `OPENAI_API_KEY` (enables the ChatGPT stage)
- `GEMINI_MODEL`
- `GEMINI_FALLBACK_MODELS` (comma-separated, default
  `gemini-3.5-flash,gemini-3.5-flash-lite`): tried in order when
  `GEMINI_MODEL` exhausts its retries on 503/429/5xx/timeouts or returns 404.
- `CLAUDE_MODEL`
- `OPENAI_MODEL` (default `gpt-5`)

## Run
```bash
python orchestrator/ai_collaboration.py input.md
```

Outputs are written to `artifacts/`.

## Important
API keys must never be committed to GitHub. Use local environment variables or repository/CI secrets.
