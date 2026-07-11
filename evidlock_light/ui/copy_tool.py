"""Okno kopii 1:1 i porownania A/B wzorowane na narzedziu EvidLockV2."""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..services import copying


class CopyCompareDialog(ctk.CTkToplevel):
    def __init__(self, parent, colors: dict[str, str], initial_mode: str = "copy", on_result=None, initial_source: str = "", initial_target: str = "") -> None:
        super().__init__(parent)
        self.colors = colors
        self.on_result = on_result
        self.running = False
        self.result: dict | None = None
        self.title("Kopia 1:1 i porównanie A/B")
        self.geometry("900x690")
        self.minsize(760, 590)
        self.configure(fg_color=colors["bg"])
        self.transient(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="Kopia 1:1 i porównanie A/B", text_color=colors["text"], font=("Segoe UI", 19, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        ctk.CTkLabel(self, text="Kopia zachowuje metadane, a po zapisie automatycznie weryfikuje SHA-256 i tworzy raport PDF/TXT/JSON.", text_color=colors["muted"], font=("Segoe UI", 10), anchor="w").grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        form = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        form.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        form.grid_columnconfigure(1, weight=1)
        self.source = tk.StringVar(value=initial_source)
        self.target = tk.StringVar(value=initial_target)
        self._path_row(form, 0, "Źródło / element A", self.source)
        self._path_row(form, 1, "Cel / element B", self.target)

        work = ctk.CTkFrame(self, fg_color="transparent")
        work.grid(row=3, column=0, sticky="nsew", padx=18)
        work.grid_columnconfigure(0, weight=1)
        work.grid_rowconfigure(2, weight=1)
        self.progress = ctk.CTkProgressBar(work, height=12, progress_color=colors["accent"])
        self.progress.grid(row=0, column=0, sticky="ew", pady=(2, 6))
        self.progress.set(0)
        self.status = ctk.CTkLabel(work, text="Wybierz źródło i cel.", text_color=colors["muted"], font=("Segoe UI", 10), anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.output = ctk.CTkTextbox(work, fg_color=colors["soft"], text_color=colors["text"], font=("Cascadia Mono", 10), wrap="word")
        self.output.grid(row=2, column=0, sticky="nsew")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=18, pady=14)
        footer.grid_columnconfigure(0, weight=1)
        self.open_reports = ctk.CTkButton(footer, text="Otwórz raporty", command=self._open_reports, state="disabled", width=130)
        self.open_reports.grid(row=0, column=0, sticky="w")
        self.compare_button = ctk.CTkButton(footer, text="Porównaj A/B", command=lambda: self._start("compare"), width=130, fg_color=colors["teal"])
        self.compare_button.grid(row=0, column=1, padx=(8, 0))
        self.copy_button = ctk.CTkButton(footer, text="Kopia 1:1 + SHA-256", command=lambda: self._start("copy"), width=170, fg_color=colors["green"])
        self.copy_button.grid(row=0, column=2, padx=(8, 0))
        ctk.CTkButton(footer, text="Zamknij", command=self.destroy, width=100).grid(row=0, column=3, padx=(8, 0))
        if initial_mode == "compare":
            self.compare_button.focus_set()

    def _path_row(self, parent, row: int, label: str, variable: tk.StringVar) -> None:
        ctk.CTkLabel(parent, text=label, text_color=self.colors["text"], font=("Segoe UI", 10, "bold"), anchor="w").grid(row=row, column=0, sticky="w", padx=(14, 8), pady=12)
        ctk.CTkEntry(parent, textvariable=variable, height=34).grid(row=row, column=1, sticky="ew", pady=10)
        ctk.CTkButton(parent, text="Plik", command=lambda: self._browse(variable, False), width=70).grid(row=row, column=2, padx=(8, 4))
        ctk.CTkButton(parent, text="Katalog", command=lambda: self._browse(variable, True), width=82).grid(row=row, column=3, padx=(4, 14))

    def _browse(self, variable: tk.StringVar, directory: bool) -> None:
        path = filedialog.askdirectory(parent=self) if directory else filedialog.askopenfilename(parent=self)
        if path:
            variable.set(os.path.abspath(path))

    def _start(self, mode: str) -> None:
        if self.running:
            return
        source = self.source.get().strip()
        target = self.target.get().strip()
        if not source or not target:
            self.status.configure(text="Wybierz oba elementy.")
            return
        if mode == "copy" and Path(target).is_dir() and any(Path(target).iterdir()):
            if not messagebox.askyesno(
                "Kopia 1:1",
                "Katalog docelowy nie jest pusty. Istniejące pliki o tych samych nazwach mogą zostać nadpisane. Kontynuować?",
                parent=self,
            ):
                return
        self.running = True
        self.result = None
        self.progress.set(0)
        self.output.delete("1.0", "end")
        self.open_reports.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.compare_button.configure(state="disabled")

        def worker() -> None:
            try:
                if mode == "copy":
                    result = copying.copy_1to1(source, target, callback=self._report)
                else:
                    result = copying.compare_paths(source, target, callback=self._report)
                self.after(0, lambda: self._finish(result, mode))
            except Exception as exc:
                self.after(0, lambda error=exc: self._fail(error))

        threading.Thread(target=worker, daemon=True).start()

    def _report(self, percent: float, message: str) -> None:
        self.after(0, lambda: self._update(percent, message))

    def _update(self, percent: float, message: str) -> None:
        self.progress.set(max(0, min(100, percent)) / 100)
        self.status.configure(text=message)
        self.output.insert("end", message + "\n")
        self.output.see("end")

    def _finish(self, result: dict, mode: str) -> None:
        self.running = False
        self.result = result
        self.progress.set(1)
        verdict = "ZGODNE" if result.get("ok") else "RÓŻNICE WYKRYTE"
        self.status.configure(text=f"{verdict} - operacja zakończona")
        self.output.insert("end", "\n" + json.dumps(result, ensure_ascii=False, indent=2))
        self.copy_button.configure(state="normal")
        self.compare_button.configure(state="normal")
        self.open_reports.configure(state="normal")
        if self.on_result:
            self.on_result(mode, result)

    def _fail(self, exc: Exception) -> None:
        self.running = False
        self.progress.configure(progress_color=self.colors["red"])
        self.status.configure(text=f"Błąd: {exc}")
        self.output.insert("end", f"\nBŁĄD: {exc}")
        self.copy_button.configure(state="normal")
        self.compare_button.configure(state="normal")

    def _open_reports(self) -> None:
        if not self.result:
            return
        report = self.result.get("report_pdf") or self.result.get("report_json")
        if report:
            os.startfile(str(Path(report).parent))
