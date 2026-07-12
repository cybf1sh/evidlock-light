"""Okno kompletnego zabezpieczenia danych One-click."""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import reports, winapi
from ..services import one_click
from .windowing import ManagedToplevel


class OneClickDialog(ManagedToplevel):
    def __init__(self,parent,colors:dict[str,str],initial_sources=None,on_result=None)->None:
        super().__init__(parent);self.colors=colors;self.on_result=on_result;self.sources=[];self.result=None;self.running=False
        self.title("One-click - zabezpiecz dane");self.geometry("860x720");self.minsize(720,620);self.configure(fg_color=colors["bg"]);self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(4,weight=1)
        ctk.CTkLabel(self,text="One-click",text_color=colors["text"],font=("Segoe UI",24,"bold"),anchor="w").grid(row=0,column=0,sticky="ew",padx=18,pady=(16,2))
        ctk.CTkLabel(self,text="Read-only, SHA-256 każdego pliku, profesjonalny raport PDF i szyfrowane archiwum w jednym przebiegu.",text_color=colors["muted"],font=("Segoe UI",10),anchor="w",wraplength=800).grid(row=1,column=0,sticky="ew",padx=18,pady=(0,10))
        source=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8);source.grid(row=2,column=0,sticky="ew",padx=18,pady=(0,10));source.grid_columnconfigure(0,weight=1)
        actions=ctk.CTkFrame(source,fg_color="transparent");actions.grid(row=0,column=0,sticky="ew",padx=10,pady=(10,5))
        ctk.CTkLabel(actions,text="Krok 1 - wybierz dane",text_color=colors["text"],font=("Segoe UI",11,"bold")).pack(side=tk.LEFT,padx=(3,12))
        ctk.CTkButton(actions,text="Dodaj pliki",width=100,command=self._files).pack(side=tk.LEFT,padx=3);ctk.CTkButton(actions,text="Dodaj katalog",width=110,command=self._directory).pack(side=tk.LEFT,padx=3);ctk.CTkButton(actions,text="Wyczyść",width=85,command=self._clear,fg_color=colors["soft"],text_color=colors["text"],border_width=1,border_color=colors["border"]).pack(side=tk.LEFT,padx=3)
        ctk.CTkButton(actions,text="Następne",width=95,command=self._next).pack(side=tk.RIGHT,padx=3)
        self.source_view=ctk.CTkTextbox(source,height=105,fg_color=colors["soft"],text_color=colors["text"],font=("Cascadia Mono",9));self.source_view.grid(row=1,column=0,sticky="ew",padx=12,pady=(0,10))
        options=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8);options.grid(row=3,column=0,sticky="ew",padx=18,pady=(0,10));options.grid_columnconfigure((0,1),weight=1)
        self.format=tk.StringVar(value="zip");self.password=tk.StringVar();self.repeat=tk.StringVar();self.show=tk.BooleanVar()
        ctk.CTkLabel(options,text="Krok 2 - wybierz format i podaj hasło",text_color=colors["text"],font=("Segoe UI",11,"bold"),anchor="w").grid(row=0,column=0,columnspan=2,sticky="ew",padx=12,pady=(10,4))
        ctk.CTkRadioButton(options,text="ZIP AES-256",variable=self.format,value="zip",text_color=colors["text"]).grid(row=1,column=0,sticky="w",padx=12,pady=(2,6));ctk.CTkRadioButton(options,text="7z AES-256",variable=self.format,value="7z",text_color=colors["text"]).grid(row=1,column=1,sticky="w",padx=12,pady=(2,6))
        ctk.CTkLabel(options,text="Hasło - minimum 8 znaków",text_color=colors["text"],font=("Segoe UI",9,"bold")).grid(row=2,column=0,sticky="w",padx=12)
        ctk.CTkLabel(options,text="Powtórz hasło",text_color=colors["text"],font=("Segoe UI",9,"bold")).grid(row=2,column=1,sticky="w",padx=12)
        self.password_entry=ctk.CTkEntry(options,textvariable=self.password,show="*");self.password_entry.grid(row=3,column=0,sticky="ew",padx=12,pady=(3,6));self.repeat_entry=ctk.CTkEntry(options,textvariable=self.repeat,show="*");self.repeat_entry.grid(row=3,column=1,sticky="ew",padx=12,pady=(3,6))
        ctk.CTkCheckBox(options,text="Pokaż hasło",variable=self.show,command=self._toggle,text_color=colors["text"]).grid(row=4,column=0,columnspan=2,sticky="w",padx=12,pady=(0,10))
        work=ctk.CTkFrame(self,fg_color="transparent");work.grid(row=4,column=0,sticky="nsew",padx=18);work.grid_columnconfigure(0,weight=1);work.grid_rowconfigure(2,weight=1)
        self.progress=ctk.CTkProgressBar(work,height=12,progress_color=colors["accent"]);self.progress.grid(row=0,column=0,sticky="ew");self.progress.set(0)
        self.status=ctk.CTkLabel(work,text="Wybierz dane i uruchom zabezpieczenie.",text_color=colors["muted"],font=("Segoe UI",9,"bold"),anchor="w");self.status.grid(row=1,column=0,sticky="ew",pady=5)
        self.log=ctk.CTkTextbox(work,fg_color=colors["card"],text_color=colors["text"],font=("Cascadia Mono",9));self.log.grid(row=2,column=0,sticky="nsew")
        footer=ctk.CTkFrame(self,fg_color="transparent");footer.grid(row=5,column=0,sticky="ew",padx=18,pady=14);footer.grid_columnconfigure(0,weight=1)
        self.folder_button=ctk.CTkButton(footer,text="Otwórz",state="disabled",command=self._open,width=95);self.folder_button.grid(row=0,column=0,sticky="w")
        self.pdf_button=ctk.CTkButton(footer,text="Przeglądaj PDF",state="disabled",command=self._pdf,width=125);self.pdf_button.grid(row=0,column=1,padx=8)
        self.start_button=ctk.CTkButton(footer,text="Zabezpiecz One-click",command=self._start,width=165,fg_color=colors["green"]);self.start_button.grid(row=0,column=2,padx=8)
        ctk.CTkButton(footer,text="Zamknij",command=self.destroy,width=95,fg_color=colors["soft"],text_color=colors["text"],border_width=1,border_color=colors["border"]).grid(row=0,column=3)
        self._add(initial_sources or [])

    def _add(self,paths):
        existing={os.path.normcase(str(Path(path).resolve())) for path in self.sources}
        for path in paths:
            value=str(Path(path).resolve());key=os.path.normcase(value)
            if Path(value).exists() and key not in existing:self.sources.append(value);existing.add(key)
        self.source_view.delete("1.0","end");self.source_view.insert("1.0","\n".join(self.sources) or "Brak wybranych danych.")
    def _files(self):self._add(filedialog.askopenfilenames(parent=self))
    def _directory(self):
        path=filedialog.askdirectory(parent=self)
        if path:self._add([path])
    def _clear(self):self.sources.clear();self._add([])
    def _next(self):
        if not self.sources:messagebox.showwarning("One-click","Najpierw dodaj pliki lub katalogi.",parent=self);return
        self.password_entry.focus_set();self.status.configure(text="Krok 2 - wybierz format i podaj hasło minimum 8 znaków.")
    def _toggle(self):
        show="" if self.show.get() else "*";self.password_entry.configure(show=show);self.repeat_entry.configure(show=show)
    def _start(self):
        if self.running:return
        if not self.sources:messagebox.showwarning("One-click","Dodaj pliki lub katalogi.",parent=self);return
        if len(self.password.get())<8:messagebox.showwarning("Hasło","Hasło musi mieć minimum 8 znaków.",parent=self);return
        if self.password.get()!=self.repeat.get():messagebox.showwarning("Hasło","Podane hasła nie są identyczne.",parent=self);return
        self.running=True;self.result=None;self.start_button.configure(state="disabled",text="Zabezpieczanie...");self.progress.set(0);self.log.delete("1.0","end")
        def callback(value,text):self.after(0,lambda:self._update(value,text))
        def worker():
            try:result=one_click.secure(self.sources,self.password.get(),self.format.get(),callback);self.after(0,lambda:self._finish(result))
            except Exception as exc:self.after(0,lambda error=exc:self._finish({"error":str(error)}))
        threading.Thread(target=worker,daemon=True).start()
    def _update(self,value,text):self.progress.set(max(0,min(100,value))/100);self.status.configure(text=f"{int(value)}% - {text}");self.log.insert("end",text+"\n");self.log.see("end")
    def _finish(self,result):
        self.running=False;self.result=result;self.start_button.configure(state="normal",text="Zabezpiecz One-click");self.log.insert("end","\n"+json.dumps(result,ensure_ascii=False,indent=2))
        if "error" in result:self.status.configure(text=f"Błąd: {result['error']}");return
        self.progress.set(1);self.status.configure(text="100% - zakończono. Dane znajdują się w katalogu wynikowym.");self.folder_button.configure(state="normal");self.pdf_button.configure(state="normal")
        if self.on_result:self.on_result(result)
    def _open(self):
        if self.result:winapi.open_path(self.result["output_dir"])
    def _pdf(self):
        pdf=reports.find_pdf(self.result)
        if pdf:reports.open_pdf(pdf)
