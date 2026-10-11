#!/usr/bin/env python3
"""트랙 B 롱폼 영상용 씬 그래픽 생성기 (16:9, 6장 고정 세트).

트랙 B는 video_generator.py 같은 자동 영상 조립 파이프라인이 없다 —
사람이 목소리를 녹음하고, 그 위에 올릴 화면을 직접 편집 프로그램에서
붙인다. 이 스크립트는 그 "화면 재료"를 make_thumbnail_longform.py와
같은 남색+골드 브랜드 톤으로 로컬에서 무료로 만든다 (Pixabay/AI 사진
없이 플랫 벡터 아이콘 + 타이포그래피만 사용).

economy/scripts/*.md의 "씬 구성 아이디어" 6개 비주얼 비트에 맞춰
고정된 6장을 한 번에 뽑는다:
  1. 타이틀 카드
  2. 물가 통계 카드 (꺾은선 그래프 아이콘)
  3. 최저임금 통계 카드 (봉투 아이콘)
  4. 대출 통계 카드 (집+그래프 아이콘)
  5. 할 일 체크리스트 (최대 4개)
  6. 구독 유도 CTA 카드

Usage:
    python scripts/make_scene_graphics.py \
        --out-dir "output/scenes/2026-10-11_롱폼_이번주경제뉴스3가지" \
        --title "이번 주 경제 뉴스 3가지" \
        --subtitle "물가 · 최저임금 · 대출" \
        --stat1-label "9월 소비자물가" --stat1-value "2.9%" \
        --stat2-label "2027년 최저임금" --stat2-value "1만700원" \
        --stat3-label "8월 주택담보대출" --stat3-value "+4.3조" \
        --todo "식비·장보기 지출 점검하기" \
        --todo "내년 인건비 미리 계산해보기" \
        --todo "금통위 결과 나오면 이자 부담 확인하기" \
        --todo "대출 규제 최신 내용 재확인하기" \
        --cta "구독과 좋아요 눌러두시면 매주 일요일 저녁에 바로 받아보실 수 있어요"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_generator as vg  # noqa: E402
from make_thumbnail_longform import (  # noqa: E402
    W, H, GOLD, CHANNEL_MARK, _wrap_to_width, _fit_headline,
)

NAVY_TOP = (10, 16, 32)
NAVY_BOTTOM = (26, 38, 66)
CARD_FILL = (22, 32, 56)
TEXT_WHITE = (248, 250, 252)


def _bg(draw, img):
    for y in range(H):
        t = y / H
        r = int(NAVY_TOP[0] + (NAVY_BOTTOM[0] - NAVY_TOP[0]) * t)
        g = int(NAVY_TOP[1] + (NAVY_BOTTOM[1] - NAVY_TOP[1]) * t)
        b = int(NAVY_TOP[2] + (NAVY_BOTTOM[2] - NAVY_TOP[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    draw.rectangle([0, 70, W, 76], fill=GOLD)


def _watermark(draw, font_bold):
    from PIL import ImageFont
    mark_font = ImageFont.truetype(font_bold, 34)
    mb = draw.textbbox((0, 0), CHANNEL_MARK, font=mark_font)
    mw = mb[2] - mb[0]
    draw.text((W - mw - 36, H - 56), CHANNEL_MARK, font=mark_font, fill=(255, 255, 255, 180))


def _draw_line_chart_icon(draw, center, scale=1.0):
    cx, cy = center
    s = 90 * scale
    pts = [(cx - s, cy + s * 0.5), (cx - s * 0.3, cy - s * 0.1),
           (cx + s * 0.3, cy + s * 0.2), (cx + s, cy - s * 0.9)]
    draw.line(pts, fill=GOLD, width=max(4, int(6 * scale)), joint="curve")
    for p in pts:
        draw.ellipse([p[0] - 7 * scale, p[1] - 7 * scale, p[0] + 7 * scale, p[1] + 7 * scale], fill=GOLD)
    draw.line([cx - s, cy + s, cx + s, cy + s], fill=(90, 100, 130), width=2)
    draw.line([cx - s, cy - s, cx - s, cy + s], fill=(90, 100, 130), width=2)


def _draw_envelope_icon(draw, center, scale=1.0):
    cx, cy = center
    w, h = 220 * scale, 150 * scale
    left, top = cx - w / 2, cy - h / 2
    right, bottom = cx + w / 2, cy + h / 2
    draw.rounded_rectangle([left, top, right, bottom], radius=10 * scale, outline=GOLD, width=max(4, int(5 * scale)))
    draw.line([left, top, cx, cy + 6 * scale, right, top], fill=GOLD, width=max(3, int(4 * scale)), joint="curve")
    won_r = 26 * scale
    draw.ellipse([cx - won_r, bottom - won_r * 0.6, cx + won_r, bottom + won_r * 1.2], fill=GOLD)


def _draw_house_loan_icon(draw, center, scale=1.0):
    cx, cy = center
    s = 90 * scale
    house_cx = cx - s * 0.6
    roof = [(house_cx - s * 0.65, cy - s * 0.1), (house_cx, cy - s * 0.75), (house_cx + s * 0.65, cy - s * 0.1)]
    draw.polygon(roof, outline=GOLD, width=max(3, int(5 * scale)))
    draw.rectangle([house_cx - s * 0.5, cy - s * 0.1, house_cx + s * 0.5, cy + s * 0.55], outline=GOLD,
                    width=max(3, int(5 * scale)))
    door_w = s * 0.22
    draw.rectangle([house_cx - door_w / 2, cy + s * 0.1, house_cx + door_w / 2, cy + s * 0.55], outline=GOLD, width=3)

    ax0, ay0 = cx + s * 0.25, cy + s * 0.4
    ax1, ay1 = cx + s * 0.95, cy - s * 0.55
    draw.line([ax0, ay0, ax1, ay1], fill=(234, 90, 90), width=max(4, int(6 * scale)))
    head = 18 * scale
    draw.polygon([(ax1, ay1), (ax1 - head, ay1 + head * 0.3), (ax1 - head * 0.3, ay1 + head)], fill=(234, 90, 90))


def _draw_check_icon(draw, box, checked=True):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=8, outline=GOLD, width=3)
    if checked:
        draw.line([x0 + (x1 - x0) * 0.22, (y0 + y1) / 2,
                   x0 + (x1 - x0) * 0.42, y1 - (y1 - y0) * 0.22], fill=GOLD, width=5)
        draw.line([x0 + (x1 - x0) * 0.42, y1 - (y1 - y0) * 0.22,
                   x1 - (x1 - x0) * 0.18, y0 + (y1 - y0) * 0.2], fill=GOLD, width=5)


def _draw_bell_heart_icon(draw, center, scale=1.0):
    """채워진 종 모양(몸통이 아래로 갈수록 넓어지는 전형적 실루엣) + 추 + 하트."""
    cx, cy = center
    s = 64 * scale
    top_y = cy - s * 0.95
    bottom_y = cy + s * 0.55
    # 종 몸통: 위는 좁고 아래로 갈수록 벌어지는 다각형 실루엣
    body = [
        (cx - s * 0.06, top_y),
        (cx + s * 0.06, top_y),
        (cx + s * 0.18, cy - s * 0.3),
        (cx + s * 0.62, bottom_y),
        (cx - s * 0.62, bottom_y),
        (cx - s * 0.18, cy - s * 0.3),
    ]
    draw.polygon(body, fill=GOLD)
    # 종 받침(아래 테두리 띠)
    draw.rounded_rectangle([cx - s * 0.72, bottom_y, cx + s * 0.72, bottom_y + s * 0.12],
                            radius=s * 0.06, fill=GOLD)
    # 추
    draw.ellipse([cx - s * 0.13, bottom_y + s * 0.18, cx + s * 0.13, bottom_y + s * 0.44], fill=GOLD)
    # 꼭대기 손잡이
    draw.rounded_rectangle([cx - s * 0.09, top_y - s * 0.22, cx + s * 0.09, top_y + s * 0.06],
                            radius=s * 0.05, fill=GOLD)

    hx, hy = cx + s * 1.7, cy + s * 0.1
    hs = 34 * scale
    draw.polygon([
        (hx, hy + hs * 0.8),
        (hx - hs, hy - hs * 0.2),
        (hx - hs * 0.5, hy - hs * 0.9),
        (hx, hy - hs * 0.4),
        (hx + hs * 0.5, hy - hs * 0.9),
        (hx + hs, hy - hs * 0.2),
    ], fill=(234, 90, 90))


def _title_text(draw, text, font_extrabold, y, size=64, fill=TEXT_WHITE, max_lines=1):
    font, lines, heights = _fit_headline(draw, text, font_extrabold, W - 140, max_lines=max_lines,
                                          start_size=size, min_size=32)
    for line, lh in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        draw.text(((W - lw) // 2, y), line, font=font, fill=fill)
        y += lh + 10
    return y


def scene_title(title: str, subtitle: str, font_extrabold, font_bold):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), NAVY_TOP)
    draw = ImageDraw.Draw(img)
    _bg(draw, img)
    y = _title_text(draw, title, font_extrabold, int(H * 0.38), size=84, max_lines=2)
    if subtitle:
        sub_font = ImageFont.truetype(font_bold, 40)
        sb = draw.textbbox((0, 0), subtitle, font=sub_font)
        sw = sb[2] - sb[0]
        draw.text(((W - sw) // 2, y + 16), subtitle, font=sub_font, fill=GOLD)
    _watermark(draw, font_bold)
    return img


def scene_stat(label: str, value: str, icon: str, font_extrabold, font_bold):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), NAVY_TOP)
    draw = ImageDraw.Draw(img)
    _bg(draw, img)

    icon_cy = int(H * 0.37)
    if icon == "chart":
        _draw_line_chart_icon(draw, (W // 2, icon_cy), scale=1.3)
    elif icon == "envelope":
        _draw_envelope_icon(draw, (W // 2, icon_cy), scale=1.2)
    elif icon == "house":
        _draw_house_loan_icon(draw, (W // 2, icon_cy), scale=1.2)

    value_font = ImageFont.truetype(font_extrabold, 110)
    vb = draw.textbbox((0, 0), value, font=value_font)
    vw = vb[2] - vb[0]
    vy = int(H * 0.56)
    draw.text(((W - vw) // 2 + 4, vy + 4), value, font=value_font, fill=(0, 0, 0, 140))
    draw.text(((W - vw) // 2, vy), value, font=value_font, fill=TEXT_WHITE)

    label_font = ImageFont.truetype(font_bold, 38)
    lb = draw.textbbox((0, 0), label, font=label_font)
    lw = lb[2] - lb[0]
    draw.text(((W - lw) // 2, vy + (vb[3] - vb[1]) + 30), label, font=label_font, fill=GOLD)

    _watermark(draw, font_bold)
    return img


def scene_checklist(items: list[str], font_extrabold, font_bold):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), NAVY_TOP)
    draw = ImageDraw.Draw(img)
    _bg(draw, img)

    _title_text(draw, "이번 주 당장 할 일", font_extrabold, 110, size=58, max_lines=1)

    item_font = ImageFont.truetype(font_bold, 34)
    box_size = 44
    row_gap = 36
    text_max_w = W - 260
    y = 250
    for item in items[:4]:
        lines = _wrap_to_width(draw, item, item_font, text_max_w)
        box_top = y + 4
        _draw_check_icon(draw, (130, box_top, 130 + box_size, box_top + box_size), checked=True)
        ty = y
        for line in lines:
            draw.text((200, ty), line, font=item_font, fill=TEXT_WHITE)
            lb = draw.textbbox((0, 0), line, font=item_font)
            ty += (lb[3] - lb[1]) + 10
        y = max(ty, box_top + box_size) + row_gap

    _watermark(draw, font_bold)
    return img


def scene_cta(cta_text: str, font_extrabold, font_bold):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), NAVY_TOP)
    draw = ImageDraw.Draw(img)
    _bg(draw, img)

    _draw_bell_heart_icon(draw, (W // 2, int(H * 0.32)), scale=1.4)

    y = int(H * 0.52)
    cta_font = ImageFont.truetype(font_bold, 42)
    for line in _wrap_to_width(draw, cta_text, cta_font, W - 260):
        lb = draw.textbbox((0, 0), line, font=cta_font)
        lw = lb[2] - lb[0]
        draw.text(((W - lw) // 2, y), line, font=cta_font, fill=TEXT_WHITE)
        y += (lb[3] - lb[1]) + 18

    mark_font = ImageFont.truetype(font_extrabold, 56)
    mb = draw.textbbox((0, 0), CHANNEL_MARK, font=mark_font)
    mw = mb[2] - mb[0]
    draw.text(((W - mw) // 2, y + 30), CHANNEL_MARK, font=mark_font, fill=GOLD)

    return img


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--stat1-label", default="")
    parser.add_argument("--stat1-value", default="")
    parser.add_argument("--stat2-label", default="")
    parser.add_argument("--stat2-value", default="")
    parser.add_argument("--stat3-label", default="")
    parser.add_argument("--stat3-value", default="")
    parser.add_argument("--todo", action="append", default=[], help="최대 4개까지 사용됨")
    parser.add_argument("--cta", required=True)
    args = parser.parse_args()

    font_extrabold = vg.resolve_font("SHORTS_FONT_EXTRABOLD", "NanumGothicExtraBold.ttf")
    font_bold = vg.resolve_font("SHORTS_FONT_BOLD", "NanumGothicBold.ttf")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("scene1_title.png", scene_title(args.title, args.subtitle, font_extrabold, font_bold)),
        ("scene2_stat_price.png",
         scene_stat(args.stat1_label, args.stat1_value, "chart", font_extrabold, font_bold)),
        ("scene3_stat_wage.png",
         scene_stat(args.stat2_label, args.stat2_value, "envelope", font_extrabold, font_bold)),
        ("scene4_stat_loan.png",
         scene_stat(args.stat3_label, args.stat3_value, "house", font_extrabold, font_bold)),
        ("scene5_checklist.png", scene_checklist(args.todo, font_extrabold, font_bold)),
        ("scene6_cta.png", scene_cta(args.cta, font_extrabold, font_bold)),
    ]
    for name, img in jobs:
        out_path = args.out_dir / name
        img.save(out_path)
        print(f"OK: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
