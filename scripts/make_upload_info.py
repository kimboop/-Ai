#!/usr/bin/env python3
"""에피소드 JSON에서 업로드용 제목·설명·해시태그를 뽑아 텍스트 파일로 저장.

썸네일 옆에 같이 두고 YouTube Studio 업로드 시 바로 복붙할 수 있게 하기
위한 용도. episode JSON에 "description"/"hashtags" 필드가 없으면 빈 채로
두지 않고 직접 채워야 한다는 안내 문구를 남긴다 — 파일이 있는데 내용이
비어 있으면 업로드 직전에야 빠진 걸 알아차리기 쉬우므로.

Usage:
    python scripts/make_upload_info.py \
        --episode scripts/episode_2026-10-09_kramatorsk-bus-bombing.json \
        --output output/thumbnails/episode_2026-10-09_kramatorsk-bus-bombing.upload.txt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def format_upload_info(episode: dict) -> str:
    # upload_title이 있으면 그걸 우선한다 — episode.json의 title은 영상 내
    # 타이틀바/썸네일 헤드라인용 작업용 제목이라, 검색 키워드를 넣어 다듬은
    # 최종 업로드 제목과 다를 수 있다(예: title에는 없는 지명/숫자를
    # upload_title에만 추가하는 식).
    title = (episode.get("upload_title") or episode.get("title", "")).strip() \
        or "[제목 없음 — episode JSON의 title/upload_title 필드 확인]"
    description = episode.get("description", "").strip()
    hashtags = [h if h.startswith("#") else f"#{h}" for h in episode.get("hashtags", [])]

    lines = ["[업로드용 제목]", title, "", "[설명]"]
    lines.append(description or "(episode JSON에 description 필드가 없음 — 직접 작성 필요)")
    lines += ["", "[해시태그]"]
    lines.append(" ".join(hashtags) if hashtags else "(episode JSON에 hashtags 필드가 없음 — 직접 작성 필요)")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    episode = json.loads(args.episode.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(format_upload_info(episode), encoding="utf-8")
    print(f"OK: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
