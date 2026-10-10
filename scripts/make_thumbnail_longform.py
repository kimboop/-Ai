#!/usr/bin/env python3
"""트랙 B(경제 뉴스 해설) 롱폼용 16:9 브랜드 썸네일 생성기.

make_thumbnail.py는 트랙 A 쇼츠 전용 9:16 캔버스(vg.TARGET_SIZE)에 고정돼
있어서 트랙 B 롱폼(16:9)에는 그대로 쓸 수 없다. 같은 남색+골드 브랜드
팔레트와 나눔고딕 폰트를 재사용하되, 가로 캔버스 + 숫자 카드 레이아웃으로
새로 만든다. Pixabay 등 외부 이미지 없이 타이포그래피만으로 구성해서
네트워크가 막힌 환경에서도 바로 쓸 수 있다.

Usage (카드형, --style cards 또는 생략 시 기본값):
    python scripts/make_thumbnail_longform.py \
        --headline "이번 주 경제 뉴스 3가지" \
        --subtitle "물가 · 최저임금 · 대출" \
        --stat "9월 물가:2.9%" \
        --stat "2027 최저임금:1만700원" \
        --stat "8월 주담대:+4.3조" \
        --output output/thumbnails/2026-10-11_롱폼_썸네일.png

Usage (미니멀 큰 숫자형, --style minimal):
    python scripts/make_thumbnail_longform.py --style minimal \
        --hero-label "9월 소비자물가" \
        --hero-value "2.9%" \
        --headline "물가, 더 올랐다" \
        --footer "최저임금 1만700원 · 가계대출 +4.3조" \
        --output output/thumbnails/2026-10-11_롱폼_썸네일_미니멀.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_generator as vg  # noqa: E402

W, H = 1280, 720
GOLD = vg.GOLD_ACCENT[:3]
CHANNEL_MARK = "고달프"


def _wrap_to_width(draw, text: str, font, max_width: int) -> list[str]:
    words = text.split(" ")
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
    return lines or [""]


def _fit_headline(draw, title: str, font_path: str, max_width: int, max_lines: int = 2,
                   start_size: int = 86, min_size: int = 44, step: int = 6):
    from PIL import ImageFont

    size = start_size
    while True:
        font = ImageFont.truetype(font_path, size)
        lines = _wrap_to_width(draw, title, font, max_width)
        if len(lines) <= max_lines or size <= min_size:
            heights = [draw.textbbox((0, 0), ln, font=font)[3] - draw.textbbox((0, 0), ln, font=font)[1]
                       for ln in lines]
            return font, lines, heights
        size -= step


def _draw_stat_card(draw, font_label, font_value, center_x: int, top: int, card_w: int, card_h: int,
                     label: str, value: str) -> None:
    left = center_x - card_w // 2
    draw.rounded_rectangle(
        [left, top, left + card_w, top + card_h], radius=18,
        fill=(22, 32, 56), outline=GOLD, width=2,
    )
    vb = draw.textbbox((0, 0), value, font=font_value)
    vw = vb[2] - vb[0]
    draw.text((center_x - vw // 2, top + 34), value, font=font_value, fill=(248, 250, 252))

    lb = draw.textbbox((0, 0), label, font=font_label)
    lw = lb[2] - lb[0]
    draw.text((center_x - lw // 2, top + card_h - 56), label, font=font_label, fill=GOLD)


def make_thumbnail(headline: str, subtitle: str, stats: list[tuple[str, str]],
                    font_extrabold: str, font_bold: str):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (W, H), (8, 12, 24))
    draw = ImageDraw.Draw(img)

    top, bottom = (10, 16, 32), (26, 38, 66)
    for y in range(H):
        t = y / H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    draw.rectangle([0, 70, W, 76], fill=GOLD)

    headline_font, lines, line_heights = _fit_headline(draw, headline, font_extrabold, W - 140)
    y = 100
    for line, lh in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        draw.text((x + 3, y + 3), line, font=headline_font, fill=(0, 0, 0, 160))
        draw.text((x, y), line, font=headline_font, fill=(248, 250, 252))
        y += lh + 16

    if subtitle:
        sub_font = ImageFont.truetype(font_bold, 38)
        sb = draw.textbbox((0, 0), subtitle, font=sub_font)
        sw = sb[2] - sb[0]
        draw.text(((W - sw) // 2, y + 10), subtitle, font=sub_font, fill=GOLD)
        y += (sb[3] - sb[1]) + 10

    if stats:
        n = len(stats)
        card_w, card_h = 330, 230
        gap = 36
        total_w = n * card_w + (n - 1) * gap
        start_x = (W - total_w) // 2 + card_w // 2
        card_top = max(y + 40, H - card_h - 110)
        font_label = ImageFont.truetype(font_bold, 30)
        font_value = ImageFont.truetype(font_extrabold, 56)
        for i, (label, value) in enumerate(stats):
            cx = start_x + i * (card_w + gap)
            _draw_stat_card(draw, font_label, font_value, cx, card_top, card_w, card_h, label, value)

    mark_font = ImageFont.truetype(font_bold, 34)
    mb = draw.textbbox((0, 0), CHANNEL_MARK, font=mark_font)
    mw = mb[2] - mb[0]
    draw.text((W - mw - 36, H - 56), CHANNEL_MARK, font=mark_font, fill=(255, 255, 255, 180))

    return img


def make_thumbnail_minimal(hero_label: str, hero_value: str, headline: str, footer: str,
                            font_extrabold: str, font_bold: str):
    """숫자 하나만 화면 중앙에 거대하게 띄우고 나머지는 여백으로 비우는
    미니멀 스타일. 클릭을 유도하는 핵심 '충격 숫자' 하나에 집중한다."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (W, H), (8, 12, 24))
    draw = ImageDraw.Draw(img)

    top, bottom = (9, 14, 28), (20, 30, 54)
    for y in range(H):
        t = y / H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 아주 옅은 대형 원형 테두리 — 배경이 완전히 빈 느낌이 나지 않도록 하는 장식
    ring_r = 300
    draw.ellipse(
        [W // 2 - ring_r, H // 2 - 20 - ring_r, W // 2 + ring_r, H // 2 - 20 + ring_r],
        outline=(212, 175, 55, 60), width=2,
    )

    label_h = 0
    if hero_label:
        label_font = ImageFont.truetype(font_bold, 36)
        lb = draw.textbbox((0, 0), hero_label, font=label_font)
        lw = lb[2] - lb[0]
        label_h = lb[3] - lb[1]
        draw.text(((W - lw) // 2, 90), hero_label, font=label_font, fill=GOLD)

    # 아래쪽에 헤드라인 1줄(~70px) + 푸터 1줄(~50px) + 여백이 들어갈 공간을
    # 먼저 예약해두고, 숫자는 폭(68%)과 '남은 높이' 둘 다를 넘지 않을 때까지 줄인다.
    reserved_bottom = (70 if headline else 0) + (50 if footer else 0) + 60
    top_used = 90 + label_h + 30
    max_value_width = int(W * 0.68)
    max_value_height = H - top_used - reserved_bottom
    size = 320
    hero_font = ImageFont.truetype(font_extrabold, size)
    vb = draw.textbbox((0, 0), hero_value, font=hero_font)
    while ((vb[2] - vb[0]) > max_value_width or (vb[3] - vb[1]) > max_value_height) and size > 70:
        size -= 10
        hero_font = ImageFont.truetype(font_extrabold, size)
        vb = draw.textbbox((0, 0), hero_value, font=hero_font)
    vw = vb[2] - vb[0]
    vx = (W - vw) // 2
    vy = top_used - vb[1]
    draw.text((vx + 6, vy + 6), hero_value, font=hero_font, fill=(0, 0, 0, 140))
    draw.text((vx, vy), hero_value, font=hero_font, fill=(248, 250, 252))

    # 실제로 그려진 바닥선은 draw.text의 anchor 기준(top-left) + bbox bottom이므로
    # vb[3](= draw.textbbox((0,0),...)의 bottom)을 그대로 더해 실제 하단 y를 구한다.
    y = vy + vb[3] + 40
    if headline:
        headline_font, lines, line_heights = _fit_headline(draw, headline, font_extrabold, W - 160,
                                                             max_lines=1, start_size=56, min_size=36)
        for line, lh in zip(lines, line_heights):
            bbox = draw.textbbox((0, 0), line, font=headline_font)
            lw = bbox[2] - bbox[0]
            draw.text(((W - lw) // 2, y), line, font=headline_font, fill=(248, 250, 252))
            y += lh + 14

    if footer:
        footer_font = ImageFont.truetype(font_bold, 30)
        fb = draw.textbbox((0, 0), footer, font=footer_font)
        fw = fb[2] - fb[0]
        draw.text(((W - fw) // 2, y + 10), footer, font=footer_font, fill=(180, 190, 210))

    mark_font = ImageFont.truetype(font_bold, 34)
    mb2 = draw.textbbox((0, 0), CHANNEL_MARK, font=mark_font)
    mw = mb2[2] - mb2[0]
    draw.text((W - mw - 36, H - 56), CHANNEL_MARK, font=mark_font, fill=(255, 255, 255, 180))

    return img


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--style", choices=["cards", "minimal"], default="cards")
    parser.add_argument("--headline", default="")
    parser.add_argument("--subtitle", default="", help="cards 스타일 전용")
    parser.add_argument("--stat", action="append", default=[],
                         help="cards 스타일 전용. '라벨:값' 형식, 최대 3개까지 권장 (예: '9월 물가:2.9%')")
    parser.add_argument("--hero-label", default="", help="minimal 스타일 전용. 큰 숫자 위 작은 라벨")
    parser.add_argument("--hero-value", default="", help="minimal 스타일 전용. 화면 중앙의 초대형 숫자")
    parser.add_argument("--footer", default="", help="minimal 스타일 전용. 하단 보조 텍스트")
    parser.add_argument("--output", type=Path, default=vg.ROOT / "output" / "thumbnails" / "longform_thumbnail.png")
    args = parser.parse_args()

    font_extrabold = vg.resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")
    font_bold = vg.resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")

    if args.style == "minimal":
        if not args.hero_value:
            parser.error("--style minimal에는 --hero-value가 필요합니다")
        img = make_thumbnail_minimal(args.hero_label, args.hero_value, args.headline, args.footer,
                                      font_extrabold, font_bold)
    else:
        if not args.headline:
            parser.error("--style cards에는 --headline이 필요합니다")
        stats: list[tuple[str, str]] = []
        for raw in args.stat[:3]:
            if ":" not in raw:
                print(f"무시됨 (':' 없음): {raw}")
                continue
            label, value = raw.split(":", 1)
            stats.append((label.strip(), value.strip()))
        img = make_thumbnail(args.headline, args.subtitle, stats, font_extrabold, font_bold)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.output)
    print(f"OK: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
