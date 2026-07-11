"""Lekki znak EvidLock: tarcza i klodka rysowane jak w EvidLockV2."""

from __future__ import annotations

import tkinter as tk


class EvidLockLogo(tk.Canvas):
    def __init__(self, parent, background: str, accent: str, fill: str, size: int = 58) -> None:
        super().__init__(parent, width=size, height=size, bg=background, highlightthickness=0, bd=0)
        scale = size / 58
        points = [29, 4, 53, 15, 48, 45, 29, 56, 10, 45, 5, 15]
        points = [round(value * scale) for value in points]
        self.create_polygon(*points, fill=fill, outline=accent, width=max(2, round(4 * scale)))
        self.create_rectangle(19 * scale, 27 * scale, 39 * scale, 42 * scale, outline=accent, width=max(2, round(3 * scale)))
        self.create_arc(19 * scale, 15 * scale, 39 * scale, 37 * scale, start=0, extent=180, outline=accent, width=max(2, round(3 * scale)), style=tk.ARC)
