from PIL import Image

from channel_toolkit.thumbnail import generate_thumbnail


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
