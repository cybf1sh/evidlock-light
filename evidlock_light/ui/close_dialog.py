"""Czytelne potwierdzenie zamknięcia aplikacji z logo EvidLock."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .logo import EvidLockLogo
from .windowing import present_toplevel


class CloseRequestDialog(ctk.CTkToplevel):
    """Modalne okno potwierdzenia zamknięcia aplikacji.

    Ten sam widok obsługuje zwykłe zamknięcie oraz próbę zamknięcia podczas
    operacji. W drugim przypadku nie ma przycisku kończącego program.
    """

    def __init__(
        self,
        parent,
        colors: dict[str, str],
        operation: str | None = None,
        on_result: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.colors = colors
        self.operation = operation
        self.on_result = on_result
        self._resolved = False
        self._managed_parent = parent

        self.title("EvidLock Light")
        self.geometry("560x360" if operation else "560x340")
        self.minsize(500, 320)
        self.resizable(False, False)
        self.configure(fg_color=colors["bg"])
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _event: self._cancel())
        if not operation:
            self.bind("<Return>", lambda _event: self._confirm())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color=colors["card"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        EvidLockLogo(header, colors["card"], colors["brand"], colors["logo_fill"], 58).grid(
            row=0, column=0, padx=(22, 12), pady=18
        )
        heading_box = ctk.CTkFrame(header, fg_color="transparent")
        heading_box.grid(row=0, column=1, sticky="ew", padx=(0, 22), pady=18)
        ctk.CTkLabel(
            heading_box,
            text="Operacja jest w toku" if operation else "Zamknąć EvidLock Light?",
            text_color=colors["text"],
            font=("Segoe UI", 19, "bold"),
            anchor="w",
        ).pack(fill=tk.X)
        ctk.CTkLabel(
            heading_box,
            text="Bezpieczne zamknięcie programu",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill=tk.X, pady=(3, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew", padx=26, pady=(22, 5))
        body.grid_columnconfigure(0, weight=1)
        if operation:
            message = (
                "Nie można teraz zamknąć aplikacji, ponieważ trwa aktywna operacja.\n"
                "Poczekaj na jej zakończenie, aby zachować spójność danych i raportów."
            )
        else:
            message = (
                "Czy na pewno chcesz zamknąć program?\n"
                "Niezapisane wyniki bieżącej pracy mogą zostać utracone."
            )
        ctk.CTkLabel(
            body,
            text=message,
            text_color=colors["text"],
            font=("Segoe UI", 11),
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        if operation:
            operation_box = ctk.CTkFrame(
                body,
                fg_color=colors["soft"],
                border_width=1,
                border_color=colors["border"],
                corner_radius=7,
            )
            operation_box.grid(row=1, column=0, sticky="ew", pady=(16, 0))
            ctk.CTkLabel(
                operation_box,
                text="Bieżąca funkcja",
                text_color=colors["muted"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(fill=tk.X, padx=12, pady=(9, 1))
            ctk.CTkLabel(
                operation_box,
                text=operation,
                text_color=colors["text"],
                font=("Segoe UI", 11, "bold"),
                anchor="w",
                wraplength=460,
            ).pack(fill=tk.X, padx=12, pady=(0, 9))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=22, pady=(12, 20))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            footer,
            text="Wróć do pracy" if operation else "Anuluj",
            command=self._cancel,
            width=125,
            fg_color=colors["soft"],
            hover_color=colors["border"],
            text_color=colors["text"],
            border_width=1,
            border_color=colors["border"],
        ).grid(row=0, column=1, padx=(8, 0))
        if not operation:
            ctk.CTkButton(
                footer,
                text="Zamknij aplikację",
                command=self._confirm,
                width=145,
                fg_color=colors["red"],
                hover_color="#991b1b",
            ).grid(row=0, column=2, padx=(8, 0))

        self.after_idle(self._present)

    def _present(self) -> None:
        present_toplevel(self, self._managed_parent)
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _cancel(self) -> None:
        self._resolve(False)

    def _confirm(self) -> None:
        if not self.operation:
            self._resolve(True)

    def _resolve(self, confirmed: bool) -> None:
        if self._resolved:
            return
        self._resolved = True
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            super().destroy()
        finally:
            if self.on_result:
                self.on_result(confirmed)
