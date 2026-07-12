"""Okno tworzenia i szyfrowania dokumentów PDF."""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import reports
from ..services import pdf_tools


class PdfToolsDialog(ctk.CTkToplevel):
    def __init__(self, parent, colors: dict[str, str], on_result=None) -> None:
        super().__init__(parent); self.colors=colors; self.on_result=on_result; self.result=None; self.running=False
        self.title("Narzędzia PDF"); self.geometry("760x590"); self.minsize(650,520); self.configure(fg_color=colors["bg"]); self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(4,weight=1)
        ctk.CTkLabel(self,text="Narzędzia PDF",text_color=colors["text"],font=("Segoe UI",22,"bold"),anchor="w").grid(row=0,column=0,sticky="ew",padx=18,pady=(16,2))
        ctk.CTkLabel(self,text="Utwórz PDF bez nagłówka z dowolnego pliku albo zaszyfruj istniejący PDF algorytmem AES-256.",text_color=colors["muted"],font=("Segoe UI",10),anchor="w",wraplength=700).grid(row=1,column=0,sticky="ew",padx=18,pady=(0,10))
        form=ctk.CTkFrame(self,fg_color=colors["card"],border_width=1,border_color=colors["border"],corner_radius=8);form.grid(row=2,column=0,sticky="ew",padx=18,pady=(0,10));form.grid_columnconfigure(1,weight=1)
        self.source=tk.StringVar(); self.password=tk.StringVar(); self.repeat=tk.StringVar(); self.encrypt_created=tk.BooleanVar(); self.show_password=tk.BooleanVar()
        ctk.CTkLabel(form,text="Plik źródłowy",text_color=colors["text"],font=("Segoe UI",10,"bold")).grid(row=0,column=0,padx=12,pady=10)
        ctk.CTkEntry(form,textvariable=self.source).grid(row=0,column=1,sticky="ew",pady=10);ctk.CTkButton(form,text="Wybierz",width=85,command=self._choose).grid(row=0,column=2,padx=10)
        ctk.CTkLabel(form,text="Hasło (minimum 8 znaków)",text_color=colors["text"],font=("Segoe UI",9,"bold")).grid(row=1,column=0,sticky="w",padx=12)
        self.password_entry=ctk.CTkEntry(form,textvariable=self.password,show="*");self.password_entry.grid(row=2,column=0,columnspan=2,sticky="ew",padx=(12,6),pady=(3,8))
        self.repeat_entry=ctk.CTkEntry(form,textvariable=self.repeat,show="*",placeholder_text="Powtórz hasło");self.repeat_entry.grid(row=2,column=2,sticky="ew",padx=(6,10),pady=(3,8))
        ctk.CTkCheckBox(form,text="Szyfruj tworzony PDF",variable=self.encrypt_created,text_color=colors["text"]).grid(row=3,column=0,columnspan=2,sticky="w",padx=12,pady=(0,10))
        ctk.CTkCheckBox(form,text="Pokaż hasło",variable=self.show_password,command=self._toggle,text_color=colors["text"]).grid(row=3,column=2,sticky="w",padx=10,pady=(0,10))
        actions=ctk.CTkFrame(self,fg_color="transparent");actions.grid(row=3,column=0,sticky="ew",padx=18,pady=(0,8));actions.grid_columnconfigure(0,weight=1)
        self.create_button=ctk.CTkButton(actions,text="Utwórz PDF",width=120,command=self._create);self.create_button.grid(row=0,column=1,padx=4)
        self.encrypt_button=ctk.CTkButton(actions,text="Szyfruj PDF",width=120,command=self._encrypt,fg_color=colors["purple"]);self.encrypt_button.grid(row=0,column=2,padx=4)
        self.browse_button=ctk.CTkButton(actions,text="Przeglądaj PDF",width=125,state="disabled",command=self._browse);self.browse_button.grid(row=0,column=3,padx=4)
        self.folder_button=ctk.CTkButton(actions,text="Otwórz katalog",width=115,state="disabled",command=self._folder,fg_color=colors["soft"],text_color=colors["text"],border_width=1,border_color=colors["border"]);self.folder_button.grid(row=0,column=4,padx=(4,0))
        self.output=ctk.CTkTextbox(self,fg_color=colors["card"],text_color=colors["text"],border_width=1,border_color=colors["border"],font=("Cascadia Mono",10));self.output.grid(row=4,column=0,sticky="nsew",padx=18,pady=(0,10))
        ctk.CTkButton(self,text="Zamknij",width=95,command=self.destroy,fg_color=colors["soft"],text_color=colors["text"],border_width=1,border_color=colors["border"]).grid(row=5,column=0,sticky="e",padx=18,pady=(0,14))

    def _choose(self):
        path=filedialog.askopenfilename(parent=self)
        if path:self.source.set(path)
    def _toggle(self):
        show="" if self.show_password.get() else "*";self.password_entry.configure(show=show);self.repeat_entry.configure(show=show)
    def _password(self,required=True):
        must_encrypt=required or self.encrypt_created.get(); password=self.password.get() if must_encrypt else ""
        if must_encrypt:
            pdf_tools.validate_password(password)
            if password!=self.repeat.get():raise ValueError("Podane hasła nie są identyczne.")
        return password
    def _create(self):
        try: password=self._password(required=False)
        except Exception as exc:messagebox.showwarning("Hasło",str(exc),parent=self);return
        self._run(lambda:pdf_tools.create_pdf_from_file(self.source.get(),password))
    def _encrypt(self):
        try: password=self._password(required=True)
        except Exception as exc:messagebox.showwarning("Hasło",str(exc),parent=self);return
        self._run(lambda:pdf_tools.encrypt_pdf(self.source.get(),password))
    def _run(self,operation):
        if self.running:return
        self.running=True;self.create_button.configure(state="disabled");self.encrypt_button.configure(state="disabled");self.output.delete("1.0","end");self.output.insert("1.0","Operacja w toku...")
        def worker():
            try:result=operation();self.after(0,lambda:self._finish(result))
            except Exception as exc:self.after(0,lambda error=exc:self._finish({"error":str(error)}))
        threading.Thread(target=worker,daemon=True).start()
    def _finish(self,result):
        self.running=False;self.result=result;self.create_button.configure(state="normal");self.encrypt_button.configure(state="normal");self.output.delete("1.0","end");self.output.insert("1.0",json.dumps(result,ensure_ascii=False,indent=2))
        enabled="normal" if reports.find_pdf(result) else "disabled";self.browse_button.configure(state=enabled);self.folder_button.configure(state=enabled)
        if self.on_result:self.on_result(result)
    def _browse(self):
        pdf=reports.find_pdf(self.result)
        if pdf:reports.open_pdf(pdf)
    def _folder(self):
        pdf=reports.find_pdf(self.result)
        if pdf:os.startfile(str(pdf.parent))
