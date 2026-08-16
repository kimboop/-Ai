#!/usr/bin/env python3
"""아빠모해TV 쇼츠 파이프라인 수동 스모크 테스트.

`generate_premium_shorts()`를 아주 짧은 인라인 샘플(2씬)로 바로 실행해서
에러 없이 MP4가 나오는지 빠르게 확인하는 용도다. CLI 서브커맨드가 아니라
독립 스크립트로 둔 이유는 "지금 당장 돌려보기" 외의 다른 용도가 없어서다
(정식 입력은 `video_generator.py episode.json`처럼 파일로 넘긴다).

API 키는 절대 이 파일에 하드코딩하지 않는다 — CLAUDE.md의 "API 키를
채팅/커밋에 붙여넣지 않기" 규칙과 동일하게, 환경변수로만 받는다.

Usage:
    PEXELS_API_KEY=... python scripts/test_run.py
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_generator as vg  # noqa: E402

SAMPLE_EPISODE = {
    "title": "테스트 리포트",
    "scenes": [
        {"script": "테스트 첫 번째 문장입니다.", "pexels_query": "city night vertical"},
        {"script": "테스트 두 번째 문장입니다.", "pexels_query": "ocean waves vertical"},
    ],
}


def main() -> int:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("test_run")

    pexels_key = os.environ.get("PEXELS_API_KEY")
    if not pexels_key:
        log.error("Missing PEXELS_API_KEY env var. Run: PEXELS_API_KEY=... python scripts/test_run.py")
        return 1

    problems = vg.check_environment()
    if problems:
        for p in problems:
            log.error(p)
        return 1

    output = vg.ROOT / "output" / "test_run.mp4"
    work_dir = vg.ROOT / "output" / ".cache" / "test_run"

    try:
        vg.generate_premium_shorts(
            SAMPLE_EPISODE, pexels_key, voice=os.environ.get("SHORTS_TTS_VOICE", "ko-KR-SunHiNeural"),
            output_path=output, work_dir=work_dir, resume=True,
            fps=24, preset="ultrafast", threads=os.cpu_count() or 2,
        )
    except Exception as e:  # noqa: BLE001 - smoke-test boundary, want the real traceback below
        log.error("Test run failed: %s", e)
        raise
    log.info("OK: %s (%d bytes)", output, output.stat().st_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
