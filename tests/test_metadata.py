import json
import sys
import types
from unittest.mock import MagicMock

import pytest

from channel_toolkit.metadata import (
    generate_metadata,
    generate_metadata_ai,
    generate_tags,
    generate_title,
)


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


def test_generate_metadata_ai_parses_model_response(monkeypatch):
    fake_block = types.SimpleNamespace(
        type="text",
        text=json.dumps(
            {
                "title": "AI가 만든 제목",
                "description": "AI가 만든 설명입니다.",
                "tags": ["태그1", "태그2"],
            }
        ),
    )
    fake_response = types.SimpleNamespace(content=[fake_block])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    fake_anthropic_module = types.SimpleNamespace(Anthropic=lambda api_key=None: fake_client)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    result = generate_metadata_ai("파이썬 자동화", keywords=["유튜브"])

    assert result.title == "AI가 만든 제목"
    assert result.tags == ["태그1", "태그2"]


def test_generate_metadata_ai_tolerates_prose_around_json(monkeypatch):
    fake_block = types.SimpleNamespace(
        type="text",
        text='물론이죠! {"title": "T", "description": "D", "tags": []} 도움이 되었길 바라요.',
    )
    fake_response = types.SimpleNamespace(content=[fake_block])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    fake_anthropic_module = types.SimpleNamespace(Anthropic=lambda api_key=None: fake_client)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    result = generate_metadata_ai("주제")

    assert result.title == "T"


def test_generate_metadata_ai_requires_anthropic_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(RuntimeError, match="anthropic"):
        generate_metadata_ai("주제")
