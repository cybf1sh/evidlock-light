"""Lekkie, skalowalne ikony akcji renderowane przez Pillow."""

from __future__ import annotations

from PIL import Image, ImageDraw


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = str(hex_color or "#15803d").lstrip("#")
    if len(value) != 6:
        return 21, 128, 61
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def one_click_icon(color: str, size: int = 64) -> Image.Image:
    """Przezroczysta tarcza z delikatnym znacznikiem integralności."""

    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    ink = (*_rgb(color), 255)
    width = max(5, size * scale // 22)
    shield = [
        (32 * scale, 7 * scale), (53 * scale, 15 * scale), (51 * scale, 37 * scale),
        (45 * scale, 48 * scale), (32 * scale, 57 * scale), (19 * scale, 48 * scale),
        (13 * scale, 37 * scale), (11 * scale, 15 * scale), (32 * scale, 7 * scale),
    ]
    draw.line(shield, fill=ink, width=width, joint="curve")
    draw.line(
        [(21 * scale, 32 * scale), (29 * scale, 40 * scale), (44 * scale, 23 * scale)],
        fill=ink, width=width, joint="curve",
    )
    radius = width // 2
    for x, y in ((21, 32), (44, 23)):
        draw.ellipse((x * scale - radius, y * scale - radius, x * scale + radius, y * scale + radius), fill=ink)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)
