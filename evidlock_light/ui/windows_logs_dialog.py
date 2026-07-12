"""Okno opcji i postepu eksportu logow Windows zgodne z workflow V2."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import reports, winapi
from ..services import windows_logs
from .windowing import ManagedToplevel


class WindowsLogsDialog(ManagedToplevel):
    def __init__(self,parent,colors:dict[str,str],on_result=None)->None:
        super().__init__(parent); self.colors=colors; self.on_result=on_result; self.result=None; self.running=False; self.per_log={}
        self.title("Eksport logów systemowych Windows"); self.geometry("940x780"); self.minsize(790,650); self.configure(fg_color=colors["bg"]); self.transient(parent)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(6,weight=1)
        header=ctk.CTkFrame(self,fg_color="transparent"); header.grid(row=0,column=0,sticky="ew",padx=18,pady=(16,8)); header.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(header,text="Eksport logów systemowych Windows",text_color=colors["text"],font=("Segoe UI",21,"bold"),anchor="w").grid(row=0,column=0,sticky="ew")
        ctk.CTkLabel(header,text="Zakres czasu, limit, sortowanie, wybrane dzienniki, EVTX i raporty z SHA-256.",text_color=colors["muted"],font=("Segoe UI",10),anchor="w").grid(row=1,column=0,sticky="ew")
        ctk.CTkLabel(header,text=f"Administrator: {'TAK' if winapi.is_admin() else 'NIE'}",text_color=colors["green"] if winapi.is_admin() else colors["red"],font=("Segoe UI",10,"bold")).grid(row=0,column=1,rowspan=2)

        options=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8); options.grid(row=1,column=0,sticky="ew",padx=18,pady=(0,10)); options.grid_columnconfigure((0,1),weight=1)
        self.mode=tk.StringVar(value="full"); self.range=tk.StringVar(value="7d"); self.limit=tk.StringVar(value="5000"); self.sort=tk.StringVar(value="time_desc"); self.start=tk.StringVar(); self.end=tk.StringVar()
        mode_box=self._section(options,"Tryb eksportu",0,0)
        ctk.CTkRadioButton(mode_box,text="Szybki - XLSX, CSV, TXT, PDF i JSON",variable=self.mode,value="quick",text_color=colors["text"]).pack(anchor="w",padx=12,pady=4)
        ctk.CTkRadioButton(mode_box,text="Pełny - dodatkowo oryginalne EVTX, SHA-256 i read-only",variable=self.mode,value="full",text_color=colors["text"]).pack(anchor="w",padx=12,pady=(4,12))
        limit_box=self._section(options,"Limit i sortowanie",0,1)
        row=ctk.CTkFrame(limit_box,fg_color="transparent"); row.pack(fill=tk.X,padx=12,pady=(2,8)); ctk.CTkLabel(row,text="Limit na dziennik",text_color=colors["text"]).pack(side=tk.LEFT); ctk.CTkEntry(row,textvariable=self.limit,width=110).pack(side=tk.RIGHT)
        ctk.CTkOptionMenu(limit_box,variable=self.sort,values=["time_desc","time_asc","id"],fg_color=colors["soft"],button_color=colors["accent"],text_color=colors["text"]).pack(fill=tk.X,padx=12,pady=(0,12))

        range_box=self._section(options,"Zakres czasu",1,0,2)
        range_grid=ctk.CTkFrame(range_box,fg_color="transparent"); range_grid.pack(fill=tk.X,padx=12,pady=(0,6))
        for index,(label,value) in enumerate((("24 godziny","24h"),("7 dni","7d"),("30 dni","30d"),("Cały zakres","all"),("Własny","custom"))):
            ctk.CTkRadioButton(range_grid,text=label,variable=self.range,value=value,command=self._range_state,text_color=colors["text"]).grid(row=0,column=index,sticky="w",padx=(0,18),pady=4)
        dates=ctk.CTkFrame(range_box,fg_color="transparent"); dates.pack(fill=tk.X,padx=12,pady=(2,12)); dates.grid_columnconfigure((1,3),weight=1)
        ctk.CTkLabel(dates,text="Od",text_color=colors["text"]).grid(row=0,column=0,padx=(0,6)); self.start_entry=ctk.CTkEntry(dates,textvariable=self.start,placeholder_text="RRRR-MM-DD HH:MM"); self.start_entry.grid(row=0,column=1,sticky="ew",padx=(0,16))
        ctk.CTkLabel(dates,text="Do",text_color=colors["text"]).grid(row=0,column=2,padx=(0,6)); self.end_entry=ctk.CTkEntry(dates,textvariable=self.end,placeholder_text="RRRR-MM-DD HH:MM"); self.end_entry.grid(row=0,column=3,sticky="ew")

        logs_box=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8); logs_box.grid(row=2,column=0,sticky="ew",padx=18,pady=(0,10)); logs_box.grid_columnconfigure((0,1),weight=1)
        self.log_vars={}
        for index,(label,channel) in enumerate(windows_logs.DEFAULT_LOGS):
            variable=tk.BooleanVar(value=True); self.log_vars[label]=variable
            item=ctk.CTkFrame(logs_box,fg_color=colors["soft"],corner_radius=6); item.grid(row=index//2,column=index%2,sticky="ew",padx=8,pady=6); item.grid_columnconfigure(0,weight=1)
            ctk.CTkCheckBox(item,text=f"{label} ({channel})",variable=variable,text_color=colors["text"],font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w",padx=8,pady=(7,3))
            bar=ctk.CTkProgressBar(item,height=6,progress_color=colors["accent"]); bar.grid(row=1,column=0,sticky="ew",padx=8,pady=(0,7)); bar.set(0); self.per_log[label]=bar

        destination=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8); destination.grid(row=3,column=0,sticky="ew",padx=18,pady=(0,10)); destination.grid_columnconfigure(1,weight=1); self.output_dir=tk.StringVar()
        ctk.CTkLabel(destination,text="Katalog docelowy",text_color=colors["text"],font=("Segoe UI",10,"bold")).grid(row=0,column=0,padx=12,pady=10); ctk.CTkEntry(destination,textvariable=self.output_dir,placeholder_text="Automatyczny katalog eksport/WindowsLogs").grid(row=0,column=1,sticky="ew"); ctk.CTkButton(destination,text="Wybierz",width=90,command=self._choose_output).grid(row=0,column=2,padx=10)
        self.progress=ctk.CTkProgressBar(self,height=12,progress_color=colors["accent"]); self.progress.grid(row=4,column=0,sticky="ew",padx=18,pady=(0,6)); self.progress.set(0)
        self.status=ctk.CTkLabel(self,text="Gotowe do eksportu.",text_color=colors["muted"],font=("Segoe UI",9,"bold"),anchor="w"); self.status.grid(row=5,column=0,sticky="ew",padx=18,pady=(0,6))
        self.log=ctk.CTkTextbox(self,fg_color=colors["card"],text_color=colors["text"],font=("Cascadia Mono",10),border_width=1,border_color=colors["border"]); self.log.grid(row=6,column=0,sticky="nsew",padx=18,pady=(0,10))
        footer=ctk.CTkFrame(self,fg_color="transparent"); footer.grid(row=7,column=0,sticky="ew",padx=18,pady=(0,14)); footer.grid_columnconfigure(0,weight=1)
        self.open_button=ctk.CTkButton(footer,text="Otwórz katalog",state="disabled",command=self._open,width=130); self.open_button.grid(row=0,column=0,sticky="w")
        self.browse_pdf=ctk.CTkButton(footer,text="Przeglądaj PDF",state="disabled",command=self._browse_pdf,width=125); self.browse_pdf.grid(row=0,column=1,padx=(8,0))
        self.export_button=ctk.CTkButton(footer,text="Rozpocznij eksport",command=self._start,width=170); self.export_button.grid(row=0,column=2,padx=(8,0))
        ctk.CTkButton(footer,text="Zamknij",command=self.destroy,width=105,fg_color=colors["soft"],text_color=colors["text"],border_width=1,border_color=colors["border"]).grid(row=0,column=3,padx=(8,0))
        self._range_state()

    def _section(self,parent,title,row,column,columnspan=1):
        box=ctk.CTkFrame(parent,fg_color=self.colors["soft"],corner_radius=6); box.grid(row=row,column=column,columnspan=columnspan,sticky="nsew",padx=6,pady=6); ctk.CTkLabel(box,text=title,text_color=self.colors["text"],font=("Segoe UI",11,"bold"),anchor="w").pack(fill=tk.X,padx=12,pady=(10,5)); return box
    def _range_state(self):
        state="normal" if self.range.get()=="custom" else "disabled"; self.start_entry.configure(state=state); self.end_entry.configure(state=state)
    def _choose_output(self):
        path=filedialog.askdirectory(parent=self,title="Katalog eksportu logów"); self.output_dir.set(path or self.output_dir.get())
    def _collect_options(self):
        logs=[item for item in windows_logs.DEFAULT_LOGS if self.log_vars[item[0]].get()]
        if not logs:raise ValueError("Wybierz przynajmniej jeden dziennik.")
        limit=int(self.limit.get());
        if limit<1:raise ValueError("Limit musi być większy od zera.")
        return {"mode":self.mode.get(),"range":self.range.get(),"start":self.start.get(),"end":self.end.get(),"limit":limit,"sort":self.sort.get(),"logs":logs}
    def _start(self):
        if self.running:return
        try:options=self._collect_options()
        except Exception as exc:messagebox.showwarning("Opcje logów",str(exc),parent=self);return
        self.running=True;self.result=None;self.browse_pdf.configure(state="disabled");self.log.delete("1.0","end");self.progress.set(0);self.export_button.configure(state="disabled",text="Eksportowanie...")
        for bar in self.per_log.values():bar.set(0)
        def worker():
            try:
                result=windows_logs.export_logs(options,self.output_dir.get() or None,self._report);self.after(0,lambda:self._finish(result))
            except Exception as exc:self.after(0,lambda error=exc:self._fail(error))
        threading.Thread(target=worker,daemon=True).start()
    def _report(self,percent,message,label=None,log_percent=None):self.after(0,lambda:self._update(percent,message,label,log_percent))
    def _update(self,percent,message,label,log_percent):
        self.progress.set(max(0,min(100,percent))/100);self.status.configure(text=f"{int(percent)}% | {message}");self.log.insert("end",message+"\n");self.log.see("end")
        if label in self.per_log:self.per_log[label].set(max(0,min(100,log_percent or 0))/100)
    def _finish(self,result):
        self.running=False;self.result=result;self.progress.set(1);self.status.configure(text=f"Gotowe. Rekordy: {result.get('event_count')}");self.log.insert("end",f"\nKatalog: {result.get('output_dir')}");self.export_button.configure(state="normal",text="Rozpocznij eksport");self.open_button.configure(state="normal");self.browse_pdf.configure(state="normal" if reports.find_pdf(result) else "disabled")
        if self.on_result:self.on_result(result)
    def _fail(self,error):self.running=False;self.progress.configure(progress_color=self.colors["red"]);self.status.configure(text=f"Błąd: {error}");self.log.insert("end",f"\nBŁĄD: {error}");self.export_button.configure(state="normal",text="Rozpocznij eksport")
    def _open(self):
        if self.result and self.result.get("output_dir"):winapi.open_path(self.result["output_dir"])
    def _browse_pdf(self):
        pdf=reports.find_pdf(self.result)
        if pdf:
            try:reports.open_pdf(pdf)
            except Exception as exc:messagebox.showerror("Przeglądaj PDF",str(exc),parent=self)
