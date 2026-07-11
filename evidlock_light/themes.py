"""Palety interfejsu i trwale ustawienia EvidLock Light.

Modul nie zalezy od widokow CTk. Dzieki temu skorki mozna testowac i
rozbudowywac bez modyfikowania logiki poszczegolnych narzedzi.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


SKIN_LABELS = {
    "green": "Green",
    "system": "System",
    "black": "Black",
}
DEFAULT_SKIN = "system"


def _settings_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "EvidLockLight" / "settings.json"


def load_settings() -> dict:
    """Wczytuje ustawienia profilu bez uzalezniania ich od GUI."""

    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_settings(data: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_skin(value: str | None) -> str:
    """Zwraca jedna z trzech obslugiwanych nazw skorek."""

    value = str(value or "").strip().lower()
    return value if value in SKIN_LABELS else DEFAULT_SKIN


def load_skin() -> str:
    """Wczytuje skorke; uszkodzony plik ustawien nie blokuje startu."""

    try:
        data = load_settings()
        return normalize_skin(data.get("skin"))
    except (OSError, ValueError, TypeError):
        return DEFAULT_SKIN


def save_skin(skin: str) -> None:
    """Zapisuje wybor w profilu uzytkownika, takze dla buildu one-file."""

    data = load_settings()
    data["skin"] = normalize_skin(skin)
    save_settings(data)


def skin_from_label(label: str) -> str:
    normalized = str(label or "").strip().lower()
    for skin, display_name in SKIN_LABELS.items():
        if normalized == display_name.lower():
            return skin
    return normalize_skin(normalized)


def system_uses_dark_mode() -> bool:
    """Odczytuje ustawienie aplikacji Windows; domyslnie wybiera jasny tryb."""

    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(value) == 0
    except (ImportError, OSError, TypeError, ValueError):
        return False


def appearance_mode(skin: str) -> str:
    if normalize_skin(skin) == "black":
        return "Dark"
    if normalize_skin(skin) == "system" and system_uses_dark_mode():
        return "Dark"
    return "Light"


def palette(skin: str) -> dict[str, str]:
    """Zwraca komplet kolorow wymaganych przez powloke i widoki Light."""

    skin = normalize_skin(skin)
    if skin == "green":
        return {
            "bg": "#eef8f1", "card": "#ffffff", "soft": "#e3f3e8",
            "border": "#b7d7c0", "text": "#102416", "muted": "#4f6b58",
            "sidebar": "#123c24", "sidebar_text": "#f0fdf4",
            "sidebar_muted": "#bbf7d0", "brand": "#86efac", "logo_fill": "#e8f8ee",
            "nav_hover": "#1c5634", "accent": "#15803d", "accent_hover": "#166534",
            "green": "#16a34a", "red": "#dc2626", "purple": "#6d28d9",
            "teal": "#0f766e", "console_bg": "#0c2415", "console_text": "#dcfce7",
        }
    if skin == "black" or (skin == "system" and system_uses_dark_mode()):
        if skin == "black":
            return {
                "bg": "#fde047", "card": "#fffdf0", "soft": "#fff7c2",
                "border": "#d4a900", "text": "#111827", "muted": "#4b5563",
                "sidebar": "#050505", "sidebar_text": "#111827",
                "sidebar_muted": "#fde68a", "brand": "#facc15", "logo_fill": "#111827",
                "nav_hover": "#242424", "accent": "#111827", "accent_hover": "#000000",
                "green": "#15803d", "red": "#dc2626", "purple": "#6d28d9",
                "teal": "#0f766e", "console_bg": "#fffef2", "console_text": "#111827",
            }
        accent = "#2563eb"
        return {
            "bg": "#101214", "card": "#181b1f", "soft": "#20242a",
            "border": "#343a40", "text": "#f5f7fa", "muted": "#aeb6c2",
            "sidebar": "#050607", "sidebar_text": "#f5f7fa",
            "sidebar_muted": "#9aa4b2", "brand": "#60a5fa", "logo_fill": "#111827",
            "nav_hover": "#24282e", "accent": accent,
            "accent_hover": "#1d4ed8",
            "green": "#15803d", "red": "#b91c1c", "purple": "#6d28d9",
            "teal": "#0f766e", "console_bg": "#050607", "console_text": "#f5f7fa",
        }
    return {
        "bg": "#f3f3f3", "card": "#ffffff", "soft": "#f5f5f5",
        "border": "#c7c7c7", "text": "#1f1f1f", "muted": "#505050",
        "sidebar": "#202020", "sidebar_text": "#f5f5f5",
        "sidebar_muted": "#b7b7b7", "brand": "#60a5fa", "logo_fill": "#e8f3ff",
        "nav_hover": "#343434", "accent": "#0078d4", "accent_hover": "#005a9e",
        "green": "#107c10", "red": "#c42b1c", "purple": "#5c2d91",
        "teal": "#038387", "console_bg": "#0b1020", "console_text": "#e5edf7",
    }
