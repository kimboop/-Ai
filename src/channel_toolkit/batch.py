"""Batch-generate metadata + thumbnails for a list of video topics."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from . import metadata as metadata_mod
from . import thumbnail as thumbnail_mod


@dataclass
class BatchTopic:
    topic: str
    keywords: list[str] | None = None
    hook: str | None = None
    cta: str | None = None
    background: str | None = None
    template: str | None = None
    logo: str | None = None
    engine: str | None = None
    model: str | None = None


def load_topics(path: str | Path) -> list[BatchTopic]:
    """Load topics from a JSON file: a list of strings and/or objects, e.g.

    ["주제1", {"topic": "주제2", "keywords": ["a", "b"], "template": "ocean"}]
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        BatchTopic(topic=entry) if isinstance(entry, str) else BatchTopic(**entry) for entry in data
    ]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", text).strip("-")
    return slug or "video"


def run_batch(
    topics: list[BatchTopic],
    out_dir: str | Path,
    engine: str = "template",
    model: str = metadata_mod.DEFAULT_AI_MODEL,
    template: str = "dark",
    logo_path: str | Path | None = None,
) -> list[dict]:
    """Generate metadata.json + thumbnail.png per topic under out_dir/<slug>/.

    Per-topic fields (engine, model, template, logo, ...) override these
    batch-level defaults.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for item in topics:
        video_dir = out_dir / _slugify(item.topic)
        video_dir.mkdir(parents=True, exist_ok=True)

        if (item.engine or engine) == "ai":
            meta = metadata_mod.generate_metadata_ai(
                item.topic, keywords=item.keywords, model=item.model or model
            )
        else:
            meta = metadata_mod.generate_metadata(
                item.topic, keywords=item.keywords, hook=item.hook, cta=item.cta
            )

        (video_dir / "metadata.json").write_text(
            json.dumps(asdict(meta), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        thumbnail_mod.generate_thumbnail(
            meta.title,
            video_dir / "thumbnail.png",
            background_path=item.background,
            template=item.template or template,
            logo_path=item.logo or logo_path,
        )

        results.append({"topic": item.topic, "dir": str(video_dir), "title": meta.title})
    return results
