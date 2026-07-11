"""Jedno odświeżane okno podglądu raportów wszystkich modułów."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import reports


class ReportWindow(ctk.CTkToplevel):
    def __init__(self, parent, colors: dict[str, str], on_close=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.on_close = on_close
        self.report_title = "Bieżący raport"
        self.report_data: object = {}
        self.title("Bieżący raport")
        self.geometry("860x640")
        self.minsize(680, 480)
        self.configure(fg_color=colors["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        header.grid_columnconfigure(0, weight=1)
        self.heading = ctk.CTkLabel(header, text=self.report_title, text_color=colors["text"], font=("Segoe UI", 20, "bold"), anchor="w")
        self.heading.grid(row=0, column=0, sticky="ew")
        self.status = ctk.CTkLabel(header, text="Okno odświeża się po każdym kolejnym wyniku.", text_color=colors["muted"], font=("Segoe UI", 9), anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        ctk.CTkButton(header, text="Zapisz PDF", width=115, command=self._save_pdf).grid(row=0, column=1, rowspan=2, padx=(8, 4))
        ctk.CTkButton(header, text="Zamknij", width=95, command=self._close, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=2, rowspan=2, padx=(4, 0))

        self.content = ctk.CTkTextbox(self, fg_color=colors["card"], text_color=colors["text"], border_width=1, border_color=colors["border"], font=("Cascadia Mono", 10), wrap="word")
        self.content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.protocol("WM_DELETE_WINDOW", self._close)

    def update_report(self, title: str, data: object) -> None:
        self.report_title = title or "Bieżący raport"
        self.report_data = data
        self.title(self.report_title)
        self.heading.configure(text=self.report_title)
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2, default=str)
        self.content.configure(state="normal")
        self.content.delete("1.0", "end")
        self.content.insert("1.0", text)
        self.content.configure(state="disabled")
        self.status.configure(text="Wyświetlono aktualny wynik. Następna operacja odświeży to samo okno.")

    def _save_pdf(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Zapisz raport PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            output = reports.write_result_pdf(self.report_title, self.report_data, path)
            self.status.configure(text=f"Zapisano PDF: {output}")
        except Exception as exc:
            messagebox.showerror("Raport PDF", str(exc), parent=self)

    def _close(self) -> None:
        if self.on_close:
            self.on_close()
        self.destroy()
