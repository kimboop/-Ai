# Channel Toolkit

Tooling for expanding a YouTube channel — analytics, metadata/SEO helpers,
and content-ops scripts built on the YouTube Data API.

## Setup

```
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in your YouTube Data API credentials
```

## Usage

```
# Collect channel + recent video stats (requires YOUTUBE_API_KEY)
channel-toolkit collect --channel-id UCxxxxxxxxxxxxxxxxxxxxxx --out data/channel.json

# Generate a title / description / tags for a topic (no API key needed)
channel-toolkit metadata --topic "파이썬 자동화" --keywords "유튜브,채널성장"

# Generate a 1280x720 thumbnail with wrapped, centered title text
channel-toolkit thumbnail --text "파이썬으로 유튜브 채널 자동화하기" --out data/thumbnail.png
```

`metadata` is template-based today (no external API call) so it works out
of the box — see `src/channel_toolkit/metadata.py` for the templates, or
swap in an LLM-backed generator later without changing the CLI or callers.

`thumbnail` bundles [Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR)
(OFL-licensed, see `src/channel_toolkit/assets/fonts/OFL.txt`) so Korean
titles render correctly by default; pass `--background`/`font-size` or use
the module's `font_path` argument to customize.

## Dev commands

```
pytest          # run tests
ruff check .    # lint
ruff format .   # format
```

See `AGENTS.md` for the multi-agent (Claude Code / Gemini CLI / ChatGPT)
collaboration conventions used in this repo.
