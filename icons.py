"""
Icon generation and management for Night Light by HT.
Generates high-DPI system tray icons, app icons, and Windows .ico files.
"""

import io
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def create_moon_icon(size: int = 64, active: bool = True, warmth_ratio: float = 0.8) -> Image.Image:
    """Draw a transparent, supersampled crescent that stays legible at tray sizes."""
    scale = 8
    edge = size * scale
    mask = Image.new("L", (edge, edge), 0)
    draw = ImageDraw.Draw(mask)
    # A substantial silhouette survives the 16 px title bar without a fuzzy halo.
    draw.ellipse((edge * .10, edge * .09, edge * .88, edge * .91), fill=255)
    draw.ellipse((edge * .36, edge * .01, edge * 1.04, edge * .72), fill=0)
    if size >= 24:
        draw_star(draw, edge * .77, edge * .25, edge * .065)
    warmth = max(0.0, min(1.0, warmth_ratio))
    color = (222, int(144 - 26 * warmth), 29) if active else (137, 155, 179)
    image = Image.new("RGBA", (edge, edge), color + (255,))
    image.putalpha(mask)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def draw_star(draw_obj, cx, cy, r):
    """Draws a 4-point sparkle star."""
    points = [
        (cx, cy - r),
        (cx + r * 0.25, cy - r * 0.25),
        (cx + r, cy),
        (cx + r * 0.25, cy + r * 0.25),
        (cx, cy + r),
        (cx - r * 0.25, cy + r * 0.25),
        (cx - r, cy),
        (cx - r * 0.25, cy - r * 0.25),
    ]
    draw_obj.polygon(points, fill=255)


def generate_ico_file(filepath: Path, active: bool = True):
    """Generates a multi-resolution Windows .ico file."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [create_moon_icon(s, active=active) for s in sizes]
    images[-1].save(
        filepath,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1],
    )


if __name__ == "__main__":
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    generate_ico_file(assets_dir / "nightlight_active.ico", active=True)
    generate_ico_file(assets_dir / "nightlight_inactive.ico", active=False)
    generate_ico_file(assets_dir / "app.ico", active=True)
    print("Generated all icons successfully!")
