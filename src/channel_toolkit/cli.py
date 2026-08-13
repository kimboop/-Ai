"""Command-line entry point for channel-toolkit."""

from __future__ import annotations

import argparse
import json
import sys

from . import analytics, metadata, thumbnail


def _cmd_collect(args: argparse.Namespace) -> None:
    out = analytics.collect(args.channel_id, out_path=args.out, max_results=args.max_results)
    print(f"Wrote channel + video stats to {out}")


def _cmd_metadata(args: argparse.Namespace) -> None:
    keywords = args.keywords.split(",") if args.keywords else None
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
    )
    print(f"Wrote thumbnail to {out}")


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
    metadata_p.set_defaults(func=_cmd_metadata)

    thumbnail_p = sub.add_parser("thumbnail", help="Generate a thumbnail image")
    thumbnail_p.add_argument("--text", required=True)
    thumbnail_p.add_argument("--out", default="data/thumbnail.png")
    thumbnail_p.add_argument("--background", default=None)
    thumbnail_p.add_argument("--font-size", type=int, default=96)
    thumbnail_p.set_defaults(func=_cmd_thumbnail)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
