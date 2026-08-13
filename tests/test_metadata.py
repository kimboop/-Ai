from channel_toolkit.metadata import generate_metadata, generate_tags, generate_title


def test_generate_title_respects_max_length():
    title = generate_title("아주 긴 주제 " * 20)
    assert len(title) <= 70


def test_generate_metadata_includes_keywords_in_tags():
    result = generate_metadata("파이썬 자동화", keywords=["유튜브", "채널 성장"])
    assert "파이썬 자동화" in result.tags
    assert "유튜브" in result.tags
    assert "채널 성장" in result.tags
    assert "파이썬 자동화" in result.description


def test_generate_tags_dedupes_case_insensitively():
    tags = generate_tags("Python", keywords=["python", "PYTHON tips"])
    assert tags.count("Python") == 1
    assert "PYTHON tips" in tags
