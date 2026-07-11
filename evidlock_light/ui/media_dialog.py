"""Okno informacji o nosnikach z lekkimi ikonami zgodnymi z EvidLockV2."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from ..services import media


class MediaDialog(ctk.CTkToplevel):
    def __init__(self, parent, colors: dict[str, str], on_result=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.on_result = on_result
        self.report_host = parent
        self.icon_images: list[ctk.CTkImage] = []
        self.items = media.list_media()
        self.selected: dict[str, tk.BooleanVar] = {}
        self.title("Informacje o nośnikach")
        self.geometry("1040x720")
        self.minsize(820, 560)
        self.configure(fg_color=colors["bg"])
        self.transient(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="Informacje o nośnikach", text_color=colors["text"], font=("Segoe UI", 22, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))
        ctk.CTkLabel(self, text="Wybierz dyski do zbiorczego raportu PDF. Ikona i kolor pokazują rzeczywisty typ urządzenia.", text_color=colors["muted"], font=("Segoe UI", 10), anchor="w").grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        toolbar = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        toolbar.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(toolbar, text="", text_color=colors["text"], font=("Segoe UI", 10, "bold"), anchor="w")
        self.status.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
        ctk.CTkButton(toolbar, text="Odśwież", width=90, command=self.refresh).grid(row=0, column=1, padx=4)
        ctk.CTkButton(toolbar, text="Zaznacz wszystko", width=140, command=self._toggle_all, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=2, padx=(4, 10))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self.progress = ctk.CTkProgressBar(self, height=10, progress_color=colors["accent"])
        self.progress.grid(row=4, column=0, sticky="ew", padx=18)
        self.progress.set(0)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=18, pady=14)
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(footer, text="Zamknij", width=105, command=self.destroy, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=2, padx=(8, 0))
        ctk.CTkButton(footer, text="Podgląd", width=105, command=self._preview).grid(row=0, column=1, padx=(8, 0))
        self.generate = ctk.CTkButton(footer, text="Generuj raport", width=150, command=self._generate)
        self.generate.grid(row=0, column=0, sticky="e")
        self._render()

    def _variant(self, item: dict) -> tuple[str, str, str]:
        drive_type = int(item.get("drive_type") or 0)
        if drive_type == 2:
            return "usb", "Pendrive / USB", "#7c3aed"
        if drive_type == 5:
            return "optical", "Napęd optyczny", "#d97706"
        if drive_type == 4:
            return "network", "Dysk sieciowy", "#0891b2"
        if drive_type == 6:
            return "memory", "Dysk RAM", "#db2777"
        return "disk", "Dysk lokalny" if drive_type == 3 else item.get("drive_type_name", "Nieznany"), "#2563eb" if drive_type == 3 else "#64748b"

    def _draw_icon(self, parent, variant: str, color: str) -> None:
        bg = self.colors["soft"]
        asset_name = "disk" if variant == "memory" else variant
        asset_path = Path(__file__).resolve().parents[1] / "assets" / "media_icons" / f"{asset_name}.png"
        try:
            image = Image.open(asset_path).convert("RGBA")
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(58, 58))
            self.icon_images.append(ctk_image)
            label = ctk.CTkLabel(parent, text="", image=ctk_image, fg_color="transparent")
            label.place(relx=.5, rely=.5, anchor="center")
            return
        except (OSError, ValueError):
            pass
        canvas = tk.Canvas(parent, width=58, height=58, bg=bg, highlightthickness=0, bd=0)
        canvas.place(relx=.5, rely=.5, anchor="center")
        if variant == "usb":
            canvas.create_polygon(19,20,39,20,40,22,40,42,37,46,21,46,18,42,18,22,fill=bg,outline=color,width=2,smooth=True)
            canvas.create_rectangle(23,11,35,21,fill=bg,outline=color,width=2)
            canvas.create_rectangle(25,13,28,18,fill=color,outline="")
            canvas.create_rectangle(31,13,34,18,fill=color,outline="")
        elif variant == "optical":
            canvas.create_oval(10,10,48,48,fill=bg,outline=color,width=2)
            canvas.create_oval(22,22,36,36,fill=bg,outline=color,width=2)
            canvas.create_arc(15,15,43,43,start=30,extent=75,style="arc",outline=color,width=2)
        elif variant == "network":
            canvas.create_rectangle(11,14,47,39,fill=bg,outline=color,width=2)
            canvas.create_line(29,39,29,47,fill=color,width=2)
            canvas.create_line(18,47,40,47,fill=color,width=2)
            for x in (18,29,40): canvas.create_oval(x-3,24,x+3,30,fill=color,outline="#ffffff")
        elif variant == "memory":
            canvas.create_rectangle(13,19,45,39,fill=bg,outline=color,width=2)
            for x in (19,25,31,37):
                canvas.create_line(x,15,x,19,fill=color,width=2); canvas.create_line(x,39,x,43,fill=color,width=2)
            canvas.create_rectangle(19,24,39,34,fill=bg,outline=color,width=2)
        else:
            canvas.create_polygon(13,15,45,15,49,34,47,42,43,45,15,45,11,42,9,34,fill=bg,outline=color,width=2,smooth=True)
            canvas.create_line(10,34,48,34,fill=color,width=2)
            canvas.create_line(16,39,28,39,fill=color,width=2)
            canvas.create_oval(40,37,44,41,fill=bg,outline=color,width=2)

    def _render(self) -> None:
        for child in self.list_frame.winfo_children(): child.destroy()
        self.icon_images.clear()
        previous = {key: value.get() for key, value in self.selected.items()}
        self.selected = {}
        for item in self.items:
            letter = item["letter"]
            variable = tk.BooleanVar(value=previous.get(letter, False))
            self.selected[letter] = variable
            row = ctk.CTkFrame(self.list_frame, fg_color=self.colors["soft"], border_width=1, border_color=self.colors["border"], corner_radius=8)
            row.pack(fill=tk.X, padx=2, pady=5)
            row.grid_columnconfigure(2, weight=1)
            ctk.CTkCheckBox(row, text="", variable=variable, command=self._update_status, width=24).grid(row=0, column=0, rowspan=3, padx=(12,8), pady=16, sticky="nw")
            variant, type_name, color = self._variant(item)
            icon = ctk.CTkFrame(row, width=58, height=58, fg_color=self.colors["soft"], corner_radius=0)
            icon.grid(row=0, column=1, rowspan=3, padx=(0,12), pady=12); icon.grid_propagate(False)
            self._draw_icon(icon, variant, color)
            ctk.CTkLabel(row, text=f"{letter}\\  {item.get('label') or 'Brak etykiety'}", text_color=self.colors["text"], font=("Segoe UI",13,"bold"), anchor="w").grid(row=0,column=2,sticky="ew",pady=(10,0))
            description = f"{type_name}   |   {item.get('file_system')}   |   Zajęte: {media.format_bytes(item.get('used'))} z {media.format_bytes(item.get('size'))}   |   Wolne: {media.format_bytes(item.get('free'))}"
            ctk.CTkLabel(row,text=description,text_color=self.colors["muted"],font=("Segoe UI",9),anchor="w").grid(row=1,column=2,sticky="ew",pady=(1,4))
            bar=ctk.CTkProgressBar(row,height=8,fg_color=self.colors["border"],progress_color=color); bar.grid(row=2,column=2,sticky="ew",padx=(0,54),pady=(0,12)); bar.set(float(item.get("used_percent") or 0)/100)
            ctk.CTkLabel(row,text=f"{float(item.get('used_percent') or 0):.0f}%",text_color=self.colors["muted"],font=("Segoe UI",9,"bold"),width=42).grid(row=2,column=2,sticky="e",padx=(0,8),pady=(0,12))
        self._update_status()

    def _update_status(self) -> None:
        count=sum(variable.get() for variable in self.selected.values())
        self.status.configure(text=f"Zaznaczone nośniki: {count} / {len(self.selected)}")
        self.generate.configure(state="normal" if count else "disabled")

    def _toggle_all(self) -> None:
        value=not all(variable.get() for variable in self.selected.values())
        for variable in self.selected.values(): variable.set(value)
        self._update_status()

    def refresh(self) -> None:
        self.items=media.list_media(); self._render()

    def _selected_letters(self) -> list[str]:
        return [letter for letter, variable in self.selected.items() if variable.get()]

    def _generate(self) -> None:
        letters=self._selected_letters()
        if not letters: return
        self.generate.configure(state="disabled",text="Generowanie..."); self.progress.set(.05)
        def worker():
            try:
                result=media.report_media(letters=letters)
                self.after(0,lambda:self._finish(str(result)))
            except Exception as exc:
                self.after(0,lambda error=exc:self._fail(error))
        threading.Thread(target=worker,daemon=True).start()

    def _finish(self,path:str)->None:
        self.progress.set(1); self.status.configure(text=f"Raport gotowy: {path}"); self.generate.configure(state="normal",text="Generuj raport")
        if self.on_result: self.on_result({"pdf":path})

    def _fail(self,exc:Exception)->None:
        self.progress.configure(progress_color=self.colors["red"]); self.status.configure(text=f"Błąd: {exc}"); self.generate.configure(state="normal",text="Generuj raport")

    def _preview(self)->None:
        letters=self._selected_letters()
        if not letters: return
        selected=[item for item in self.items if item["letter"] in letters]
        title="Informacje o nośniku" if len(selected)==1 else "Informacje o nośnikach"
        if hasattr(self.report_host,"show_report"):
            self.report_host.show_report(title, {"nośniki": selected})
