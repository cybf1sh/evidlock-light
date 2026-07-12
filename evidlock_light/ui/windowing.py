"""Wspolne zachowanie okien roboczych EvidLock Light."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk


def present_toplevel(window, parent=None, topmost_ms: int = 350) -> None:
    """Pokazuje okno nad aplikacja, bez pozostawiania stalego topmost."""

    try:
        if parent is not None:
            window.transient(parent)
    except Exception:
        pass
    try:
        window.deiconify()
        window.lift()
        window.attributes("-topmost", True)
        window.focus_force()
        window.after(topmost_ms, lambda: _clear_topmost(window))
    except Exception:
        pass


def _clear_topmost(window) -> None:
    try:
        if window.winfo_exists():
            window.attributes("-topmost", False)
            window.lift()
    except Exception:
        pass


def operation_name(window) -> str:
    try:
        return str(window.title() or "Operacja")
    except Exception:
        return "Operacja"


def is_window_busy(window) -> bool:
    return bool(getattr(window, "running", False) or getattr(window, "_running", False))


class ManagedToplevel(ctk.CTkToplevel):
    """Okno zawsze prezentowane nad rodzicem i chronione podczas operacji."""

    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._managed_parent = parent
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self.after_idle(lambda: present_toplevel(self, parent))

    def request_close(self) -> bool:
        if is_window_busy(self):
            messagebox.showwarning(
                "Operacja w toku",
                f"Nie można zamknąć okna „{operation_name(self)}”, ponieważ trwa operacja.\n\nPoczekaj na jej zakończenie.",
                parent=self,
            )
            present_toplevel(self, self._managed_parent)
            return False
        self._destroy_managed()
        return True

    def destroy(self) -> None:
        self.request_close()

    def force_destroy(self) -> None:
        self._destroy_managed()

    def _destroy_managed(self) -> None:
        try:
            super().destroy()
        except Exception:
            pass
