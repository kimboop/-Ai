# Channel Toolkit

Tooling for expanding a YouTube channel — analytics, metadata/SEO helpers,
and content-ops scripts built on the YouTube Data API.

## Setup

```
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # add ",ai" for the Claude-API metadata engine
cp .env.example .env           # fill in your YouTube Data API credentials
```

## Usage

```
# Collect channel + recent video stats (requires YOUTUBE_API_KEY)
channel-toolkit collect --channel-id UCxxxxxxxxxxxxxxxxxxxxxx --out data/channel.json

# Generate a title / description / tags for a topic (no API key needed)
channel-toolkit metadata --topic "파이썬 자동화" --keywords "유튜브,채널성장"

# Same, but AI-backed via the Claude API (needs `pip install -e ".[ai]"`
# and ANTHROPIC_API_KEY)
channel-toolkit metadata --topic "파이썬 자동화" --engine ai

# Generate a 1280x720 thumbnail with wrapped, centered title text
channel-toolkit thumbnail --text "파이썬으로 유튜브 채널 자동화하기" --out data/thumbnail.png

# ...with a gradient template and a logo watermark
channel-toolkit thumbnail --text "쇼츠로 채널 키우기" --template ocean \
  --logo assets/logo.png --logo-position bottom-right --out data/thumbnail.png

# Batch: metadata + thumbnail for every topic in a JSON file, one folder each
channel-toolkit batch --topics-file topics.json --out-dir data/batch --template sunset
```

`topics.json` is a list of topic strings and/or objects that can override
any batch-level default per topic:

```json
["파이썬으로 유튜브 자동화하기", {"topic": "쇼츠로 채널 키우기", "keywords": ["쇼츠"], "template": "ocean"}]
```

`metadata` defaults to a template engine (no external API call, works out
of the box) — see `src/channel_toolkit/metadata.py` for the templates.
Pass `--engine ai` to generate via the Claude API instead; both engines
return the same shape so nothing downstream needs to change.

`thumbnail` templates: `dark`, `sunset`, `ocean`, `minimal-light` (see
`TEMPLATES` in `src/channel_toolkit/thumbnail.py` to add more). It bundles
[Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR)
(OFL-licensed, see `src/channel_toolkit/assets/fonts/OFL.txt`) so Korean
titles render correctly by default; pass `--background`/`--font-size` or
use the module's `font_path` argument to customize further.

## Dev commands

```
pytest          # run tests
ruff check .    # lint
ruff format .   # format
```

See `AGENTS.md` for the multi-agent (Claude Code / Gemini CLI / ChatGPT)
collaboration conventions used in this repo.
