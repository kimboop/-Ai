from unittest.mock import MagicMock, patch

import pytest

from channel_toolkit import analytics


def _fake_youtube_client(channel_items, search_items, video_items):
    youtube = MagicMock()
    youtube.channels.return_value.list.return_value.execute.return_value = {"items": channel_items}
    youtube.search.return_value.list.return_value.execute.return_value = {"items": search_items}
    youtube.videos.return_value.list.return_value.execute.return_value = {"items": video_items}
    return youtube


@patch("channel_toolkit.analytics.build")
def test_fetch_channel_stats_parses_response(mock_build):
    mock_build.return_value = _fake_youtube_client(
        channel_items=[
            {
                "snippet": {"title": "Test Channel"},
                "statistics": {
                    "subscriberCount": "1000",
                    "viewCount": "50000",
                    "videoCount": "42",
                },
            }
        ],
        search_items=[],
        video_items=[],
    )

    result = analytics.fetch_channel_stats("UC123", api_key="fake-key")

    assert result.title == "Test Channel"
    assert result.subscriber_count == 1000
    assert result.view_count == 50000
    assert result.video_count == 42


@patch("channel_toolkit.analytics.build")
def test_fetch_recent_videos_parses_response(mock_build):
    mock_build.return_value = _fake_youtube_client(
        channel_items=[],
        search_items=[{"id": {"videoId": "vid1"}}],
        video_items=[
            {
                "id": "vid1",
                "snippet": {"title": "My Video", "publishedAt": "2026-01-01T00:00:00Z"},
                "statistics": {"viewCount": "10", "likeCount": "2", "commentCount": "1"},
            }
        ],
    )

    result = analytics.fetch_recent_videos("UC123", api_key="fake-key")

    assert len(result) == 1
    assert result[0].video_id == "vid1"
    assert result[0].view_count == 10


def test_fetch_channel_stats_requires_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="YOUTUBE_API_KEY"):
        analytics.fetch_channel_stats("UC123", api_key=None)
