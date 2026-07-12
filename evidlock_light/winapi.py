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


def open_path(path: str | Path) -> None:
    """Otwiera plik lub katalog przez ShellExecuteW."""

    if not is_windows():
        raise RuntimeError("Otwieranie ścieżek przez WinAPI jest dostępne tylko w Windows.")
    result = ctypes.windll.shell32.ShellExecuteW(None, "open", str(Path(path).resolve()), None, None, 1)
    if int(result) <= 32:
        raise OSError(f"ShellExecuteW nie otworzył ścieżki. Kod: {int(result)}")


def launch_program(executable: str, parameters: str = "", elevate: bool = False) -> None:
    """Uruchamia program systemowy przez ShellExecuteW."""

    if not is_windows():
        raise RuntimeError("Uruchamianie programów systemowych jest dostępne tylko w Windows.")
    verb = "runas" if elevate else "open"
    result = ctypes.windll.shell32.ShellExecuteW(None, verb, executable, parameters or None, None, 1)
    if int(result) <= 32:
        raise OSError(f"ShellExecuteW nie uruchomił programu {executable}. Kod: {int(result)}")


def launch_remote_desktop(host: str) -> None:
    """Otwiera klienta RDP dla jawnie wskazanego hosta."""

    launch_program("mstsc.exe", f'/v:"{host}"')


def launch_remote_assistance_offer(host: str) -> None:
    """Uruchamia wyłącznie tryb Offer Remote Assistance dla technika."""

    launch_program("msra.exe", f'/offerra "{host}"', elevate=True)


def icmp_echo(ip_address: str, timeout_ms: int = 500) -> bool:
    """Sprawdza host przez IcmpSendEcho bez uruchamiania ping.exe."""

    if not is_windows():
        return False
    ws2_32, icmp = ctypes.windll.ws2_32, ctypes.windll.iphlpapi
    ws2_32.inet_addr.argtypes = [ctypes.c_char_p]
    ws2_32.inet_addr.restype = wintypes.ULONG
    icmp.IcmpCreateFile.restype = wintypes.HANDLE
    icmp.IcmpSendEcho.argtypes = [wintypes.HANDLE, wintypes.ULONG, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
    icmp.IcmpSendEcho.restype = wintypes.DWORD
    icmp.IcmpCloseHandle.argtypes = [wintypes.HANDLE]
    destination = ws2_32.inet_addr(str(ip_address).encode("ascii"))
    handle = icmp.IcmpCreateFile()
    if not handle or int(handle) == -1:
        return False
    reply = ctypes.create_string_buffer(128)
    try:
        return bool(icmp.IcmpSendEcho(handle, destination, None, 0, None, reply, len(reply), max(50, int(timeout_ms))))
    finally:
        icmp.IcmpCloseHandle(handle)


def mac_address(ip_address: str) -> str:
    """Pobiera MAC hosta z lokalnego segmentu przez SendARP."""

    if not is_windows():
        return ""
    ws2_32, iphlpapi = ctypes.windll.ws2_32, ctypes.windll.iphlpapi
    ws2_32.inet_addr.argtypes = [ctypes.c_char_p]
    ws2_32.inet_addr.restype = wintypes.ULONG
    destination = ws2_32.inet_addr(str(ip_address).encode("ascii"))
    buffer = (ctypes.c_ubyte * 8)()
    length = wintypes.ULONG(8)
    iphlpapi.SendARP.argtypes = [wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, ctypes.POINTER(wintypes.ULONG)]
    iphlpapi.SendARP.restype = wintypes.DWORD
    if iphlpapi.SendARP(destination, 0, ctypes.byref(buffer), ctypes.byref(length)) != 0:
        return ""
    return "-".join(f"{buffer[index]:02X}" for index in range(min(6, int(length.value))))


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


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _configure_capture_api() -> None:
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    handle = ctypes.c_void_p
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.GetWindowDC.restype = handle
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = handle
    user32.ReleaseDC.argtypes = [wintypes.HWND, handle]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.PrintWindow.argtypes = [wintypes.HWND, handle, wintypes.UINT]
    user32.PrintWindow.restype = wintypes.BOOL
    gdi32.CreateCompatibleDC.argtypes = [handle]
    gdi32.CreateCompatibleDC.restype = handle
    gdi32.CreateCompatibleBitmap.argtypes = [handle, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = handle
    gdi32.SelectObject.argtypes = [handle, handle]
    gdi32.SelectObject.restype = handle
    gdi32.DeleteObject.argtypes = [handle]
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteDC.argtypes = [handle]
    gdi32.DeleteDC.restype = wintypes.BOOL
    gdi32.GetDIBits.argtypes = [handle, handle, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.BitBlt.argtypes = [handle, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, handle, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
    gdi32.BitBlt.restype = wintypes.BOOL


def _bitmap_to_image(hdc: int, bitmap: int, width: int, height: int):
    """Konwertuje bitmapę GDI do obrazu PIL bez przechwytywania przez Pillow."""

    from PIL import Image

    info = _BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0
    buffer = ctypes.create_string_buffer(width * height * 4)
    if not ctypes.windll.gdi32.GetDIBits(hdc, bitmap, 0, height, buffer, ctypes.byref(info), 0):
        raise OSError("GetDIBits nie zwrócił obrazu.")
    return Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1).copy()


def capture_window_image(hwnd: int):
    """Przechwytuje pełne okno przez User32/GDI, także gdy jest częściowo zasłonięte."""

    if not is_windows():
        raise RuntimeError("Przechwytywanie WinAPI jest dostępne tylko w Windows.")
    _configure_capture_api()
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    root_hwnd = int(user32.GetAncestor(wintypes.HWND(hwnd), 2) or hwnd)
    rect = wintypes.RECT()
    if not user32.GetWindowRect(wintypes.HWND(root_hwnd), ctypes.byref(rect)):
        raise OSError("GetWindowRect nie zwrócił wymiarów okna.")
    width, height = int(rect.right - rect.left), int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        raise ValueError("Okno nie ma widocznego obszaru.")
    source_dc = user32.GetWindowDC(wintypes.HWND(root_hwnd))
    if not source_dc:
        raise OSError("GetWindowDC nie zwrócił kontekstu urządzenia.")
    memory_dc = gdi32.CreateCompatibleDC(source_dc)
    bitmap = gdi32.CreateCompatibleBitmap(source_dc, width, height)
    previous = gdi32.SelectObject(memory_dc, bitmap)
    try:
        rendered = user32.PrintWindow(wintypes.HWND(root_hwnd), memory_dc, 0x00000002)
        if not rendered:
            rendered = user32.PrintWindow(wintypes.HWND(root_hwnd), memory_dc, 0)
        if not rendered:
            raise OSError("PrintWindow nie zwrócił obrazu okna.")
        return _bitmap_to_image(memory_dc, bitmap, width, height)
    finally:
        gdi32.SelectObject(memory_dc, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(wintypes.HWND(root_hwnd), source_dc)


def capture_visible_window_image(hwnd: int):
    """Przechwytuje widoczny prostokąt okna z pulpitu przez BitBlt."""

    if not is_windows():
        raise RuntimeError("Przechwytywanie WinAPI jest dostępne tylko w Windows.")
    _configure_capture_api()
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    root_hwnd = int(user32.GetAncestor(wintypes.HWND(hwnd), 2) or hwnd)
    rect = wintypes.RECT()
    if not user32.GetWindowRect(wintypes.HWND(root_hwnd), ctypes.byref(rect)):
        raise OSError("GetWindowRect nie zwrócił wymiarów okna.")
    x, y = int(rect.left), int(rect.top)
    width, height = int(rect.right - rect.left), int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        raise ValueError("Okno nie ma widocznego obszaru.")
    source_dc = user32.GetDC(0)
    memory_dc = gdi32.CreateCompatibleDC(source_dc)
    bitmap = gdi32.CreateCompatibleBitmap(source_dc, width, height)
    previous = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if not gdi32.BitBlt(memory_dc, 0, 0, width, height, source_dc, x, y, 0x40CC0020):
            raise OSError("BitBlt nie zwrócił obrazu okna.")
        return _bitmap_to_image(memory_dc, bitmap, width, height)
    finally:
        gdi32.SelectObject(memory_dc, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(0, source_dc)


def capture_desktop_image():
    """Przechwytuje cały wirtualny pulpit wszystkich monitorów przez BitBlt."""

    if not is_windows():
        raise RuntimeError("Przechwytywanie WinAPI jest dostępne tylko w Windows.")
    _configure_capture_api()
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    x = int(user32.GetSystemMetrics(76))
    y = int(user32.GetSystemMetrics(77))
    width = int(user32.GetSystemMetrics(78))
    height = int(user32.GetSystemMetrics(79))
    if width <= 0 or height <= 0:
        raise OSError("GetSystemMetrics nie zwrócił rozmiaru pulpitu.")
    source_dc = user32.GetDC(0)
    memory_dc = gdi32.CreateCompatibleDC(source_dc)
    bitmap = gdi32.CreateCompatibleBitmap(source_dc, width, height)
    previous = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if not gdi32.BitBlt(memory_dc, 0, 0, width, height, source_dc, x, y, 0x40CC0020):
            raise OSError("BitBlt nie zwrócił obrazu pulpitu.")
        return _bitmap_to_image(memory_dc, bitmap, width, height)
    finally:
        gdi32.SelectObject(memory_dc, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(0, source_dc)
