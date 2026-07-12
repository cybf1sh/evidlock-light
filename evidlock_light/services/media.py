"""Obsługa nośników w wersji Light."""

from __future__ import annotations

from pathlib import Path

from .. import winapi
from ..reports import write_json, write_professional_pdf


def list_media() -> list[dict]:
    return [volume.to_dict() for volume in winapi.list_volumes()]


def media_by_letter(letter: str) -> dict:
    wanted = letter.rstrip("\\").upper()
    for item in list_media():
        if item["letter"].upper() == wanted:
            return item
    raise ValueError(f"Nie znaleziono nośnika: {letter}")


def report_media(letter: str | None = None, output: str | Path | None = None, letters: list[str] | None = None) -> Path:
    data = [media_by_letter(item) for item in letters] if letters else ([media_by_letter(letter)] if letter else list_media())
    sections = []
    for item in data:
        sections.append({
            "title": f"Nośnik {item['letter']} - {item['label'] or 'Brak etykiety'}",
            "rows": [
                ("Litera dysku", item["letter"]),
                ("Etykieta", item["label"]),
                ("Typ nośnika", item["drive_type_name"]),
                ("System plików", item["file_system"]),
                ("Rozmiar całkowity", format_bytes(item["size"])),
                ("Miejsce zajęte", format_bytes(item["used"])),
                ("Miejsce wolne", format_bytes(item["free"])),
                ("Wykorzystanie", f"{item['used_percent']:.1f}%"),
                ("Numer seryjny woluminu", item["volume_serial"] or "Brak danych"),
                ("Środowisko wirtualne", item["virtual_hint"] or "Nie wykryto"),
            ],
        })
    return write_professional_pdf(
        "Informacje o nośnikach",
        sections,
        output,
        subtitle="Raport pojemności, systemu plików i identyfikacji woluminów Windows.",
        metadata={"Liczba nośników": len(data), "Źródło danych": "Windows API"},
    )


def export_media_json(output: str | Path | None = None) -> Path:
    return write_json(list_media(), output, "nosniki")


def format_bytes(value: int | float | None) -> str:
    size = float(value or 0)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
