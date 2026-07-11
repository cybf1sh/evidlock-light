"""Raporty PDF/JSON dla EvidLock Light."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .config import default_report_path


def write_json(data: object, path: str | Path | None = None, prefix: str = "raport") -> Path:
    output = Path(path) if path else default_report_path(prefix, ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_simple_pdf(title: str, rows: Iterable[tuple[str, str]], path: str | Path | None = None) -> Path:
    """Tworzy czytelny raport PDF bez zależności od GUI."""

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    output = Path(path) if path else default_report_path(title)
    output.parent.mkdir(parents=True, exist_ok=True)
    font_name = _register_unicode_font()
    pdf = canvas.Canvas(str(output), pagesize=A4)
    width, height = A4
    y = height - 48
    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.setFont(font_name, 16)
    pdf.drawString(42, y, title[:90])
    y -= 28
    pdf.setStrokeColorRGB(0.85, 0.89, 0.94)
    pdf.line(42, y + 10, width - 42, y + 10)
    pdf.setFont(font_name, 9)
    for key, value in rows:
        if not key and not value:
            y -= 8
            continue
        text = f"{key}: {value}"
        for line in _wrap(text, 112):
            if y < 48:
                pdf.showPage()
                pdf.setFont(font_name, 9)
                y = height - 48
            pdf.drawString(42, y, line)
            y -= 14
    pdf.save()
    return output


def _register_unicode_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    for font_path in candidates:
        if font_path.exists():
            name = font_path.stem.replace(" ", "_")
            try:
                pdfmetrics.registerFont(TTFont(name, str(font_path)))
                return name
            except Exception:
                continue
    return "Helvetica"


def _wrap(text: str, width: int) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines or [""]
