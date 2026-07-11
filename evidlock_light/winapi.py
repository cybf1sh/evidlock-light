"""Cienka warstwa WinAPI używana przez moduły Light.

Moduł nie zależy od GUI. Dzięki temu CLI, testy i aplikacja CTk korzystają
z tej samej logiki.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass, asdict
from pathlib import Path


DRIVE_TYPES = {
    0: "Nieznany",
    1: "Brak katalogu głównego",
    2: "Wymienny / USB",
    3: "Lokalny",
    4: "Sieciowy",
    5: "Optyczny",
    6: "RAM disk",
}


@dataclass
class VolumeInfo:
    letter: str
    label: str
    file_system: str
    drive_type: int
    drive_type_name: str
    size: int
    free: int
    volume_serial: str
    virtual_hint: str = ""

    @property
    def used(self) -> int:
        return max(0, self.size - self.free)

    @property
    def used_percent(self) -> float:
        return (self.used / self.size * 100.0) if self.size else 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["used"] = self.used
        data["used_percent"] = round(self.used_percent, 2)
        return data


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    """Sprawdza realny token administratora przez WinAPI."""

    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(arguments: list[str] | None = None) -> None:
    """Uruchamia bieżący interpreter/skrypt z podniesionymi uprawnieniami."""

    if not is_windows():
        raise RuntimeError("Tryb administratora jest dostępny tylko w Windows.")
    import sys

    args = " ".join(f'"{arg}"' for arg in (arguments or sys.argv))
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
    if int(result) <= 32:
        raise RuntimeError(f"ShellExecuteW nie uruchomił administratora. Kod: {int(result)}")


def _root_path(letter: str) -> str:
    letter = str(letter or "").strip()
    if len(letter) == 1:
        letter += ":"
    if not letter.endswith("\\"):
        letter += "\\"
    return letter


def detect_virtual_volume(label: str, drive_type: int) -> str:
    text = (label or "").upper()
    for marker, name in (
        ("GOOGLE DRIVE", "Google Drive"),
        ("GOOGLE", "Google Drive"),
        ("ONEDRIVE", "Microsoft OneDrive"),
        ("DROPBOX", "Dropbox"),
        ("ICLOUD", "Apple iCloud Drive"),
    ):
        if marker in text:
            return name
    if drive_type == 4:
        return "Dysk sieciowy / wirtualny"
    return ""


def list_volumes() -> list[VolumeInfo]:
    """Zwraca listę woluminów przez GetLogicalDrives i GetVolumeInformationW."""

    if not is_windows():
        return []

    kernel32 = ctypes.windll.kernel32
    mask = int(kernel32.GetLogicalDrives())
    volumes: list[VolumeInfo] = []
    for idx in range(26):
        if not (mask & (1 << idx)):
            continue
        letter = f"{chr(65 + idx)}:"
        root = _root_path(letter)
        label = ctypes.create_unicode_buffer(260)
        fs = ctypes.create_unicode_buffer(260)
        serial = wintypes.DWORD(0)
        max_component = wintypes.DWORD(0)
        flags = wintypes.DWORD(0)
        total = ctypes.c_ulonglong(0)
        free = ctypes.c_ulonglong(0)
        available = ctypes.c_ulonglong(0)
        try:
            drive_type = int(kernel32.GetDriveTypeW(root))
        except Exception:
            drive_type = 0
        try:
            kernel32.GetVolumeInformationW(
                root,
                label,
                len(label),
                ctypes.byref(serial),
                ctypes.byref(max_component),
                ctypes.byref(flags),
                fs,
                len(fs),
            )
        except Exception:
            pass
        try:
            kernel32.GetDiskFreeSpaceExW(root, ctypes.byref(available), ctypes.byref(total), ctypes.byref(free))
        except Exception:
            pass
        volumes.append(
            VolumeInfo(
                letter=letter,
                label=label.value or "Brak etykiety",
                file_system=fs.value or "Brak danych",
                drive_type=drive_type,
                drive_type_name=DRIVE_TYPES.get(drive_type, "Nieznany"),
                size=int(total.value or 0),
                free=int(free.value or available.value or 0),
                volume_serial=f"{serial.value:08X}" if serial.value else "",
                virtual_hint=detect_virtual_volume(label.value, drive_type),
            )
        )
    return sorted(volumes, key=lambda item: item.letter)


def set_readonly(path: str | Path, readonly: bool) -> None:
    """Ustawia lub zdejmuje atrybut tylko do odczytu rekurencyjnie."""

    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(str(target))
    paths = [target]
    if target.is_dir():
        paths.extend(p for p in target.rglob("*") if p.exists())
    for item in paths:
        if not is_windows():
            mode = item.stat().st_mode
            item.chmod((mode & ~0o222) if readonly else (mode | 0o200))
            continue
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(item))
        if attrs == -1:
            continue
        new_attrs = attrs | 0x01 if readonly else attrs & ~0x01
        ctypes.windll.kernel32.SetFileAttributesW(str(item), new_attrs)
