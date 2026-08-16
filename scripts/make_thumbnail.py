#!/usr/bin/env python3
"""아빠모해TV 쇼츠용 브랜드 썸네일 생성기.

Pexels 등 외부 이미지 소스 없이, video_generator.py가 이미 쓰는 프리미엄
뉴스 팔레트(남색 배경 + 골드 포인트)와 나눔고딕 폰트만으로 9:16 썸네일을
만든다. 실제 배경 영상/사진이 필요 없어서 네트워크가 막힌 환경에서도 바로
쓸 수 있다 — 짧고 굵은 헤드라인 중심의 타이포그래피 썸네일은 뉴스/정보성
쇼츠에서 흔히 쓰이는, 그 자체로 유효한 스타일이다.

Usage:
    python scripts/make_thumbnail.py \
        --title "로봇이 스스로\n배터리를 간다" \
        --kicker "테크 이슈" \
        --subtitle "3분 만에 — 테슬라 vs 보스턴다이내믹스" \
        --output output/thumbnails/robot-battery.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_generator as vg  # noqa: E402


def make_thumbnail(title: str, kicker: str, subtitle: str, font_extrabold: str, font_bold: str):
    from PIL import Image, ImageDraw, ImageFont

    W, H = vg.TARGET_SIZE
    img = Image.new("RGB", (W, H), (8, 12, 24))
    draw = ImageDraw.Draw(img)

    # 남색 세로 그라데이션 배경
    top = (10, 16, 32)
    bottom = (26, 38, 66)
    for y in range(H):
        t = y / H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 골드 액센트 바 (상단)
    draw.rectangle([0, int(H * 0.40), W, int(H * 0.40) + 6], fill=vg.GOLD_ACCENT[:3])

    # 킥커(작은 라벨) 배지
    kicker_font = ImageFont.truetype(font_bold, 44)
    kb = draw.textbbox((0, 0), kicker, font=kicker_font)
    kw, kh = kb[2] - kb[0], kb[3] - kb[1]
    kx, ky = (W - kw) // 2, int(H * 0.22)
    pad_x, pad_y = 28, 14
    draw.rounded_rectangle(
        [kx - pad_x, ky - pad_y, kx + kw + pad_x, ky + kh + pad_y],
        radius=10, fill=(212, 175, 55, 255),
    )
    draw.text((kx, ky), kicker, font=kicker_font, fill=(15, 23, 42, 255))

    # 헤드라인 (여러 줄 지원 — \n으로 줄바꿈)
    headline_font = ImageFont.truetype(font_extrabold, 118)
    lines = title.split("\n")
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        line_heights.append(bbox[3] - bbox[1])
    y = int(H * 0.47)
    for line, lh in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        # 얇은 그림자로 가독성 확보
        draw.text((x + 4, y + 4), line, font=headline_font, fill=(0, 0, 0, 160))
        draw.text((x, y), line, font=headline_font, fill=(248, 250, 252, 255))
        y += lh + 24

    # 서브타이틀
    sub_font = ImageFont.truetype(font_bold, 52)
    sb = draw.textbbox((0, 0), subtitle, font=sub_font)
    sw = sb[2] - sb[0]
    draw.text(((W - sw) // 2, y + 24), subtitle, font=sub_font, fill=(212, 175, 55, 255))

    _draw_battery_bolt_icon(draw, center=(W // 2, int(H * 0.80)), scale=1.0)

    # 채널 워터마크
    mark_font = ImageFont.truetype(font_bold, 40)
    mark = "아빠모해TV"
    mb = draw.textbbox((0, 0), mark, font=mark_font)
    mw = mb[2] - mb[0]
    draw.text((W - mw - 50, H - 110), mark, font=mark_font, fill=(255, 255, 255, 180))

    return img


def _draw_battery_bolt_icon(draw, center: tuple, scale: float = 1.0) -> None:
    """빈 하단 공간을 채우는 미니멀 배터리+번개 아이콘 (실사 이미지 없이도
    '배터리/전력' 주제를 시각적으로 암시)."""
    cx, cy = center
    bw, bh = int(180 * scale), int(280 * scale)
    nub_w, nub_h = int(70 * scale), int(22 * scale)
    left = cx - bw // 2
    top = cy - bh // 2
    outline = (212, 175, 55, 255)
    lw = max(6, int(8 * scale))

    draw.rounded_rectangle(
        [left, top + nub_h, left + bw, top + bh], radius=int(20 * scale),
        outline=outline, width=lw,
    )
    draw.rounded_rectangle(
        [cx - nub_w // 2, top, cx + nub_w // 2, top + nub_h + 6],
        radius=int(6 * scale), fill=outline,
    )
    # 번개 볼트 (채워진 다각형)
    bolt = [
        (cx + int(28 * scale), top + nub_h + int(40 * scale)),
        (cx - int(18 * scale), top + nub_h + int(150 * scale)),
        (cx + int(6 * scale), top + nub_h + int(150 * scale)),
        (cx - int(28 * scale), top + nub_h + int(250 * scale)),
        (cx + int(30 * scale), top + nub_h + int(125 * scale)),
        (cx + int(4 * scale), top + nub_h + int(125 * scale)),
    ]
    draw.polygon(bolt, fill=(248, 250, 252, 255))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True, help="헤드라인. \\n으로 줄바꿈")
    parser.add_argument("--kicker", default="테크 이슈")
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--output", type=Path, default=vg.ROOT / "output" / "thumbnail.png")
    args = parser.parse_args()

    font_extrabold = vg.resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")
    font_bold = vg.resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")

    img = make_thumbnail(args.title.replace("\\n", "\n"), args.kicker, args.subtitle,
                          font_extrabold, font_bold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.output)
    print(f"OK: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
