"""Podgląd i eksport pełnego raportu systemowego."""
from __future__ import annotations
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from .. import reports, winapi
from ..services import system_report
from .windowing import ManagedToplevel, present_toplevel

class SystemReportDialog(ManagedToplevel):
    def __init__(self,parent,colors,on_result=None,on_close=None):
        super().__init__(parent)
        self.colors=colors; self.on_result=on_result; self.on_close=on_close
        self.sections=[]; self.current_text=""; self.pdf_path=None; self.txt_path=None
        self.font_size=10; self.running=False
        self.title("Pełny raport systemowy"); self.geometry("1040x740"); self.minsize(760,540)
        self.configure(fg_color=colors["bg"]); self.transient(parent)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(3,weight=1)
        ctk.CTkLabel(self,text="Pełny raport systemowy",text_color=colors["text"],font=("Segoe UI",22,"bold"),anchor="w").grid(row=0,column=0,sticky="ew",padx=18,pady=(16,2))
        ctk.CTkLabel(self,text="Przeglądaj dane przed zapisem. Generuj tworzy jednocześnie raport PDF i TXT.",text_color=colors["muted"],font=("Segoe UI",10),anchor="w").grid(row=1,column=0,sticky="ew",padx=18,pady=(0,10))
        bar=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8)
        bar.grid(row=2,column=0,sticky="ew",padx=18,pady=(0,10)); bar.grid_columnconfigure(0,weight=1)
        self.status=ctk.CTkLabel(bar,text="Przygotowanie podglądu...",text_color=colors["text"],font=("Segoe UI",10,"bold"),anchor="w")
        self.status.grid(row=0,column=0,sticky="ew",padx=12,pady=(9,3))
        self.progress=ctk.CTkProgressBar(bar,height=9,progress_color=colors["accent"]); self.progress.grid(row=1,column=0,sticky="ew",padx=12,pady=(0,10)); self.progress.set(0)
        self.content=ctk.CTkTextbox(self,fg_color=colors["card"],text_color=colors["text"],border_width=1,border_color=colors["border"],font=("Cascadia Mono",self.font_size),wrap="word")
        self.content.grid(row=3,column=0,sticky="nsew",padx=18,pady=(0,10)); self.content.insert("1.0","Pobieranie danych systemowych..."); self.content.configure(state="disabled")
        footer=ctk.CTkFrame(self,fg_color="transparent"); footer.grid(row=4,column=0,sticky="ew",padx=18,pady=(0,14)); footer.grid_columnconfigure(0,weight=1)
        neutral={"fg_color":colors["soft"],"text_color":colors["text"],"border_width":1,"border_color":colors["border"]}
        self.generate=ctk.CTkButton(footer,text="Generuj PDF i TXT",width=150,command=self._generate,state="disabled"); self.generate.grid(row=0,column=1,padx=4)
        self.browse=ctk.CTkButton(footer,text="Przeglądaj PDF",width=125,command=self._browse,state="disabled",**neutral); self.browse.grid(row=0,column=2,padx=4)
        self.copy=ctk.CTkButton(footer,text="Kopiuj tekst",width=115,command=self._copy,state="disabled",**neutral); self.copy.grid(row=0,column=3,padx=4)
        ctk.CTkButton(footer,text="A−",width=44,command=lambda:self._zoom(-1),**neutral).grid(row=0,column=4,padx=2)
        ctk.CTkButton(footer,text="A+",width=44,command=lambda:self._zoom(1),**neutral).grid(row=0,column=5,padx=2)
        ctk.CTkButton(footer,text="Zamknij",width=95,command=self._close,**neutral).grid(row=0,column=6,padx=(8,0))
        self.protocol("WM_DELETE_WINDOW",self._close); self.after(120,self.refresh)

    def refresh(self):
        if self.running:return
        self.running=True; self.progress.set(0); self.status.configure(text="Pobieranie pełnych danych systemowych...")
        self.generate.configure(state="disabled"); self.copy.configure(state="disabled")
        def worker():
            try: result=system_report.collect_system_data(lambda p,m:self.after(0,lambda:self._progress(p,m)))
            except Exception as exc: self.after(0,lambda e=exc:self._fail(e)); return
            self.after(0,lambda:self._loaded(result))
        threading.Thread(target=worker,daemon=True).start()

    def _progress(self,percent,message):
        self.progress.set(max(0,min(100,float(percent)))/100); self.status.configure(text=message)

    def _loaded(self,sections):
        self.running=False; self.sections=sections; self.current_text=system_report.format_sections_text(sections)
        self.content.configure(state="normal"); self.content.delete("1.0","end"); self.content.insert("1.0",self.current_text); self.content.configure(state="disabled")
        self.progress.set(1); self.status.configure(text=f"Podgląd gotowy — sekcje: {len(sections)}")
        self.generate.configure(state="normal"); self.copy.configure(state="normal")

    def _generate(self):
        if self.running or not self.sections:return
        self.running=True; self.generate.configure(state="disabled",text="Generowanie..."); self.browse.configure(state="disabled"); self.progress.set(.05)
        def worker():
            try: result=system_report.write_system_report(self.sections,formats=("pdf","txt"),progress=lambda p,m:self.after(0,lambda:self._progress(p,m)))
            except Exception as exc: self.after(0,lambda e=exc:self._fail(e)); return
            self.after(0,lambda:self._generated(result))
        threading.Thread(target=worker,daemon=True).start()

    def _generated(self,result):
        self.running=False; self.pdf_path=result.get("pdf"); self.txt_path=result.get("txt"); self.progress.set(1)
        self.generate.configure(state="normal",text="Generuj PDF i TXT"); self.browse.configure(state="normal" if self.pdf_path else "disabled")
        self.status.configure(text=f"Gotowe — PDF: {self.pdf_path} | TXT: {self.txt_path}")
        if self.on_result:self.on_result(result)

    def _copy(self):
        self.clipboard_clear(); self.clipboard_append(self.current_text); self.update_idletasks(); self.status.configure(text="Skopiowano cały raport jako tekst do schowka.")

    def _zoom(self,direction):
        self.font_size=max(8,min(22,self.font_size+direction)); self.content.configure(font=("Cascadia Mono",self.font_size)); self.status.configure(text=f"Rozmiar czcionki: {self.font_size} pt")

    def _browse(self):
        if self.pdf_path:
            try: reports.open_pdf(self.pdf_path)
            except Exception as exc: messagebox.showerror("Przeglądaj PDF",str(exc),parent=self)

    def _fail(self,exc):
        self.running=False; self.progress.configure(progress_color=self.colors["red"]); self.status.configure(text=f"Błąd: {exc}"); self.generate.configure(state="normal" if self.sections else "disabled",text="Generuj PDF i TXT")
        messagebox.showerror("Pełny raport systemowy",str(exc),parent=self)

    def _close(self):
        if self.request_close() and self.on_close:self.on_close()
