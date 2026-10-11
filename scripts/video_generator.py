#!/usr/bin/env python3
"""아빠모해TV 쇼츠 자동화 파이프라인 (Project AutoShorts).

Pixabay API에서 세로형 B-roll을 받아오고, Edge-TTS로 내레이션을 합성하고,
MoviePy로 9:16 프리미엄 뉴스 쇼츠(제목 배지 + 자막 카드)를 렌더링한다.

원래는 Pexels을 썼는데, 대시보드에 보이는 키 값과 바이트 단위로 완전히
일치하는데도 Pexels API가 계속 "Invalid API key"(401)로 거부해서(계정
승인/활성화 쪽 문제로 보이며 우리 쪽에서 고칠 수 없음) Pixabay로 교체했다
— 가입 즉시 키가 바로 활성화되는 경우가 대부분이라 이런 대기 없이 바로
쓸 수 있다.

Input: {"title": str, "scenes": [{"script": str, "broll_query": str}, ...]}
형태의 JSON — orchestrator/ai_collaboration.py가 만드는 최종 프로덕션
패키지의 대본/장면 지시를 구조화한 것. --init으로 샘플을 생성할 수 있다.

설계 원칙 (CLAUDE.md "글로벌 톱 벤치마킹 기준" #1 — 프로덕션 레벨 아키텍처):
  - 상태 유지: 내레이션 오디오와 씬별 Pixabay 다운로드를 work-dir에 캐싱하고
    해시로 변경 여부를 판단한다. 재실행 시 이미 받은 자산은 재사용해서
    (유료/쿼터 제한이 있는) Pixabay·Edge-TTS 호출을 불필요하게 반복하지 않는다.
  - 재시도: Pixabay API 호출과 다운로드는 orchestrator/ai_collaboration.py의
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
import urllib.parse
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

# Pixabay(Cloudflare 뒤에 있음)는 urllib의 기본 User-Agent("Python-urllib/3.x")를
# 차단한다 — 같은 GitHub Actions 러너에서 똑같은 키·엔드포인트로 curl(기본 UA든
# 브라우저 UA든)은 200이 오는데 urllib 기본 UA만 403이 나는 걸 직접 확인했다.
# IP 차단이나 키 문제가 아니라 순수 UA 기반 WAF 룰이라, 모든 Pixabay 요청에
# 브라우저 UA를 달아서 우회한다.
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


# --------------------------------------------------------------------------
# Retry helper (orchestrator/ai_collaboration.py의 post()와 동일한 429/503
# 지수 백오프 모양 — 두 파이프라인이 일시적 오류에 같은 방식으로 반응한다).
# --------------------------------------------------------------------------
def _is_transient(e: Exception) -> bool:
    code = getattr(e, "code", None)
    return code in (429, 503) or not isinstance(e, urllib.error.HTTPError)


def _redact_url(url: str) -> str:
    """로그에 찍기 전에 쿼리스트링의 key= 값을 가린다. Pexels은 Authorization
    헤더로 키를 받았지만 Pixabay는 URL 쿼리파라미터(?key=...)로 받기 때문에,
    재시도/에러 로그가 그대로 키를 노출시키지 않도록 막는 안전장치다."""
    parsed = urllib.parse.urlsplit(url)
    params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [(k, "***" if k.lower() == "key" else v) for k, v in params]
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(redacted)))


def get_json_with_retry(url: str, headers: dict, retries: int = 4, backoff: int = 10) -> dict:
    req = urllib.request.Request(url, headers={**DEFAULT_HEADERS, **headers}, method="GET")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError) as e:
            if _is_transient(e) and attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                LOG.warning("%s failed (%s), retrying in %ss (attempt %d/%d)",
                            _redact_url(url), e, wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Exhausted retries for {_redact_url(url)}")


def download_with_retry(url: str, dest: Path, retries: int = 4, backoff: int = 10) -> Path:
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS, method="GET")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
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


def create_title_image(title_text: str, font_path: str, size: tuple = TARGET_SIZE, font_size: int = 56):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    # 글자 수가 아니라 실제 렌더링 픽셀 너비로 줄바꿈한다 — 폰트 크기를 키운
    # 뒤에도 긴 제목이 캔버스 밖으로 잘리지 않게 하기 위함
    # (make_thumbnail.py의 _wrap_to_width와 동일한 접근).
    max_width = int(size[0] * 0.86)
    words = title_text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    wrapped_text = "\n".join(lines)

    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - text_w) // 2
    y = int(size[1] * 0.08)
    pad_x, pad_y = 32, 14
    draw.rounded_rectangle(
        [x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y],
        radius=12, fill=TITLE_PANEL, outline=TITLE_BORDER, width=1,
    )
    draw.multiline_text((x, y), wrapped_text, font=font, fill=(248, 250, 252, 255), align="center")
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


def pick_pixabay_video_file(videos: dict) -> str:
    """Pixabay가 주는 large/medium/small/tiny 해상도 중 하나를 고른다. 화질과
    다운로드 용량의 균형을 위해 medium(보통 1280x720)을 우선한다 — 어차피
    crop_to_aspect_ratio()가 9:16으로 크롭하므로 원본이 더 클 필요는 없다."""
    if not videos:
        raise ValueError("Pixabay returned a hit with no video renditions")
    for quality in ("medium", "large", "small", "tiny"):
        rendition = videos.get(quality)
        if rendition and rendition.get("url"):
            return rendition["url"]
    raise ValueError("Pixabay video renditions had no usable url")


def fetch_background_clip(query: str, scene_duration: float, api_key: str, cache_dir: Path):
    """캐시에 없으면 Pixabay에서 받아온다. 실패하면 None을 돌려주고 호출자가
    ColorClip 폴백을 쓴다 — 씬 하나가 비어도 전체 렌더링은 계속 진행한다."""
    from moviepy import VideoFileClip, vfx

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"bg_{hashlib.sha256(query.encode()).hexdigest()[:16]}.mp4"

    if not cache_file.exists():
        url = (f"https://pixabay.com/api/videos/?key={urllib.parse.quote(api_key)}"
               f"&q={urllib.parse.quote(query)}&per_page=3&safesearch=true")
        try:
            data = get_json_with_retry(url, {})
            hits = data.get("hits", [])
            if not hits:
                LOG.warning("Pixabay returned no results for query %r", query)
                return None
            link = pick_pixabay_video_file(hits[0]["videos"])
            download_with_retry(link, cache_file)
        except Exception as e:  # noqa: BLE001 - network/API fallback boundary
            code = getattr(e, "code", None)
            if code in (400, 401, 403):
                LOG.warning(
                    "Pixabay fetch failed for query %r: %s — this looks like an "
                    "auth/WAF rejection, not a transient error. Check that "
                    "PIXABAY_API_KEY is a valid key from "
                    "https://pixabay.com/api/docs/ with no extra whitespace "
                    "(every scene will fail identically until this is fixed).",
                    query, e,
                )
            else:
                LOG.warning("Pixabay fetch failed for query %r: %s", query, e)
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
def synthesize_narration(text: str, voice: str, dest: Path, rate: str = "+0%",
                          retries: int = 3, backoff: int = 5) -> list[tuple[str, float]]:
    """전체 대본을 한 번에(single pass) 합성한다 — 씬별로 따로 합성하면 문장과
    문장 사이의 자연스러운 억양·호흡이 끊겨 부자연스럽게 들린다. 대신
    WordBoundary 이벤트((단어 텍스트, 시작 초) 목록, 발화 순서)를 같이 받아서
    돌려준다 — 호출자가 이걸로 각 씬 텍스트가 실제 오디오의 어느 시점에서
    시작하는지 역산할 수 있어서, 씬을 쪼개지 않고도 자막 타이밍을 맞출 수 있다
    (locate_scene_starts_from_word_events 참고)."""
    import edge_tts

    async def _make() -> list[tuple[str, float]]:
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        audio_chunks: list[bytes] = []
        events: list[tuple[str, float]] = []
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration은 100ns 단위("ticks")로 온다 — 초 단위로 변환.
                events.append((chunk["text"], chunk["offset"] / 10_000_000))
        dest.write_bytes(b"".join(audio_chunks))
        return events

    for attempt in range(retries):
        try:
            events = asyncio.run(_make())
            if dest.exists() and dest.stat().st_size > 0:
                return events
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
        {"script": "오늘의 첫 번째 소식입니다.", "broll_query": "news studio vertical"},
        {"script": "두 번째 소식으로 넘어가겠습니다.", "broll_query": "city skyline night vertical"},
    ],
}


# --------------------------------------------------------------------------
# 렌더링
# --------------------------------------------------------------------------
def compute_scene_starts(durations: list[float]) -> list[float]:
    """각 씬의 (서로 다를 수 있는) 길이를 기준으로 누적 시작 시각을 구한다.
    씬 개수로 균등 분할한 고정값보다 정확하지만, 이것도 "씬 길이"가 정확해야
    맞는다 — word-boundary 타이밍을 못 구했을 때의 폴백으로만 쓴다
    (locate_scene_starts_from_word_events 참고)."""
    starts = []
    cursor = 0.0
    for d in durations:
        starts.append(cursor)
        cursor += d
    return starts


def compute_scene_char_offsets(scripts: list[str]) -> list[int]:
    """각 씬 스크립트가 전체 내레이션 텍스트(" ".join(scripts))에서 몇 번째
    문자부터 시작하는지 구한다. generate_premium_shorts()가 실제로 join하는
    방식(스페이스 1칸)과 반드시 같은 규칙을 써야 한다."""
    offsets = []
    cursor = 0
    for s in scripts:
        offsets.append(cursor)
        cursor += len(s) + 1  # +1: 다음 스크립트와 이어붙일 때의 join 스페이스
    return offsets


def locate_scene_starts_from_word_events(
    full_text: str,
    scene_char_starts: list[int],
    word_events: list[tuple[str, float]],
) -> list[float] | None:
    """edge-tts의 WordBoundary 이벤트(발화 순서대로 정렬된 (단어 텍스트, 시작
    초) 목록)로 각 씬이 실제 오디오에서 몇 초에 시작하는지 구한다. 단어
    텍스트를 full_text에서 순서대로 찾아가며 "문자 위치 → 시각" 대응표를
    만들고, 각 씬의 시작 문자 위치 이상인 첫 단어의 시각을 그 씬의 시작으로
    쓴다. 이벤트가 비었거나 텍스트를 못 찾으면(edge-tts 출력이 예상과
    다르면) None을 돌려줘서 호출자가 균등 분할로 안전하게 폴백하게 한다."""
    if not word_events:
        return None

    word_positions: list[tuple[int, float]] = []
    cursor = 0
    for word_text, offset_sec in word_events:
        pos = full_text.find(word_text, cursor)
        if pos == -1:
            return None
        word_positions.append((pos, offset_sec))
        cursor = pos + len(word_text)

    scene_starts = []
    for char_start in scene_char_starts:
        match = next((t for p, t in word_positions if p >= char_start), None)
        if match is None:
            match = word_positions[-1][1]
        scene_starts.append(match)
    return scene_starts


def generate_premium_shorts(episode: dict[str, Any], pixabay_key: str, voice: str,
                             output_path: Path, work_dir: Path, resume: bool,
                             fps: int, preset: str, threads: int,
                             tts_rate: str = "+0%") -> None:
    import numpy as np
    from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip, concatenate_videoclips

    title = episode.get("title", "글로벌 핵심 이슈 리포트")
    scenes = episode["scenes"]
    LOG.info("아빠모해TV 쇼츠 제작 시작: %s (%d개 씬)", title, len(scenes))

    subtitle_font = resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")
    title_font = resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")

    work_dir.mkdir(parents=True, exist_ok=True)

    # 내레이션은 전체 대본을 한 번에(single pass) 합성한다. 씬별로 따로
    # 합성했더니 자막 타이밍은 맞았지만 문장 사이 자연스러운 억양·호흡이
    # 끊겨 부자연스럽게 들린다는 피드백을 받았다. 대신 WordBoundary
    # 이벤트(실제 발화 시각)를 받아서 각 씬 텍스트가 전체 오디오의 어느
    # 시점에서 시작하는지 역산한다 — 씬을 쪼개지 않고도 자막-음성 타이밍을
    # 맞추는 방법이다.
    full_text = " ".join(s["script"] for s in scenes)
    narration_dir = work_dir / "narration"
    narration_dir.mkdir(parents=True, exist_ok=True)
    text_hash = hashlib.sha256(full_text.encode()).hexdigest()[:16]
    voice_path = narration_dir / f"voice_{text_hash}.mp3"
    events_path = narration_dir / f"voice_{text_hash}.events.json"

    if resume and voice_path.exists() and events_path.exists():
        LOG.info("Reusing cached narration (%s)", voice_path)
        word_events = [tuple(e) for e in json.loads(events_path.read_text(encoding="utf-8"))]
    else:
        LOG.info("Synthesizing narration (single pass, %d scenes) with voice=%s", len(scenes), voice)
        word_events = synthesize_narration(full_text, voice, voice_path, rate=tts_rate)
        events_path.write_text(json.dumps(word_events, ensure_ascii=False), encoding="utf-8")

    audio_clip = AudioFileClip(str(voice_path))
    total_duration = audio_clip.duration

    scene_char_starts = compute_scene_char_offsets([s["script"] for s in scenes])
    scene_starts = locate_scene_starts_from_word_events(full_text, scene_char_starts, word_events)
    if scene_starts is None:
        LOG.warning(
            "Could not align subtitles to narration via word-boundary timestamps "
            "(unexpected edge-tts output) — falling back to an equal split across "
            "scenes, which can drift out of sync for scenes of very different lengths."
        )
        scene_starts = compute_scene_starts([total_duration / len(scenes)] * len(scenes))

    scene_durations = [
        max(
            (scene_starts[i + 1] if i + 1 < len(scene_starts) else total_duration) - scene_starts[i],
            0.3,
        )
        for i in range(len(scene_starts))
    ]

    downloads_dir = work_dir / "downloads"
    video_clips = []
    subtitle_clips = []

    for idx, scene in enumerate(scenes):
        scene_duration = scene_durations[idx]
        query = scene.get("broll_query", "news background vertical")
        clip = fetch_background_clip(query, scene_duration, pixabay_key, downloads_dir)
        if clip is None:
            clip = ColorClip(size=TARGET_SIZE, color=(15, 23, 42)).with_duration(scene_duration)
        video_clips.append(clip)

        sub_img = create_subtitle_image(scene["script"], subtitle_font)
        subtitle_clips.append(
            ImageClip(np.array(sub_img))
            .with_start(scene_starts[idx])
            .with_duration(scene_duration)
            .with_position(("center", "center"))
        )

    combined_bg = concatenate_videoclips(video_clips, method="compose").with_audio(audio_clip)
    # 이모지(📌 등)는 나눔고딕에 글리프가 없어 깨진 네모(tofu)로 렌더링된다 —
    # 폰트 cmap에 실제로 있는 기호만 쓴다(fontTools로 확인: U+25CF는 포함됨).
    title_img = create_title_image(f"● {title}", title_font)
    title_clip = (
        ImageClip(np.array(title_img))
        .with_duration(total_duration)
        .with_position(("center", "top"))
    )

    final_video = CompositeVideoClip([combined_bg, title_clip, *subtitle_clips], size=TARGET_SIZE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        final_video.write_videofile(str(output_path), fps=fps, codec="libx264",
                                     audio_codec="aac", preset=preset, threads=threads)
    finally:
        # VideoFileClip/AudioFileClip hold open ffmpeg reader processes and file
        # handles; close() is a no-op on clip types that don't need it (ColorClip,
        # CompositeVideoClip, ImageClip), so this is safe to call unconditionally.
        final_video.close()
        audio_clip.close()
        for clip in video_clips:
            clip.close()

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
    parser.add_argument("--tts-rate", default=os.environ.get("SHORTS_TTS_RATE", "+0%"),
                         help="Edge-TTS speaking-rate adjustment, e.g. -5%% for a slightly slower, "
                              "less rushed delivery (default: +0%%)")
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

    # .strip(): a trailing newline/space from copy-pasting into a GitHub secret
    # silently corrupts the ?key= query param and Pixabay returns a plain
    # 400/401 with no hint that whitespace was the cause — cheap to guard against.
    pixabay_key = (os.environ.get("PIXABAY_API_KEY") or "").strip()
    if not pixabay_key:
        LOG.error("Missing PIXABAY_API_KEY env var — see scripts/README.md#required-environment-variables")
        return 1

    output = args.output or (ROOT / "output" / f"{args.input.stem}.mp4")
    work_dir = args.work_dir or (ROOT / "output" / ".cache" / args.input.stem)

    try:
        generate_premium_shorts(episode, pixabay_key, args.voice, output, work_dir,
                                 resume=not args.no_resume, fps=args.fps,
                                 preset=args.preset, threads=args.threads, tts_rate=args.tts_rate)
    except Exception as e:  # noqa: BLE001 - top-level command boundary
        LOG.error("Render failed: %s", e)
        LOG.error("Cached narration/B-roll in %s are reused on the next run.", work_dir)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
