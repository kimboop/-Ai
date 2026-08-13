"""Command-line entry point for channel-toolkit."""

from __future__ import annotations

import argparse
import json
import sys

from . import analytics, batch, metadata, thumbnail


def _cmd_collect(args: argparse.Namespace) -> None:
    out = analytics.collect(args.channel_id, out_path=args.out, max_results=args.max_results)
    print(f"Wrote channel + video stats to {out}")


def _cmd_metadata(args: argparse.Namespace) -> None:
    keywords = args.keywords.split(",") if args.keywords else None
    if args.engine == "ai":
        result = metadata.generate_metadata_ai(args.topic, keywords=keywords, model=args.model)
    else:
        result = metadata.generate_metadata(args.topic, keywords=keywords)
    print(
        json.dumps(
            {"title": result.title, "description": result.description, "tags": result.tags},
            ensure_ascii=False,
            indent=2,
        )
    )


def _cmd_thumbnail(args: argparse.Namespace) -> None:
    out = thumbnail.generate_thumbnail(
        args.text,
        args.out,
        background_path=args.background,
        font_size=args.font_size,
        template=args.template,
        logo_path=args.logo,
        logo_position=args.logo_position,
        logo_opacity=args.logo_opacity,
    )
    print(f"Wrote thumbnail to {out}")


def _cmd_batch(args: argparse.Namespace) -> None:
    topics = batch.load_topics(args.topics_file)
    results = batch.run_batch(
        topics,
        out_dir=args.out_dir,
        engine=args.engine,
        model=args.model,
        template=args.template,
        logo_path=args.logo,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="channel-toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    collect_p = sub.add_parser("collect", help="Collect channel + recent video stats")
    collect_p.add_argument("--channel-id", required=True)
    collect_p.add_argument("--out", default="data/channel.json")
    collect_p.add_argument("--max-results", type=int, default=10)
    collect_p.set_defaults(func=_cmd_collect)

    metadata_p = sub.add_parser("metadata", help="Generate title/description/tags for a topic")
    metadata_p.add_argument("--topic", required=True)
    metadata_p.add_argument("--keywords", help="Comma-separated keyword list")
    metadata_p.add_argument("--engine", choices=["template", "ai"], default="template")
    metadata_p.add_argument("--model", default=metadata.DEFAULT_AI_MODEL)
    metadata_p.set_defaults(func=_cmd_metadata)

    thumbnail_p = sub.add_parser("thumbnail", help="Generate a thumbnail image")
    thumbnail_p.add_argument("--text", required=True)
    thumbnail_p.add_argument("--out", default="data/thumbnail.png")
    thumbnail_p.add_argument("--background", default=None)
    thumbnail_p.add_argument("--font-size", type=int, default=96)
    thumbnail_p.add_argument("--template", choices=sorted(thumbnail.TEMPLATES), default="dark")
    thumbnail_p.add_argument("--logo", default=None, help="Path to a logo/watermark image")
    thumbnail_p.add_argument(
        "--logo-position", choices=thumbnail.LOGO_POSITIONS, default="bottom-right"
    )
    thumbnail_p.add_argument("--logo-opacity", type=float, default=1.0)
    thumbnail_p.set_defaults(func=_cmd_thumbnail)

    batch_p = sub.add_parser("batch", help="Generate metadata + thumbnails for a list of topics")
    batch_p.add_argument(
        "--topics-file", required=True, help="JSON file: list of topic strings and/or objects"
    )
    batch_p.add_argument("--out-dir", default="data/batch")
    batch_p.add_argument("--engine", choices=["template", "ai"], default="template")
    batch_p.add_argument("--model", default=metadata.DEFAULT_AI_MODEL)
    batch_p.add_argument("--template", choices=sorted(thumbnail.TEMPLATES), default="dark")
    batch_p.add_argument("--logo", default=None, help="Path to a logo/watermark image")
    batch_p.set_defaults(func=_cmd_batch)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
