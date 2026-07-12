"""Jedno odświeżane okno podglądu raportów wszystkich modułów."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
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
        self.current_pdf = None
        self.font_size = 10
        self.current_text = ""
        self.title("Bieżący raport")
        self.geometry("860x640")
        self.minsize(680, 480)
        self.configure(fg_color=colors["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        header.grid_columnconfigure(0, weight=1)
        self.heading = ctk.CTkLabel(header, text=self.report_title, text_color=colors["text"], font=("Segoe UI", 20, "bold"), anchor="w")
        self.heading.grid(row=0, column=0, sticky="ew")
        self.status = ctk.CTkLabel(header, text="Okno odświeża się po każdym kolejnym wyniku.", text_color=colors["muted"], font=("Segoe UI", 9), anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        ctk.CTkButton(actions, text="Zamknij", width=90, command=self._close, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).pack(side=tk.RIGHT, padx=(4, 0))
        ctk.CTkButton(actions, text="Zapisz PDF", width=105, command=self._save_pdf).pack(side=tk.RIGHT, padx=4)
        ctk.CTkButton(actions, text="Przeglądaj PDF", width=125, command=self._browse_pdf).pack(side=tk.RIGHT, padx=4)
        ctk.CTkButton(actions, text="Zapisz TXT", width=100, command=self._save_txt, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).pack(side=tk.RIGHT, padx=4)
        ctk.CTkButton(actions, text="A+", width=42, command=lambda: self._zoom(1), fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).pack(side=tk.RIGHT, padx=2)
        ctk.CTkButton(actions, text="A-", width=42, command=lambda: self._zoom(-1), fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).pack(side=tk.RIGHT, padx=2)

        self.content = ctk.CTkTextbox(self, fg_color=colors["card"], text_color=colors["text"], border_width=1, border_color=colors["border"], font=("Cascadia Mono", self.font_size), wrap="word")
        self.content.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.protocol("WM_DELETE_WINDOW", self._close)

    def update_report(self, title: str, data: object) -> None:
        self.report_title = title or "Bieżący raport"
        self.report_data = data
        self.current_pdf = reports.find_pdf(data)
        self.title(self.report_title)
        self.heading.configure(text=self.report_title)
        text = self._format_data(data)
        self.current_text = text
        self.content.configure(state="normal")
        self.content.delete("1.0", "end")
        self.content.insert("1.0", text)
        self.content.configure(state="disabled")
        self.status.configure(text="Wyświetlono aktualny wynik. Następna operacja odświeży to samo okno.")

    def _format_data(self, data: object) -> str:
        if isinstance(data, dict) and isinstance(data.get("nośniki"), list):
            blocks = []
            labels = {
                "letter": "Litera dysku", "label": "Etykieta", "file_system": "System plików",
                "drive_type_name": "Typ", "size": "Rozmiar [B]", "used": "Zajęte [B]",
                "free": "Wolne [B]", "used_percent": "Wykorzystanie [%]",
                "volume_serial": "Numer woluminu", "virtual_hint": "Środowisko wirtualne",
            }
            for index, item in enumerate(data["nośniki"], 1):
                lines = [f"NOŚNIK {index}: {item.get('letter', '')}", "-" * 64]
                lines.extend(f"{labels.get(key, key)}: {value if value not in ('', None) else 'Brak danych'}" for key, value in item.items() if key in labels)
                blocks.append("\n".join(lines))
            return "\n\n".join(blocks)
        return data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2, default=str)

    def _zoom(self, direction: int) -> None:
        self.font_size = max(8, min(20, self.font_size + direction))
        self.content.configure(font=("Cascadia Mono", self.font_size))
        self.status.configure(text=f"Rozmiar tekstu podglądu: {self.font_size} pt")

    def _save_txt(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Zapisz podgląd TXT", defaultextension=".txt", filetypes=[("TXT", "*.txt")])
        if path:
            try:
                Path(path).write_text(self.current_text, encoding="utf-8-sig")
                self.status.configure(text=f"Zapisano TXT: {path}")
            except Exception as exc:
                messagebox.showerror("Zapisz TXT", str(exc), parent=self)

    def _save_pdf(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Zapisz raport PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            output = reports.write_result_pdf(self.report_title, self.report_data, path)
            self.current_pdf = output
            self.status.configure(text=f"Zapisano PDF: {output}")
        except Exception as exc:
            messagebox.showerror("Raport PDF", str(exc), parent=self)

    def _browse_pdf(self) -> None:
        try:
            pdf_path = self.current_pdf or reports.write_result_pdf(self.report_title, self.report_data)
            self.current_pdf = reports.open_pdf(pdf_path)
            self.status.configure(text=f"Otwarto PDF: {self.current_pdf}")
        except Exception as exc:
            messagebox.showerror("Przeglądaj PDF", str(exc), parent=self)

    def _close(self) -> None:
        if self.on_close:
            self.on_close()
        self.destroy()
