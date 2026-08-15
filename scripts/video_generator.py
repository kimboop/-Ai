#!/usr/bin/env python3
"""아빠모해TV 쇼츠 자동화 파이프라인 (Project AutoShorts).

Pexels API에서 세로형 B-roll을 받아오고, Edge-TTS로 내레이션을 합성하고,
MoviePy로 9:16 프리미엄 뉴스 쇼츠(제목 배지 + 자막 카드)를 렌더링한다.

Input: {"title": str, "scenes": [{"script": str, "pexels_query": str}, ...]}
형태의 JSON — orchestrator/ai_collaboration.py가 만드는 최종 프로덕션
패키지의 대본/장면 지시를 구조화한 것. --init으로 샘플을 생성할 수 있다.

설계 원칙 (CLAUDE.md "글로벌 톱 벤치마킹 기준" #1 — 프로덕션 레벨 아키텍처):
  - 상태 유지: 내레이션 오디오와 씬별 Pexels 다운로드를 work-dir에 캐싱하고
    해시로 변경 여부를 판단한다. 재실행 시 이미 받은 자산은 재사용해서
    (유료/쿼터 제한이 있는) Pexels·Edge-TTS 호출을 불필요하게 반복하지 않는다.
  - 재시도: Pexels API 호출과 다운로드는 orchestrator/ai_collaboration.py의
    post()와 같은 429/503 지수 백오프(재시도 최대 4회) 로직을 공유한다.
  - 빠른 실패: 폰트·API 키가 없으면 렌더링을 시작하기 전에 명확한 에러로
    막는다 — 원본 프로토타입처럼 폰트를 못 찾았을 때 조용히 기본 비트맵
    폰트로 대체해서 "제목 없는 광고 같은" 결과물을 프로덕션에 흘려보내지
    않는다.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger("video_generator")

TARGET_SIZE = (1080, 1920)  # 9:16

# 프리미엄 뉴스 톤 팔레트 — 아빠모해TV 브랜드 스타일
NAVY_PANEL = (15, 23, 42, 230)
GOLD_ACCENT = (212, 175, 55, 255)
TITLE_PANEL = (30, 41, 59, 240)
TITLE_BORDER = (255, 255, 255, 100)


# --------------------------------------------------------------------------
# Retry helper (orchestrator/ai_collaboration.py의 post()와 동일한 429/503
# 지수 백오프 모양 — 두 파이프라인이 일시적 오류에 같은 방식으로 반응한다).
# --------------------------------------------------------------------------
def _is_transient(e: Exception) -> bool:
    code = getattr(e, "code", None)
    return code in (429, 503) or not isinstance(e, urllib.error.HTTPError)


def get_json_with_retry(url: str, headers: dict, retries: int = 4, backoff: int = 10) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError) as e:
            if _is_transient(e) and attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                LOG.warning("%s failed (%s), retrying in %ss (attempt %d/%d)",
                            url, e, wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Exhausted retries for {url}")


def download_with_retry(url: str, dest: Path, retries: int = 4, backoff: int = 10) -> Path:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                dest.write_bytes(resp.read())
            return dest
        except (urllib.error.URLError, TimeoutError) as e:
            if _is_transient(e) and attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                LOG.warning("download %s failed (%s), retrying in %ss (attempt %d/%d)",
                            url, e, wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Exhausted retries for {url}")


# --------------------------------------------------------------------------
# Fonts — 실패를 조용히 삼키지 않는다. 원본 프로토타입은 폰트를 못 찾으면
# ImageFont.load_default()(작은 비트맵 폰트)로 조용히 대체했는데, 이건
# "프리미엄 뉴스 쇼츠"에 깨진 자막을 그대로 내보내는 것과 같다.
# --------------------------------------------------------------------------
def resolve_font(env_var: str, filename: str) -> str:
    candidates = []
    env = os.environ.get(env_var)
    if env:
        candidates.append(Path(env))
    candidates.append(ROOT / "assets" / "fonts" / filename)
    candidates.append(Path("/usr/share/fonts/truetype/nanum") / filename)
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError(
        f"Font not found (tried {', '.join(str(c) for c in candidates)}). "
        f"Set {env_var} or install it — see scripts/README.md#fonts."
    )


# --------------------------------------------------------------------------
# 디자인 자막 / 타이틀 카드
# --------------------------------------------------------------------------
def create_subtitle_image(text: str, font_path: str, size: tuple = TARGET_SIZE, font_size: int = 50):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    wrapped_text = "\n".join(textwrap.wrap(text, width=16))
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - text_w) // 2
    y = int(size[1] * 0.68)
    pad_x, pad_y = 30, 20
    draw.rounded_rectangle(
        [x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y],
        radius=15, fill=NAVY_PANEL, outline=GOLD_ACCENT, width=2,
    )
    draw.multiline_text((x, y), wrapped_text, font=font, fill=(255, 255, 255, 255), align="center")
    return img


def create_title_image(title_text: str, font_path: str, size: tuple = TARGET_SIZE, font_size: int = 44):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), title_text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - text_w) // 2
    y = int(size[1] * 0.08)
    pad_x, pad_y = 32, 14
    draw.rounded_rectangle(
        [x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y],
        radius=12, fill=TITLE_PANEL, outline=TITLE_BORDER, width=1,
    )
    draw.text((x, y), title_text, font=font, fill=(248, 250, 252, 255))
    return img


# --------------------------------------------------------------------------
# 배경 영상
# --------------------------------------------------------------------------
def crop_to_aspect_ratio(clip, target_w: int = TARGET_SIZE[0], target_h: int = TARGET_SIZE[1]):
    orig_w, orig_h = clip.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h
    if orig_ratio > target_ratio:
        new_w, new_h = int(orig_h * target_ratio), orig_h
    else:
        new_w, new_h = orig_w, int(orig_w / target_ratio)
    cropped = clip.cropped(width=new_w, height=new_h, x_center=orig_w / 2, y_center=orig_h / 2)
    return cropped.resized((target_w, target_h))


def pick_video_file(video_files: list[dict]) -> str:
    """세로 영상 중 1080폭에 가장 가까운 걸 고른다 — 원본은 video_files[0]을
    그냥 썼는데, Pexels가 가로형/저해상도 파일을 0번으로 줄 때도 있다."""
    portrait = [f for f in video_files if f.get("height", 0) >= f.get("width", 0)]
    candidates = portrait or video_files
    candidates = sorted(candidates, key=lambda f: abs(f.get("width", 0) - TARGET_SIZE[0]))
    return candidates[0]["link"]


def fetch_background_clip(query: str, scene_duration: float, headers: dict, cache_dir: Path):
    """캐시에 없으면 Pexels에서 받아온다. 실패하면 None을 돌려주고 호출자가
    ColorClip 폴백을 쓴다 — 씬 하나가 비어도 전체 렌더링은 계속 진행한다."""
    from moviepy import VideoFileClip, vfx

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"bg_{hashlib.sha256(query.encode()).hexdigest()[:16]}.mp4"

    if not cache_file.exists():
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=3"
        try:
            data = get_json_with_retry(url, headers)
            videos = data.get("videos", [])
            if not videos:
                LOG.warning("Pexels returned no results for query %r", query)
                return None
            link = pick_video_file(videos[0]["video_files"])
            download_with_retry(link, cache_file)
        except Exception as e:  # noqa: BLE001 - network/API fallback boundary
            LOG.warning("Pexels fetch failed for query %r: %s", query, e)
            return None
    else:
        LOG.info("Reusing cached B-roll for query %r", query)

    clip = VideoFileClip(str(cache_file))
    if clip.duration < scene_duration:
        clip = clip.with_effects([vfx.Loop(duration=scene_duration)])
    else:
        clip = clip.subclipped(0, scene_duration)
    return crop_to_aspect_ratio(clip)


# --------------------------------------------------------------------------
# TTS
# --------------------------------------------------------------------------
def synthesize_narration(text: str, voice: str, dest: Path, retries: int = 3, backoff: int = 5) -> None:
    import edge_tts

    async def _make():
        comm = edge_tts.Communicate(text, voice, rate="+0%")
        await comm.save(str(dest))

    for attempt in range(retries):
        try:
            asyncio.run(_make())
            if dest.exists() and dest.stat().st_size > 0:
                return
            raise RuntimeError("edge-tts produced an empty file")
        except Exception as e:  # noqa: BLE001 - transient network/service errors
            if attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                LOG.warning("edge-tts failed (%s), retrying in %ss (attempt %d/%d)",
                            e, wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            raise


# --------------------------------------------------------------------------
# 매니페스트
# --------------------------------------------------------------------------
def validate_episode(data: dict[str, Any]) -> None:
    if not data.get("scenes"):
        raise ValueError("Episode JSON has no 'scenes' array")
    for i, scene in enumerate(data["scenes"]):
        if not scene.get("script", "").strip():
            raise ValueError(f"scenes[{i}] is missing non-empty 'script'")


SAMPLE_EPISODE = {
    "title": "글로벌 핵심 이슈 리포트",
    "scenes": [
        {"script": "오늘의 첫 번째 소식입니다.", "pexels_query": "news studio vertical"},
        {"script": "두 번째 소식으로 넘어가겠습니다.", "pexels_query": "city skyline night vertical"},
    ],
}


# --------------------------------------------------------------------------
# 렌더링
# --------------------------------------------------------------------------
def generate_premium_shorts(episode: dict[str, Any], pexels_key: str, voice: str,
                             output_path: Path, work_dir: Path, resume: bool,
                             fps: int, preset: str, threads: int) -> None:
    import numpy as np
    from moviepy import ColorClip, CompositeVideoClip, ImageClip, concatenate_videoclips

    title = episode.get("title", "글로벌 핵심 이슈 리포트")
    scenes = episode["scenes"]
    LOG.info("아빠모해TV 쇼츠 제작 시작: %s (%d개 씬)", title, len(scenes))

    subtitle_font = resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")
    title_font = resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")

    work_dir.mkdir(parents=True, exist_ok=True)
    full_text = " ".join(s["script"] for s in scenes)
    text_hash = hashlib.sha256(full_text.encode()).hexdigest()[:16]
    voice_path = work_dir / "voice.mp3"
    state_path = work_dir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    if resume and voice_path.exists() and state.get("voice_hash") == text_hash:
        LOG.info("Reusing cached narration (%s)", voice_path)
    else:
        LOG.info("Synthesizing narration with voice=%s", voice)
        synthesize_narration(full_text, voice, voice_path)
        state["voice_hash"] = text_hash
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    from moviepy import AudioFileClip
    audio_clip = AudioFileClip(str(voice_path))
    total_duration = audio_clip.duration
    scene_duration = total_duration / len(scenes)

    headers = {"Authorization": pexels_key}
    downloads_dir = work_dir / "downloads"
    video_clips = []
    subtitle_clips = []

    for idx, scene in enumerate(scenes):
        query = scene.get("pexels_query", "news background vertical")
        clip = fetch_background_clip(query, scene_duration, headers, downloads_dir)
        if clip is None:
            clip = ColorClip(size=TARGET_SIZE, color=(15, 23, 42)).with_duration(scene_duration)
        video_clips.append(clip)

        sub_img = create_subtitle_image(scene["script"], subtitle_font)
        subtitle_clips.append(
            ImageClip(np.array(sub_img))
            .with_start(idx * scene_duration)
            .with_duration(scene_duration)
            .with_position(("center", "center"))
        )

    combined_bg = concatenate_videoclips(video_clips, method="compose").with_audio(audio_clip)
    title_img = create_title_image(f"📌 {title}", title_font)
    title_clip = (
        ImageClip(np.array(title_img))
        .with_duration(total_duration)
        .with_position(("center", "top"))
    )

    final_video = CompositeVideoClip([combined_bg, title_clip, *subtitle_clips], size=TARGET_SIZE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_video.write_videofile(str(output_path), fps=fps, codec="libx264",
                                 audio_codec="aac", preset=preset, threads=threads)
    LOG.info("완성: %s", output_path)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def check_environment() -> list[str]:
    problems = []
    try:
        import moviepy.config as mpconfig
    except ImportError:
        problems.append("moviepy not installed — run: pip install -r scripts/requirements.txt")
        return problems
    if mpconfig.FFMPEG_BINARY in ("unset", None):
        problems.append(
            "moviepy could not locate an ffmpeg binary. This normally comes "
            "bundled via the imageio-ffmpeg dependency — reinstall "
            "requirements, or see scripts/README.md#dependencies for a "
            "system-ffmpeg fallback."
        )
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        problems.append("edge-tts not installed — run: pip install -r scripts/requirements.txt")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=ROOT / "scripts" / "episode.json",
                         help="Episode JSON path (default: scripts/episode.json)")
    parser.add_argument("--output", type=Path, default=None,
                         help="Output MP4 path (default: output/<input-stem>.mp4)")
    parser.add_argument("--work-dir", type=Path, default=None,
                         help="Cache dir for narration/B-roll downloads (default: output/.cache/<input-stem>)")
    parser.add_argument("--voice", default=os.environ.get("SHORTS_TTS_VOICE", "ko-KR-SunHiNeural"))
    parser.add_argument("--no-resume", action="store_true", help="Ignore cached narration/B-roll and refetch")
    parser.add_argument("--fps", type=int, default=int(os.environ.get("VIDEO_FPS", 30)))
    parser.add_argument("--preset", default=os.environ.get("VIDEO_PRESET", "medium"))
    parser.add_argument("--threads", type=int, default=int(os.environ.get("VIDEO_RENDER_THREADS", os.cpu_count() or 4)))
    parser.add_argument("--validate-only", action="store_true", help="Validate the episode JSON and exit")
    parser.add_argument("--init", action="store_true", help="Write a sample episode JSON to <input> and exit")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    if args.init:
        args.input.parent.mkdir(parents=True, exist_ok=True)
        args.input.write_text(json.dumps(SAMPLE_EPISODE, ensure_ascii=False, indent=2), encoding="utf-8")
        LOG.info("Wrote sample episode to %s", args.input)
        return 0

    try:
        if not args.input.exists():
            raise FileNotFoundError(f"Episode JSON not found: {args.input}")
        episode = json.loads(args.input.read_text(encoding="utf-8"))
        validate_episode(episode)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        LOG.error("Episode JSON problem: %s", e)
        return 1

    if args.validate_only:
        LOG.info("Episode OK: %d scene(s)", len(episode["scenes"]))
        return 0

    problems = check_environment()
    if problems:
        for p in problems:
            LOG.error(p)
        return 1

    pexels_key = os.environ.get("PEXELS_API_KEY")
    if not pexels_key:
        LOG.error("Missing PEXELS_API_KEY env var — see scripts/README.md#required-environment-variables")
        return 1

    output = args.output or (ROOT / "output" / f"{args.input.stem}.mp4")
    work_dir = args.work_dir or (ROOT / "output" / ".cache" / args.input.stem)

    try:
        generate_premium_shorts(episode, pexels_key, args.voice, output, work_dir,
                                 resume=not args.no_resume, fps=args.fps,
                                 preset=args.preset, threads=args.threads)
    except Exception as e:  # noqa: BLE001 - top-level command boundary
        LOG.error("Render failed: %s", e)
        LOG.error("Cached narration/B-roll in %s are reused on the next run.", work_dir)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
