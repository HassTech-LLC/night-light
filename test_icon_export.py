from PIL import Image

from icons import generate_ico_file


def test_export_preserves_all_windows_sizes_and_transparent_corners(tmp_path):
    path = tmp_path / 'moon.ico'
    generate_ico_file(path)
    with Image.open(path) as icon:
        assert icon.ico.sizes() == {(s, s) for s in (16, 24, 32, 48, 64, 128, 256)}
        for size in icon.ico.sizes():
            frame = icon.ico.getimage(size).convert('RGBA')
            assert frame.getpixel((0, 0))[3] == 0
            assert frame.getchannel('A').getextrema() == (0, 255)
