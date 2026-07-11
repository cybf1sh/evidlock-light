"""Wspólny panel sprawdzania i zmiany atrybutu read-only."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from ..services import readonly


class ReadOnlyDialog(ctk.CTkToplevel):
    def __init__(self, parent, colors: dict[str, str], initial_path: str = "", on_result=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.on_result = on_result
        self.running = False
        self.title("Ochrona read-only")
        self.geometry("780x560")
        self.minsize(650, 460)
        self.configure(fg_color=colors["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="Ochrona tylko do odczytu", text_color=colors["text"], font=("Segoe UI", 21, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))
        ctk.CTkLabel(self, text="Sprawdź, ustaw albo usuń atrybut read-only dla pliku lub całego katalogu.", text_color=colors["muted"], font=("Segoe UI", 10), anchor="w").grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        form = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        form.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        form.grid_columnconfigure(0, weight=1)
        self.path = tk.StringVar(value=initial_path)
        ctk.CTkEntry(form, textvariable=self.path, placeholder_text="Plik lub katalog", height=34).grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=12)
        ctk.CTkButton(form, text="Plik", width=70, command=self._choose_file).grid(row=0, column=1, padx=4)
        ctk.CTkButton(form, text="Katalog", width=82, command=self._choose_directory).grid(row=0, column=2, padx=(4, 12))

        self.output = ctk.CTkTextbox(self, fg_color=colors["card"], text_color=colors["text"], border_width=1, border_color=colors["border"], font=("Cascadia Mono", 10), wrap="word")
        self.output.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self.output.insert("1.0", "Wybierz element i sprawdź jego status.")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        self.check_button = ctk.CTkButton(footer, text="Sprawdź status", width=125, command=lambda: self._start("check"))
        self.check_button.grid(row=0, column=0, sticky="w")
        self.set_button = ctk.CTkButton(footer, text="Ustaw read-only", width=130, command=lambda: self._start("set"), fg_color=colors["green"])
        self.set_button.grid(row=0, column=1, padx=(8, 0))
        self.clear_button = ctk.CTkButton(footer, text="Usuń read-only", width=130, command=lambda: self._start("clear"), fg_color=colors["red"])
        self.clear_button.grid(row=0, column=2, padx=(8, 0))
        ctk.CTkButton(footer, text="Zamknij", width=95, command=self.destroy, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=3, padx=(8, 0))

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(parent=self)
        if path:
            self.path.set(path)

    def _choose_directory(self) -> None:
        path = filedialog.askdirectory(parent=self)
        if path:
            self.path.set(path)

    def _start(self, action: str) -> None:
        if self.running or not self.path.get().strip():
            return
        self.running = True
        for button in (self.check_button, self.set_button, self.clear_button):
            button.configure(state="disabled")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", "Przetwarzanie...")

        def worker() -> None:
            try:
                path = self.path.get().strip()
                if action == "set":
                    readonly.apply_readonly(path)
                elif action == "clear":
                    readonly.clear_readonly(path)
                result = readonly.check_readonly(path)
                result["operation"] = action
                self.after(0, lambda: self._finish(result))
            except Exception as exc:
                self.after(0, lambda error=exc: self._finish({"error": str(error)}))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, result: dict) -> None:
        self.running = False
        for button in (self.check_button, self.set_button, self.clear_button):
            button.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2))
        if self.on_result:
            self.on_result(result)
