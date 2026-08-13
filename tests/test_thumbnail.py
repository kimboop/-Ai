import pytest
from PIL import Image

from channel_toolkit.thumbnail import TEMPLATES, generate_thumbnail


def test_generate_thumbnail_creates_image_with_expected_size(tmp_path):
    out_path = tmp_path / "thumb.png"

    result = generate_thumbnail("파이썬으로 유튜브 채널 자동화하기", out_path)

    assert result == out_path
    with Image.open(out_path) as img:
        assert img.size == (1280, 720)


def test_generate_thumbnail_wraps_long_text(tmp_path):
    out_path = tmp_path / "thumb.png"

    generate_thumbnail("아주 아주 아주 아주 아주 긴 제목 텍스트를 넣어보는 테스트", out_path)

    assert out_path.exists()


@pytest.mark.parametrize("template", sorted(TEMPLATES))
def test_generate_thumbnail_supports_every_template(template, tmp_path):
    out_path = tmp_path / "thumb.png"

    generate_thumbnail("템플릿 테스트", out_path, template=template)

    assert out_path.exists()


def test_generate_thumbnail_rejects_unknown_template(tmp_path):
    with pytest.raises(ValueError, match="Unknown template"):
        generate_thumbnail("텍스트", tmp_path / "thumb.png", template="not-a-template")


def test_generate_thumbnail_applies_logo_watermark(tmp_path):
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (200, 200), (255, 0, 0, 255)).save(logo_path)
    out_path = tmp_path / "thumb.png"

    generate_thumbnail("워터마크 테스트", out_path, logo_path=logo_path)

    with Image.open(out_path) as img:
        # Well inside the bottom-right logo footprint (padding=24, max
        # width ~18% of 1280px, logo itself is 200x200).
        pixel = img.convert("RGB").getpixel((img.width - 50, img.height - 50))
    assert pixel == (255, 0, 0)
