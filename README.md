# Channel Toolkit

Tooling for expanding a YouTube channel — analytics, metadata/SEO helpers,
and content-ops scripts built on the YouTube Data API.

## Setup

```
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in your YouTube Data API credentials
```

## Commands

```
pytest          # run tests
ruff check .    # lint
ruff format .   # format
```

See `AGENTS.md` for the multi-agent (Claude Code / Gemini CLI / ChatGPT)
collaboration conventions used in this repo.
