"""
Icon generation and management for Night Light by HT.
Generates high-DPI system tray icons, app icons, and Windows .ico files.
"""

import io
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def create_moon_icon(size: int = 64, active: bool = True, warmth_ratio: float = 0.8) -> Image.Image:
    """
    Creates a crisp, modern anti-aliased Moon icon.
    - active=True: Warm golden/amber glowing moon with subtle rays/stars.
    - active=False: Sleek cool silver/gray outline moon.
    """
    # Render at 4x for smooth supersampled anti-aliasing
    scale = 4
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x = canvas_size * 0.48
    center_y = canvas_size * 0.50
    radius = canvas_size * 0.38

    if active:
        # Calculate warm color based on warmth
        # Amber / Orange: (255, 170, 45) to Deep Amber: (255, 130, 20)
        r = 255
        g = int(140 + (1.0 - warmth_ratio) * 60)
        b = int(20 + (1.0 - warmth_ratio) * 70)

        # Glow layer
        glow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse(
            [
                center_x - radius * 1.15,
                center_y - radius * 1.15,
                center_x + radius * 1.15,
                center_y + radius * 1.15,
            ],
            fill=(r, g, b, 70),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=8 * scale))
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)

        # Base circle for crescent moon
        moon_mask = Image.new("L", (canvas_size, canvas_size), 0)
        mask_draw = ImageDraw.Draw(moon_mask)
        mask_draw.ellipse(
            [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ],
            fill=255,
        )

        # Cutout circle for crescent shape
        cutout_radius = radius * 0.90
        cutout_cx = center_x + radius * 0.52
        cutout_cy = center_y - radius * 0.32
        mask_draw.ellipse(
            [
                cutout_cx - cutout_radius,
                cutout_cy - cutout_radius,
                cutout_cx + cutout_radius,
                cutout_cy + cutout_radius,
            ],
            fill=0,
        )

        # Moon gradient body
        moon_layer = Image.new("RGBA", (canvas_size, canvas_size), (r, g, b, 255))
        
        # Add subtle warm highlight
        highlight = Image.new("RGBA", (canvas_size, canvas_size), (255, 240, 180, 200))
        h_mask = Image.new("L", (canvas_size, canvas_size), 0)
        h_draw = ImageDraw.Draw(h_mask)
        h_draw.ellipse(
            [
                center_x - radius * 0.85,
                center_y - radius * 0.85,
                center_x + radius * 0.2,
                center_y + radius * 0.85,
            ],
            fill=180,
        )
        h_mask = h_mask.filter(ImageFilter.GaussianBlur(radius=4 * scale))
        moon_layer.paste(highlight, (0, 0), h_mask)

        # Little companion sparkle star
        star_cx = canvas_size * 0.72
        star_cy = canvas_size * 0.30
        star_r = canvas_size * 0.08
        draw_star(mask_draw, star_cx, star_cy, star_r)

        # Composite moon using mask
        img.paste(moon_layer, (0, 0), moon_mask)

    else:
        # Inactive State: Sleek silver/dim cool blue moon
        r, g, b = (175, 185, 205)
        moon_mask = Image.new("L", (canvas_size, canvas_size), 0)
        mask_draw = ImageDraw.Draw(moon_mask)
        mask_draw.ellipse(
            [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ],
            fill=255,
        )

        cutout_radius = radius * 0.90
        cutout_cx = center_x + radius * 0.52
        cutout_cy = center_y - radius * 0.32
        mask_draw.ellipse(
            [
                cutout_cx - cutout_radius,
                cutout_cy - cutout_radius,
                cutout_cx + cutout_radius,
                cutout_cy + cutout_radius,
            ],
            fill=0,
        )

        moon_layer = Image.new("RGBA", (canvas_size, canvas_size), (r, g, b, 210))
        img.paste(moon_layer, (0, 0), moon_mask)

    # Downsample with high-quality Lanczos anti-aliasing
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


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
    images[0].save(
        filepath,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )


if __name__ == "__main__":
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    generate_ico_file(assets_dir / "nightlight_active.ico", active=True)
    generate_ico_file(assets_dir / "nightlight_inactive.ico", active=False)
    generate_ico_file(assets_dir / "app.ico", active=True)
    print("Generated all icons successfully!")
