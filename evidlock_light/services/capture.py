"""Zrzut głównego okna aplikacji.

Nagrywanie zostanie rozbudowane na tym samym module, aby nie wiązać logiki
przechwytywania obrazu z konkretnym ekranem GUI.
"""

from __future__ import annotations

from pathlib import Path

from ..config import default_report_path


def capture_window(window, output: str | Path | None = None) -> Path:
    """Zapisuje PNG ograniczony do obszaru głównego okna."""

    from PIL import ImageGrab

    window.update_idletasks()
    x = window.winfo_rootx()
    y = window.winfo_rooty()
    width = window.winfo_width()
    height = window.winfo_height()
    path = Path(output) if output else default_report_path("zrzut_okna", ".png")
    image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def recording_status() -> dict:
    return {
        "available": False,
        "status": "Nagrywanie głównego okna jest zaplanowane jako kolejny etap modułu capture.",
    }
