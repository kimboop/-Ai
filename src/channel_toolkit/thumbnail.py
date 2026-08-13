"""Generate YouTube thumbnails: a styled background plus centered, wrapped title text."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_SIZE = (1280, 720)

# Named style presets. "solid" backgrounds use a single color; "gradient"
# backgrounds blend two colors along `direction`. Add new looks here rather
# than passing raw colors through the CLI/API — keeps output consistent.
TEMPLATES = {
    "dark": {
        "kind": "solid",
        "colors": [(17, 17, 17)],
        "text_color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
    },
    "sunset": {
        "kind": "gradient",
        "colors": [(255, 94, 77), (255, 195, 113)],
        "direction": "horizontal",
        "text_color": (40, 15, 5),
        "stroke_color": (255, 255, 255),
    },
    "ocean": {
        "kind": "gradient",
        "colors": [(9, 32, 63), (0, 168, 204)],
        "direction": "vertical",
        "text_color": (255, 255, 255),
        "stroke_color": (0, 20, 40),
    },
    "minimal-light": {
        "kind": "solid",
        "colors": [(245, 245, 245)],
        "text_color": (20, 20, 20),
        "stroke_color": (255, 255, 255),
    },
}

LOGO_POSITIONS = ("bottom-right", "bottom-left", "top-right", "top-left")

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


def _linear_gradient(
    size: tuple[int, int],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    direction: str = "vertical",
) -> Image.Image:
    width, height = size
    base = Image.new("RGB", size, start)
    top = Image.new("RGB", size, end)
    mask = Image.new("L", size)

    if direction == "horizontal":
        row = [int(255 * x / max(width - 1, 1)) for x in range(width)]
        mask_data = row * height
    else:
        mask_data = [
            value for y in range(height) for value in [int(255 * y / max(height - 1, 1))] * width
        ]
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


def _make_background(size: tuple[int, int], style: dict) -> Image.Image:
    if style["kind"] == "solid":
        return Image.new("RGB", size, style["colors"][0])
    start, end = style["colors"]
    return _linear_gradient(size, start, end, direction=style.get("direction", "vertical"))


def _apply_watermark(
    image: Image.Image,
    logo_path: str | Path,
    position: str = "bottom-right",
    padding: int = 24,
    opacity: float = 1.0,
    max_width_ratio: float = 0.18,
) -> Image.Image:
    if position not in LOGO_POSITIONS:
        raise ValueError(
            f"Unknown logo position {position!r}. Available: {', '.join(LOGO_POSITIONS)}"
        )

    logo = Image.open(logo_path).convert("RGBA")
    max_width = int(image.width * max_width_ratio)
    if logo.width > max_width:
        ratio = max_width / logo.width
        logo = logo.resize((max_width, max(1, int(logo.height * ratio))))
    if opacity < 1.0:
        alpha = logo.split()[3].point(lambda p: int(p * opacity))
        logo.putalpha(alpha)

    x = padding if "left" in position else image.width - logo.width - padding
    y = padding if "top" in position else image.height - logo.height - padding
    image.paste(logo, (x, y), logo)
    return image


def generate_thumbnail(
    text: str,
    output_path: str | Path,
    background_path: str | Path | None = None,
    size: tuple[int, int] = DEFAULT_SIZE,
    font_path: str | None = None,
    font_size: int = 96,
    template: str = "dark",
    logo_path: str | Path | None = None,
    logo_position: str = "bottom-right",
    logo_opacity: float = 1.0,
) -> Path:
    if template not in TEMPLATES:
        raise ValueError(
            f"Unknown template {template!r}. Available: {', '.join(sorted(TEMPLATES))}"
        )
    style = TEMPLATES[template]

    if background_path:
        image = Image.open(background_path).convert("RGB").resize(size)
    else:
        image = _make_background(size, style)

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
            fill=style["text_color"],
            stroke_width=4,
            stroke_fill=style["stroke_color"],
        )
        y += line_height

    if logo_path:
        image = _apply_watermark(
            image.convert("RGBA"), logo_path, position=logo_position, opacity=logo_opacity
        ).convert("RGB")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
