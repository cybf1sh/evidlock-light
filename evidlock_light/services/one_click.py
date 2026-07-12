"""Kompletny workflow zabezpieczenia materiału jednym kliknięciem."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from .. import reports, winapi
from ..config import ONE_CLICK_DIR
from . import archive, hashing


def _files(sources: list[str | Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for source in sources:
        path = Path(source).resolve()
        if not path.exists():
            raise FileNotFoundError(str(path))
        items = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
        for item in items:
            resolved = item.resolve()
            if resolved not in seen:
                seen.add(resolved); result.append(resolved)
    if not result:
        raise ValueError("Nie wybrano plików do zabezpieczenia.")
    return result


def secure(sources: list[str | Path], password: str, archive_format: str = "zip", callback=None) -> dict:
    if len(password or "") < 8:
        raise ValueError("Hasło musi mieć minimum 8 znaków.")
    files = _files(sources)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = ONE_CLICK_DIR / f"zabezpieczenie_{stamp}"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    total = max(1, len(files))
    for index, file_path in enumerate(files, 1):
        if callback: callback(5 + index / total * 50, f"SHA-256 {index}/{len(files)}: {file_path.name}")
        digest = hashing.sha256_file(file_path)
        try:
            winapi.set_readonly(file_path, True); readonly_status = "TAK"
        except Exception as exc:
            readonly_status = f"BŁĄD: {exc}"
        records.append({"name": file_path.name, "path": str(file_path), "size": file_path.stat().st_size, "sha256": digest, "readonly": readonly_status})

    if callback: callback(60, "Generowanie profesjonalnego raportu PDF")
    report_path = output / f"raport_one_click_{stamp}.pdf"
    sections = [{
        "title": "Wykaz zabezpieczonych plików",
        "table": [[index, item["name"], item["path"], item["size"], item["sha256"], item["readonly"]] for index, item in enumerate(records, 1)],
        "headers": ["Lp.", "Nazwa", "Ścieżka", "Rozmiar [B]", "SHA-256", "Read-only"],
        "widths": [28, 90, 190, 65, 250, 65],
        "wide": True,
    }]
    reports.write_professional_pdf(
        "One-click - raport zabezpieczenia danych",
        sections,
        report_path,
        subtitle="Integralność SHA-256, stan read-only i pakiet szyfrowany.",
        metadata={"Liczba plików": len(records), "Format archiwum": archive_format.upper()},
    )

    extension = "7z" if archive_format.lower() == "7z" else "zip"
    archive_path = output / f"pakiet_one_click_{stamp}.{extension}"
    if callback: callback(70, f"Tworzenie szyfrowanego archiwum {extension.upper()}")
    archive_result = archive.create_encrypted_archive([*sources, report_path], archive_path, archive_format, password, callback=lambda value, text: callback(70 + value * .28, text) if callback else None)
    try:
        winapi.set_readonly(report_path, True); winapi.set_readonly(archive_path, True)
    except Exception:
        pass
    if callback: callback(100, "Zabezpieczenie One-click zakończone")
    return {"ok": True, "output_dir": str(output), "files": len(records), "pdf": str(report_path), "archive": str(archive_path), "archive_sha256": archive_result["sha256"], "records": records}
