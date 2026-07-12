"""Panel zrzutów okien aplikacji i pulpitu w stylu EvidLockV2."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .. import winapi
from ..services import capture
from .windowing import ManagedToplevel, present_toplevel


class CaptureDialog(ManagedToplevel):
    def __init__(self, parent, colors: dict[str, str], windows_provider, on_result=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.windows_provider = windows_provider
        self.on_result = on_result
        self.running = False
        self.windows: list[object] = []
        self.title("Zrzut ekranu")
        self.geometry("700x540")
        self.minsize(620, 470)
        self.configure(fg_color=colors["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Zrzut ekranu", text_color=colors["text"], font=("Segoe UI", 21, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 3))
        ctk.CTkLabel(
            self,
            text="Wybierz jedno lub kilka okien EvidLock Light albo przejdź do zrzutu pulpitu.",
            text_color=colors["muted"], font=("Segoe UI", 10), anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        body = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 7))
        ctk.CTkLabel(toolbar, text="Widoczne okna aplikacji", text_color=colors["text"], font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        ctk.CTkButton(toolbar, text="Odśwież", width=90, command=self.refresh, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).pack(side=tk.RIGHT)
        self.listbox = tk.Listbox(
            body, selectmode=tk.EXTENDED, activestyle="none", relief="flat", highlightthickness=1,
            highlightbackground=colors["border"], bg=colors["soft"], fg=colors["text"],
            selectbackground=colors["accent"], selectforeground="#ffffff", font=("Segoe UI", 10),
        )
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(footer, text="Zrzut pulpitu", command=self._outside_panel, width=125, fg_color=colors["teal"]).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(footer, text="Wszystkie okna", command=self._capture_all, width=125, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=1, padx=6)
        ctk.CTkButton(footer, text="Zaznaczone", command=self._capture_selected, width=120).grid(row=0, column=2, padx=6)
        ctk.CTkButton(footer, text="Zamknij", command=self.request_close, width=95, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=3, padx=(6, 0))
        self.refresh()

    def refresh(self) -> None:
        self.windows = [window for window in self.windows_provider() if window is not self]
        self.listbox.delete(0, tk.END)
        for index, window in enumerate(self.windows, 1):
            try:
                title = str(window.title() or "Okno aplikacji")
                size = f"{window.winfo_width()}x{window.winfo_height()}"
            except Exception:
                title, size = "Okno aplikacji", ""
            self.listbox.insert(tk.END, f"{index}. {title}  ({size})")
        if self.windows:
            self.listbox.selection_set(0)

    def _capture_selected(self) -> None:
        indexes = list(self.listbox.curselection()) or ([0] if self.windows else [])
        self._capture([self.windows[index] for index in indexes if index < len(self.windows)])

    def _capture_all(self) -> None:
        self.refresh()
        self._capture(self.windows)

    def _capture(self, windows: list[object]) -> None:
        if not windows:
            messagebox.showwarning("Zrzut ekranu", "Brak widocznych okien do przechwycenia.", parent=self)
            return
        self.running = True
        self.withdraw()
        self.update_idletasks()

        def execute() -> None:
            try:
                paths = capture.capture_windows(windows)
                result = {"mode": "windows", "count": len(paths), "png": [str(path) for path in paths], "folder": str(paths[0].parent)}
                if self.on_result:
                    self.on_result(result)
                self._show_saved(result)
            except Exception as exc:
                messagebox.showerror("Zrzut ekranu", str(exc), parent=self.master)
            finally:
                self.running = False
                self.force_destroy()

        self.after(250, execute)

    def _outside_panel(self) -> None:
        parent = self.master
        setattr(parent, "_external_capture_active", True)
        self.force_destroy()
        try:
            parent.iconify()
        except Exception:
            pass
        overlay = tk.Toplevel(parent)
        overlay.title("Zrzut pulpitu")
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        try:
            overlay.attributes("-toolwindow", True)
        except Exception:
            pass
        width, height = 178, 72
        x = max(12, overlay.winfo_screenwidth() - width - 28)
        y = max(12, overlay.winfo_screenheight() - height - 70)
        overlay.geometry(f"{width}x{height}+{x}+{y}")
        overlay.configure(bg="#111827")
        frame = tk.Frame(overlay, bg="#111827", padx=8, pady=8)
        frame.pack(fill=tk.BOTH, expand=True)

        def restore() -> None:
            setattr(parent, "_external_capture_active", False)
            try:
                overlay.destroy()
            except Exception:
                pass
            try:
                parent.deiconify()
                present_toplevel(parent)
            except Exception:
                pass

        def capture_after_hide() -> None:
            try:
                path = capture.capture_desktop()
                result = {"mode": "desktop", "count": 1, "png": [str(path)], "folder": str(path.parent)}
                if self.on_result:
                    self.on_result(result)
                restore()
                self._show_saved(result, parent=parent)
            except Exception as exc:
                restore()
                messagebox.showerror("Zrzut pulpitu", str(exc), parent=parent)

        def take_shot() -> None:
            overlay.withdraw()
            overlay.after(250, capture_after_hide)

        tk.Button(frame, text="Zrób zrzut", command=take_shot, bg="#15803d", fg="#ffffff", activebackground="#166534", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))
        tk.Button(frame, text="X", command=restore, bg="#374151", fg="#ffffff", activebackground="#4b5563", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), width=4).pack(side=tk.RIGHT, fill=tk.Y)
        overlay.bind("<Escape>", lambda _event: restore())

    def _show_saved(self, result: dict, parent=None) -> None:
        count = int(result.get("count", 0))
        if messagebox.askyesno("Zrzut ekranu", f"Zapisano {count} plik(ów) PNG.\n\nOtworzyć katalog ze zrzutami?", parent=parent or self.master):
            winapi.open_path(result["folder"])
