"""Blokada uruchomienia więcej niż jednej instancji EvidLock Light."""

from __future__ import annotations

import ctypes
import os


ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9
_active_instance = None


class SingleInstance:
    def __init__(self, name: str = r"Local\EvidLockLight.SingleInstance") -> None:
        self.handle = None
        self.acquired = True
        if os.name != "nt":
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        self.handle = kernel32.CreateMutexW(None, False, name)
        self.acquired = bool(self.handle) and ctypes.get_last_error() != ERROR_ALREADY_EXISTS
        if not self.acquired and self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None
        if self.acquired:
            global _active_instance
            _active_instance = self

    def release(self) -> None:
        global _active_instance
        if self.handle and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None
        if _active_instance is self:
            _active_instance = None


def release_for_relaunch() -> None:
    """Zwalnia mutex tuż przed kontrolowanym restartem jako administrator."""

    if _active_instance is not None:
        _active_instance.release()


def activate_existing_window(title_prefix: str = "EvidLock Light") -> bool:
    """Przywraca główne okno pierwszej instancji, jeśli jest już widoczne."""

    if os.name != "nt":
        return False
    user32 = ctypes.windll.user32
    found = {"value": False}
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def visit(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if buffer.value.startswith(title_prefix):
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
                found["value"] = True
                return False
        return True

    user32.EnumWindows(callback_type(visit), 0)
    return found["value"]
