"""Generate SEO-oriented video metadata (title, description, tags) from a topic.

Two engines share the same `VideoMetadata` shape, so callers can switch
between them without touching anything downstream:

- `generate_metadata()` — template-based, no external API, works offline.
- `generate_metadata_ai()` — Claude-API-backed, needs `pip install -e ".[ai]"`
  and an `ANTHROPIC_API_KEY`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

TITLE_MAX_LEN = 70  # YouTube truncates titles beyond ~70 chars in search results
DEFAULT_AI_MODEL = "claude-sonnet-5"

DEFAULT_HOOKS = [
    "{topic} 완벽 정리",
    "{topic}, 이것만 알면 끝",
    "몰랐다면 손해보는 {topic}",
]


@dataclass
class VideoMetadata:
    title: str
    description: str
    tags: list[str]


def _slugify_words(text: str) -> list[str]:
    return [w for w in re.split(r"[^0-9A-Za-z가-힣]+", text) if w]


def generate_title(topic: str, hook: str | None = None) -> str:
    hook = hook or DEFAULT_HOOKS[0]
    return hook.format(topic=topic)[:TITLE_MAX_LEN]


def generate_description(
    topic: str, keywords: list[str] | None = None, cta: str | None = None
) -> str:
    keywords = keywords or []
    cta = cta or "구독과 좋아요는 채널 성장에 큰 힘이 됩니다!"

    lines = [f"이번 영상에서는 '{topic}'에 대해 다룹니다.", ""]
    if keywords:
        lines.append("관련 키워드: " + ", ".join(keywords))
        lines.append("")
    lines.append(cta)
    return "\n".join(lines)


def generate_tags(
    topic: str, keywords: list[str] | None = None, extra: list[str] | None = None
) -> list[str]:
    keywords = keywords or []
    extra = extra or []
    phrases = [topic, *keywords, *extra]
    words = [w for phrase in phrases for w in _slugify_words(phrase)]

    tags: list[str] = []
    seen: set[str] = set()
    for tag in [*phrases, *words]:
        key = tag.lower()
        if tag and key not in seen:
            seen.add(key)
            tags.append(tag)
    return tags


def generate_metadata(
    topic: str,
    keywords: list[str] | None = None,
    hook: str | None = None,
    cta: str | None = None,
) -> VideoMetadata:
    return VideoMetadata(
        title=generate_title(topic, hook=hook),
        description=generate_description(topic, keywords=keywords, cta=cta),
        tags=generate_tags(topic, keywords=keywords),
    )


def _extract_json(text: str) -> str:
    """Pull the first {...} object out of a response, tolerating any prose
    the model adds around it despite being asked for JSON-only output."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in model response: {text!r}")
    return text[start : end + 1]


def generate_metadata_ai(
    topic: str,
    keywords: list[str] | None = None,
    model: str = DEFAULT_AI_MODEL,
    api_key: str | None = None,
) -> VideoMetadata:
    """AI-backed metadata generation using the Claude API.

    Requires the `anthropic` package (`pip install -e ".[ai]"`) and an API
    key, either passed directly or via the `ANTHROPIC_API_KEY` env var.
    Raises rather than silently falling back to `generate_metadata()` —
    callers that want a fallback should catch the error themselves.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "The 'anthropic' package is required for AI-backed metadata generation. "
            'Install it with: pip install -e ".[ai]"'
        ) from exc

    client = anthropic.Anthropic(api_key=api_key)
    keyword_line = f"\n관련 키워드: {', '.join(keywords)}" if keywords else ""
    prompt = (
        "다음 유튜브 영상 주제에 대해 클릭을 유도하면서도 과장되지 않은 "
        f"제목({TITLE_MAX_LEN}자 이내), 설명(3~5문장, 구독 유도 문구 포함), "
        "태그(5~10개, 검색 키워드) 를 JSON으로만 응답하세요. "
        '형식: {"title": "...", "description": "...", "tags": ["...", "..."]}\n\n'
        f"주제: {topic}{keyword_line}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    data = json.loads(_extract_json(raw_text))
    return VideoMetadata(
        title=data["title"][:TITLE_MAX_LEN],
        description=data["description"],
        tags=list(data.get("tags", [])),
    )
