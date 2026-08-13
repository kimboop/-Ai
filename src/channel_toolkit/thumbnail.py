"""Generate YouTube thumbnails: a background plus centered, wrapped title text."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_SIZE = (1280, 720)
DEFAULT_BG_COLOR = (17, 17, 17)
DEFAULT_TEXT_COLOR = (255, 255, 255)
DEFAULT_STROKE_COLOR = (0, 0, 0)

# Pillow's built-in default font has no Hangul glyphs, so titles in Korean
# (this project's primary language) would render as tofu boxes. Bundle a
# font with Korean coverage and use it unless the caller overrides it.
_BUNDLED_FONT = files("channel_toolkit") / "assets" / "fonts" / "NotoSansKR-Variable.ttf"


def _load_font(size: int, font_path: str | None = None):
    if font_path:
        return ImageFont.truetype(font_path, size)
    with as_file(_BUNDLED_FONT) as path:
        return ImageFont.truetype(str(path), size)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_thumbnail(
    text: str,
    output_path: str | Path,
    background_path: str | Path | None = None,
    size: tuple[int, int] = DEFAULT_SIZE,
    font_path: str | None = None,
    font_size: int = 96,
) -> Path:
    if background_path:
        image = Image.open(background_path).convert("RGB").resize(size)
    else:
        image = Image.new("RGB", size, DEFAULT_BG_COLOR)

    draw = ImageDraw.Draw(image)
    font = _load_font(font_size, font_path)

    max_width = int(size[0] * 0.9)
    lines = _wrap_text(draw, text, font, max_width)

    line_height = font.getbbox("Ag")[3] + 10
    total_height = line_height * len(lines)
    y = (size[1] - total_height) // 2

    for line in lines:
        line_width = draw.textlength(line, font=font)
        x = (size[0] - line_width) / 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=DEFAULT_TEXT_COLOR,
            stroke_width=4,
            stroke_fill=DEFAULT_STROKE_COLOR,
        )
        y += line_height

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
