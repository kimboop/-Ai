#!/usr/bin/env python3
"""Pexels/Edge-TTS 네트워크 호출을 모킹한 단위 테스트.

이 샌드박스처럼 외부 네트워크(Pexels API, Edge-TTS 웹소켓)가 막힌 환경에서도
자막 카드·타이틀 카드 렌더링, 배경 크롭/루프, 캐싱·재시도 경계, 최종 합성
구조가 깨지지 않는지 확인하는 용도다. 실제 Pexels/edge-tts 호출이 라이브로
도는지는 여기서 검증하지 않는다 — 그건 네트워크 제약이 없는 환경에서
scripts/test_run.py로 확인한다 (README의 "실가동 검증" 절 참고).

Usage:
    python scripts/test_mock.py
    python scripts/test_mock.py -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_generator as vg  # noqa: E402

try:
    from moviepy import AudioClip, ColorClip
    DEPS_AVAILABLE = True
    _import_error = None
except ImportError as e:  # pragma: no cover - environment-dependent
    DEPS_AVAILABLE = False
    _import_error = e

_needs_media_deps = unittest.skipUnless(
    DEPS_AVAILABLE, f"moviepy not installed — run: pip install -r scripts/requirements.txt ({_import_error})"
)


def _make_fake_video(path: Path, duration: float = 0.5, size: tuple = (640, 360), fps: int = 10) -> None:
    """Pexels 다운로드 대신 로컬에서 즉시 만드는 자리표시자 클립."""
    ColorClip(size=size, color=(40, 80, 120)).with_duration(duration).write_videofile(
        str(path), fps=fps, codec="libx264", audio=False, preset="ultrafast", logger=None,
    )


def _make_fake_audio(path: Path, duration: float = 1.0) -> None:
    """Edge-TTS 합성 대신 로컬에서 즉시 만드는 무음 내레이션."""
    AudioClip(lambda t: 0.0, duration=duration, fps=22050).write_audiofile(str(path), logger=None)


# --------------------------------------------------------------------------
# 순수 로직 — moviepy/네트워크 없이 바로 검증 가능
# --------------------------------------------------------------------------
class PickVideoFileTests(unittest.TestCase):
    def test_prefers_portrait_closest_to_1080(self):
        files = [
            {"width": 1920, "height": 1080, "link": "landscape"},
            {"width": 720, "height": 1280, "link": "portrait-small"},
            {"width": 1080, "height": 1920, "link": "portrait-exact"},
        ]
        self.assertEqual(vg.pick_video_file(files), "portrait-exact")

    def test_falls_back_to_any_file_when_no_portrait(self):
        files = [{"width": 1920, "height": 1080, "link": "only-option"}]
        self.assertEqual(vg.pick_video_file(files), "only-option")

    def test_raises_on_empty_video_files(self):
        # Pexels can return a video entry with no encodes yet (still transcoding);
        # this must raise so the caller's except-block triggers the ColorClip
        # fallback, instead of an unhandled IndexError.
        with self.assertRaises(ValueError):
            vg.pick_video_file([])


class ValidateEpisodeTests(unittest.TestCase):
    def test_rejects_empty_scenes(self):
        with self.assertRaises(ValueError):
            vg.validate_episode({"scenes": []})

    def test_rejects_blank_script(self):
        with self.assertRaises(ValueError):
            vg.validate_episode({"scenes": [{"script": "   "}]})

    def test_accepts_sample_episode(self):
        vg.validate_episode(vg.SAMPLE_EPISODE)  # raises on failure


# --------------------------------------------------------------------------
# 자막/타이틀 카드 — 실제 PIL 렌더링, 네트워크는 안 씀 (폰트만 필요)
# --------------------------------------------------------------------------
@_needs_media_deps
class SubtitleAndTitleCardTests(unittest.TestCase):
    def setUp(self):
        try:
            self.subtitle_font = vg.resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")
            self.title_font = vg.resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")
        except FileNotFoundError as e:
            self.skipTest(str(e))

    def test_subtitle_card_is_full_canvas_rgba(self):
        img = vg.create_subtitle_image("자막 렌더링 테스트 문장입니다", self.subtitle_font)
        self.assertEqual(img.size, vg.TARGET_SIZE)
        self.assertEqual(img.mode, "RGBA")

    def test_title_card_is_full_canvas_rgba(self):
        img = vg.create_title_image("타이틀 테스트", self.title_font)
        self.assertEqual(img.size, vg.TARGET_SIZE)
        self.assertEqual(img.mode, "RGBA")


@_needs_media_deps
class CropToAspectRatioTests(unittest.TestCase):
    def test_landscape_source_crops_to_9_16(self):
        clip = ColorClip(size=(1920, 1080), color=(0, 0, 0)).with_duration(0.2)
        cropped = vg.crop_to_aspect_ratio(clip)
        self.assertEqual(tuple(cropped.size), vg.TARGET_SIZE)


# --------------------------------------------------------------------------
# Pexels 검색/다운로드를 모킹 — 캐싱·재시도 경계 안쪽 로직만 검증
# --------------------------------------------------------------------------
@_needs_media_deps
class FetchBackgroundClipMockedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @patch("video_generator.download_with_retry")
    @patch("video_generator.get_json_with_retry")
    def test_downloads_once_and_reuses_cache(self, mock_search, mock_download):
        mock_search.return_value = {
            "videos": [{"video_files": [{"width": 1080, "height": 1920, "link": "https://example/fake.mp4"}]}]
        }
        mock_download.side_effect = lambda url, dest, **kw: _make_fake_video(dest) or dest

        clip1 = vg.fetch_background_clip("city night vertical", 0.3, {"Authorization": "x"}, self.cache_dir)
        self.assertIsNotNone(clip1)
        self.assertEqual(mock_search.call_count, 1)
        self.assertEqual(mock_download.call_count, 1)

        clip2 = vg.fetch_background_clip("city night vertical", 0.3, {"Authorization": "x"}, self.cache_dir)
        self.assertIsNotNone(clip2)
        self.assertEqual(mock_search.call_count, 1, "캐시가 있으면 Pexels 검색을 다시 호출하면 안 된다")
        self.assertEqual(mock_download.call_count, 1, "캐시가 있으면 다시 다운로드하면 안 된다")

    @patch("video_generator.get_json_with_retry")
    def test_no_results_falls_back_to_none(self, mock_search):
        mock_search.return_value = {"videos": []}
        clip = vg.fetch_background_clip("nonexistent query xyz", 0.3, {"Authorization": "x"}, self.cache_dir)
        self.assertIsNone(clip)  # 호출자가 ColorClip으로 대체해야 함

    @patch("video_generator.get_json_with_retry")
    def test_query_with_spaces_and_korean_is_url_encoded(self, mock_search):
        # 이전에는 f-string으로 그대로 URL에 꽂아 넣어서 스페이스·한글이 들어간
        # 검색어(샘플 매니페스트의 "news studio vertical" 포함)마다 urllib이
        # http.client.InvalidURL을 던졌다 — 모든 씬이 조용히 ColorClip으로만
        # 대체되던 버그. get_json_with_retry에 실제로 넘어가는 URL을 검사해서
        # 재발을 막는다.
        mock_search.return_value = {"videos": []}
        vg.fetch_background_clip("도시 야경 vertical", 0.3, {"Authorization": "x"}, self.cache_dir)
        called_url = mock_search.call_args[0][0]
        self.assertNotIn(" ", called_url)
        self.assertIn("%20", called_url)


# --------------------------------------------------------------------------
# 전체 파이프라인 — Pexels/Edge-TTS를 모킹해서 합성·인코딩 구조를 검증
# --------------------------------------------------------------------------
@_needs_media_deps
class GeneratePremiumShortsMockedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        try:
            vg.resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")
            vg.resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")
        except FileNotFoundError as e:
            self.skipTest(str(e))

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _fake_tts(text, voice, dest, **kw):
        _make_fake_audio(dest, duration=0.6)

    @staticmethod
    def _fake_bg(query, duration, headers, cache_dir):
        return ColorClip(size=vg.TARGET_SIZE, color=(60, 90, 160)).with_duration(duration)

    @patch("video_generator.synthesize_narration")
    @patch("video_generator.fetch_background_clip")
    def test_renders_mp4_without_touching_network(self, mock_fetch_bg, mock_tts):
        mock_tts.side_effect = self._fake_tts
        mock_fetch_bg.side_effect = self._fake_bg

        episode = {
            "title": "모킹 테스트",
            "scenes": [
                {"script": "첫 번째 테스트 문장", "pexels_query": "q1"},
                {"script": "두 번째 테스트 문장", "pexels_query": "q2"},
            ],
        }
        output = self.root / "out.mp4"
        vg.generate_premium_shorts(episode, "dummy-key", "ko-KR-SunHiNeural", output,
                                    self.root / "cache", resume=True, fps=10,
                                    preset="ultrafast", threads=2)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 0)
        mock_tts.assert_called_once()
        self.assertEqual(mock_fetch_bg.call_count, 2)

    @patch("video_generator.synthesize_narration")
    @patch("video_generator.fetch_background_clip")
    def test_resume_skips_narration_when_text_unchanged(self, mock_fetch_bg, mock_tts):
        mock_tts.side_effect = self._fake_tts
        mock_fetch_bg.side_effect = self._fake_bg

        episode = {"title": "재실행 테스트", "scenes": [{"script": "동일한 문장", "pexels_query": "q1"}]}
        work_dir = self.root / "cache"

        vg.generate_premium_shorts(episode, "dummy-key", "ko-KR-SunHiNeural", self.root / "out1.mp4",
                                    work_dir, resume=True, fps=10, preset="ultrafast", threads=2)
        vg.generate_premium_shorts(episode, "dummy-key", "ko-KR-SunHiNeural", self.root / "out2.mp4",
                                    work_dir, resume=True, fps=10, preset="ultrafast", threads=2)

        mock_tts.assert_called_once()  # 두 번째 실행은 캐시된 내레이션을 재사용해야 한다


if __name__ == "__main__":
    unittest.main(verbosity=2)
