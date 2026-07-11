"""Wspolne okno postepu dla dluzszych operacji Light."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk


class ProgressDialog(ctk.CTkToplevel):
    """Uruchamia zadanie w tle i bezpiecznie aktualizuje interfejs CTk."""

    def __init__(self, parent, title: str, colors: dict[str, str], font: str = "Segoe UI") -> None:
        super().__init__(parent)
        self.colors = colors
        self.font = font
        self.title(title)
        self.geometry("700x470")
        self.minsize(580, 390)
        self.configure(fg_color=colors["bg"])
        self.transient(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(self, text=title, text_color=colors["text"], font=(font, 18, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        progress_box = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        progress_box.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        progress_box.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(progress_box, height=12, progress_color=colors["accent"])
        self.progress.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        self.progress.set(0)
        self.status = ctk.CTkLabel(progress_box, text="Przygotowanie...", text_color=colors["muted"], font=(font, 10), anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.log = ctk.CTkTextbox(self, fg_color=colors["soft"], text_color=colors["text"], font=("Cascadia Mono", 10), wrap="word")
        self.log.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self.close_button = ctk.CTkButton(self, text="Zamknij", command=self.destroy, state="disabled", width=110)
        self.close_button.grid(row=3, column=0, sticky="e", padx=18, pady=(0, 16))
        self.protocol("WM_DELETE_WINDOW", self._close_if_done)
        self._running = True

    def start(self, worker: Callable[[Callable[[float, str], None]], object], on_done: Callable[[object], None] | None = None) -> None:
        def run() -> None:
            try:
                result = worker(self.report)
                self.after(0, lambda: self._finish(result, on_done))
            except Exception as exc:
                self.after(0, lambda error=exc: self._fail(error))

        threading.Thread(target=run, daemon=True).start()

    def report(self, percent: float, message: str) -> None:
        self.after(0, lambda: self._update(percent, message))

    def _update(self, percent: float, message: str) -> None:
        self.progress.set(max(0.0, min(100.0, float(percent))) / 100)
        self.status.configure(text=message)
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")

    def _finish(self, result: object, on_done: Callable[[object], None] | None) -> None:
        self._running = False
        self.progress.set(1)
        self.status.configure(text="Operacja zakończona")
        self.log.insert("end", "\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        self.log.see("end")
        self.close_button.configure(state="normal")
        if on_done:
            on_done(result)

    def _fail(self, exc: Exception) -> None:
        self._running = False
        self.progress.configure(progress_color=self.colors["red"])
        self.status.configure(text=f"Błąd: {exc}")
        self.log.insert("end", f"\nBŁĄD: {exc}\n")
        self.close_button.configure(state="normal")

    def _close_if_done(self) -> None:
        if not self._running:
            self.destroy()
