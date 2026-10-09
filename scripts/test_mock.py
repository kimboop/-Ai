#!/usr/bin/env python3
"""Pixabay/Edge-TTS 네트워크 호출을 모킹한 단위 테스트.

이 샌드박스처럼 외부 네트워크(Pixabay API, Edge-TTS 웹소켓)가 막힌 환경에서도
자막 카드·타이틀 카드 렌더링, 배경 크롭/루프, 캐싱·재시도 경계, 최종 합성
구조가 깨지지 않는지 확인하는 용도다. 실제 Pixabay/edge-tts 호출이 라이브로
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
    """Pixabay 다운로드 대신 로컬에서 즉시 만드는 자리표시자 클립."""
    ColorClip(size=size, color=(40, 80, 120)).with_duration(duration).write_videofile(
        str(path), fps=fps, codec="libx264", audio=False, preset="ultrafast", logger=None,
    )


def _make_fake_audio(path: Path, duration: float = 1.0) -> None:
    """Edge-TTS 합성 대신 로컬에서 즉시 만드는 무음 내레이션."""
    AudioClip(lambda t: 0.0, duration=duration, fps=22050).write_audiofile(str(path), logger=None)


# --------------------------------------------------------------------------
# 순수 로직 — moviepy/네트워크 없이 바로 검증 가능
# --------------------------------------------------------------------------
class PickPixabayVideoFileTests(unittest.TestCase):
    def test_prefers_medium_quality(self):
        videos = {
            "large": {"url": "large-url", "width": 1920, "height": 1080},
            "medium": {"url": "medium-url", "width": 1280, "height": 720},
            "small": {"url": "small-url", "width": 960, "height": 540},
        }
        self.assertEqual(vg.pick_pixabay_video_file(videos), "medium-url")

    def test_falls_back_to_large_when_no_medium(self):
        videos = {"large": {"url": "only-option", "width": 1920, "height": 1080}}
        self.assertEqual(vg.pick_pixabay_video_file(videos), "only-option")

    def test_raises_on_empty_videos(self):
        # Pixabay can in principle return a hit with no renditions; this must
        # raise so the caller's except-block triggers the ColorClip fallback,
        # instead of an unhandled KeyError/IndexError.
        with self.assertRaises(ValueError):
            vg.pick_pixabay_video_file({})


class ComputeSceneStartsTests(unittest.TestCase):
    """compute_scene_starts()는 word-boundary 타이밍을 못 구했을 때 쓰는
    균등-분할 폴백이다 (generate_premium_shorts 참고) — 정상 경로는
    LocateSceneStartsFromWordEventsTests가 검증한다."""

    def test_unequal_durations_produce_cumulative_offsets(self):
        self.assertEqual(vg.compute_scene_starts([1.0, 2.5, 0.5]), [0.0, 1.0, 3.5])

    def test_equal_durations_matches_old_even_split_behavior(self):
        self.assertEqual(vg.compute_scene_starts([2.0, 2.0, 2.0]), [0.0, 2.0, 4.0])

    def test_single_scene_starts_at_zero(self):
        self.assertEqual(vg.compute_scene_starts([3.3]), [0.0])

    def test_empty_list(self):
        self.assertEqual(vg.compute_scene_starts([]), [])


class ComputeSceneCharOffsetsTests(unittest.TestCase):
    def test_offsets_account_for_join_space(self):
        # generate_premium_shorts()가 " ".join(...)으로 전체 내레이션 텍스트를
        # 만들므로, 오프셋도 그 스페이스 1칸을 반드시 반영해야 locate_scene_
        # starts_from_word_events()의 문자 위치 매칭이 맞아떨어진다.
        self.assertEqual(vg.compute_scene_char_offsets(["안녕", "반가워요"]), [0, 3])

    def test_single_scene(self):
        self.assertEqual(vg.compute_scene_char_offsets(["하나"]), [0])

    def test_empty_list(self):
        self.assertEqual(vg.compute_scene_char_offsets([]), [])


class LocateSceneStartsFromWordEventsTests(unittest.TestCase):
    def test_matches_word_positions_to_scene_boundaries(self):
        scripts = ["첫 문장 입니다", "두번째 문장 입니다"]
        full_text = " ".join(scripts)
        scene_char_starts = vg.compute_scene_char_offsets(scripts)
        word_events = [
            ("첫", 0.0), ("문장", 0.3), ("입니다", 0.6),
            ("두번째", 1.0), ("문장", 1.3), ("입니다", 1.6),
        ]
        starts = vg.locate_scene_starts_from_word_events(full_text, scene_char_starts, word_events)
        self.assertEqual(starts, [0.0, 1.0])

    def test_handles_repeated_words_via_sequential_search(self):
        # "문장"과 "입니다"가 두 씬 모두에 등장한다 — 첫 번째 발생 위치에
        # 멈추지 않고 순서대로 다음 발생을 찾아가야 한다.
        scripts = ["문장 입니다", "문장 입니다"]
        full_text = " ".join(scripts)
        scene_char_starts = vg.compute_scene_char_offsets(scripts)
        word_events = [("문장", 0.0), ("입니다", 0.4), ("문장", 0.9), ("입니다", 1.3)]
        starts = vg.locate_scene_starts_from_word_events(full_text, scene_char_starts, word_events)
        self.assertEqual(starts, [0.0, 0.9])

    def test_returns_none_when_events_empty(self):
        self.assertIsNone(vg.locate_scene_starts_from_word_events("텍스트", [0], []))

    def test_returns_none_when_word_not_found_in_text(self):
        # edge-tts가 예상과 다른 텍스트를 돌려주는 상황 — 억지로 맞추지 않고
        # None을 돌려줘서 호출자가 균등 분할로 안전하게 폴백하게 한다.
        starts = vg.locate_scene_starts_from_word_events("안녕하세요", [0], [("없는단어", 0.0)])
        self.assertIsNone(starts)


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


# --------------------------------------------------------------------------
# 썸네일 — 긴 한 줄 제목이 캔버스 밖으로 잘리던 버그의 회귀 테스트
# --------------------------------------------------------------------------
@_needs_media_deps
class ThumbnailHeadlineFitTests(unittest.TestCase):
    def setUp(self):
        try:
            self.font_extrabold = vg.resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")
            self.font_bold = vg.resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")
        except FileNotFoundError as e:
            self.skipTest(str(e))
        import make_thumbnail as mt
        self.mt = mt

    def test_long_single_line_title_wraps_within_canvas_width(self):
        # render-shorts.yml는 episode.json의 title을 \n 없이 그대로 넘긴다 —
        # 줄바꿈 없는 긴 한 줄을 그대로 그려서 좌우로 잘리던 실제 버그 재현.
        from PIL import Image, ImageDraw
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        title = "테슬라와 보스턴 다이내믹스가 벌이는 인간형 로봇 배터리 기술 경쟁의 모든 것"
        font, lines, _ = self.mt._fit_headline(draw, title, self.font_extrabold, max_width=1080 - 2 * 70)
        self.assertGreater(len(lines), 1, "wrapping should split a long single-line title")
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            self.assertLessEqual(bbox[2] - bbox[0], 1080 - 2 * 70,
                                  f"line {line!r} overflows the canvas width")

    def test_thumbnail_image_has_expected_canvas_size(self):
        img = self.mt.make_thumbnail("로봇, 스스로 배터리를 갈다", "테크 이슈", "",
                                      self.font_extrabold, self.font_bold)
        self.assertEqual(img.size, vg.TARGET_SIZE)


@_needs_media_deps
class CropToAspectRatioTests(unittest.TestCase):
    def test_landscape_source_crops_to_9_16(self):
        clip = ColorClip(size=(1920, 1080), color=(0, 0, 0)).with_duration(0.2)
        cropped = vg.crop_to_aspect_ratio(clip)
        self.assertEqual(tuple(cropped.size), vg.TARGET_SIZE)


# --------------------------------------------------------------------------
# Pixabay 검색/다운로드를 모킹 — 캐싱·재시도 경계 안쪽 로직만 검증
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
            "hits": [{"videos": {"medium": {"url": "https://example/fake.mp4", "width": 1280, "height": 720}}}]
        }
        mock_download.side_effect = lambda url, dest, **kw: _make_fake_video(dest) or dest

        clip1 = vg.fetch_background_clip("city night vertical", 0.3, "fake-api-key", self.cache_dir)
        self.assertIsNotNone(clip1)
        self.assertEqual(mock_search.call_count, 1)
        self.assertEqual(mock_download.call_count, 1)

        clip2 = vg.fetch_background_clip("city night vertical", 0.3, "fake-api-key", self.cache_dir)
        self.assertIsNotNone(clip2)
        self.assertEqual(mock_search.call_count, 1, "캐시가 있으면 Pixabay 검색을 다시 호출하면 안 된다")
        self.assertEqual(mock_download.call_count, 1, "캐시가 있으면 다시 다운로드하면 안 된다")

    @patch("video_generator.get_json_with_retry")
    def test_no_results_falls_back_to_none(self, mock_search):
        mock_search.return_value = {"hits": []}
        clip = vg.fetch_background_clip("nonexistent query xyz", 0.3, "fake-api-key", self.cache_dir)
        self.assertIsNone(clip)  # 호출자가 ColorClip으로 대체해야 함

    @patch("video_generator.get_json_with_retry")
    def test_query_with_spaces_and_korean_is_url_encoded(self, mock_search):
        # 이전에는 f-string으로 그대로 URL에 꽂아 넣어서 스페이스·한글이 들어간
        # 검색어(샘플 매니페스트의 "news studio vertical" 포함)마다 urllib이
        # http.client.InvalidURL을 던졌다 — 모든 씬이 조용히 ColorClip으로만
        # 대체되던 버그. get_json_with_retry에 실제로 넘어가는 URL을 검사해서
        # 재발을 막는다.
        mock_search.return_value = {"hits": []}
        vg.fetch_background_clip("도시 야경 vertical", 0.3, "fake-api-key", self.cache_dir)
        called_url = mock_search.call_args[0][0]
        self.assertNotIn(" ", called_url)
        self.assertIn("%20", called_url)

    @patch("video_generator.get_json_with_retry")
    def test_api_key_is_not_logged_in_retry_warnings(self, mock_search):
        # Pixabay 키는 Authorization 헤더가 아니라 URL 쿼리파라미터(?key=...)로
        # 들어가므로, 재시도/에러 로그에 그대로 찍히면 키가 노출된다.
        # _redact_url()이 실제로 가리는지 확인한다.
        url = "https://pixabay.com/api/videos/?key=super-secret-key&q=cats"
        redacted = vg._redact_url(url)
        self.assertNotIn("super-secret-key", redacted)
        self.assertIn("key=%2A%2A%2A", redacted)


# --------------------------------------------------------------------------
# 전체 파이프라인 — Pixabay/Edge-TTS를 모킹해서 합성·인코딩 구조를 검증
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
        # 진짜 edge-tts처럼 (단어, 시작 초) 이벤트를 돌려준다 — 정확한 매칭
        # 로직 자체는 LocateSceneStartsFromWordEventsTests가 따로 검증하므로,
        # 여기선 "파이프라인이 반환값을 제대로 흘려보내는지"만 확인하면 된다.
        words = text.split(" ")
        step = 0.6 / max(len(words), 1)
        return [(w, i * step) for i, w in enumerate(words)]

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
                {"script": "첫 번째 테스트 문장", "broll_query": "q1"},
                {"script": "두 번째 테스트 문장", "broll_query": "q2"},
            ],
        }
        output = self.root / "out.mp4"
        vg.generate_premium_shorts(episode, "dummy-key", "ko-KR-SunHiNeural", output,
                                    self.root / "cache", resume=True, fps=10,
                                    preset="ultrafast", threads=2)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 0)
        mock_tts.assert_called_once()  # 전체 대본을 한 번에(single pass) 합성해야 자연스럽다
        self.assertEqual(mock_fetch_bg.call_count, 2)

    @patch("video_generator.synthesize_narration")
    @patch("video_generator.fetch_background_clip")
    def test_resume_skips_narration_when_text_unchanged(self, mock_fetch_bg, mock_tts):
        mock_tts.side_effect = self._fake_tts
        mock_fetch_bg.side_effect = self._fake_bg

        episode = {"title": "재실행 테스트", "scenes": [{"script": "동일한 문장", "broll_query": "q1"}]}
        work_dir = self.root / "cache"

        vg.generate_premium_shorts(episode, "dummy-key", "ko-KR-SunHiNeural", self.root / "out1.mp4",
                                    work_dir, resume=True, fps=10, preset="ultrafast", threads=2)
        vg.generate_premium_shorts(episode, "dummy-key", "ko-KR-SunHiNeural", self.root / "out2.mp4",
                                    work_dir, resume=True, fps=10, preset="ultrafast", threads=2)

        mock_tts.assert_called_once()  # 두 번째 실행은 캐시된 내레이션(+이벤트)을 재사용해야 한다

    @patch("video_generator.synthesize_narration")
    @patch("video_generator.fetch_background_clip")
    def test_resume_resynthesizes_when_any_scene_text_changes(self, mock_fetch_bg, mock_tts):
        # 내레이션은 전체 대본을 한 번에 합성하므로(자연스러운 억양을 위해),
        # 캐시도 전체 대본 해시로 건다 — 씬 하나만 바뀌어도 다시 합성해야
        # 한다. (씬 단위로 부분 캐싱하면 다시 자막-음성 타이밍 불일치로
        # 이어질 수 있다 — 예전 버그가 바로 이거였다.)
        mock_tts.side_effect = self._fake_tts
        mock_fetch_bg.side_effect = self._fake_bg
        work_dir = self.root / "cache"

        episode_v1 = {
            "title": "제목",
            "scenes": [
                {"script": "안 바뀌는 첫 문장", "broll_query": "q1"},
                {"script": "바뀔 예정인 문장", "broll_query": "q2"},
            ],
        }
        vg.generate_premium_shorts(episode_v1, "dummy-key", "ko-KR-SunHiNeural", self.root / "out1.mp4",
                                    work_dir, resume=True, fps=10, preset="ultrafast", threads=2)
        self.assertEqual(mock_tts.call_count, 1)

        episode_v2 = {
            "title": "제목",
            "scenes": [
                {"script": "안 바뀌는 첫 문장", "broll_query": "q1"},
                {"script": "완전히 달라진 두 번째 문장", "broll_query": "q2"},
            ],
        }
        vg.generate_premium_shorts(episode_v2, "dummy-key", "ko-KR-SunHiNeural", self.root / "out2.mp4",
                                    work_dir, resume=True, fps=10, preset="ultrafast", threads=2)
        self.assertEqual(mock_tts.call_count, 2, "씬 하나만 바뀌어도 전체 대본을 다시 합성해야 한다")


if __name__ == "__main__":
    unittest.main(verbosity=2)
