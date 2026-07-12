"""Zrzuty okien aplikacji i pulpitu wykonywane przez WinAPI."""

from __future__ import annotations

import datetime as dt
import re
import time
from pathlib import Path

from .. import winapi
from ..config import SCREENSHOTS_DIR, ensure_runtime_dirs


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ_-]+", "_", str(value or "okno")).strip("_")
    return cleaned[:70] or "okno"


def _output_path(kind: str, name: str = "") -> Path:
    ensure_runtime_dirs()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    suffix = f"_{_safe_name(name)}" if name else ""
    return SCREENSHOTS_DIR / f"zrzut_{kind}{suffix}_{stamp}.png"


def capture_window(window, output: str | Path | None = None) -> Path:
    """Podnosi okno i zapisuje jego rzeczywistą zawartość przez BitBlt."""

    window.deiconify()
    window.lift()
    try:
        window.attributes("-topmost", True)
    except Exception:
        pass
    window.update()
    window.update_idletasks()
    time.sleep(0.18)
    title = str(window.title() or "aplikacja")
    path = Path(output) if output else _output_path("okna", title)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        winapi.capture_visible_window_image(int(window.winfo_id())).save(path, "PNG")
    finally:
        try:
            window.attributes("-topmost", False)
        except Exception:
            pass
    return path.resolve()


def capture_windows(windows: list[object]) -> list[Path]:
    return [capture_window(window) for window in windows]


def capture_desktop(output: str | Path | None = None) -> Path:
    """Zapisuje cały wirtualny pulpit wszystkich monitorów przez BitBlt."""

    path = Path(output) if output else _output_path("pulpitu")
    path.parent.mkdir(parents=True, exist_ok=True)
    winapi.capture_desktop_image().save(path, "PNG")
    return path.resolve()


def recording_status() -> dict:
    return {"available": False, "status": "Nagrywanie pozostaje poza lekkim modułem zrzutów WinAPI."}
