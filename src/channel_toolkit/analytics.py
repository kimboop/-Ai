"""Collect channel and video statistics from the YouTube Data API v3."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()


@dataclass
class ChannelStats:
    channel_id: str
    title: str
    subscriber_count: int
    view_count: int
    video_count: int


@dataclass
class VideoStats:
    video_id: str
    title: str
    published_at: str
    view_count: int
    like_count: int
    comment_count: int


def _client(api_key: str | None = None):
    api_key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is not set. Add it to .env (see .env.example).")
    return build("youtube", "v3", developerKey=api_key)


def fetch_channel_stats(channel_id: str, api_key: str | None = None) -> ChannelStats:
    youtube = _client(api_key)
    response = youtube.channels().list(part="snippet,statistics", id=channel_id).execute()
    items = response.get("items", [])
    if not items:
        raise ValueError(f"No channel found for id={channel_id!r}")
    item = items[0]
    stats = item["statistics"]
    return ChannelStats(
        channel_id=channel_id,
        title=item["snippet"]["title"],
        subscriber_count=int(stats.get("subscriberCount", 0)),
        view_count=int(stats.get("viewCount", 0)),
        video_count=int(stats.get("videoCount", 0)),
    )


def fetch_recent_videos(
    channel_id: str, max_results: int = 10, api_key: str | None = None
) -> list[VideoStats]:
    youtube = _client(api_key)

    search_response = (
        youtube.search()
        .list(
            part="id",
            channelId=channel_id,
            order="date",
            type="video",
            maxResults=max_results,
        )
        .execute()
    )
    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
    if not video_ids:
        return []

    videos_response = (
        youtube.videos().list(part="snippet,statistics", id=",".join(video_ids)).execute()
    )

    results = []
    for item in videos_response.get("items", []):
        stats = item.get("statistics", {})
        results.append(
            VideoStats(
                video_id=item["id"],
                title=item["snippet"]["title"],
                published_at=item["snippet"]["publishedAt"],
                view_count=int(stats.get("viewCount", 0)),
                like_count=int(stats.get("likeCount", 0)),
                comment_count=int(stats.get("commentCount", 0)),
            )
        )
    return results


def collect(
    channel_id: str,
    out_path: str | Path = "data/channel.json",
    max_results: int = 10,
    api_key: str | None = None,
) -> Path:
    """Fetch channel + recent video stats and write them to a JSON file."""
    channel = fetch_channel_stats(channel_id, api_key=api_key)
    videos = fetch_recent_videos(channel_id, max_results=max_results, api_key=api_key)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"channel": asdict(channel), "videos": [asdict(v) for v in videos]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out_path
