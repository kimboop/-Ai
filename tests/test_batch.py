import json
from pathlib import Path

from channel_toolkit import batch


def test_load_topics_handles_strings_and_objects(tmp_path):
    topics_file = tmp_path / "topics.json"
    topics_file.write_text(
        json.dumps(["파이썬 기초", {"topic": "유튜브 SEO", "keywords": ["seo", "썸네일"]}]),
        encoding="utf-8",
    )

    topics = batch.load_topics(topics_file)

    assert topics[0].topic == "파이썬 기초"
    assert topics[1].topic == "유튜브 SEO"
    assert topics[1].keywords == ["seo", "썸네일"]


def test_run_batch_generates_metadata_and_thumbnail_per_topic(tmp_path):
    topics = [batch.BatchTopic(topic="파이썬 자동화"), batch.BatchTopic(topic="유튜브 성장 전략")]

    results = batch.run_batch(topics, out_dir=tmp_path)

    assert len(results) == 2
    for result in results:
        video_dir = Path(result["dir"])
        assert (video_dir / "metadata.json").exists()
        assert (video_dir / "thumbnail.png").exists()


def test_run_batch_lets_topic_override_batch_defaults(tmp_path):
    topics = [batch.BatchTopic(topic="파이썬 자동화", template="ocean")]

    results = batch.run_batch(topics, out_dir=tmp_path, template="dark")

    video_dir = Path(results[0]["dir"])
    assert (video_dir / "thumbnail.png").exists()
