"""Build the small animated support banner used by the GitHub README."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "media" / "support-night-light.gif"
FONT_DIR = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def frame(index: int, count: int) -> Image.Image:
    width, height = 880, 240
    phase = index / count * math.tau
    image = Image.new("RGB", (width, height), "#0b0d11")
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    pulse = 10 + int(4 * (1 + math.sin(phase)))
    glow_draw.ellipse((46 - pulse, 26 - pulse, 250 + pulse, 230 + pulse), fill=(243, 173, 61, 46))
    image = Image.alpha_composite(image.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(34)))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((2, 2, width - 3, height - 3), 30, fill="#15181e", outline="#41454e", width=2)
    draw.arc((39, 20, 250, 231), 20 + index * 6, 304 + index * 6, fill="#f3ad3d", width=2)
    star_angle = phase - 0.6
    star_x = 145 + math.cos(star_angle) * 104
    star_y = 126 + math.sin(star_angle) * 104
    draw.ellipse((star_x - 4, star_y - 4, star_x + 4, star_y + 4), fill="#ffd27d")

    # Warm mug with a crescent cut into it.
    draw.rounded_rectangle((76, 91, 194, 178), 20, fill="#f3ad3d")
    draw.arc((172, 104, 226, 162), 270, 90, fill="#f3ad3d", width=13)
    draw.ellipse((112, 111, 151, 150), fill="#171a20")
    draw.ellipse((124, 104, 158, 140), fill="#f3ad3d")

    for offset, x in enumerate((105, 136, 164)):
        travel = (index * 5 + offset * 12) % 48
        alpha = int(210 * (1 - travel / 48))
        steam = Image.new("RGBA", image.size, (0, 0, 0, 0))
        steam_draw = ImageDraw.Draw(steam)
        y = 86 - travel
        steam_draw.arc((x - 11, y - 19, x + 11, y + 17), 100, 270, fill=(255, 245, 220, alpha), width=4)
        image = Image.alpha_composite(image, steam)

    draw = ImageDraw.Draw(image)
    draw.text((285, 43), "KEEP THE NIGHTS CALM.", font=font("segoeuib.ttf", 17), fill="#f3ad3d")
    draw.text((285, 72), "Keep the project free.", font=font("georgiai.ttf", 38), fill="#fffaf0")
    draw.text((287, 124), "Optional support funds development, Windows testing, and clear research.", font=font("segoeui.ttf", 15), fill="#c5c2bc")
    draw.rounded_rectangle((285, 163, 548, 210), 23, fill="#f3ad3d")
    draw.text((312, 176), "BUY NIGHT LIGHT A COFFEE", font=font("segoeuib.ttf", 12), fill="#211506")
    draw.text((570, 176), "Every feature stays free.", font=font("segoeui.ttf", 13), fill="#e4e0d7")
    return image.convert("RGB")


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rgb_frames = [frame(i, 24) for i in range(24)]
    palette = rgb_frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    frames = [palette, *[item.quantize(palette=palette, dither=Image.Dither.NONE) for item in rgb_frames[1:]]]
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=False)
    print(OUTPUT)


if __name__ == "__main__":
    main()
