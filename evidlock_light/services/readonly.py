"""Operacje atrybutu tylko do odczytu."""

from __future__ import annotations

from pathlib import Path

from ..winapi import set_readonly


def apply_readonly(path: str | Path) -> dict:
    set_readonly(path, True)
    return {"path": str(Path(path).resolve()), "readonly": True}


def clear_readonly(path: str | Path) -> dict:
    set_readonly(path, False)
    return {"path": str(Path(path).resolve()), "readonly": False}
