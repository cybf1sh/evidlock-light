"""Pelne okno eksportu rejestru Windows w stylu EvidLockV2."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import winapi
from ..services import registry


class RegistryExportDialog(ctk.CTkToplevel):
    def __init__(self, parent, colors: dict[str, str], on_result=None) -> None:
        super().__init__(parent)
        self.colors=colors; self.on_result=on_result; self.result=None; self.running=False
        self.title("Eksport rejestru Windows"); self.geometry("980x760"); self.minsize(800,620); self.configure(fg_color=colors["bg"]); self.transient(parent)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(5,weight=1)
        header=ctk.CTkFrame(self,fg_color="transparent"); header.grid(row=0,column=0,sticky="ew",padx=18,pady=(16,8)); header.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(header,text="Eksport rejestru Windows",text_color=colors["text"],font=("Segoe UI",22,"bold"),anchor="w").grid(row=0,column=0,sticky="ew")
        ctk.CTkLabel(header,text="Hive .hiv oraz pełne dane fizycznych gałęzi do REG, CSV, XLSX, TXT, PDF i JSON z SHA-256.",text_color=colors["muted"],font=("Segoe UI",10),anchor="w").grid(row=1,column=0,sticky="ew",pady=(3,0))
        admin="TAK" if winapi.is_admin() else "NIE - część gałęzi może wymagać trybu administratora"
        ctk.CTkLabel(header,text=f"Tryb administratora: {admin}",text_color=colors["green"] if winapi.is_admin() else colors["red"],font=("Segoe UI",10,"bold")).grid(row=0,column=1,rowspan=2,padx=(12,0))

        mode=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8); mode.grid(row=1,column=0,sticky="ew",padx=18,pady=(0,10)); mode.grid_columnconfigure((0,1),weight=1)
        self.export_hives=tk.BooleanVar(value=True); self.export_data=tk.BooleanVar(value=True)
        ctk.CTkCheckBox(mode,text="Eksportuj hive .hiv",variable=self.export_hives,text_color=colors["text"],font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w",padx=14,pady=12)
        ctk.CTkCheckBox(mode,text="Eksportuj dane REG / CSV / XLSX / TXT",variable=self.export_data,text_color=colors["text"],font=("Segoe UI",10,"bold")).grid(row=0,column=1,sticky="w",padx=14,pady=12)

        choices=ctk.CTkFrame(self,fg_color="transparent"); choices.grid(row=2,column=0,sticky="ew",padx=18,pady=(0,10)); choices.grid_columnconfigure((0,1),weight=1)
        hive_box=ctk.CTkFrame(choices,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8); hive_box.grid(row=0,column=0,sticky="nsew",padx=(0,5))
        branch_box=ctk.CTkFrame(choices,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8); branch_box.grid(row=0,column=1,sticky="nsew",padx=(5,0))
        ctk.CTkLabel(hive_box,text="Hive",text_color=colors["text"],font=("Segoe UI",12,"bold"),anchor="w").pack(fill=tk.X,padx=12,pady=(10,5))
        self.hive_vars={}
        for definition in registry.HIVES:
            variable=tk.BooleanVar(value=True); self.hive_vars[definition["id"]]=variable
            row=ctk.CTkFrame(hive_box,fg_color=colors["soft"],corner_radius=6); row.pack(fill=tk.X,padx=8,pady=3)
            ctk.CTkCheckBox(row,text=definition["label"],variable=variable,text_color=colors["text"],font=("Segoe UI",10,"bold")).pack(anchor="w",padx=8,pady=(6,1))
            ctk.CTkLabel(row,text=definition["description"],text_color=colors["muted"],font=("Segoe UI",8),anchor="w").pack(fill=tk.X,padx=30,pady=(0,6))
        ctk.CTkLabel(branch_box,text="Pełne gałęzie danych",text_color=colors["text"],font=("Segoe UI",12,"bold"),anchor="w").pack(fill=tk.X,padx=12,pady=(10,5))
        self.branch_vars={}
        for branch_id,key in registry.FULL_BRANCHES:
            variable=tk.BooleanVar(value=True); self.branch_vars[branch_id]=variable
            ctk.CTkCheckBox(branch_box,text=key,variable=variable,text_color=colors["text"],font=("Segoe UI",9,"bold")).pack(anchor="w",padx=12,pady=5)

        destination=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8); destination.grid(row=3,column=0,sticky="ew",padx=18,pady=(0,10)); destination.grid_columnconfigure(1,weight=1)
        self.output_dir=tk.StringVar(value="")
        ctk.CTkLabel(destination,text="Katalog docelowy",text_color=colors["text"],font=("Segoe UI",10,"bold")).grid(row=0,column=0,padx=12,pady=10)
        ctk.CTkEntry(destination,textvariable=self.output_dir,placeholder_text="Automatyczny katalog eksport/Registry",height=32).grid(row=0,column=1,sticky="ew",pady=10)
        ctk.CTkButton(destination,text="Wybierz",width=90,command=self._choose_output).grid(row=0,column=2,padx=10)

        self.progress=ctk.CTkProgressBar(self,height=12,progress_color="#be123c"); self.progress.grid(row=4,column=0,sticky="ew",padx=18,pady=(0,8)); self.progress.set(0)
        self.log=ctk.CTkTextbox(self,fg_color=colors["card"],text_color=colors["text"],font=("Cascadia Mono",10),wrap="word",border_width=1,border_color=colors["border"]); self.log.grid(row=5,column=0,sticky="nsew",padx=18,pady=(0,10))
        footer=ctk.CTkFrame(self,fg_color="transparent"); footer.grid(row=6,column=0,sticky="ew",padx=18,pady=(0,14)); footer.grid_columnconfigure(0,weight=1)
        self.open_button=ctk.CTkButton(footer,text="Otwórz katalog",state="disabled",command=self._open,width=130); self.open_button.grid(row=0,column=0,sticky="w")
        ctk.CTkButton(footer,text="Zamknij",command=self.destroy,width=105,fg_color=colors["soft"],text_color=colors["text"],border_width=1,border_color=colors["border"]).grid(row=0,column=2,padx=(8,0))
        self.export_button=ctk.CTkButton(footer,text="Eksportuj",command=self._start,width=140,fg_color="#be123c"); self.export_button.grid(row=0,column=1)

    def _choose_output(self):
        path=filedialog.askdirectory(parent=self,title="Katalog eksportu rejestru")
        if path:self.output_dir.set(path)

    def _start(self):
        if self.running:return
        hives=[key for key,var in self.hive_vars.items() if var.get()]; branches=[key for key,var in self.branch_vars.items() if var.get()]
        if not self.export_hives.get() and not self.export_data.get(): messagebox.showwarning("Eksport rejestru","Wybierz przynajmniej jeden typ eksportu.",parent=self); return
        if self.export_hives.get() and not hives: messagebox.showwarning("Eksport rejestru","Wybierz przynajmniej jeden hive.",parent=self); return
        if self.export_data.get() and not branches: messagebox.showwarning("Eksport rejestru","Wybierz przynajmniej jedną gałąź danych.",parent=self); return
        self.running=True; self.result=None; self.log.delete("1.0","end"); self.progress.set(0); self.export_button.configure(state="disabled",text="Eksportowanie...")
        def worker():
            try:
                result=registry.export_registry(hives,branches,self.export_hives.get(),self.export_data.get(),self.output_dir.get() or None,self._report)
                self.after(0,lambda:self._finish(result))
            except Exception as exc:self.after(0,lambda error=exc:self._fail(error))
        threading.Thread(target=worker,daemon=True).start()

    def _report(self,percent,message):self.after(0,lambda:self._update(percent,message))
    def _update(self,percent,message):self.progress.set(max(0,min(100,percent))/100); self.log.insert("end",message+"\n"); self.log.see("end")
    def _finish(self,result):
        self.running=False; self.result=result; self.progress.set(1); self.log.insert("end",f"\nGotowe. Rekordy: {result.get('record_count')}\n{result.get('output_dir')}"); self.export_button.configure(state="normal",text="Eksportuj"); self.open_button.configure(state="normal")
        if self.on_result:self.on_result(result)
    def _fail(self,error):self.running=False; self.progress.configure(progress_color=self.colors["red"]); self.log.insert("end",f"\nBŁĄD: {error}"); self.export_button.configure(state="normal",text="Eksportuj")
    def _open(self):
        if self.result and self.result.get("output_dir"):os.startfile(self.result["output_dir"])
