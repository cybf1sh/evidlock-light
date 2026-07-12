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


def _archive_files(sources: list[str | Path], output: Path) -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    used_roots: dict[str, int] = {}
    seen: set[Path] = set()
    for source in sources:
        src = Path(source).resolve()
        if not src.exists():
            raise FileNotFoundError(str(src))
        root = src.name or "dane"
        count = used_roots.get(root, 0)
        used_roots[root] = count + 1
        if count:
            root = f"{root}_{count + 1}"
        files = [src] if src.is_file() else sorted(item for item in src.rglob("*") if item.is_file())
        for item in files:
            resolved = item.resolve()
            if resolved == output.resolve() or resolved in seen:
                continue
            seen.add(resolved)
            relative = item.name if src.is_file() else str(item.relative_to(src)).replace("\\", "/")
            result.append((item, f"{root}/{relative}"))
    if not result:
        raise ValueError("Nie znaleziono plików do spakowania.")
    return result


def create_encrypted_archive(sources: list[str | Path], output: str | Path, archive_format: str, password: str, callback=None) -> dict:
    if len(password or "") < 8:
        raise ValueError("Hasło archiwum musi mieć minimum 8 znaków.")
    fmt = archive_format.lower()
    if fmt not in {"zip", "7z"}:
        raise ValueError("Obsługiwane formaty to ZIP i 7z.")
    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    files = _archive_files(sources, out)
    total = max(1, len(files))
    if fmt == "zip":
        import pyzipper

        with pyzipper.AESZipFile(out, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as archive:
            archive.setpassword(password.encode("utf-8")); archive.setencryption(pyzipper.WZ_AES, nbits=256)
            for index, (source, name) in enumerate(files, 1):
                archive.write(source, name)
                if callback: callback(index / total * 100, f"ZIP AES-256 {index}/{len(files)}: {name}")
        algorithm = "ZIP AES-256"
    else:
        import py7zr

        with py7zr.SevenZipFile(out, "w", password=password) as archive:
            for index, (source, name) in enumerate(files, 1):
                archive.write(source, name)
                if callback: callback(index / total * 100, f"7z AES-256 {index}/{len(files)}: {name}")
        algorithm = "7z AES-256"
    from .hashing import sha256_file
    return {"archive": str(out), "format": fmt, "encryption": algorithm, "files": len(files), "sha256": sha256_file(out)}
