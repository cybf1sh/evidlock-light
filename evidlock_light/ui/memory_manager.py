"""Lekki manager zrzutów RAM oparty na WinPmem i Volatility 3."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..services import hashing, memory


class MemoryManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent, colors: dict[str, str], on_result=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.on_result = on_result
        self.running = False
        self.title("Manager pamięci")
        self.geometry("980x720")
        self.minsize(820, 620)
        self.configure(fg_color=colors["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self, text="Manager pamięci", text_color=colors["text"], font=("Segoe UI", 22, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))
        ctk.CTkLabel(self, text="Zrzuty RAM A/B, SHA-256, porównanie, WinPmem i pluginy Volatility 3.", text_color=colors["muted"], font=("Segoe UI", 10), anchor="w").grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        self.deps = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        self.deps.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.deps.grid_columnconfigure(0, weight=1)
        self.dep_status = ctk.CTkLabel(self.deps, text="", text_color=colors["text"], font=("Segoe UI", 10, "bold"), anchor="w", justify="left")
        self.dep_status.grid(row=0, column=0, columnspan=5, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkButton(self.deps, text="Odśwież", width=85, command=self.refresh_status).grid(row=1, column=1, padx=4, pady=(0, 10))
        ctk.CTkButton(self.deps, text="Instaluj Volatility 3", width=145, command=self._install_volatility).grid(row=1, column=2, padx=4, pady=(0, 10))
        ctk.CTkButton(self.deps, text="Pobierz WinPmem", width=125, command=self._download_winpmem).grid(row=1, column=3, padx=4, pady=(0, 10))
        ctk.CTkButton(self.deps, text="Wskaż WinPmem", width=115, command=self._import_winpmem).grid(row=1, column=4, padx=(4, 10), pady=(0, 10))

        files = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        files.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))
        files.grid_columnconfigure(1, weight=1)
        self.file_a = tk.StringVar()
        self.file_b = tk.StringVar()
        self._file_row(files, 0, "Zrzut A", self.file_a)
        self._file_row(files, 1, "Zrzut B", self.file_b)

        work = ctk.CTkFrame(self, fg_color="transparent")
        work.grid(row=4, column=0, sticky="nsew", padx=18)
        work.grid_columnconfigure(0, weight=1)
        work.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(work, fg_color=colors["soft"], corner_radius=8)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(toolbar, text="SHA-256 A", width=95, command=lambda: self._run(lambda: {"file": self.file_a.get(), "sha256": hashing.sha256_file(self.file_a.get())})).pack(side=tk.LEFT, padx=(8, 4), pady=8)
        ctk.CTkButton(toolbar, text="SHA-256 B", width=95, command=lambda: self._run(lambda: {"file": self.file_b.get(), "sha256": hashing.sha256_file(self.file_b.get())})).pack(side=tk.LEFT, padx=4, pady=8)
        ctk.CTkButton(toolbar, text="Porównaj A/B", width=110, command=lambda: self._run(lambda: memory.compare_dumps(self.file_a.get(), self.file_b.get()))).pack(side=tk.LEFT, padx=4, pady=8)
        self.plugin = tk.StringVar(value="windows.info")
        ctk.CTkEntry(toolbar, textvariable=self.plugin, width=170).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 4), pady=8)
        ctk.CTkButton(toolbar, text="Uruchom plugin", width=115, command=lambda: self._run(lambda: memory.run_volatility(self.file_a.get(), self.plugin.get()))).pack(side=tk.LEFT, padx=4, pady=8)
        ctk.CTkButton(toolbar, text="Zrzut WinPmem", width=120, command=self._acquire).pack(side=tk.LEFT, padx=(4, 8), pady=8)
        self.output = ctk.CTkTextbox(work, fg_color=colors["card"], text_color=colors["text"], border_width=1, border_color=colors["border"], font=("Cascadia Mono", 10), wrap="word")
        self.output.grid(row=1, column=0, sticky="nsew")

        ctk.CTkButton(self, text="Zamknij", width=100, command=self.destroy, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=5, column=0, sticky="e", padx=18, pady=14)
        self.refresh_status()

    def _file_row(self, parent, row: int, label: str, variable: tk.StringVar) -> None:
        ctk.CTkLabel(parent, text=label, text_color=self.colors["text"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, padx=(12, 8), pady=9)
        ctk.CTkEntry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=9)
        ctk.CTkButton(parent, text="Wybierz", width=85, command=lambda: self._choose(variable)).grid(row=row, column=2, padx=10)

    def _choose(self, variable: tk.StringVar) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("Zrzuty RAM", "*.raw *.mem *.dmp *.vmem *.bin"), ("Wszystkie pliki", "*.*")])
        if path:
            variable.set(path)

    def refresh_status(self) -> None:
        status = memory.dependency_status()
        winpmem = f"GOTOWY: {status['winpmem_path']}" if status["winpmem_present"] else "BRAK - pobierz i wskaż winpmem_mini_x64.exe"
        volatility = f"GOTOWY: {status['volatility_path']}" if status["volatility_present"] else "BRAK - kliknij Instaluj Volatility 3"
        self.dep_status.configure(text=f"WinPmem: {winpmem}\nVolatility 3: {volatility}", text_color=self.colors["green"] if status["winpmem_present"] and status["volatility_present"] else self.colors["red"])

    def _install_volatility(self) -> None:
        self._show_result(memory.install_volatility())

    def _download_winpmem(self) -> None:
        self._show_result(memory.open_winpmem_download())

    def _import_winpmem(self) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("WinPmem", "*.exe")])
        if path:
            try:
                self._show_result({"winpmem": str(memory.import_winpmem(path))})
                self.refresh_status()
            except Exception as exc:
                messagebox.showerror("WinPmem", str(exc), parent=self)

    def _acquire(self) -> None:
        output = filedialog.asksaveasfilename(parent=self, defaultextension=".raw", filetypes=[("RAW", "*.raw")])
        if output:
            self._run(lambda: memory.acquire_memory(output))

    def _run(self, operation) -> None:
        if self.running:
            return
        self.running = True
        self.output.delete("1.0", "end")
        self.output.insert("1.0", "Operacja w toku...")

        def worker() -> None:
            try:
                result = operation()
                self.after(0, lambda: self._finish(result))
            except Exception as exc:
                self.after(0, lambda error=exc: self._finish({"error": str(error)}))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, result: object) -> None:
        self.running = False
        self._show_result(result)
        if self.on_result:
            self.on_result(result)

    def _show_result(self, result: object) -> None:
        self.output.delete("1.0", "end")
        self.output.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2, default=str))
