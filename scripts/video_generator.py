#!/usr/bin/env python3
"""Renders a final MP4 from a JSON scene manifest (images/B-roll + narration +
background music + burned-in subtitles).

Consumes the production package produced by orchestrator/ai_collaboration.py
(scene-by-scene visual instructions, graphics specs, SRT draft) once that
markdown output has been turned into a structured scenes.json — see
scripts/README.md for the manifest schema and asset/font layout.

Design goals (see CLAUDE.md "글로벌 톱 벤치마킹 기준" #1 — production-level
architecture, not a script that dies on the first error):
  - Stateful: each scene is rendered to a cached clip and checked off in a
    state file, so a crash or Ctrl-C loses at most the in-flight scene.
  - Retries transient errors (network hiccups fetching a remote asset) with
    exponential backoff instead of failing the whole run.
  - Fails fast and loudly on configuration problems (missing font, missing
    ffmpeg, bad manifest) instead of silently producing a broken video.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger("video_generator")


# --------------------------------------------------------------------------
# Retry helper (same 429/503 exponential-backoff shape as
# orchestrator/ai_collaboration.py's post(), so both pipelines behave the
# same way under transient failures).
# --------------------------------------------------------------------------
def fetch_with_retry(url: str, dest: Path, retries: int = 4, backoff: int = 5) -> Path:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                dest.write_bytes(resp.read())
            return dest
        except (urllib.error.URLError, TimeoutError) as e:
            code = getattr(e, "code", None)
            transient = code in (429, 503) or not isinstance(e, urllib.error.HTTPError)
            if transient and attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                LOG.warning("fetch %s failed (%s), retrying in %ss (attempt %d/%d)",
                            url, e, wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Failed to fetch asset {url}: {e}") from e
    raise RuntimeError(f"Failed to fetch asset {url}")


def resolve_asset(path_or_url: str, manifest_dir: Path, cache_dir: Path) -> Path:
    """Local paths resolve relative to the manifest; remote URLs are
    downloaded (with retry) into the cache and reused on subsequent runs."""
    if path_or_url.startswith(("http://", "https://")):
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = cache_dir / hashlib.sha256(path_or_url.encode()).hexdigest()[:16]
        suffix = Path(path_or_url.split("?")[0]).suffix
        dest = dest.with_suffix(suffix or ".bin")
        if not dest.exists():
            fetch_with_retry(path_or_url, dest)
        return dest
    p = (manifest_dir / path_or_url).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Asset not found: {p}")
    return p


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------
@dataclass
class Manifest:
    path: Path
    data: dict[str, Any]

    @property
    def dir(self) -> Path:
        return self.path.parent

    @property
    def resolution(self) -> tuple[int, int]:
        w, h = self.data.get("resolution", [1920, 1080])
        return int(w), int(h)

    @property
    def fps(self) -> int:
        return int(self.data.get("fps", 30))

    @property
    def scenes(self) -> list[dict[str, Any]]:
        return self.data["scenes"]

    @property
    def font(self) -> str:
        font = self.data.get("font") or os.environ.get("VIDEO_FONT_PATH")
        if not font:
            raise ValueError(
                "No font configured. Set 'font' in the manifest or the "
                "VIDEO_FONT_PATH env var — see scripts/README.md#fonts."
            )
        return font


def load_manifest(path: Path) -> Manifest:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(data)
    return Manifest(path=path, data=data)


def validate_manifest(data: dict[str, Any]) -> None:
    if not data.get("scenes"):
        raise ValueError("Manifest has no 'scenes' array")
    for i, scene in enumerate(data["scenes"]):
        if "visual" not in scene:
            raise ValueError(f"scenes[{i}] is missing 'visual'")
        if scene.get("duration", 0) <= 0:
            raise ValueError(f"scenes[{i}] must have a positive 'duration'")
        vtype = scene["visual"].get("type")
        if vtype not in ("image", "video", "color"):
            raise ValueError(f"scenes[{i}].visual.type must be image/video/color, got {vtype!r}")


def scene_hash(scene: dict[str, Any], font: str) -> str:
    payload = json.dumps({"scene": scene, "font": font}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# Subtitle parsing (hand-rolled SRT reader — avoids pulling in a whole
# subtitle library for a ~20-line format)
# --------------------------------------------------------------------------
@dataclass
class Caption:
    start: float
    end: float
    text: str


def _srt_time_to_seconds(t: str) -> float:
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path: Path) -> list[Caption]:
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")
    captions = []
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        time_line = next((ln for ln in lines if "-->" in ln), None)
        if not time_line:
            continue
        start_s, end_s = [seg.strip().split(" ")[0] for seg in time_line.split("-->")]
        text = "\n".join(lines[lines.index(time_line) + 1:])
        captions.append(Caption(_srt_time_to_seconds(start_s), _srt_time_to_seconds(end_s), text))
    return captions


# --------------------------------------------------------------------------
# Rendering (moviepy is imported lazily so `--validate-only` and `--init`
# work even without the heavy dependency installed)
# --------------------------------------------------------------------------
def render(manifest: Manifest, output_path: Path, resume: bool, cache_dir: Path,
           preset: str, threads: int) -> None:
    from moviepy import (
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ColorClip,
        ImageClip,
        TextClip,
        VideoFileClip,
        afx,
        concatenate_videoclips,
    )

    size = manifest.resolution
    font = manifest.font
    state_path = cache_dir / "state.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    state = json.loads(state_path.read_text(encoding="utf-8")) if (resume and state_path.exists()) else {}

    def save_state():
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def build_visual(scene: dict[str, Any]):
        visual = scene["visual"]
        duration = float(scene["duration"])
        if visual["type"] == "image":
            asset = resolve_asset(visual["path"], manifest.dir, cache_dir / "downloads")
            clip = ImageClip(str(asset)).with_duration(duration)
            clip = clip.resized(height=size[1]) if clip.h < size[1] else clip
            if visual.get("ken_burns", True):
                ratio = float(visual.get("zoom_ratio", 1.08))
                clip = clip.resized(lambda t: 1 + (ratio - 1) * (t / duration))
        elif visual["type"] == "video":
            asset = resolve_asset(visual["path"], manifest.dir, cache_dir / "downloads")
            clip = VideoFileClip(str(asset)).subclipped(0, duration)
        else:  # color
            clip = ColorClip(size=size, color=tuple(visual.get("rgb", [0, 0, 0]))).with_duration(duration)
        return CompositeVideoClip([clip.with_position("center")], size=size).with_duration(duration)

    def build_graphic(scene: dict[str, Any], duration: float):
        graphic = scene.get("graphic")
        if not graphic:
            return None
        position = graphic.get("position", "bottom_left")
        pos_map = {
            "bottom_left": ("left", "bottom"),
            "bottom_right": ("right", "bottom"),
            "top_left": ("left", "top"),
            "top_right": ("right", "top"),
        }
        text_clip = TextClip(
            font=font,
            text=graphic["text"],
            font_size=graphic.get("font_size", 32),
            color=graphic.get("color", "white"),
            stroke_color=graphic.get("stroke_color", "black"),
            stroke_width=graphic.get("stroke_width", 1),
            method="caption",
            size=(int(size[0] * 0.6), None),
        ).with_duration(duration).with_position(pos_map.get(position, ("left", "bottom")), relative=False)
        return text_clip

    scene_clips = []
    for scene in manifest.scenes:
        scene_id = scene.get("id", len(scene_clips) + 1)
        h = scene_hash(scene, font)
        cached_file = cache_dir / f"scene_{scene_id}.mp4"
        cached = state.get(str(scene_id))

        if resume and cached and cached.get("hash") == h and cached_file.exists():
            LOG.info("Scene %s: reusing cached render", scene_id)
            scene_clips.append(VideoFileClip(str(cached_file)))
            continue

        LOG.info("Scene %s: rendering", scene_id)
        duration = float(scene["duration"])
        layers = [build_visual(scene)]
        graphic = build_graphic(scene, duration)
        if graphic is not None:
            layers.append(graphic)
        composed = CompositeVideoClip(layers, size=size).with_duration(duration)
        composed.write_videofile(str(cached_file), fps=manifest.fps, codec="libx264",
                                  audio=False, preset=preset, threads=threads, logger=None)
        composed.close()
        state[str(scene_id)] = {"hash": h, "file": str(cached_file)}
        save_state()
        scene_clips.append(VideoFileClip(str(cached_file)))

    base = concatenate_videoclips(scene_clips, method="compose")

    subtitles_path = manifest.data.get("subtitles_srt")
    if subtitles_path:
        captions = parse_srt(resolve_asset(subtitles_path, manifest.dir, cache_dir / "downloads"))
        sub_clips = [
            TextClip(font=font, text=c.text, font_size=44, color="white",
                     stroke_color="black", stroke_width=2, method="caption",
                     size=(int(size[0] * 0.85), None))
            .with_start(c.start).with_duration(c.end - c.start)
            .with_position(("center", "bottom"))
            for c in captions
        ]
        base = CompositeVideoClip([base, *sub_clips], size=size).with_duration(base.duration)

    audio_tracks = []
    narration_path = manifest.data.get("narration_audio")
    if narration_path:
        audio_tracks.append(AudioFileClip(str(resolve_asset(narration_path, manifest.dir, cache_dir / "downloads"))))
    bgm_path = manifest.data.get("background_music")
    if bgm_path:
        bgm = AudioFileClip(str(resolve_asset(bgm_path, manifest.dir, cache_dir / "downloads")))
        volume = float(manifest.data.get("bgm_volume", 0.15))
        bgm = bgm.with_effects([afx.MultiplyVolume(volume)])
        if bgm.duration < base.duration:
            bgm = bgm.with_effects([afx.AudioLoop(duration=base.duration)])
        else:
            bgm = bgm.subclipped(0, base.duration)
        audio_tracks.append(bgm)
    if audio_tracks:
        base = base.with_audio(CompositeAudioClip(audio_tracks))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.write_videofile(str(output_path), fps=manifest.fps, codec="libx264",
                          audio_codec="aac", preset=preset, threads=threads)
    LOG.info("Wrote %s", output_path)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
SAMPLE_MANIFEST = {
    "resolution": [1920, 1080],
    "fps": 30,
    "font": "assets/fonts/Pretendard-Bold.ttf",
    "narration_audio": "assets/audio/narration.mp3",
    "background_music": "assets/audio/bgm.mp3",
    "bgm_volume": 0.15,
    "subtitles_srt": "assets/subtitles/final.srt",
    "scenes": [
        {
            "id": 1,
            "duration": 5.0,
            "visual": {"type": "image", "path": "assets/images/scene01.jpg", "ken_burns": True, "zoom_ratio": 1.08},
            "graphic": {"text": "출처: 예시 통계청 2026", "position": "bottom_left"},
        },
        {
            "id": 2,
            "duration": 4.0,
            "visual": {"type": "video", "path": "assets/video/broll01.mp4"},
        },
    ],
}


def check_environment() -> list[str]:
    problems = []
    try:
        import moviepy.config as mpconfig
    except ImportError:
        problems.append("moviepy not installed — run: pip install -r scripts/requirements.txt")
        return problems
    # moviepy resolves ffmpeg itself: by default via the bundled imageio-ffmpeg
    # binary (no system install needed), or via $FFMPEG_BINARY if set. Only
    # flag it if moviepy's own resolution actually failed.
    if mpconfig.FFMPEG_BINARY in ("unset", None):
        problems.append(
            "moviepy could not locate an ffmpeg binary. This normally comes "
            "bundled via the imageio-ffmpeg dependency — reinstall "
            "requirements, or see scripts/README.md#dependencies for a "
            "system-ffmpeg fallback."
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "scripts" / "scenes.json",
                         help="Path to the scene manifest JSON (default: scripts/scenes.json)")
    parser.add_argument("--output", type=Path, default=None,
                         help="Output MP4 path (default: output/<manifest-stem>.mp4)")
    parser.add_argument("--cache-dir", type=Path, default=None,
                         help="Per-scene render cache/state dir (default: output/.cache/<manifest-stem>)")
    parser.add_argument("--no-resume", action="store_true", help="Ignore cached scene renders and start clean")
    parser.add_argument("--preset", default=os.environ.get("VIDEO_PRESET", "medium"),
                         help="ffmpeg x264 preset (ultrafast..veryslow); default: medium")
    parser.add_argument("--threads", type=int, default=int(os.environ.get("VIDEO_RENDER_THREADS", os.cpu_count() or 4)))
    parser.add_argument("--validate-only", action="store_true", help="Validate the manifest and exit")
    parser.add_argument("--init", action="store_true", help="Write a sample manifest to --manifest and exit")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    if args.init:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(SAMPLE_MANIFEST, ensure_ascii=False, indent=2), encoding="utf-8")
        LOG.info("Wrote sample manifest to %s", args.manifest)
        return 0

    try:
        manifest = load_manifest(args.manifest)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        LOG.error("Manifest problem: %s", e)
        return 1

    if args.validate_only:
        LOG.info("Manifest OK: %d scene(s)", len(manifest.scenes))
        return 0

    problems = check_environment()
    if problems:
        for p in problems:
            LOG.error(p)
        return 1

    output = args.output or (ROOT / "output" / f"{args.manifest.stem}.mp4")
    cache_dir = args.cache_dir or (ROOT / "output" / ".cache" / args.manifest.stem)

    try:
        render(manifest, output, resume=not args.no_resume, cache_dir=cache_dir,
               preset=args.preset, threads=args.threads)
    except Exception as e:  # noqa: BLE001 - top-level command boundary
        LOG.error("Render failed: %s", e)
        LOG.error("Progress up to the last completed scene is cached in %s — rerun to resume.", cache_dir)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
