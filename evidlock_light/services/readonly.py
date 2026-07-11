"""Operacje atrybutu tylko do odczytu."""

from __future__ import annotations

from pathlib import Path
import os

from ..winapi import set_readonly


def apply_readonly(path: str | Path) -> dict:
    set_readonly(path, True)
    return {"path": str(Path(path).resolve()), "readonly": True}


def clear_readonly(path: str | Path) -> dict:
    set_readonly(path, False)
    return {"path": str(Path(path).resolve()), "readonly": False}


def check_readonly(path: str | Path) -> dict:
    """Sprawdza atrybut read-only dla pliku albo zawartości katalogu."""

    target = Path(path).resolve()
    if not target.exists():
        raise FileNotFoundError(str(target))
    items = [target] if target.is_file() else sorted(item for item in target.rglob("*") if item.is_file())
    readonly_items: list[str] = []
    writable_items: list[str] = []
    errors: list[dict] = []
    for item in items:
        try:
            attrs = getattr(item.stat(), "st_file_attributes", 0)
            is_readonly = bool(attrs & 0x01) if os.name == "nt" else not os.access(item, os.W_OK)
            (readonly_items if is_readonly else writable_items).append(str(item))
        except OSError as exc:
            errors.append({"path": str(item), "error": str(exc)})
    return {
        "path": str(target),
        "checked": len(items),
        "readonly": len(readonly_items),
        "writable": len(writable_items),
        "readonly_items": readonly_items,
        "writable_items": writable_items,
        "errors": errors,
    }
