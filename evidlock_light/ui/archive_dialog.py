"""Okno szyfrowanej archiwizacji ZIP AES-256 i 7z."""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import winapi
from ..services import archive
from .windowing import ManagedToplevel


class ArchiveDialog(ManagedToplevel):
    def __init__(self, parent, colors: dict[str, str], initial_sources=None, on_result=None) -> None:
        super().__init__(parent)
        self.colors = colors; self.on_result = on_result; self.sources = []
        self.result = None; self.running = False
        self.title("Archiwizuj"); self.geometry("780x680"); self.minsize(680, 580); self.configure(fg_color=colors["bg"])
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(self, text="Archiwizuj", text_color=colors["text"], font=("Segoe UI", 22, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))
        ctk.CTkLabel(self, text="Pliki i katalogi zostaną spakowane jako ZIP AES-256 albo 7z AES-256. Hasło musi mieć minimum 8 znaków.", text_color=colors["muted"], font=("Segoe UI", 10), anchor="w", wraplength=720).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        controls = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10)); controls.grid_columnconfigure(0, weight=1)
        buttons = ctk.CTkFrame(controls, fg_color="transparent"); buttons.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkButton(buttons, text="Dodaj pliki", width=100, command=self._add_files).pack(side=tk.LEFT, padx=3)
        ctk.CTkButton(buttons, text="Dodaj katalog", width=110, command=self._add_directory).pack(side=tk.LEFT, padx=3)
        ctk.CTkButton(buttons, text="Wyczyść", width=85, command=self._clear, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).pack(side=tk.LEFT, padx=3)
        self.source_view = ctk.CTkTextbox(controls, height=100, fg_color=colors["soft"], text_color=colors["text"], font=("Cascadia Mono", 9))
        self.source_view.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        options = ctk.CTkFrame(controls, fg_color="transparent"); options.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12)); options.grid_columnconfigure((1, 3), weight=1)
        self.format = tk.StringVar(value="zip"); self.password = tk.StringVar(); self.repeat = tk.StringVar(); self.show_password = tk.BooleanVar()
        ctk.CTkRadioButton(options, text="ZIP AES-256", variable=self.format, value="zip", text_color=colors["text"]).grid(row=0, column=0, sticky="w", padx=(0, 14))
        ctk.CTkRadioButton(options, text="7z AES-256", variable=self.format, value="7z", text_color=colors["text"]).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(options, text="Hasło (min. 8 znaków)", text_color=colors["text"], font=("Segoe UI", 9, "bold")).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 3))
        self.password_entry = ctk.CTkEntry(options, textvariable=self.password, show="*"); self.password_entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(options, text="Powtórz hasło", text_color=colors["text"], font=("Segoe UI", 9, "bold")).grid(row=1, column=2, columnspan=2, sticky="w", pady=(10, 3))
        self.repeat_entry = ctk.CTkEntry(options, textvariable=self.repeat, show="*"); self.repeat_entry.grid(row=2, column=2, columnspan=2, sticky="ew")
        ctk.CTkCheckBox(options, text="Pokaż hasło", variable=self.show_password, command=self._toggle_password, text_color=colors["text"]).grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))

        work = ctk.CTkFrame(self, fg_color="transparent"); work.grid(row=3, column=0, sticky="nsew", padx=18); work.grid_columnconfigure(0, weight=1); work.grid_rowconfigure(2, weight=1)
        self.progress = ctk.CTkProgressBar(work, height=11, progress_color=colors["accent"]); self.progress.grid(row=0, column=0, sticky="ew"); self.progress.set(0)
        self.status = ctk.CTkLabel(work, text="Gotowe do archiwizacji.", text_color=colors["muted"], font=("Segoe UI", 9, "bold"), anchor="w"); self.status.grid(row=1, column=0, sticky="ew", pady=5)
        self.log = ctk.CTkTextbox(work, fg_color=colors["card"], text_color=colors["text"], font=("Cascadia Mono", 9)); self.log.grid(row=2, column=0, sticky="nsew")
        footer = ctk.CTkFrame(self, fg_color="transparent"); footer.grid(row=4, column=0, sticky="ew", padx=18, pady=14); footer.grid_columnconfigure(0, weight=1)
        self.open_button = ctk.CTkButton(footer, text="Otwórz katalog", state="disabled", command=self._open_folder, width=115); self.open_button.grid(row=0, column=0, sticky="w")
        self.start_button = ctk.CTkButton(footer, text="Archiwizuj", command=self._start, width=125); self.start_button.grid(row=0, column=1, padx=8)
        ctk.CTkButton(footer, text="Zamknij", command=self.destroy, width=95, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=2)
        self._add_sources(initial_sources or [])

    def _add_sources(self, paths) -> None:
        existing = {os.path.normcase(str(Path(path).resolve())) for path in self.sources}
        for path in paths:
            resolved = str(Path(path).resolve())
            if Path(resolved).exists() and os.path.normcase(resolved) not in existing:
                self.sources.append(resolved); existing.add(os.path.normcase(resolved))
        self.source_view.delete("1.0", "end"); self.source_view.insert("1.0", "\n".join(self.sources) or "Brak wybranych źródeł.")

    def _add_files(self): self._add_sources(filedialog.askopenfilenames(parent=self))
    def _add_directory(self):
        path = filedialog.askdirectory(parent=self)
        if path: self._add_sources([path])
    def _clear(self): self.sources.clear(); self._add_sources([])
    def _toggle_password(self):
        show = "" if self.show_password.get() else "*"; self.password_entry.configure(show=show); self.repeat_entry.configure(show=show)

    def _start(self) -> None:
        if self.running: return
        if not self.sources: messagebox.showwarning("Archiwizuj", "Dodaj pliki lub katalogi.", parent=self); return
        if len(self.password.get()) < 8: messagebox.showwarning("Hasło", "Hasło musi mieć minimum 8 znaków.", parent=self); return
        if self.password.get() != self.repeat.get(): messagebox.showwarning("Hasło", "Podane hasła nie są identyczne.", parent=self); return
        extension = ".7z" if self.format.get() == "7z" else ".zip"
        output = filedialog.asksaveasfilename(parent=self, defaultextension=extension, filetypes=[("Archiwum", f"*{extension}")])
        if not output: return
        self.running=True; self.result=None; self.start_button.configure(state="disabled", text="Archiwizowanie..."); self.progress.set(0); self.log.delete("1.0", "end")
        def callback(value, text): self.after(0, lambda: self._update(value, text))
        def worker():
            try: result=archive.create_encrypted_archive(self.sources, output, self.format.get(), self.password.get(), callback); self.after(0, lambda:self._finish(result))
            except Exception as exc: self.after(0, lambda error=exc:self._finish({"error":str(error)}))
        threading.Thread(target=worker, daemon=True).start()

    def _update(self, value, text): self.progress.set(max(0,min(100,value))/100); self.status.configure(text=text); self.log.insert("end",text+"\n"); self.log.see("end")
    def _finish(self, result):
        self.running=False; self.result=result; self.start_button.configure(state="normal",text="Archiwizuj"); self.log.insert("end","\n"+json.dumps(result,ensure_ascii=False,indent=2));
        if "error" in result: self.status.configure(text=f"Błąd: {result['error']}"); return
        self.progress.set(1); self.status.configure(text="Archiwum zostało utworzone."); self.open_button.configure(state="normal")
        if self.on_result: self.on_result(result)
    def _open_folder(self):
        if self.result and self.result.get("archive"): winapi.open_path(Path(self.result["archive"]).parent)
