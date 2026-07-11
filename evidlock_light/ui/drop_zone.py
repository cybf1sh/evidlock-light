"""Lekka strefa przeciagania plikow i katalogow z kontrola duplikatow."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    from tkinterdnd2 import COPY, DND_FILES
except Exception:
    COPY = "copy"
    DND_FILES = None


class DropZone(ctk.CTkFrame):
    def __init__(self, parent, app, colors: dict[str, str], paths: list[str], large: bool = False) -> None:
        super().__init__(parent, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        self.app = app
        self.colors = colors
        self.paths = paths
        self.large = large
        self.grid_columnconfigure(0, weight=1)
        if large:
            self.configure(height=154)
            self.grid_propagate(False)
            self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="Przeciągnij pliki lub katalogi tutaj",
            text_color=colors["text"],
            font=("Segoe UI", 17 if large else 12, "bold"),
            anchor="center" if large else "w",
        )
        title.grid(row=0, column=0, sticky="ew", padx=14, pady=((22, 3) if large else (10, 2)))
        if large:
            hint = ctk.CTkLabel(
                self,
                text="Elementy zostaną przekazane do wybranego narzędzia. Duplikaty nie są dodawane.",
                text_color=colors["muted"],
                font=("Segoe UI", 10),
                anchor="center",
            )
            hint.grid(row=1, column=0, sticky="new", padx=14)
            self._enable_drop(hint)
        self.status = ctk.CTkLabel(self, text="", text_color=colors["muted"], font=("Segoe UI", 9), anchor="center" if large else "w")
        self.status.grid(row=2 if large else 1, column=0, sticky="ew", padx=14, pady=((2, 12) if large else (0, 9)))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=0, column=1, rowspan=3 if large else 2, padx=12, pady=12)
        ctk.CTkButton(buttons, text="Pliki", width=72, height=30, command=self._choose_files).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(buttons, text="Katalog", width=82, height=30, command=self._choose_directory).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(buttons, text="Wyczyść", width=82, height=30, command=self.clear, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).pack(side=tk.LEFT)
        self._enable_drop(title)
        self._enable_drop(self)
        self.refresh()

    def _enable_drop(self, widget) -> None:
        if not getattr(self.app, "drag_drop_available", False) or DND_FILES is None:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            self.app.drag_drop_available = False

    def _on_drop(self, event):
        try:
            incoming = list(self.app.tk.splitlist(event.data))
        except Exception:
            incoming = [event.data]
        self.add_paths(incoming)
        return COPY

    def _choose_files(self) -> None:
        self.add_paths(filedialog.askopenfilenames(parent=self.app, title="Dodaj pliki"))

    def _choose_directory(self) -> None:
        path = filedialog.askdirectory(parent=self.app, title="Dodaj katalog")
        if path:
            self.add_paths([path])

    def add_paths(self, incoming) -> None:
        existing = {os.path.normcase(os.path.abspath(path)): path for path in self.paths}
        added = 0
        duplicates: list[str] = []
        invalid: list[str] = []
        for raw in incoming:
            path = os.path.abspath(str(raw).strip().strip("{}").strip('"'))
            if not os.path.exists(path):
                invalid.append(path)
                continue
            key = os.path.normcase(path)
            if key in existing:
                duplicates.append(path)
                continue
            self.paths.append(path)
            existing[key] = path
            added += 1
        self.refresh()
        if duplicates:
            names = "\n".join(f"- {Path(path).name or path}" for path in duplicates[:8])
            messagebox.showwarning("Element już istnieje", f"Następujący plik lub katalog jest już dodany:\n\n{names}", parent=self.app)
        if invalid:
            messagebox.showwarning("Nieprawidłowa ścieżka", "Pominięto nierozpoznane elementy.", parent=self.app)
        if added:
            self.app.on_dropped_paths_changed()

    def clear(self) -> None:
        self.paths.clear()
        self.refresh()
        self.app.on_dropped_paths_changed()

    def refresh(self) -> None:
        files = sum(Path(path).is_file() for path in self.paths)
        directories = sum(Path(path).is_dir() for path in self.paths)
        dnd = "przeciąganie aktywne" if getattr(self.app, "drag_drop_available", False) else "przeciąganie niedostępne - użyj przycisków"
        recent = ", ".join(Path(path).name or path for path in self.paths[-3:])
        suffix = f" | ostatnie: {recent}" if recent else ""
        self.status.configure(text=f"Dodane: {len(self.paths)} | pliki: {files} | katalogi: {directories} | {dnd}{suffix}")
