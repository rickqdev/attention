"""Render a 3x3 grid PNG from GridResult + source photos.

Produces a square image (900x900) with real photos arranged in grid order,
cover photo highlighted with an orange border and badge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont

CELL = 300        # px per cell
GAP = 4           # px gap between cells
COVER_BORDER = 6  # px cover border thickness
COVER_COLOR = (247, 106, 0)   # #f76a00
BG_COLOR = (240, 240, 240)    # placeholder grey
BADGE_BG = (0, 0, 0, 140)     # semi-transparent black
COVER_BADGE_BG = (*COVER_COLOR, 220)

GRID_SIZE = CELL * 3 + GAP * 2   # 908px


def _load_square(path: Path, size: int) -> Image.Image:
    """Load an image and center-crop to a square of given size."""
    try:
        img = Image.open(path).convert("RGB")
    except Exception:
        return Image.new("RGB", (size, size), BG_COLOR)

    w, h = img.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    img = img.crop((left, top, left + min_side, top + min_side))
    img = img.resize((size, size), Image.LANCZOS)
    return img


def _badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, is_cover: bool) -> None:
    """Draw a small badge in the top-left corner of a cell."""
    pad_x, pad_y = 7, 4
    font_size = 20

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    bx0 = x + 6
    by0 = y + 6
    bx1 = bx0 + tw + pad_x * 2
    by1 = by0 + th + pad_y * 2

    bg = COVER_BADGE_BG if is_cover else BADGE_BG
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=6, fill=bg)
    draw.text((bx0 + pad_x, by0 + pad_y), text, font=font, fill=(255, 255, 255))


def render_grid_png(
    slots: list[dict],
    photos_dir: Union[str, Path],
    output_path: Union[str, Path, None] = None,
) -> Image.Image:
    """
    Render a 3x3 grid image from slot data.

    Args:
        slots: list of dicts with keys: position (1-9), filename
        photos_dir: directory containing the source photos
        output_path: if provided, save PNG to this path

    Returns:
        PIL Image (RGB)
    """
    photos_dir = Path(photos_dir)
    canvas = Image.new("RGB", (GRID_SIZE, GRID_SIZE), (250, 250, 250))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Build position -> slot map
    slot_map = {s["position"]: s for s in slots if 1 <= s.get("position", 0) <= 9}

    for pos in range(1, 10):
        col = (pos - 1) % 3
        row = (pos - 1) // 3
        x = col * (CELL + GAP)
        y = row * (CELL + GAP)
        is_cover = pos == 1

        slot = slot_map.get(pos)
        if slot:
            img_path = photos_dir / slot["filename"]
            cell_img = _load_square(img_path, CELL)
        else:
            cell_img = Image.new("RGB", (CELL, CELL), BG_COLOR)

        canvas.paste(cell_img, (x, y))

        # Cover border
        if is_cover:
            for t in range(COVER_BORDER):
                draw.rectangle(
                    [x + t, y + t, x + CELL - t - 1, y + CELL - t - 1],
                    outline=COVER_COLOR,
                )

        # Badge
        badge_text = "封面" if is_cover else str(pos)
        _badge(draw, x, y, badge_text, is_cover)

    if output_path:
        canvas.save(str(output_path), format="PNG")

    return canvas
