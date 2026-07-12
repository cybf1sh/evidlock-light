"""Tworzenie i szyfrowanie dokumentów PDF bez nagłówka treści."""

from __future__ import annotations

import datetime as dt
import shutil
import textwrap
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image

from .. import reports
from ..config import PDF_DIR, ensure_runtime_dirs
from .hashing import sha256_file


def validate_password(password: str) -> None:
    if len(password or "") < 8:
        raise ValueError("Hasło musi mieć minimum 8 znaków.")


def _output_path(source: Path, suffix: str) -> Path:
    ensure_runtime_dirs()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return PDF_DIR / f"{source.stem}_{suffix}_{stamp}.pdf"


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        parts = []
        for element in root.iter():
            tag = element.tag.split("}")[-1]
            if tag == "t" and element.text:
                parts.append(element.text)
            elif tag in {"p", "br"}:
                parts.append("\n")
        return "".join(parts)
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _create_text_pdf(source: Path, output: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    regular, _bold = reports._register_unicode_fonts()
    text = _read_text(source)
    pdf = canvas.Canvas(str(output), pagesize=A4)
    width, height = A4
    y = height - 42
    pdf.setFont(regular, 10)
    for original_line in text.splitlines() or [""]:
        lines = textwrap.wrap(original_line.expandtabs(4), width=105, replace_whitespace=False, drop_whitespace=False) or [""]
        for line in lines:
            if y < 42:
                pdf.showPage(); pdf.setFont(regular, 10); y = height - 42
            pdf.drawString(42, y, line)
            y -= 14
    pdf.save()


def _create_image_pdf(source: Path, output: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    with Image.open(source) as image:
        image = image.convert("RGB")
        width, height = A4
        scale = min((width - 56) / image.width, (height - 56) / image.height)
        draw_width, draw_height = image.width * scale, image.height * scale
        pdf = canvas.Canvas(str(output), pagesize=A4)
        pdf.drawImage(ImageReader(image), (width - draw_width) / 2, (height - draw_height) / 2, draw_width, draw_height, preserveAspectRatio=True)
        pdf.save()


def encrypt_pdf(source: str | Path, password: str, output: str | Path | None = None) -> dict:
    validate_password(password)
    from pypdf import PdfReader, PdfWriter

    src = Path(source).resolve()
    if not src.is_file() or src.suffix.lower() != ".pdf":
        raise ValueError("Wskaż istniejący plik PDF.")
    target = Path(output) if output else _output_path(src, "zaszyfrowany")
    target.parent.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(src))
    if reader.is_encrypted:
        raise ValueError("Wybrany PDF jest już zaszyfrowany.")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": src.stem, "/Producer": "EvidLock Light"})
    writer.encrypt(password, algorithm="AES-256")
    with target.open("wb") as handle:
        writer.write(handle)
    return {"source": str(src), "pdf": str(target.resolve()), "encrypted": True, "algorithm": "AES-256", "sha256": sha256_file(target)}


def create_pdf_from_file(source: str | Path, password: str = "", output: str | Path | None = None) -> dict:
    src = Path(source).resolve()
    if not src.is_file() or src.stat().st_size == 0:
        raise ValueError("Wskaż istniejący, niepusty plik.")
    final_target = Path(output) if output else _output_path(src, "bez_naglowka_zaszyfrowany" if password else "bez_naglowka")
    target = _output_path(src, "tymczasowy") if password else final_target
    target.parent.mkdir(parents=True, exist_ok=True); final_target.parent.mkdir(parents=True, exist_ok=True)
    suffix = src.suffix.lower()
    if suffix == ".pdf":
        shutil.copy2(src, target)
    elif suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}:
        _create_image_pdf(src, target)
    else:
        _create_text_pdf(src, target)
    result = {"source": str(src), "pdf": str(target.resolve()), "encrypted": False, "sha256": sha256_file(target)}
    if password:
        result = encrypt_pdf(target, password, final_target)
        result["source"] = str(src)
        target.unlink(missing_ok=True)
    return result
