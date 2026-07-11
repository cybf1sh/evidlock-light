"""Graficzny interfejs EvidLock Light oparty o CustomTkinter.

Light ma lżejszy kod i brak modułów spraw/OCR, ale zachowuje wygodny,
nowoczesny układ znany z EvidLockV2: menu boczne, nagłówek, kafle akcji,
panel wyników i wbudowaną konsolę CLI.
"""

from __future__ import annotations

import contextlib
import io
import json
import shlex
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import APP_NAME, APP_VERSION
from . import cli, themes, winapi
from .config import ensure_runtime_dirs
from .services import archive, capture, copying, docs, hashing, journal, media, memory, network, registry, windows_logs
from .ui.copy_tool import CopyCompareDialog
from .ui.drop_zone import DropZone
from .ui.media_dialog import MediaDialog
from .ui.memory_manager import MemoryManagerDialog
from .ui.logo import EvidLockLogo
from .ui.progress import ProgressDialog
from .ui.report_window import ReportWindow
from .ui.registry_dialog import RegistryExportDialog
from .ui.readonly_dialog import ReadOnlyDialog
from .ui.windows_logs_dialog import WindowsLogsDialog

try:
    from tkinterdnd2 import TkinterDnD
except Exception:
    TkinterDnD = None


FONT = "Segoe UI"
FONT_MONO = "Cascadia Mono"
QUICK_LIMIT = 32
QUICK_CATEGORIES = (
    "Dane i integralność",
    "Nośniki i raporty",
    "Sieć i pamięć",
    "Windows i system",
)


class EvidLockLightApp(ctk.CTk):
    """Modułowa aplikacja Light z GUI i wbudowaną konsolą CLI."""

    def __init__(self) -> None:
        super().__init__()
        self.drag_drop_available = False
        if TkinterDnD is not None:
            try:
                TkinterDnD.require(self)
                self.drag_drop_available = True
            except Exception:
                self.drag_drop_available = False
        ensure_runtime_dirs()
        self.skin = themes.load_skin()
        ctk.set_appearance_mode(themes.appearance_mode(self.skin))
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1240x760")
        self.minsize(1040, 640)
        self.colors = themes.palette(self.skin)
        self._apply_ctk_skin_defaults()
        self.current_page = "Dashboard"
        self.selected_tool_category = QUICK_CATEGORIES[0]
        self.tools_menu_expanded = True
        self.tools_submenu: ctk.CTkFrame | None = None
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.detached_windows: list[ctk.CTkToplevel] = []
        self.output: ctk.CTkTextbox | None = None
        self.console_output: ctk.CTkTextbox | None = None
        self.console_entry: ctk.CTkEntry | None = None
        self.content: ctk.CTkFrame | None = None
        self.quick_selected_frame: ctk.CTkScrollableFrame | None = None
        self.quick_count_label: ctk.CTkLabel | None = None
        self.quick_drag_id: str | None = None
        self.quick_drag_widgets: list[tuple[str, ctk.CTkFrame]] = []
        self.quick_drag_widgets_by_category: dict[str, list[tuple[str, ctk.CTkFrame]]] = {}
        self.quick_tab_frames: dict[str, ctk.CTkScrollableFrame] = {}
        self.quick_editor_frames: dict[str, tuple[ctk.CTkScrollableFrame, ctk.CTkScrollableFrame]] = {}
        self.quick_editor: ctk.CTkToplevel | None = None
        self.quick_editor_count: ctk.CTkLabel | None = None
        self.report_window: ReportWindow | None = None
        self.media_dialog: MediaDialog | None = None
        self.registry_dialog: RegistryExportDialog | None = None
        self.windows_logs_dialog: WindowsLogsDialog | None = None
        self.readonly_dialog: ReadOnlyDialog | None = None
        self.memory_manager_dialog: MemoryManagerDialog | None = None
        self.last_report_title = "Bieżący raport"
        self.last_report_data: object = {"status": "Brak wyników do wyświetlenia."}
        self.quick_drag_category: str | None = None
        self.dropped_paths: list[str] = []
        self.drop_zone: DropZone | None = None
        self._build_shell()
        self.show_page("Dashboard")
        journal.log_event("INFO", "UI", "Uruchomiono EvidLock Light", {"version": APP_VERSION, "drag_drop": self.drag_drop_available})

    def _build_shell(self) -> None:
        self.configure(fg_color=self.colors["bg"])
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=232, fg_color=self.colors["sidebar"], corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill=tk.X, padx=18, pady=(22, 18))
        EvidLockLogo(brand, self.colors["sidebar"], self.colors["brand"], self.colors["logo_fill"], 52).pack(side=tk.LEFT)
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(9, 0))
        ctk.CTkLabel(brand_text, text="EvidLock", text_color=self.colors["brand"], font=(FONT, 17, "bold"), anchor="w").pack(fill=tk.X)
        ctk.CTkLabel(brand_text, text="Light Workstation", text_color=self.colors["sidebar_muted"], font=(FONT, 9), anchor="w").pack(fill=tk.X)

        def add_nav_button(container, label: str, command, indent: bool = False) -> ctk.CTkButton:
            inactive_bg = "#fff8c5" if self.skin == "black" else "transparent"
            inactive_hover = "#fde68a" if self.skin == "black" else self.colors["nav_hover"]
            button = ctk.CTkButton(
                container,
                text=f"  {label}" if indent else label,
                command=command,
                anchor="w",
                height=36 if indent else 40,
                corner_radius=8,
                fg_color=inactive_bg,
                hover_color=inactive_hover,
                text_color=self.colors["sidebar_text"],
                font=(FONT, 10 if indent else 11, "bold" if label == "Dashboard" else "normal"),
            )
            button.pack(fill=tk.X, padx=12 if not indent else 16, pady=2 if indent else 3)
            self.nav_buttons[label] = button
            return button

        add_nav_button(sidebar, "Dashboard", lambda: self.show_page("Dashboard"))
        add_nav_button(sidebar, "Narzędzia", self._toggle_tools_menu).configure(text="Narzędzia ▾")
        self.tools_submenu = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.tools_submenu.pack(fill=tk.X)
        for category in QUICK_CATEGORIES:
            add_nav_button(self.tools_submenu, category, lambda name=category: self.show_tool_category(name), indent=True)
        for label in ("Raporty", "Konsola", "O programie"):
            add_nav_button(sidebar, label, lambda name=label: self.show_page(name))

        ctk.CTkButton(
            sidebar,
            text="Tryb administratora",
            command=self._admin,
            anchor="w",
            height=38,
            fg_color="#991b1b" if winapi.is_admin() else self.colors["nav_hover"],
            hover_color="#b91c1c" if winapi.is_admin() else self.colors["accent_hover"],
            text_color="#ffffff",
            font=(FONT, 10, "bold"),
        ).pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=14)

        main = ctk.CTkFrame(self, fg_color=self.colors["bg"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(header, text="", text_color=self.colors["text"], font=(FONT, 23, "bold"), anchor="w")
        self.title_label.grid(row=0, column=0, sticky="ew")
        self.subtitle_label = ctk.CTkLabel(header, text="", text_color=self.colors["muted"], font=(FONT, 11), anchor="w")
        self.subtitle_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        controls = ctk.CTkFrame(
            header,
            fg_color=self.colors["card"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=8,
        )
        controls.grid(row=0, column=1, rowspan=2, padx=(12, 0), sticky="e")
        ctk.CTkLabel(controls, text="Skórka", text_color=self.colors["muted"], font=(FONT, 10, "bold")).pack(side=tk.LEFT, padx=(10, 6), pady=8)
        self.skin_menu = ctk.CTkOptionMenu(
            controls,
            values=list(themes.SKIN_LABELS.values()),
            command=self._change_skin,
            width=106,
            height=34,
            fg_color=self.colors["soft"],
            button_color=self.colors["accent"],
            button_hover_color=self.colors["accent_hover"],
            dropdown_fg_color=self.colors["card"],
            dropdown_hover_color=self.colors["soft"],
            dropdown_text_color=self.colors["text"],
            text_color=self.colors["text"],
        )
        self.skin_menu.set(themes.SKIN_LABELS[self.skin])
        self.skin_menu.pack(side=tk.LEFT, padx=(0, 8), pady=8)
        ctk.CTkButton(controls, text="Konsola", width=100, height=34, command=lambda: self.show_page("Konsola")).pack(side=tk.LEFT, padx=(0, 8), pady=8)
        ctk.CTkButton(controls, text="O programie", width=112, height=34, command=lambda: self.show_page("O programie")).pack(side=tk.LEFT, padx=(0, 8), pady=8)

        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def _apply_ctk_skin_defaults(self) -> None:
        """Ujednolica neutralne przyciski z aktywną paletą aplikacji."""

        button_theme = ctk.ThemeManager.theme["CTkButton"]
        button_theme["fg_color"] = self.colors["accent"]
        button_theme["hover_color"] = self.colors["accent_hover"]
        button_theme["text_color"] = "#ffffff"

    def show_page(self, page: str) -> None:
        self.current_page = page
        page_category = {
            "Nośniki": "Nośniki i raporty",
            "Zabezpieczanie": "Dane i integralność",
            "Network": "Sieć i pamięć",
            "Pamięć": "Sieć i pamięć",
            "System": "Windows i system",
            "Dziennik": "Windows i system",
        }.get(page)
        for name, button in self.nav_buttons.items():
            active = name == page or (name == "Narzędzia" and (page == "Narzędzia" or page_category is not None)) or (name == (self.selected_tool_category if page == "Narzędzia" else page_category))
            inactive_bg = "#fff8c5" if self.skin == "black" else "transparent"
            inactive_hover = "#fde68a" if self.skin == "black" else self.colors["nav_hover"]
            button.configure(
                fg_color=self.colors["accent"] if active else inactive_bg,
                hover_color=self.colors["accent_hover"] if active else inactive_hover,
                text_color="#ffffff" if active and self.skin == "black" else self.colors["sidebar_text"],
                font=(FONT, 11, "bold" if active else "normal"),
            )
        if self.content is None:
            return
        self.output = None
        self.console_output = None
        self.console_entry = None
        for child in self.content.winfo_children():
            child.destroy()
        subtitles = {
            "Dashboard": "Centralny panel szybkich akcji i codziennych narzędzi.",
            "Narzędzia": "Wszystkie funkcje uporządkowane w tej samej kategorii co na Dashboardzie.",
            "Network": "Skaner TCP, TShark i punkt rozbudowy Network Analyzer.",
            "Pamięć": "Kontrola WinPmem i Volatility 3.",
            "System": "Rejestr, logi Windows, zrzut głównego okna.",
            "Raporty": "Szybki dostęp do generatorów raportów.",
            "Dziennik": "Dziennik operacji programu, eksport TXT/JSON.",
            "Konsola": "Wbudowane CLI. Wszystkie opcje programu są dostępne jako komendy.",
            "O programie": "Informacje, funkcje, dokumentacja techniczna i diagnostyka.",
        }
        display_title = self.selected_tool_category if page == "Narzędzia" else page
        self.title_label.configure(text=display_title)
        self.subtitle_label.configure(text=subtitles.get(page, ""))
        getattr(self, f"_page_{self._method_name(page)}")()

    def _toggle_tools_menu(self) -> None:
        if self.tools_submenu is None:
            return
        self.tools_menu_expanded = not self.tools_menu_expanded
        if self.tools_menu_expanded:
            self.tools_submenu.pack(fill=tk.X, after=self.nav_buttons["Narzędzia"])
        else:
            self.tools_submenu.pack_forget()
        self.nav_buttons["Narzędzia"].configure(text=f"Narzędzia {'▾' if self.tools_menu_expanded else '▸'}")

    def show_tool_category(self, category: str) -> None:
        self.selected_tool_category = category if category in QUICK_CATEGORIES else QUICK_CATEGORIES[0]
        if not self.tools_menu_expanded:
            self._toggle_tools_menu()
        self.show_page("Narzędzia")

    def _change_skin(self, label: str) -> None:
        """Zapisuje wybor i przebudowuje powloke bez restartu procesu."""

        skin = themes.skin_from_label(label)
        if skin == self.skin:
            return
        page = self.current_page
        self.skin = skin
        themes.save_skin(skin)
        ctk.set_appearance_mode(themes.appearance_mode(skin))
        self.colors = themes.palette(skin)
        self._apply_ctk_skin_defaults()
        for window in self.detached_windows:
            if window.winfo_exists():
                window.destroy()
        self.detached_windows.clear()
        self.report_window = None
        self.media_dialog = None
        self.registry_dialog = None
        self.windows_logs_dialog = None
        self.readonly_dialog = None
        self.memory_manager_dialog = None
        for child in self.winfo_children():
            child.destroy()
        self.nav_buttons.clear()
        self.output = None
        self.console_output = None
        self.console_entry = None
        self.content = None
        self._build_shell()
        self.show_page(page)
        journal.log_event("INFO", "UI", f"Zmieniono skórkę: {themes.SKIN_LABELS[skin]}")

    def _method_name(self, page: str) -> str:
        return {
            "Nośniki": "media",
            "Zabezpieczanie": "security",
            "Szybkie akcje": "quick",
            "Narzędzia": "tools",
            "Pamięć": "memory",
            "Dziennik": "journal",
            "Konsola": "console",
            "O programie": "about",
        }.get(page, page.lower())

    def _layout_with_output(self) -> ctk.CTkFrame:
        assert self.content is not None
        self.content.grid_columnconfigure(0, weight=3)
        self.content.grid_columnconfigure(1, weight=2)
        self.content.grid_rowconfigure(0, weight=1)
        actions = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        actions.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        result = ctk.CTkFrame(self.content, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        result.grid(row=0, column=1, sticky="nsew")
        result.grid_rowconfigure(1, weight=1)
        result.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(result, text="Wynik operacji", text_color=self.colors["text"], font=(FONT, 13, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        self.output = ctk.CTkTextbox(result, font=(FONT_MONO, 10), wrap="word", fg_color=self.colors["soft"])
        self.output.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._write({"status": "Gotowe"}, capture_report=False)
        return actions

    def _action_card(self, parent, title: str, text: str, command, color: str | None = None) -> None:
        card = ctk.CTkFrame(parent, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        card.pack(fill=tk.X, pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, text_color=self.colors["text"], font=(FONT, 14, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
        ctk.CTkLabel(card, text=text, text_color=self.colors["muted"], font=(FONT, 10), anchor="w", wraplength=560, justify="left").grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        ctk.CTkButton(card, text="Uruchom", command=command, width=116, fg_color=color or self.colors["accent"], hover_color=self.colors["accent_hover"]).grid(row=0, column=1, rowspan=2, padx=14, pady=14)

    def _detach_button(self, parent, title: str, builder, use_grid: bool = False) -> None:
        button = ctk.CTkButton(
            parent,
            text="Odepnij panel",
            command=lambda: self._open_detached(title, builder),
            width=128,
            fg_color=self.colors["card"],
            hover_color=self.colors["soft"],
            text_color=self.colors["text"],
            border_width=1,
            border_color=self.colors["border"],
        )
        if use_grid:
            button.grid(row=0, column=0, sticky="e", pady=(0, 10))
        else:
            button.pack(anchor="e", pady=(0, 10))

    def _open_detached(self, title: str, builder) -> None:
        window = ctk.CTkToplevel(self)
        self.detached_windows.append(window)
        window.title(title)
        window.geometry("780x560")
        window.minsize(620, 420)
        window.configure(fg_color=self.colors["bg"])
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(window, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=title, text_color=self.colors["text"], font=(FONT, 18, "bold"), anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(header, text="Zamknij", width=96, command=window.destroy).grid(row=0, column=1, padx=(8, 0))
        body = ctk.CTkFrame(window, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        builder(body, detached=True)
        journal.log_event("INFO", "UI", f"Odepnieto panel: {title}")

    def _write(self, data, title: str | None = None, capture_report: bool = True) -> None:
        if capture_report:
            self.last_report_title = title or self.current_page
            self.last_report_data = data
            if self.report_window is not None:
                try:
                    if self.report_window.winfo_exists():
                        self.report_window.update_report(self.last_report_title, data)
                    else:
                        self.report_window = None
                except Exception:
                    self.report_window = None
        if self.output is None or not self.output.winfo_exists():
            return
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2)
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def show_report(self, title: str | None = None, data: object | None = None) -> None:
        """Otwiera albo odświeża jedno wspólne okno bieżącego raportu."""

        if title is not None:
            self.last_report_title = title
        if data is not None:
            self.last_report_data = data
        if self.report_window is not None:
            try:
                if self.report_window.winfo_exists():
                    self.report_window.update_report(self.last_report_title, self.last_report_data)
                    self.report_window.deiconify()
                    self.report_window.lift()
                    self.report_window.focus_force()
                    return
            except Exception:
                pass
        self.report_window = ReportWindow(self, self.colors, on_close=lambda: setattr(self, "report_window", None))
        self.detached_windows.append(self.report_window)
        self.report_window.update_report(self.last_report_title, self.last_report_data)

    def _run(self, func) -> None:
        try:
            result = func()
            self._write(result)
            journal.log_event("OK", self.current_page, "Operacja wykonana", {"result": self._compact_result(result)})
        except Exception as exc:
            self._write({"błąd": str(exc)})
            journal.log_event("BŁĄD", self.current_page, str(exc))

    def _run_progress(self, title: str, worker) -> None:
        dialog = ProgressDialog(self, title, self.colors, FONT)
        self.detached_windows.append(dialog)

        def done(result) -> None:
            self._write(result)
            journal.log_event("OK", self.current_page, title, {"result": self._compact_result(result)})

        dialog.start(worker, on_done=done)

    def _compact_result(self, result) -> dict:
        if isinstance(result, list):
            return {"items": len(result)}
        if isinstance(result, dict):
            return {key: value for key, value in result.items() if key in {"pdf", "json", "txt", "events", "archive", "manifest"}}
        return {"type": type(result).__name__}

    def _page_dashboard(self) -> None:
        self._build_quick_workspace(self.content)

    def _tool_definitions(self) -> dict[str, dict]:
        """Jedno źródło definicji dla panelu narzędzi i Szybkich akcji."""

        return {
            "copy": {"title": "Kopia 1:1", "text": "Kopia z metadanymi, SHA-256 i raportem.", "category": "Dane i integralność", "color": self.colors["green"], "command": self._copy_1to1},
            "compare": {"title": "Porównaj A/B", "text": "Porównanie plików lub katalogów z raportem.", "category": "Dane i integralność", "color": self.colors["teal"], "command": self._compare},
            "archive": {"title": "Archiwizacja ZIP", "text": "Archiwum danych z paskiem postępu.", "category": "Dane i integralność", "color": self.colors["purple"], "command": self._archive},
            "hash": {"title": "SHA-256 pliku", "text": "Obliczenie skrótu wybranego pliku.", "category": "Dane i integralność", "color": self.colors["accent"], "command": self._hash_file},
            "manifest": {"title": "Manifest katalogu", "text": "Lista plików i sum SHA-256 w JSON.", "category": "Dane i integralność", "color": self.colors["accent"], "command": self._manifest},
            "readonly": {"title": "Ochrona read-only", "text": "Sprawdź, ustaw lub usuń atrybut tylko do odczytu.", "category": "Dane i integralność", "color": self.colors["green"], "command": self._open_readonly_dialog},
            "media": {"title": "Informacje o nośnikach", "text": "Okno dysków z ikonami, zajętością i raportem.", "category": "Nośniki i raporty", "color": self.colors["accent"], "command": self._open_media_dialog},
            "media_report": {"title": "Raport nośników", "text": "Raport PDF informacji o nośnikach.", "category": "Nośniki i raporty", "color": self.colors["purple"], "command": self._media_report},
            "reports": {"title": "Raporty", "text": "Otwórz centralny panel raportów.", "category": "Nośniki i raporty", "color": self.colors["red"], "command": lambda: self.show_page("Raporty")},
            "network": {"title": "Network Analyzer", "text": "Skaner TCP i narzędzia TShark.", "category": "Sieć i pamięć", "color": self.colors["teal"], "command": lambda: self.show_page("Network")},
            "memory": {"title": "Pamięć RAM", "text": "WinPmem, Volatility 3 i manager pamięci.", "category": "Sieć i pamięć", "color": self.colors["purple"], "command": lambda: self.show_page("Pamięć")},
            "registry": {"title": "Eksport rejestru", "text": "Pełne okno hive, dane i raporty rejestru.", "category": "Windows i system", "color": self.colors["red"], "command": self._open_registry_dialog},
            "windows_logs": {"title": "Logi Windows", "text": "Pełne okno opcji, EVTX i raportów logów.", "category": "Windows i system", "color": self.colors["red"], "command": self._open_windows_logs_dialog},
            "journal": {"title": "Dziennik Light", "text": "Podgląd i eksport operacji programu.", "category": "Windows i system", "color": self.colors["accent"], "command": lambda: self.show_page("Dziennik")},
            "capture": {"title": "Zrzut okna", "text": "PNG wyłącznie z głównego okna.", "category": "Windows i system", "color": self.colors["accent"], "command": lambda: self._run(lambda: {"png": str(capture.capture_window(self))})},
            "console": {"title": "Konsola", "text": "Wbudowane CLI wszystkich modułów.", "category": "Windows i system", "color": self.colors["purple"], "command": lambda: self.show_page("Konsola")},
        }

    def _default_quick_config(self) -> dict[str, list[str]]:
        return {
            "Dane i integralność": ["copy", "compare", "hash", "archive", "readonly"],
            "Nośniki i raporty": ["media", "reports"],
            "Sieć i pamięć": ["network", "memory"],
            "Windows i system": ["windows_logs", "registry", "capture"],
        }

    def _quick_config(self) -> dict[str, list[str]]:
        definitions = self._tool_definitions()
        settings = themes.load_settings()
        saved = settings.get("quick_actions_by_category")
        if not isinstance(saved, dict):
            legacy = settings.get("quick_actions")
            if isinstance(legacy, list):
                saved = {category: [item for item in legacy if definitions.get(item, {}).get("category") == category] for category in QUICK_CATEGORIES}
            else:
                saved = self._default_quick_config()
        result = {category: [] for category in QUICK_CATEGORIES}
        used: set[str] = set()
        for category in QUICK_CATEGORIES:
            values = saved.get(category, []) if isinstance(saved, dict) else []
            if category == "Dane i integralność" and isinstance(values, list) and any(item in values for item in ("readonly_set", "readonly_clear")):
                values = [item for item in values if item not in {"readonly_set", "readonly_clear"}]
                if "readonly" not in values:
                    values.append("readonly")
            for tool_id in values if isinstance(values, list) else []:
                if tool_id in definitions and definitions[tool_id]["category"] == category and tool_id not in used:
                    result[category].append(tool_id)
                    used.add(tool_id)
        return result

    def _quick_ids(self) -> list[str]:
        config = self._quick_config()
        return [tool_id for category in QUICK_CATEGORIES for tool_id in config[category]][:QUICK_LIMIT]

    def _save_quick_config(self, config: dict[str, list[str]]) -> None:
        data = themes.load_settings()
        cleaned: dict[str, list[str]] = {}
        count = 0
        definitions = self._tool_definitions()
        for category in QUICK_CATEGORIES:
            cleaned[category] = []
            for tool_id in config.get(category, []):
                if count >= QUICK_LIMIT:
                    break
                if tool_id in definitions and definitions[tool_id]["category"] == category and tool_id not in cleaned[category]:
                    cleaned[category].append(tool_id)
                    count += 1
        data["quick_actions_by_category"] = cleaned
        data.pop("quick_actions", None)
        themes.save_settings(data)

    def _build_quick_workspace(self, parent, detached: bool = False) -> None:
        assert parent is not None
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        self.drop_zone = DropZone(parent, self, self.colors, self.dropped_paths, large=True)
        self.drop_zone.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        workspace = ctk.CTkFrame(parent, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(workspace, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
        toolbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(toolbar, text="Narzędzia podręczne", text_color=self.colors["text"], font=(FONT, 14, "bold"), anchor="w").grid(row=0, column=0, sticky="ew")
        self.quick_count_label = ctk.CTkLabel(toolbar, text="", text_color=self.colors["muted"], font=(FONT, 9, "bold"))
        self.quick_count_label.grid(row=0, column=1, padx=8)
        gear = ctk.CTkButton(toolbar, text="⚙", width=34, height=30, command=self._open_quick_settings, fg_color=self.colors["soft"], hover_color=self.colors["border"], text_color=self.colors["text"], border_width=1, border_color=self.colors["border"], font=(FONT, 16))
        gear.grid(row=0, column=2)
        self._attach_tooltip(gear, "Konfiguruj Szybkie akcje")

        tabs = ctk.CTkTabview(workspace, fg_color="transparent", segmented_button_fg_color=self.colors["soft"], segmented_button_selected_color=self.colors["accent"], segmented_button_selected_hover_color=self.colors["accent_hover"], border_width=0, corner_radius=0)
        tabs.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.quick_tab_frames = {}
        for category in QUICK_CATEGORIES:
            tab = tabs.add(category)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            frame.grid_columnconfigure((0, 1), weight=1, uniform="quick")
            self.quick_tab_frames[category] = frame
        self._render_quick_tabs()

    def on_dropped_paths_changed(self) -> None:
        journal.log_event("INFO", "DragDrop", "Zmieniono listę przeciągniętych elementów", {"count": len(self.dropped_paths)})

    def _render_quick_tabs(self) -> None:
        config = self._quick_config()
        definitions = self._tool_definitions()
        if self.quick_count_label is not None and self.quick_count_label.winfo_exists():
            self.quick_count_label.configure(text=f"{len(self._quick_ids())}/{QUICK_LIMIT}")
        for category, frame in self.quick_tab_frames.items():
            if not frame.winfo_exists():
                continue
            for child in frame.winfo_children():
                child.destroy()
            selected = config[category]
            if not selected:
                ctk.CTkLabel(frame, text="Brak aktywnych narzędzi w tej zakładce. Dodaj je przez ⚙.", text_color=self.colors["muted"], font=(FONT, 10), anchor="center").grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=40)
                continue
            for index, tool_id in enumerate(selected):
                definition = definitions[tool_id]
                card = ctk.CTkFrame(frame, height=96, fg_color=self.colors["soft"], border_width=1, border_color=self.colors["border"], corner_radius=7)
                card.grid(row=index // 2, column=index % 2, sticky="ew", padx=5, pady=5)
                card.pack_propagate(False)
                ctk.CTkFrame(card, width=5, fg_color=definition["color"], corner_radius=3).pack(side=tk.LEFT, fill=tk.Y, pady=6)
                ctk.CTkButton(card, text="Uruchom", width=86, height=30, command=definition["command"], fg_color=definition["color"]).pack(side=tk.RIGHT, padx=10)
                body = ctk.CTkFrame(card, fg_color="transparent")
                body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=8)
                ctk.CTkLabel(body, text=definition["title"], text_color=self.colors["text"], font=(FONT, 11, "bold"), anchor="w").pack(fill=tk.X)
                ctk.CTkLabel(body, text=definition["text"], text_color=self.colors["muted"], font=(FONT, 8), anchor="w", justify="left", wraplength=300).pack(fill=tk.X, pady=(1, 0))

    def _open_quick_settings(self) -> None:
        if self.quick_editor is not None:
            try:
                if self.quick_editor.winfo_exists():
                    self.quick_editor.lift()
                    self.quick_editor.focus_force()
                    return
            except Exception:
                pass
        window = ctk.CTkToplevel(self)
        self.quick_editor = window
        self.detached_windows.append(window)
        window.title("Konfiguracja Szybkich akcji")
        window.geometry("1120x760")
        window.minsize(920, 620)
        window.configure(fg_color=self.colors["bg"])
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(window, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Konfiguracja Szybkich akcji", text_color=self.colors["text"], font=(FONT, 21, "bold"), anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="W każdej zakładce dodawaj funkcje z prawej strony i przeciągaj aktywne narzędzia po lewej.", text_color=self.colors["muted"], font=(FONT, 9), anchor="w").grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.quick_editor_count = ctk.CTkLabel(header, text="", text_color=self.colors["accent"], font=(FONT, 10, "bold"))
        self.quick_editor_count.grid(row=0, column=1, rowspan=2, padx=8)
        ctk.CTkButton(header, text="Dodaj wszystkie", width=120, command=self._add_all_quick_actions).grid(row=0, column=2, rowspan=2, padx=4)
        ctk.CTkButton(header, text="Resetuj", width=90, command=self._reset_quick_actions, fg_color=self.colors["soft"], text_color=self.colors["text"], border_width=1, border_color=self.colors["border"]).grid(row=0, column=3, rowspan=2, padx=4)
        def close_editor() -> None:
            self.quick_editor = None
            self.quick_editor_frames = {}
            window.destroy()

        ctk.CTkButton(header, text="Zamknij", width=90, command=close_editor).grid(row=0, column=4, rowspan=2, padx=(4, 0))
        tabs = ctk.CTkTabview(window, fg_color=self.colors["card"], segmented_button_fg_color=self.colors["soft"], segmented_button_selected_color=self.colors["accent"], segmented_button_selected_hover_color=self.colors["accent_hover"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        tabs.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.quick_editor_frames = {}
        for category in QUICK_CATEGORIES:
            tab = tabs.add(category)
            tab.grid_columnconfigure((0, 1), weight=1, uniform="editor")
            tab.grid_rowconfigure(1, weight=1)
            ctk.CTkLabel(tab, text="Aktywne w panelu", text_color=self.colors["text"], font=(FONT, 12, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=(8, 5), pady=(8, 4))
            ctk.CTkLabel(tab, text="Dostępne narzędzia", text_color=self.colors["text"], font=(FONT, 12, "bold"), anchor="w").grid(row=0, column=1, sticky="ew", padx=(5, 8), pady=(8, 4))
            selected = ctk.CTkScrollableFrame(tab, fg_color=self.colors["soft"], corner_radius=7)
            selected.grid(row=1, column=0, sticky="nsew", padx=(8, 5), pady=(0, 8))
            available = ctk.CTkScrollableFrame(tab, fg_color=self.colors["soft"], corner_radius=7)
            available.grid(row=1, column=1, sticky="nsew", padx=(5, 8), pady=(0, 8))
            self.quick_editor_frames[category] = (selected, available)
        window.protocol("WM_DELETE_WINDOW", close_editor)
        self._refresh_quick_editor()

    def _refresh_quick_editor(self) -> None:
        config = self._quick_config()
        definitions = self._tool_definitions()
        self.quick_drag_widgets_by_category = {}
        if self.quick_editor_count is not None and self.quick_editor_count.winfo_exists():
            self.quick_editor_count.configure(text=f"{len(self._quick_ids())}/{QUICK_LIMIT}")
        for category, frames in self.quick_editor_frames.items():
            selected_frame, available_frame = frames
            if not selected_frame.winfo_exists():
                continue
            for frame in frames:
                for child in frame.winfo_children():
                    child.destroy()
            self.quick_drag_widgets_by_category[category] = []
            selected_ids = config[category]
            if not selected_ids:
                ctk.CTkLabel(selected_frame, text="Przeciągnij lub dodaj narzędzie z prawej strony.", text_color=self.colors["muted"], font=(FONT, 9), wraplength=330).pack(fill=tk.X, padx=12, pady=24)
            for index, tool_id in enumerate(selected_ids):
                definition = definitions[tool_id]
                row = ctk.CTkFrame(selected_frame, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=7)
                row.pack(fill=tk.X, padx=4, pady=4)
                row.grid_columnconfigure(1, weight=1)
                handle = ctk.CTkLabel(row, text="↕", width=30, text_color=self.colors["muted"], font=(FONT, 17), cursor="fleur")
                handle.grid(row=0, column=0, rowspan=2, padx=(5, 2))
                handle.bind("<ButtonPress-1>", lambda _event, item=tool_id, cat=category: self._start_quick_drag(item, cat))
                handle.bind("<ButtonRelease-1>", self._finish_quick_drag)
                ctk.CTkLabel(row, text=definition["title"], text_color=self.colors["text"], font=(FONT, 10, "bold"), anchor="w").grid(row=0, column=1, sticky="ew", pady=(7, 1))
                ctk.CTkLabel(row, text=definition["text"], text_color=self.colors["muted"], font=(FONT, 8), anchor="w").grid(row=1, column=1, sticky="ew", pady=(0, 7))
                ctk.CTkButton(row, text="↑", width=28, height=27, command=lambda item=tool_id, cat=category: self._move_quick(item, -1, cat), state="disabled" if index == 0 else "normal").grid(row=0, column=2, rowspan=2, padx=2)
                ctk.CTkButton(row, text="↓", width=28, height=27, command=lambda item=tool_id, cat=category: self._move_quick(item, 1, cat), state="disabled" if index == len(selected_ids) - 1 else "normal").grid(row=0, column=3, rowspan=2, padx=2)
                ctk.CTkButton(row, text="×", width=28, height=27, command=lambda item=tool_id: self._remove_quick_action(item), fg_color=self.colors["red"]).grid(row=0, column=4, rowspan=2, padx=(2, 7))
                self.quick_drag_widgets_by_category[category].append((tool_id, row))
            for tool_id, definition in definitions.items():
                if definition["category"] != category:
                    continue
                used = tool_id in selected_ids
                row = ctk.CTkFrame(available_frame, fg_color=self.colors["card"] if not used else self.colors["border"], corner_radius=7)
                row.pack(fill=tk.X, padx=4, pady=4)
                row.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=definition["title"], text_color=self.colors["muted"] if used else self.colors["text"], font=(FONT, 10, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=9, pady=(7, 1))
                ctk.CTkLabel(row, text=definition["text"], text_color=self.colors["muted"], font=(FONT, 8), anchor="w").grid(row=1, column=0, sticky="ew", padx=9, pady=(0, 7))
                ctk.CTkButton(row, text="Dodano" if used else "+", width=58 if used else 32, height=28, state="disabled" if used else "normal", command=lambda item=tool_id: self._add_quick_action(item), fg_color=definition["color"]).grid(row=0, column=1, rowspan=2, padx=8)

    def _refresh_quick_views(self) -> None:
        self._render_quick_tabs()
        if self.quick_editor is not None:
            try:
                if self.quick_editor.winfo_exists():
                    self._refresh_quick_editor()
            except Exception:
                self.quick_editor = None

    def _add_quick_action(self, tool_id: str) -> None:
        config = self._quick_config()
        definitions = self._tool_definitions()
        if tool_id in self._quick_ids():
            return
        if len(self._quick_ids()) >= QUICK_LIMIT:
            messagebox.showwarning("Szybkie akcje", f"Panel zawiera już maksymalnie {QUICK_LIMIT} narzędzia.", parent=self.quick_editor or self)
            return
        category = definitions[tool_id]["category"]
        config[category].append(tool_id)
        self._save_quick_config(config)
        self._refresh_quick_views()

    def _remove_quick_action(self, tool_id: str) -> None:
        config = self._quick_config()
        for category in QUICK_CATEGORIES:
            config[category] = [item for item in config[category] if item != tool_id]
        self._save_quick_config(config)
        self._refresh_quick_views()

    def _move_quick(self, tool_id: str, direction: int, category: str | None = None) -> None:
        config = self._quick_config()
        category = category or self._tool_definitions()[tool_id]["category"]
        items = config[category]
        index = items.index(tool_id)
        target = max(0, min(len(items) - 1, index + direction))
        if target != index:
            items.insert(target, items.pop(index))
            self._save_quick_config(config)
            self._refresh_quick_views()

    def _start_quick_drag(self, tool_id: str, category: str) -> None:
        self.quick_drag_id = tool_id
        self.quick_drag_category = category

    def _finish_quick_drag(self, event) -> None:
        tool_id = self.quick_drag_id
        category = self.quick_drag_category
        self.quick_drag_id = None
        self.quick_drag_category = None
        if not tool_id or not category:
            return
        widgets = self.quick_drag_widgets_by_category.get(category, [])
        target = max(0, len(widgets) - 1)
        for index, (_item, widget) in enumerate(widgets):
            if event.y_root < widget.winfo_rooty() + widget.winfo_height() / 2:
                target = index
                break
        config = self._quick_config()
        items = config[category]
        items.insert(target, items.pop(items.index(tool_id)))
        self._save_quick_config(config)
        self._refresh_quick_views()

    def _reset_quick_actions(self) -> None:
        self._save_quick_config(self._default_quick_config())
        self._refresh_quick_views()

    def _add_all_quick_actions(self) -> None:
        definitions = self._tool_definitions()
        config = {category: [tool_id for tool_id, definition in definitions.items() if definition["category"] == category] for category in QUICK_CATEGORIES}
        self._save_quick_config(config)
        self._refresh_quick_views()

    def _attach_tooltip(self, widget, text: str) -> None:
        state = {"window": None}
        def show(_event=None):
            if state["window"] is not None:
                return
            tip = tk.Toplevel(self)
            tip.overrideredirect(True)
            tip.attributes("-topmost", True)
            tip.geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty() + widget.winfo_height() + 4}")
            tk.Label(tip, text=text, bg="#111827", fg="#ffffff", padx=8, pady=4, font=(FONT, 9)).pack()
            state["window"] = tip
        def hide(_event=None):
            if state["window"] is not None:
                state["window"].destroy()
                state["window"] = None
        widget.bind("<Enter>", show, add="+")
        widget.bind("<Leave>", hide, add="+")

    def _build_quick_panel(self, parent, detached: bool = False) -> None:
        self._build_quick_workspace(parent, detached=detached)

    def _page_quick(self) -> None:
        assert self.content is not None
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self._build_quick_panel(self.content)

    def _build_tools_panel(self, parent, detached: bool = False, category: str | None = None) -> None:
        parent.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure((0, 1), weight=1, uniform="tools")
        parent.grid_rowconfigure(0, weight=1)
        definitions = self._tool_definitions()
        selected = category or self.selected_tool_category
        items = [definition for definition in definitions.values() if definition["category"] == selected]
        for index, definition in enumerate(items):
            tile = ctk.CTkFrame(frame, height=90, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=7)
            tile.grid(row=index // 2, column=index % 2, sticky="ew", padx=5, pady=5)
            tile.pack_propagate(False)
            ctk.CTkFrame(tile, width=4, fg_color=definition["color"], corner_radius=2).pack(side=tk.LEFT, fill=tk.Y, pady=5)
            ctk.CTkButton(tile, text="Otwórz", width=76, height=30, command=definition["command"], fg_color=definition["color"]).pack(side=tk.RIGHT, padx=9)
            body = ctk.CTkFrame(tile, fg_color="transparent")
            body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=8)
            ctk.CTkLabel(body, text=definition["title"], text_color=self.colors["text"], font=(FONT, 12, "bold"), anchor="w").pack(fill=tk.X)
            ctk.CTkLabel(body, text=definition["text"], text_color=self.colors["muted"], font=(FONT, 9), anchor="w", justify="left", wraplength=290).pack(fill=tk.X, pady=(2, 0))

    def _page_tools(self) -> None:
        assert self.content is not None
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)
        category = self.selected_tool_category
        self._detach_button(self.content, category, lambda parent, detached=False: self._build_tools_panel(parent, detached, category), use_grid=True)
        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        self._build_tools_panel(body, category=category)

    def _page_media(self) -> None:
        actions = self._layout_with_output()
        self._action_card(actions, "Informacje o nośnikach", "Otwórz pełne okno nośników z ikonami dysków jak w EvidLockV2.", self._open_media_dialog)
        self._action_card(actions, "Odśwież nośniki", "Pokaż dyski, typy, system plików, zajętość i nośniki wirtualne.", lambda: self._run(media.list_media))
        self._action_card(actions, "Raport PDF nośników", "Wygeneruj zbiorczy raport PDF z informacjami o nośnikach.", self._media_report)
        self._action_card(actions, "Eksport JSON", "Zapisz surowe dane nośników do pliku JSON.", lambda: self._run(lambda: {"json": str(media.export_media_json())}))

    def _open_media_dialog(self) -> None:
        if self.media_dialog is not None and self.media_dialog.winfo_exists():
            self.media_dialog.refresh()
            self.media_dialog.lift()
            self.media_dialog.focus_force()
            return
        self.media_dialog = MediaDialog(self, self.colors, on_result=lambda result: self._write(result, "Raport nośników"))
        self.detached_windows.append(self.media_dialog)

    def _page_security(self) -> None:
        actions = self._layout_with_output()
        self._action_card(actions, "SHA-256 pliku", "Oblicz SHA-256 wskazanego pliku.", self._hash_file)
        self._action_card(actions, "Manifest katalogu", "Zapisz manifest SHA-256 dla katalogu.", self._manifest)
        self._action_card(actions, "Archiwizacja ZIP", "Utwórz archiwum ze stanem postępu.", self._archive)
        self._action_card(actions, "Porównaj A/B", "Porównaj pliki lub katalogi bez wykonywania kopii.", self._compare)
        self._action_card(actions, "Kopia 1:1", "Skopiuj katalog lub plik 1:1 z zachowaniem metadanych.", self._copy_1to1)
        self._action_card(actions, "Ochrona read-only", "Sprawdź status, ustaw albo usuń atrybut w jednym panelu.", self._open_readonly_dialog)

    def _page_network(self) -> None:
        actions = self._layout_with_output()
        status = network.tshark_status()
        dependency = ctk.CTkFrame(actions, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        dependency.pack(fill=tk.X, pady=(0, 10))
        dependency.grid_columnconfigure(0, weight=1)
        status_text = f"TShark GOTOWY\n{status['path']}" if status["available"] else "TShark BRAK\nNetwork Analyzer wymaga komponentu TShark z pakietu Wireshark."
        ctk.CTkLabel(dependency, text=status_text, text_color=self.colors["green"] if status["available"] else self.colors["red"], font=(FONT, 10, "bold"), anchor="w", justify="left", wraplength=520).grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkButton(dependency, text="Odśwież status", width=115, command=lambda: self.show_page("Network")).grid(row=1, column=1, padx=4, pady=(0, 10))
        install = ctk.CTkButton(dependency, text="Instaluj Wireshark/TShark", width=175, command=self._install_tshark, state="disabled" if status["available"] else "normal")
        install.grid(row=1, column=2, padx=(4, 10), pady=(0, 10))
        form = ctk.CTkFrame(actions, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        form.pack(fill=tk.X, pady=(0, 10))
        host = ctk.CTkEntry(form, placeholder_text="Host/IP", width=180)
        host.grid(row=0, column=0, padx=14, pady=(14, 6), sticky="ew")
        ports = ctk.CTkEntry(form, placeholder_text="Porty", width=180)
        ports.insert(0, "22,80,443,445,3389")
        ports.grid(row=0, column=1, padx=(0, 14), pady=(14, 6), sticky="ew")
        ctk.CTkButton(form, text="Skanuj TCP", command=lambda: self._run(lambda: network.scan_tcp(host.get(), network.parse_ports(ports.get())))).grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))
        self._action_card(actions, "Status techniczny TShark", "Pokaż pełną informację diagnostyczną komponentu.", lambda: self._run(network.tshark_status), self.colors["teal"])

    def _page_memory(self) -> None:
        actions = self._layout_with_output()
        status = memory.dependency_status()
        dependency = ctk.CTkFrame(actions, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        dependency.pack(fill=tk.X, pady=(0, 10))
        dependency.grid_columnconfigure(0, weight=1)
        winpmem_text = f"WinPmem GOTOWY: {status['winpmem_path']}" if status["winpmem_present"] else "WinPmem BRAK - pobierz oficjalny plik i wskaż go w managerze."
        volatility_text = f"Volatility 3 GOTOWY: {status['volatility_path']}" if status["volatility_present"] else "Volatility 3 BRAK - użyj przycisku instalacji."
        ctk.CTkLabel(dependency, text=f"{winpmem_text}\n{volatility_text}", text_color=self.colors["green"] if status["winpmem_present"] and status["volatility_present"] else self.colors["red"], font=(FONT, 10, "bold"), anchor="w", justify="left", wraplength=520).grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkButton(dependency, text="Odśwież", width=85, command=lambda: self.show_page("Pamięć")).grid(row=1, column=1, padx=4, pady=(0, 10))
        ctk.CTkButton(dependency, text="Instaluj Volatility 3", width=145, command=self._install_volatility, state="disabled" if status["volatility_present"] else "normal").grid(row=1, column=2, padx=4, pady=(0, 10))
        ctk.CTkButton(dependency, text="Pobierz WinPmem", width=125, command=lambda: self._run(memory.open_winpmem_download), state="disabled" if status["winpmem_present"] else "normal").grid(row=1, column=3, padx=(4, 10), pady=(0, 10))
        self._action_card(actions, "Manager pamięci", "Zrzuty A/B, SHA-256, porównanie, zrzut WinPmem i pluginy Volatility 3.", self._open_memory_manager, self.colors["purple"])
        self._action_card(actions, "Status techniczny", "Pokaż pełne ścieżki i stan komponentów pamięci.", lambda: self._run(memory.dependency_status))

    def _page_system(self) -> None:
        actions = self._layout_with_output()
        self._detach_button(actions, "Narzędzia systemowe", self._build_tools_panel)
        self._action_card(actions, "Eksport rejestru Windows", "Otwórz pełne okno hive, gałęzi i raportów wieloformatowych.", self._open_registry_dialog)
        self._action_card(actions, "Eksport logów Windows", "Otwórz opcje zakresu, dzienników, EVTX i raportów.", self._open_windows_logs_dialog)
        self._action_card(actions, "Eksport dziennika Light", "Eksport dziennika operacji aplikacji do TXT/JSON.", lambda: self._run(journal.export_journal))
        self._action_card(actions, "Zrzut głównego okna", "Zapisz PNG tylko z głównego okna aplikacji.", lambda: self._run(lambda: {"png": str(capture.capture_window(self))}))

    def _build_reports_panel(self, parent, detached: bool = False) -> None:
        parent.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        parent.grid_rowconfigure(0, weight=1)
        self._action_card(frame, "Bieżący raport", "Jedno odświeżane okno wyników z zapisem bieżących danych do PDF.", self.show_report, self.colors["accent"])
        self._action_card(frame, "Raport nośników PDF", "Raport generowany przez moduł raportów Light.", self._media_report)
        self._action_card(frame, "Dane nośników JSON", "Eksport danych WinAPI w formacie JSON.", lambda: self._run(lambda: {"json": str(media.export_media_json())}))
        self._action_card(frame, "Eksport dziennika TXT/JSON", "Raport z dziennika operacji programu.", lambda: self._run(journal.export_journal))
        self._action_card(frame, "Eksport logów Windows", "Opcje, EVTX, XLSX, CSV, TXT, PDF i JSON.", self._open_windows_logs_dialog, self.colors["red"])

    def _page_raporty(self) -> None:
        assert self.content is not None
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)
        self._detach_button(self.content, "Raporty", self._build_reports_panel, use_grid=True)
        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        self._build_reports_panel(body)

    def _build_journal_panel(self, parent, detached: bool = False) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(parent, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(toolbar, text="Odśwież", command=lambda: render()).pack(side=tk.LEFT, padx=10, pady=10)
        ctk.CTkButton(toolbar, text="Eksport TXT/JSON", command=lambda: self._run(journal.export_journal)).pack(side=tk.LEFT, padx=(0, 10), pady=10)
        box = ctk.CTkTextbox(parent, font=(FONT_MONO, 10), wrap="word", fg_color=self.colors["soft"])
        box.grid(row=1, column=0, sticky="nsew")

        def render() -> None:
            events = journal.read_events()
            lines = []
            for event in events:
                lines.append(f"[{event['time']}] {event['level']} | {event['module']} | {event['message']}")
                if event.get("details"):
                    lines.append(json.dumps(event["details"], ensure_ascii=False))
            box.configure(state="normal")
            box.delete("1.0", "end")
            box.insert("1.0", "\n".join(lines) if lines else "Dziennik jest pusty.")
            box.configure(state="disabled")

        render()

    def _page_journal(self) -> None:
        assert self.content is not None
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)
        self._detach_button(self.content, "Dziennik operacji", self._build_journal_panel, use_grid=True)
        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        self._build_journal_panel(body)

    def _page_console(self) -> None:
        assert self.content is not None
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(self.content, fg_color=self.colors["card"], border_width=1, border_color=self.colors["border"], corner_radius=8)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        self.console_entry = ctk.CTkEntry(toolbar, placeholder_text="np. media list --json albo network scan --host 192.168.1.1 --ports 22,80,443", height=38, font=(FONT_MONO, 11))
        self.console_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.console_entry.bind("<Return>", lambda _event: self._run_console())
        ctk.CTkButton(toolbar, text="Wykonaj", width=112, command=self._run_console).grid(row=0, column=1, padx=(0, 12), pady=12)
        self.console_output = ctk.CTkTextbox(self.content, font=(FONT_MONO, 10), wrap="word", fg_color=self.colors["console_bg"], text_color=self.colors["console_text"])
        self.console_output.grid(row=1, column=0, sticky="nsew")
        self._console_write(
            "EvidLock Light Console\n"
            "Przykłady:\n"
            "  media list --json\n"
            "  media report\n"
            "  hash file C:\\\\plik.bin\n"
            "  copy compare --a C:\\\\A --b D:\\\\B\n"
            "  network scan --host 127.0.0.1 --ports 22,80,443\n"
            "  memory deps --json\n"
            "  system journal-export --json\n"
            "  system logs-export --json\n"
            "  system diagnostics --json\n"
        )

    def _page_about(self) -> None:
        assert self.content is not None
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        tabs = ctk.CTkTabview(
            self.content,
            fg_color=self.colors["card"],
            segmented_button_fg_color=self.colors["soft"],
            segmented_button_selected_color=self.colors["accent"],
            segmented_button_selected_hover_color=self.colors["accent_hover"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=8,
        )
        tabs.grid(row=0, column=0, sticky="nsew")
        tab_about = tabs.add("O programie")
        tab_features = tabs.add("Funkcje")
        tab_docs = tabs.add("Dokumentacja techniczna")
        tab_diag = tabs.add("Diagnostyka")
        self._fill_about_tab(tab_about)
        self._fill_features_tab(tab_features)
        self._fill_docs_tab(tab_docs)
        self._fill_diag_tab(tab_diag)

    def _tab_textbox(self, parent, row: int = 0) -> ctk.CTkTextbox:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        box = ctk.CTkTextbox(parent, font=(FONT, 11), wrap="word", fg_color=self.colors["soft"])
        box.grid(row=row, column=0, sticky="nsew", padx=14, pady=14)
        return box

    def _set_box_text(self, box: ctk.CTkTextbox, text: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _fill_about_tab(self, parent) -> None:
        box = self._tab_textbox(parent)
        admin = "TAK" if winapi.is_admin() else "NIE"
        text = (
            f"{APP_NAME}\n"
            f"Wersja: {APP_VERSION}\n"
            f"Tryb administratora: {admin}\n\n"
            "EvidLock Light to lżejsza, modułowa wersja robocza EvidLock.\n"
            "Nie prowadzi spraw, nie wymaga numeru sprawy i nie zawiera OCR.\n\n"
            "Zostają narzędzia codziennej pracy: nośniki WinAPI, SHA-256, archiwizacja, "
            "kopia 1:1, porównanie A/B, raporty PDF/JSON, rejestr Windows, logi Windows, "
            "network, pamięć RAM, read-only, zrzut głównego okna i tryb administratora.\n\n"
            "Konsola jest częścią programu i daje dostęp do tych samych modułów bez osobnego EXE CLI."
        )
        self._set_box_text(box, text)

    def _fill_features_tab(self, parent) -> None:
        features = [
            ("Nośniki", "WinAPI, lista woluminów, nośniki wirtualne, raport PDF i JSON."),
            ("Zabezpieczanie", "SHA-256, manifesty, weryfikacja, archiwizacja, kopia 1:1 i porównanie."),
            ("Network", "Skaner TCP, status TShark i miejsce na rozbudowany Network Analyzer."),
            ("Pamięć", "Kontrola WinPmem i Volatility 3 oraz punkt uruchamiania analiz."),
            ("System", "Eksport rejestru Windows, logi Windows, zrzut głównego okna."),
            ("Konsola", "Wbudowany interpreter komend programu, dostępny z menu."),
            ("Raporty", "PDF i JSON generowane przez moduły usługowe."),
            ("Tryb admina", "Uruchamianie z podwyższonymi uprawnieniami przez WinAPI."),
        ]
        box = self._tab_textbox(parent)
        self._set_box_text(box, "\n\n".join(f"{name}\n{body}" for name, body in features))

    def _fill_docs_tab(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 0))
        toolbar.grid_columnconfigure(0, weight=1)
        query = ctk.CTkEntry(toolbar, placeholder_text="Szukaj w dokumentacji technicznej", height=34)
        query.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        box = self._tab_textbox(parent, row=1)

        def render() -> None:
            entries = docs.search_docs(query.get())
            if not entries:
                self._set_box_text(box, "Brak wyników dla podanej frazy.")
                return
            text = "\n\n".join(f"{entry['title']}\n{entry['body']}" for entry in entries)
            self._set_box_text(box, text)

        ctk.CTkButton(toolbar, text="Szukaj", width=110, command=render).grid(row=0, column=1)
        query.bind("<Return>", lambda _event: render())
        render()

    def _fill_diag_tab(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        ctk.CTkButton(parent, text="Odśwież diagnostykę", width=170, command=lambda: render()).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 0))
        box = self._tab_textbox(parent, row=1)

        def render() -> None:
            data = self._diagnostics()
            lines = [
                f"Aplikacja: {data['app']}",
                f"Wersja: {data['version']}",
                f"Tryb administratora: {'TAK' if data['admin'] else 'NIE'}",
                f"Skórka: {data['skin']}",
                f"Drag and Drop: {'TAK' if data['drag_drop'] else 'NIE'}",
                f"Elementy w strefie roboczej: {data['dropped_items']}",
                f"Liczba nośników: {data['media_count']}",
                "",
                "WinPmem / Volatility 3:",
                json.dumps(data["memory_deps"], ensure_ascii=False, indent=2),
                "",
                "TShark:",
                json.dumps(data["tshark"], ensure_ascii=False, indent=2),
            ]
            self._set_box_text(box, "\n".join(lines))

        render()

    def _page_docs(self) -> None:
        actions = self._layout_with_output()
        search = ctk.CTkEntry(actions, placeholder_text="Szukaj w dokumentacji", height=36)
        search.pack(fill=tk.X, pady=(0, 8))
        ctk.CTkButton(actions, text="Szukaj", command=lambda: self._run(lambda: docs.search_docs(search.get()))).pack(fill=tk.X, pady=(0, 12))
        self._write(docs.search_docs())

    def _page_diagnostics(self) -> None:
        actions = self._layout_with_output()
        self._action_card(actions, "Odśwież diagnostykę", "Stan aplikacji, admina, nośników i zależności.", lambda: self._run(self._diagnostics))
        self._write(self._diagnostics())

    def _console_write(self, text: str) -> None:
        if self.console_output is None:
            return
        self.console_output.configure(state="normal")
        self.console_output.insert("end", text.rstrip() + "\n\n")
        self.console_output.see("end")
        self.console_output.configure(state="disabled")

    def _run_console(self) -> None:
        if self.console_entry is None:
            return
        command = self.console_entry.get().strip()
        if not command:
            return
        self.console_entry.delete(0, "end")
        self._console_write(f"> {command}")
        if command.lower() in {"help", "?", "--help", "-h"}:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                cli.build_parser().print_help()
            self._console_write(stdout.getvalue())
            return
        argv = self._normalize_console_argv(command)
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(argv)
            output = stdout.getvalue() + stderr.getvalue()
            self._console_write(output.strip() or f"OK ({code})")
            journal.log_event("OK", "Konsola", command, {"code": code})
        except SystemExit as exc:
            self._console_write(stdout.getvalue() + stderr.getvalue() + f"\nKod wyjścia: {exc.code}")
            journal.log_event("BŁĄD", "Konsola", command, {"code": exc.code})
        except Exception as exc:
            self._console_write(f"Błąd: {exc}")
            journal.log_event("BŁĄD", "Konsola", command, {"error": str(exc)})

    def _normalize_console_argv(self, command: str) -> list[str]:
        argv = shlex.split(command, posix=False)
        if argv and argv[0].lower() in {"evidlock-light", "evidlocklightcli", "python"}:
            argv = argv[1:]
        if "--json" in argv and argv[0] != "--json":
            argv = ["--json"] + [part for part in argv if part != "--json"]
        return argv

    def _hash_file(self) -> None:
        path = next((item for item in self.dropped_paths if Path(item).is_file()), "")
        path = path or filedialog.askopenfilename(parent=self)
        if path:
            self._run_progress(
                "Obliczanie SHA-256",
                lambda progress: self._hash_worker(path, progress),
            )

    def _hash_worker(self, path: str, progress) -> dict:
        progress(5, "Otwieranie pliku")
        value = hashing.sha256_file(
            path,
            callback=lambda done, total: progress(5 + 90 * done / total, f"Obliczanie SHA-256: {done} / {total} bajtów"),
        )
        progress(100, "SHA-256 obliczony")
        return {"path": path, "sha256": value}

    def _manifest(self) -> None:
        path = next((item for item in self.dropped_paths if Path(item).is_dir()), "")
        path = path or filedialog.askdirectory(parent=self)
        if not path:
            return
        output = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("JSON", "*.json")])
        if output:
            self._run_progress(
                "Tworzenie manifestu SHA-256",
                lambda progress: self._manifest_worker(path, output, progress),
            )

    def _manifest_worker(self, path: str, output: str, progress) -> dict:
        progress(5, "Skanowanie katalogu")
        result = hashing.save_manifest(
            path,
            output,
            callback=lambda index, total, file_path: progress(5 + 90 * index / total, f"SHA-256 {index}/{total}: {file_path.name}"),
        )
        progress(100, "Manifest zapisany")
        return {"manifest": str(result)}

    def _archive(self) -> None:
        source = self.dropped_paths[0] if self.dropped_paths else ""
        source = source or filedialog.askdirectory(parent=self, title="Wybierz katalog do archiwizacji")
        if not source:
            source = filedialog.askopenfilename(parent=self, title="Wybierz plik do archiwizacji")
        if not source:
            return
        output = filedialog.asksaveasfilename(parent=self, defaultextension=".zip", filetypes=[("Archiwum ZIP", "*.zip")])
        if output:
            self._run_progress("Archiwizacja ZIP", lambda progress: self._archive_worker(source, output, progress))

    def _archive_worker(self, source: str, output: str, progress) -> dict:
        progress(5, "Przygotowanie archiwum")
        result = archive.create_zip(source, output, callback=progress)
        progress(100, "Archiwum zapisane")
        return {"archive": str(result)}

    def _compare(self) -> None:
        self._open_copy_tool("compare")

    def _copy_1to1(self) -> None:
        self._open_copy_tool("copy")

    def _open_copy_tool(self, mode: str) -> None:
        source = self.dropped_paths[0] if self.dropped_paths else ""
        target = self.dropped_paths[1] if mode == "compare" and len(self.dropped_paths) > 1 else ""
        dialog = CopyCompareDialog(self, self.colors, initial_mode=mode, on_result=self._copy_result, initial_source=source, initial_target=target)
        self.detached_windows.append(dialog)

    def _copy_result(self, mode: str, result: dict) -> None:
        self._write(result, "Raport kopii 1:1" if mode == "copy" else "Raport porównania A/B")
        journal.log_event("OK", "Kopia" if mode == "copy" else "Porównanie", "Operacja zakończona", {"ok": result.get("ok")})

    def _media_report(self) -> None:
        self._run_progress(
            "Raport informacji o nośnikach",
            lambda progress: self._simple_progress_worker(progress, media.report_media, "Pobieranie danych nośników", "Generowanie PDF", "pdf"),
        )

    def _registry_export(self) -> None:
        self._run_progress(
            "Eksport rejestru Windows",
            lambda progress: self._simple_progress_worker(progress, registry.export_registry, "Przygotowanie eksportu", "Eksport gałęzi rejestru", None),
        )

    def _open_registry_dialog(self) -> None:
        if self.registry_dialog is not None and self.registry_dialog.winfo_exists():
            self.registry_dialog.lift()
            self.registry_dialog.focus_force()
            return
        self.registry_dialog = RegistryExportDialog(self, self.colors, on_result=lambda result: self._write(result, "Eksport rejestru Windows"))
        self.detached_windows.append(self.registry_dialog)

    def _windows_logs_export(self) -> None:
        self._run_progress(
            "Eksport logów Windows",
            lambda progress: self._simple_progress_worker(progress, windows_logs.export_logs, "Przygotowanie kanałów", "Eksport EVTX i TXT", None),
        )

    def _open_windows_logs_dialog(self) -> None:
        if self.windows_logs_dialog is not None and self.windows_logs_dialog.winfo_exists():
            self.windows_logs_dialog.lift()
            self.windows_logs_dialog.focus_force()
            return
        self.windows_logs_dialog = WindowsLogsDialog(self, self.colors, on_result=lambda result: self._write(result, "Eksport logów Windows"))
        self.detached_windows.append(self.windows_logs_dialog)

    def _open_readonly_dialog(self) -> None:
        if self.readonly_dialog is not None and self.readonly_dialog.winfo_exists():
            self.readonly_dialog.lift()
            self.readonly_dialog.focus_force()
            return
        initial = self.dropped_paths[0] if self.dropped_paths else ""
        self.readonly_dialog = ReadOnlyDialog(self, self.colors, initial_path=initial, on_result=lambda result: self._write(result, "Ochrona read-only"))
        self.detached_windows.append(self.readonly_dialog)

    def _open_memory_manager(self) -> None:
        if self.memory_manager_dialog is not None and self.memory_manager_dialog.winfo_exists():
            self.memory_manager_dialog.refresh_status()
            self.memory_manager_dialog.lift()
            self.memory_manager_dialog.focus_force()
            return
        self.memory_manager_dialog = MemoryManagerDialog(self, self.colors, on_result=lambda result: self._write(result, "Manager pamięci"))
        if self.dropped_paths:
            self.memory_manager_dialog.file_a.set(self.dropped_paths[0])
        if len(self.dropped_paths) > 1:
            self.memory_manager_dialog.file_b.set(self.dropped_paths[1])
        self.detached_windows.append(self.memory_manager_dialog)

    def _install_tshark(self) -> None:
        if messagebox.askyesno("Instalacja TShark", "Zostanie uruchomiona instalacja oficjalnego pakietu Wireshark przez winget. Kontynuować?", parent=self):
            self._run(network.install_tshark)

    def _install_volatility(self) -> None:
        if messagebox.askyesno("Instalacja Volatility 3", "Zostanie uruchomione polecenie pip install --user volatility3. Kontynuować?", parent=self):
            self._run(memory.install_volatility)

    def _simple_progress_worker(self, progress, func, start_text: str, work_text: str, result_key: str | None):
        progress(5, start_text)
        progress(25, work_text)
        result = func()
        progress(100, "Gotowe")
        if result_key:
            return {result_key: str(result)}
        return result

    def _admin(self) -> None:
        if winapi.is_admin():
            messagebox.showinfo(APP_NAME, "Aplikacja działa już jako administrator.")
            return
        try:
            from .single_instance import release_for_relaunch

            release_for_relaunch()
            winapi.relaunch_as_admin()
            self.destroy()
        except Exception as exc:
            from .single_instance import SingleInstance

            SingleInstance()
            messagebox.showerror(APP_NAME, str(exc))

    def _diagnostics(self) -> dict:
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "skin": themes.SKIN_LABELS[self.skin],
            "admin": winapi.is_admin(),
            "drag_drop": self.drag_drop_available,
            "dropped_items": len(self.dropped_paths),
            "media_count": len(media.list_media()),
            "memory_deps": memory.dependency_status(),
            "tshark": network.tshark_status(),
        }


def main() -> None:
    app = EvidLockLightApp()
    app.mainloop()
