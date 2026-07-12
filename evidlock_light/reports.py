"""Profesjonalne raporty PDF/JSON ze spójną obsługą Unicode."""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path
from typing import Iterable

from . import winapi
from .config import default_report_path


def write_json(data: object, path: str | Path | None = None, prefix: str = "raport") -> Path:
    output = Path(path) if path else default_report_path(prefix, ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _register_unicode_fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_candidates = [Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/calibri.ttf")]
    bold_candidates = [Path("C:/Windows/Fonts/segoeuib.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"), Path("C:/Windows/Fonts/calibrib.ttf")]
    regular = next((path for path in regular_candidates if path.exists()), None)
    bold = next((path for path in bold_candidates if path.exists()), regular)
    if regular:
        try:
            pdfmetrics.registerFont(TTFont("EvidLock-Regular", str(regular)))
            pdfmetrics.registerFont(TTFont("EvidLock-Bold", str(bold)))
            return "EvidLock-Regular", "EvidLock-Bold"
        except Exception:
            pass
    return "Helvetica", "Helvetica-Bold"


def _paragraph(value: object, style):
    from reportlab.platypus import Paragraph

    text = html.escape(str(value if value is not None else "")).replace("\n", "<br/>")
    return Paragraph(text or " ", style)


def write_professional_pdf(
    title: str,
    sections: list[dict],
    path: str | Path | None = None,
    subtitle: str = "",
    metadata: dict | None = None,
) -> Path:
    """Tworzy raport z sekcjami, tabelami, stopką i osadzonym fontem Unicode."""

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = Path(path) if path else default_report_path(title)
    output.parent.mkdir(parents=True, exist_ok=True)
    regular, bold = _register_unicode_fonts()
    wide = any(section.get("wide") for section in sections)
    pagesize = landscape(A4) if wide else A4
    doc = SimpleDocTemplate(str(output), pagesize=pagesize, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title=title, author="EvidLock Light")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("EvidTitle", parent=styles["Title"], fontName=bold, fontSize=19, leading=23, textColor=colors.HexColor("#111827"), alignment=TA_LEFT, spaceAfter=5 * mm)
    subtitle_style = ParagraphStyle("EvidSubtitle", parent=styles["Normal"], fontName=regular, fontSize=9.5, leading=13, textColor=colors.HexColor("#4b5563"), spaceAfter=5 * mm)
    heading_style = ParagraphStyle("EvidHeading", parent=styles["Heading2"], fontName=bold, fontSize=12, leading=15, textColor=colors.HexColor("#111827"), spaceBefore=4 * mm, spaceAfter=2.5 * mm, keepWithNext=True)
    body_style = ParagraphStyle("EvidBody", parent=styles["BodyText"], fontName=regular, fontSize=8.5, leading=11, textColor=colors.HexColor("#1f2937"), alignment=TA_LEFT)
    small_style = ParagraphStyle("EvidSmall", parent=body_style, fontSize=7.2, leading=9)
    key_style = ParagraphStyle("EvidKey", parent=body_style, fontName=bold, textColor=colors.HexColor("#111827"))
    header_style = ParagraphStyle("EvidHeader", parent=small_style, fontName=bold, textColor=colors.white)

    story = [Paragraph(html.escape(title), title_style)]
    if subtitle:
        story.append(Paragraph(html.escape(subtitle), subtitle_style))
    info = {"Data utworzenia": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **(metadata or {})}
    info_table = Table([[_paragraph(key, key_style), _paragraph(value, body_style)] for key, value in info.items()], colWidths=[42 * mm, doc.width - 42 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([info_table, Spacer(1, 4 * mm)])

    for section in sections:
        if section.get("page_break"):
            story.append(PageBreak())
        heading = section.get("title")
        if heading:
            story.append(Paragraph(html.escape(str(heading)), heading_style))
        if section.get("text"):
            story.extend([_paragraph(section["text"], body_style), Spacer(1, 2 * mm)])
        rows = section.get("rows") or []
        if rows:
            data = [[_paragraph(key, key_style), _paragraph(value, body_style)] for key, value in rows]
            table = Table(data, colWidths=[45 * mm, doc.width - 45 * mm], repeatRows=0)
            table.setStyle(TableStyle([
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 3 * mm)])
        table_data = section.get("table")
        if table_data:
            headers = section.get("headers") or []
            prepared = [[_paragraph(value, header_style) for value in headers]] if headers else []
            prepared.extend([[_paragraph(value, small_style) for value in row] for row in table_data])
            widths = section.get("widths")
            table = Table(prepared, colWidths=widths, repeatRows=1 if headers else 0)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")) if headers else ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white) if headers else ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("ROWBACKGROUNDS", (0, 1 if headers else 0), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.extend([table, Spacer(1, 3 * mm)])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont(regular, 7.5)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(18 * mm, 9 * mm, "EvidLock Light")
        canvas.drawRightString(pagesize[0] - 18 * mm, 9 * mm, f"Strona {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output


def write_simple_pdf(title: str, rows: Iterable[tuple[str, str]], path: str | Path | None = None) -> Path:
    return write_professional_pdf(title, [{"title": "Szczegóły", "rows": list(rows)}], path=path)


def result_rows(data: object) -> list[tuple[str, str]]:
    if isinstance(data, dict):
        return [(str(key), json.dumps(value, ensure_ascii=False, indent=2, default=str) if isinstance(value, (dict, list)) else str(value)) for key, value in data.items()]
    if isinstance(data, list):
        return [(str(index), json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else str(value)) for index, value in enumerate(data, 1)]
    return [("Wynik", str(data))]


def write_result_pdf(title: str, data: object, path: str | Path | None = None) -> Path:
    return write_professional_pdf(title, [{"title": "Wynik operacji", "rows": result_rows(data)}], path=path)


def find_pdf(data: object) -> Path | None:
    if isinstance(data, dict):
        for key in ("pdf", "report_pdf"):
            candidate = data.get(key)
            if candidate:
                path = Path(str(candidate))
                if path.is_file() and path.suffix.lower() == ".pdf":
                    return path
        for value in data.values():
            found = find_pdf(value)
            if found:
                return found
    elif isinstance(data, (list, tuple)):
        for value in data:
            found = find_pdf(value)
            if found:
                return found
    elif isinstance(data, (str, Path)):
        try:
            path = Path(data)
            if path.is_file() and path.suffix.lower() == ".pdf":
                return path
        except (OSError, ValueError):
            return None
    return None


def open_pdf(path: str | Path) -> Path:
    target = Path(path).resolve()
    if not target.is_file() or target.suffix.lower() != ".pdf":
        raise FileNotFoundError(f"Nie znaleziono raportu PDF: {target}")
    winapi.open_path(target)
    return target
