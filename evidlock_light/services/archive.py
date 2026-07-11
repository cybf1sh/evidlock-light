"""Lekka archiwizacja ZIP."""

from __future__ import annotations

import zipfile
from pathlib import Path


def create_zip(source: str | Path, output: str | Path, callback=None) -> Path:
    src = Path(source).resolve()
    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file() and p.resolve() != out)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        total = max(1, len(files))
        for index, file_path in enumerate(files, 1):
            archive.write(file_path, file_path.name if src.is_file() else file_path.relative_to(src))
            if callback:
                callback(5 + 90 * index / total, f"Archiwizacja {index}/{len(files)}: {file_path.name}")
    return out
