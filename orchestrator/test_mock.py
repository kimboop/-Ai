#!/usr/bin/env python3
"""Claude/Gemini API 호출을 모킹한 단위 테스트.

실제 네트워크(Anthropic/Gemini API)를 쓰지 않고 재시도/백오프 로직, 응답 파싱,
그리고 무엇보다 지금까지 실제 CI에서 한 번도 성공한 적이 없는 "Gemini 지원
패스가 성공하는 경우"의 코드 경로를 검증한다. Gemini 무료 티어 쿼터가 소진된
상태에서도 파이프라인 로직 자체가 맞는지 확인하는 용도다 — 실제 라이브 API
호출 여부는 여기서 검증하지 않는다 (그건 GitHub Actions에서 실제 키로 확인).

Usage:
    python orchestrator/test_mock.py
    python orchestrator/test_mock.py -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_collaboration as ac  # noqa: E402


# --------------------------------------------------------------------------
# post() 재시도/백오프 — 일시적 오류(429/503)만 재시도하고, 그 외는 즉시 올림
# --------------------------------------------------------------------------
class PostRetryTests(unittest.TestCase):
    @staticmethod
    def _http_error(code, msg="error"):
        return urllib.error.HTTPError("https://example/api", code, msg, None, None)

    @patch("ai_collaboration.time.sleep")
    @patch("ai_collaboration.urllib.request.urlopen")
    def test_retries_on_429_then_succeeds(self, mock_urlopen, mock_sleep):
        ok_response = unittest.mock.MagicMock()
        ok_response.read.return_value = b'{"ok": true}'
        ok_response.__enter__.return_value = ok_response
        mock_urlopen.side_effect = [self._http_error(429), ok_response]

        result = ac.post("https://example/api", {}, {})

        self.assertEqual(result, {"ok": True})
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("ai_collaboration.time.sleep")
    @patch("ai_collaboration.urllib.request.urlopen")
    def test_gives_up_after_exhausting_retries(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = self._http_error(503)

        with self.assertRaises(urllib.error.HTTPError):
            ac.post("https://example/api", {}, {}, retries=3, backoff=1)

        self.assertEqual(mock_urlopen.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # retries-1

    @patch("ai_collaboration.time.sleep")
    @patch("ai_collaboration.urllib.request.urlopen")
    def test_non_retryable_status_raises_immediately(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = self._http_error(400, "bad request")

        with self.assertRaises(urllib.error.HTTPError):
            ac.post("https://example/api", {}, {}, retries=4, backoff=1)

        self.assertEqual(mock_urlopen.call_count, 1, "400 is not retryable, must not retry")
        mock_sleep.assert_not_called()


# --------------------------------------------------------------------------
# claude()/gemini() 응답 파싱 — 각 API 고유의 JSON 모양을 올바르게 추출하는지
# --------------------------------------------------------------------------
class ResponseParsingTests(unittest.TestCase):
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"})
    @patch("ai_collaboration.post")
    def test_claude_extracts_only_text_blocks(self, mock_post):
        mock_post.return_value = {
            "content": [
                {"type": "text", "text": "hello "},
                {"type": "tool_use", "text": "should be ignored"},
                {"type": "text", "text": "world"},
            ]
        }
        self.assertEqual(ac.claude("prompt"), "hello \nworld")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    @patch("ai_collaboration.post")
    def test_gemini_extracts_first_candidate_text(self, mock_post):
        mock_post.return_value = {
            "candidates": [{"content": {"parts": [{"text": "gemini said this"}]}}]
        }
        self.assertEqual(ac.gemini("prompt"), "gemini said this")


# --------------------------------------------------------------------------
# run() 전체 파이프라인 — Claude/Gemini 둘 다 모킹, 네트워크 없이 바로 검증
# --------------------------------------------------------------------------
class RunPipelineMockedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.tmp.name) / "artifacts"
        self.input_path = Path(self.tmp.name) / "input.md"
        self.input_path.write_text("소스 자료 본문", encoding="utf-8")
        self._out_patch = patch("ai_collaboration.OUT", self.out_dir)
        self._out_patch.start()

    def tearDown(self):
        self._out_patch.stop()
        self.tmp.cleanup()

    @patch("ai_collaboration.gemini")
    @patch("ai_collaboration.claude")
    def test_gemini_success_resolves_markers_and_writes_both_files(self, mock_claude, mock_gemini):
        # 지금까지 실제 CI에서 한 번도 타보지 못한 경로: Gemini 지원 패스가
        # 성공해서 최종 산출물까지 정상적으로 써지는 경우.
        mock_claude.return_value = "draft with [VERIFY-GEMINI: trending audio name]"
        mock_gemini.return_value = "final package, marker resolved\n\nQC & Supplement Notes: ..."

        ac.run(self.input_path)

        draft = (self.out_dir / "01-claude-lead-draft.md").read_text(encoding="utf-8")
        final = (self.out_dir / "02-final-reels-package.md").read_text(encoding="utf-8")
        self.assertIn("VERIFY-GEMINI", draft)
        self.assertEqual(final, mock_gemini.return_value)
        self.assertNotIn("GEMINI SUPPORT PASS UNAVAILABLE", final)

    @patch("ai_collaboration.gemini")
    @patch("ai_collaboration.claude")
    def test_gemini_failure_falls_back_without_losing_claude_draft(self, mock_claude, mock_gemini):
        mock_claude.return_value = "draft with [VERIFY-GEMINI: trending audio name]"
        mock_gemini.side_effect = urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com/x", 429, "Too Many Requests", None, None
        )

        with self.assertRaises(urllib.error.HTTPError):
            ac.run(self.input_path)

        draft = (self.out_dir / "01-claude-lead-draft.md").read_text(encoding="utf-8")
        fallback = (self.out_dir / "02-final-reels-package.md").read_text(encoding="utf-8")
        self.assertIn("VERIFY-GEMINI", draft)
        self.assertIn("GEMINI SUPPORT PASS UNAVAILABLE", fallback)
        self.assertIn(mock_claude.return_value, fallback)
        self.assertIn("429", fallback)


if __name__ == "__main__":
    unittest.main(verbosity=2)
