"""Logo generowane dokładnie tym samym algorytmem co w EvidLockV2."""

from __future__ import annotations

import customtkinter as ctk
from PIL import Image, ImageDraw


class EvidLockLogo(ctk.CTkLabel):
    """Przezroczysta tarcza z kłódką i antyaliasowanym konturem V2."""

    def __init__(self, parent, background: str, accent: str, fill: str, size: int = 58) -> None:
        scale = 3
        image = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        width = 3 * scale
        draw.polygon(
            [(21 * scale, 4 * scale), (36 * scale, 10 * scale), (33 * scale, 31 * scale),
             (21 * scale, 39 * scale), (9 * scale, 31 * scale), (6 * scale, 10 * scale)],
            outline=accent,
            width=width,
            fill=None,
        )
        draw.rectangle((15 * scale, 21 * scale, 27 * scale, 31 * scale), outline=accent, width=width)
        draw.arc((14 * scale, 11 * scale, 28 * scale, 25 * scale), 180, 360, fill=accent, width=width)
        image = image.resize((size, size), Image.Resampling.LANCZOS)
        self.logo_image = ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
        super().__init__(parent, text="", image=self.logo_image, fg_color="transparent", width=size, height=size)
