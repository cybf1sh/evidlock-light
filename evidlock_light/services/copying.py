"""Kopia 1:1 i porównanie katalogów/plików."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

from .hashing import sha256_file
from .. import reports
from ..config import default_report_path


ProgressCallback = Callable[[float, str], None]


def _notify(callback: ProgressCallback | None, percent: float, message: str) -> None:
    if callback:
        callback(max(0.0, min(100.0, percent)), message)


def _files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*") if path.is_file())


def _report(prefix: str, title: str, result: dict) -> dict:
    json_path = reports.write_json(result, prefix=prefix)
    txt_path = default_report_path(prefix, ".txt")
    txt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [(str(key), json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)) for key, value in result.items()]
    pdf_path = reports.write_simple_pdf(title, rows, path=default_report_path(prefix, ".pdf"))
    return {"report_json": str(json_path), "report_txt": str(txt_path), "report_pdf": str(pdf_path)}


def copy_1to1(source: str | Path, destination: str | Path, callback: ProgressCallback | None = None) -> dict:
    src = Path(source).resolve()
    dst = Path(destination).resolve()
    if not src.exists():
        raise FileNotFoundError(str(src))
    if src == dst or (src.is_dir() and src in dst.parents):
        raise ValueError("Miejsce docelowe kopii nie może być źródłem ani znajdować się wewnątrz źródła.")
    source_files = _files(src)
    total = max(1, len(source_files))
    _notify(callback, 2, f"Przygotowano pliki: {len(source_files)}")
    for index, file_path in enumerate(source_files, 1):
        rel = file_path.relative_to(src) if src.is_dir() else Path(file_path.name)
        target = dst / rel if src.is_dir() else (dst / src.name if dst.exists() and dst.is_dir() else dst)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        _notify(callback, 5 + 50 * index / total, f"Kopiowanie {index}/{total}: {rel}")
    _notify(callback, 58, "Weryfikacja kopii przez SHA-256")
    copied_root = dst if src.is_dir() else (dst / src.name if dst.exists() and dst.is_dir() else dst)
    verification = compare_paths(src, copied_root, callback=callback, progress_range=(58, 92), create_report=False)
    result = {
        "ok": verification["ok"],
        "source": str(src),
        "destination": str(copied_root),
        "files": len(source_files),
        "verification": verification,
    }
    _notify(callback, 95, "Zapisywanie raportu kopii")
    result.update(_report("kopia_1to1", "EvidLock Light - raport kopii 1:1", result))
    _notify(callback, 100, "Kopia i weryfikacja zakończone")
    return result


def compare_paths(
    a: str | Path,
    b: str | Path,
    callback: ProgressCallback | None = None,
    progress_range: tuple[float, float] = (0, 92),
    create_report: bool = True,
) -> dict:
    left = Path(a).resolve()
    right = Path(b).resolve()
    if not left.exists():
        raise FileNotFoundError(str(left))
    if not right.exists():
        raise FileNotFoundError(str(right))
    if left.is_file() != right.is_file():
        raise ValueError("Porównywane elementy muszą być tego samego typu: dwa pliki albo dwa katalogi.")
    if left.is_file() and right.is_file():
        _notify(callback, progress_range[0] + 5, "Obliczanie SHA-256 pliku A")
        left_hash = sha256_file(left)
        _notify(callback, progress_range[0] + (progress_range[1] - progress_range[0]) * 0.55, "Obliczanie SHA-256 pliku B")
        right_hash = sha256_file(right)
        same = left_hash == right_hash
        result = {"ok": same, "mode": "file", "changed": [] if same else [left.name], "missing_a": [], "missing_b": [], "sha256_a": left_hash, "sha256_b": right_hash}
        if create_report:
            result.update(_report("porownanie_ab", "EvidLock Light - porównanie A/B", result))
        _notify(callback, 100 if create_report else progress_range[1], "Porównanie zakończone")
        return result
    left_files = _files(left)
    right_files = _files(right)
    total = max(1, len(left_files) + len(right_files))
    done = 0
    left_manifest = {}
    right_manifest = {}
    span = progress_range[1] - progress_range[0]
    for root, files, target, label in ((left, left_files, left_manifest, "A"), (right, right_files, right_manifest, "B")):
        for file_path in files:
            rel = str(file_path.relative_to(root))
            target[rel] = {"path": rel, "size": file_path.stat().st_size, "sha256": sha256_file(file_path)}
            done += 1
            _notify(callback, progress_range[0] + span * done / total, f"Porównywanie {label}: {rel}")
    changed = []
    for rel, item in left_manifest.items():
        other = right_manifest.get(rel)
        if other and other["sha256"] != item["sha256"]:
            changed.append(rel)
    missing_b = sorted(set(left_manifest) - set(right_manifest))
    missing_a = sorted(set(right_manifest) - set(left_manifest))
    result = {
        "ok": not changed and not missing_a and not missing_b,
        "mode": "directory",
        "changed": changed,
        "missing_a": missing_a,
        "missing_b": missing_b,
        "left_files": len(left_manifest),
        "right_files": len(right_manifest),
    }
    if create_report:
        _notify(callback, 95, "Zapisywanie raportu porównania")
        result.update(_report("porownanie_ab", "EvidLock Light - porównanie A/B", result))
    _notify(callback, 100 if create_report else progress_range[1], "Porównanie zakończone")
    return result
