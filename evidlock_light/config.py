"""Wspólna konfiguracja ścieżek i katalogów roboczych."""

from __future__ import annotations

from pathlib import Path
import sys

from . import APP_NAME


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
RUNTIME_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PROJECT_DIR
REPORTS_DIR = RUNTIME_DIR / "raporty"
PDF_DIR = REPORTS_DIR / "PDF"
CHECKSUM_REPORTS_DIR = REPORTS_DIR / "suma-kontrolna"
ONE_CLICK_DIR = REPORTS_DIR / "One-click"
SCREENSHOTS_DIR = REPORTS_DIR / "zrzuty-ekranu"
LOGS_DIR = RUNTIME_DIR / "logi"
EXPORTS_DIR = RUNTIME_DIR / "eksport"
DOCS_DIR = RUNTIME_DIR / "docs"


def ensure_runtime_dirs() -> None:
    """Tworzy lokalne katalogi wynikowe używane przez Light."""

    for directory in (REPORTS_DIR, PDF_DIR, CHECKSUM_REPORTS_DIR, ONE_CLICK_DIR, SCREENSHOTS_DIR, LOGS_DIR, EXPORTS_DIR, DOCS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def default_report_path(prefix: str, suffix: str = ".pdf") -> Path:
    """Zwraca ścieżkę raportu z bezpiecznym prefiksem i znacznikiem czasu."""

    import datetime as _dt

    ensure_runtime_dirs()
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in prefix).strip("_")
    return REPORTS_DIR / f"{safe or APP_NAME}_{stamp}{suffix}"
