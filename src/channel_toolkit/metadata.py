"""Generate SEO-oriented video metadata (title, description, tags) from a topic.

Template-based for now (no external API dependency, works offline). Swap
`generate_title`/`generate_description` for an LLM-backed implementation
later without touching callers — the return shape (`VideoMetadata`) stays
the same.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TITLE_MAX_LEN = 70  # YouTube truncates titles beyond ~70 chars in search results

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
