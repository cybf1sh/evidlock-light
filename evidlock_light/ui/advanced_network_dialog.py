"""Nowoczesne okno zaawansowanego skanera TCP dla hosta i podsieci."""

from __future__ import annotations

import json
import ipaddress
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from .. import winapi
from ..services import network
from .windowing import ManagedToplevel, present_toplevel


class AdvancedNetworkDialog(ManagedToplevel):
    def __init__(self, parent, colors: dict[str, str], on_result=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.on_result = on_result
        self.running = False
        self.stop_event = threading.Event()
        self.result: dict | None = None
        self.hosts_by_ip: dict[str, dict] = {}
        self.export_folder: Path | None = None
        self._event_queue: queue.Queue = queue.Queue()
        self.title("Zaawansowany skaner sieci TCP")
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.configure(fg_color=colors["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self, text="Zaawansowany skaner sieci TCP", text_color=colors["text"], font=("Segoe UI", 22, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))
        ctk.CTkLabel(self, text="Rozpoznawanie hostów, nazw DNS, MAC, usług i prawdopodobnego typu urządzenia.", text_color=colors["muted"], font=("Segoe UI", 10), anchor="w").grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        settings = ctk.CTkFrame(self, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        settings.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        settings.grid_columnconfigure(1, weight=2)
        settings.grid_columnconfigure(3, weight=2)
        settings.grid_columnconfigure(5, weight=2)
        self.mode = tk.StringVar(value="Pojedynczy host")
        self.target = tk.StringVar(value="127.0.0.1")
        self.profile = tk.StringVar(value="Szybki")
        self.ports = tk.StringVar(value=network.PORT_PROFILES["Szybki"])
        self.scan_ports = tk.BooleanVar(value=True)
        self.timeout = tk.DoubleVar(value=.45)
        self.workers = tk.IntVar(value=32)
        self.include_offline = tk.BooleanVar(value=False)

        ctk.CTkLabel(settings, text="Zakres", text_color=colors["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(12, 7), pady=(10, 2))
        ctk.CTkSegmentedButton(settings, values=["Pojedynczy host", "Podsieć CIDR"], variable=self.mode, command=self._mode_changed).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(12, 8), pady=(0, 10))
        ctk.CTkLabel(settings, text="Adres / podsieć", text_color=colors["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=7, pady=(10, 2))
        self.target_entry = ctk.CTkEntry(settings, textvariable=self.target, height=32)
        self.target_entry.grid(row=1, column=2, columnspan=2, sticky="ew", padx=8, pady=(0, 10))
        self.subnet_octets = [tk.StringVar(value=value) for value in ("192", "168", "1", "0")]
        self.subnet_prefix = tk.StringVar(value="24")
        self.subnet_frame = ctk.CTkFrame(settings, fg_color="transparent")
        self.subnet_frame.grid(row=1, column=2, columnspan=2, sticky="ew", padx=8, pady=(0, 10))
        for index, variable in enumerate(self.subnet_octets):
            ctk.CTkEntry(self.subnet_frame, textvariable=variable, width=42, height=32, justify="center").pack(side=tk.LEFT, fill=tk.X, expand=True)
            if index < 3:
                ctk.CTkLabel(self.subnet_frame, text=".", text_color=colors["text"], font=("Segoe UI", 13, "bold"), width=10).pack(side=tk.LEFT)
        ctk.CTkLabel(self.subnet_frame, text="/", text_color=colors["text"], font=("Segoe UI", 13, "bold"), width=14).pack(side=tk.LEFT)
        ctk.CTkEntry(self.subnet_frame, textvariable=self.subnet_prefix, width=38, height=32, justify="center").pack(side=tk.LEFT)
        self.subnet_frame.grid_remove()
        ctk.CTkLabel(settings, text="Profil portów", text_color=colors["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w", padx=7, pady=(10, 2))
        ctk.CTkOptionMenu(settings, values=list(network.PORT_PROFILES), variable=self.profile, command=self._profile_changed).grid(row=1, column=4, columnspan=2, sticky="ew", padx=(8, 12), pady=(0, 10))

        ctk.CTkLabel(settings, text="Porty TCP", text_color=colors["text"], font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", padx=(12, 7), pady=(0, 2))
        self.ports_entry = ctk.CTkEntry(settings, textvariable=self.ports, height=32)
        self.ports_entry.grid(row=3, column=0, columnspan=3, sticky="ew", padx=(12, 8), pady=(0, 12))
        self.timeout_label = ctk.CTkLabel(settings, text="Timeout: 0,45 s", text_color=colors["text"], font=("Segoe UI", 9, "bold"))
        self.timeout_label.grid(row=2, column=3, sticky="w", padx=8)
        ctk.CTkSlider(settings, from_=0.1, to=2.0, number_of_steps=19, variable=self.timeout, command=self._sliders_changed).grid(row=3, column=3, sticky="ew", padx=8)
        self.workers_label = ctk.CTkLabel(settings, text="Równoległość: 32", text_color=colors["text"], font=("Segoe UI", 9, "bold"))
        self.workers_label.grid(row=2, column=4, sticky="w", padx=8)
        ctk.CTkSlider(settings, from_=1, to=64, number_of_steps=63, variable=self.workers, command=self._sliders_changed).grid(row=3, column=4, sticky="ew", padx=8)
        ctk.CTkCheckBox(settings, text="Skanuj otwarte porty", variable=self.scan_ports, command=self._toggle_port_scan, text_color=colors["text"]).grid(row=2, column=5, sticky="w", padx=(8, 12))
        ctk.CTkCheckBox(settings, text="Pokaż hosty bez odpowiedzi", variable=self.include_offline, text_color=colors["text"]).grid(row=3, column=5, sticky="w", padx=(8, 12))

        command_bar = ctk.CTkFrame(self, fg_color="transparent")
        command_bar.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 8))
        command_bar.grid_columnconfigure(2, weight=1)
        self.start_button = ctk.CTkButton(command_bar, text="Skanuj", command=self._start, width=110, fg_color=colors["green"])
        self.start_button.grid(row=0, column=0, padx=(0, 6))
        self.stop_button = ctk.CTkButton(command_bar, text="Stop", command=self._stop, width=80, state="disabled", fg_color=colors["red"])
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        self.progress = ctk.CTkProgressBar(command_bar, height=11, progress_color=colors["accent"])
        self.progress.grid(row=0, column=2, sticky="ew", padx=(0, 10)); self.progress.set(0)
        self.status = ctk.CTkLabel(command_bar, text="Gotowy do skanowania", text_color=colors["muted"], font=("Segoe UI", 9, "bold"), width=240, anchor="e")
        self.status.grid(row=0, column=3, sticky="e")

        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=4, column=0, sticky="nsew", padx=18)
        workspace.grid_columnconfigure(0, weight=3)
        workspace.grid_columnconfigure(1, weight=2)
        workspace.grid_rowconfigure(0, weight=1)
        table_frame = ctk.CTkFrame(workspace, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        table_frame.grid_columnconfigure(0, weight=1); table_frame.grid_rowconfigure(1, weight=1)
        self.summary = ctk.CTkLabel(table_frame, text="Wyniki: 0", text_color=colors["text"], font=("Segoe UI", 11, "bold"), anchor="w")
        self.summary.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 7))
        self._configure_tree_style()
        columns = ("ip", "name", "domain", "type", "mac", "ports")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", style="Network.Treeview")
        headings = {"ip":"Adres IP", "name":"Komputer", "domain":"Domena", "type":"Typ urządzenia", "mac":"MAC", "ports":"Otwarte porty"}
        widths = {"ip":110, "name":120, "domain":110, "type":160, "mac":125, "ports":150}
        for key in columns:
            self.tree.heading(key, text=headings[key]); self.tree.column(key, width=widths[key], minwidth=70, stretch=key in {"name","domain","type","ports"})
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10)); self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._select_host)
        self.tree.bind("<Button-3>", self._context_menu)

        details = ctk.CTkFrame(workspace, fg_color=colors["card"], border_width=1, border_color=colors["border"], corner_radius=8)
        details.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        details.grid_columnconfigure(0, weight=1); details.grid_rowconfigure(2, weight=1)
        self.detail_title = ctk.CTkLabel(details, text="Szczegóły hosta", text_color=colors["text"], font=("Segoe UI", 14, "bold"), anchor="w")
        self.detail_title.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        self.detail_type = ctk.CTkLabel(details, text="Wybierz host z tabeli", text_color=colors["muted"], font=("Segoe UI", 9), anchor="w")
        self.detail_type.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 7))
        self.detail_box = ctk.CTkTextbox(details, fg_color=colors["soft"], text_color=colors["text"], font=("Cascadia Mono", 9), wrap="word")
        self.detail_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 9)); self.detail_box.configure(state="disabled")
        remote = ctk.CTkFrame(details, fg_color="transparent")
        remote.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        remote.grid_columnconfigure((0,1), weight=1)
        ctk.CTkLabel(remote, text="Adres IP dla pomocy technicznej", text_color=colors["muted"], font=("Segoe UI", 9, "bold"), anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 3))
        self.help_target = tk.StringVar()
        self.help_target_entry = ctk.CTkEntry(remote, textvariable=self.help_target, placeholder_text="np. 192.168.1.25", height=32)
        self.help_target_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        self.help_target.trace_add("write", lambda *_args: self._remote_help_state())
        self.rdp_button = ctk.CTkButton(remote, text="Pulpit zdalny", command=self._rdp, state="disabled", fg_color=colors["teal"])
        self.rdp_button.grid(row=2, column=0, sticky="ew", padx=(0, 4))
        self.help_button = ctk.CTkButton(remote, text="Pomoc zdalna (OfferRA)", command=self._remote_help, state="disabled", fg_color=colors["purple"])
        self.help_button.grid(row=2, column=1, sticky="ew", padx=(4, 0))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=18, pady=14)
        footer.grid_columnconfigure(0, weight=1)
        self.open_folder_button = ctk.CTkButton(footer, text="Otwórz katalog", command=self._open_folder, state="disabled", width=120, fg_color="transparent", hover_color=colors["soft"], text_color=colors["accent"], border_width=0)
        self.open_folder_button.grid(row=0, column=0, sticky="w")
        self.export_button = ctk.CTkButton(footer, text="Eksport JSON/CSV/PDF", command=self._export, state="disabled", width=155, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"])
        self.export_button.grid(row=0, column=1, padx=8)
        ctk.CTkButton(footer, text="Zamknij", command=self.request_close, width=95, fg_color=colors["soft"], text_color=colors["text"], border_width=1, border_color=colors["border"]).grid(row=0, column=2)

    def _configure_tree_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Network.Treeview", background=self.colors["card"], fieldbackground=self.colors["card"], foreground=self.colors["text"], rowheight=28, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Network.Treeview.Heading", background=self.colors["soft"], foreground=self.colors["text"], font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Network.Treeview", background=[("selected", self.colors["accent"])], foreground=[("selected", "#ffffff")])

    def _mode_changed(self, value: str) -> None:
        if value == "Podsieć CIDR":
            self.target_entry.grid_remove()
            self.subnet_frame.grid()
        else:
            self.subnet_frame.grid_remove()
            self.target_entry.grid()
            self.target.set("127.0.0.1")

    def _toggle_port_scan(self) -> None:
        self.ports_entry.configure(state="normal" if self.scan_ports.get() else "disabled")

    def _subnet_target(self) -> str:
        octets = []
        for value in self.subnet_octets:
            text = value.get().strip()
            if not text.isdigit() or not 0 <= int(text) <= 255:
                raise ValueError("Każdy oktet podsieci musi być liczbą od 0 do 255.")
            octets.append(str(int(text)))
        prefix = self.subnet_prefix.get().strip()
        if not prefix.isdigit() or not 0 <= int(prefix) <= 32:
            raise ValueError("Maska CIDR musi być liczbą od 0 do 32.")
        return f"{'.'.join(octets)}/{int(prefix)}"

    def _profile_changed(self, value: str) -> None:
        self.ports.set(network.PORT_PROFILES[value])

    def _sliders_changed(self, _value=None) -> None:
        self.timeout_label.configure(text=f"Timeout: {self.timeout.get():.2f} s".replace(".", ","))
        self.workers_label.configure(text=f"Równoległość: {int(self.workers.get())}")

    def _start(self) -> None:
        if self.running:
            return
        try:
            target = self._subnet_target() if self.mode.get() == "Podsieć CIDR" else self.target.get().strip()
        except ValueError as exc:
            messagebox.showwarning("Adres podsieci", str(exc), parent=self); return
        if self.mode.get() == "Podsieć CIDR":
            self.target.set(target)
        if self.mode.get() == "Podsieć CIDR" and "/" not in target:
            messagebox.showwarning("Skaner sieci", "Dla podsieci podaj zapis CIDR, np. 192.168.1.0/24.", parent=self); return
        if self.mode.get() == "Pojedynczy host" and "/" in target:
            messagebox.showwarning("Skaner sieci", "Dla pojedynczego hosta podaj adres IP albo nazwę DNS bez maski CIDR.", parent=self); return
        try:
            ports = network.parse_ports(self.ports.get()) if self.scan_ports.get() else []
        except Exception as exc:
            messagebox.showerror("Porty TCP", str(exc), parent=self); return
        timeout = float(self.timeout.get())
        workers = int(self.workers.get())
        include_offline = bool(self.include_offline.get())
        self.running = True; self.stop_event.clear(); self.result = None; self.hosts_by_ip.clear(); self.export_folder = None
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break
        for item in self.tree.get_children(): self.tree.delete(item)
        self.progress.set(0); self.status.configure(text="Przygotowanie skanu..."); self.summary.configure(text="Wyniki: 0")
        self.start_button.configure(state="disabled"); self.stop_button.configure(state="normal"); self.export_button.configure(state="disabled"); self.open_folder_button.configure(state="disabled")
        self._show_details(None)

        def callback(value, text): self._event_queue.put(("progress", value, text))
        def host_callback(host): self._event_queue.put(("host", host))
        def worker():
            try:
                result = network.scan_network(
                    target, ports, timeout, workers, include_offline,
                    callback, self.stop_event, host_callback,
                )
                self._event_queue.put(("finish", result))
            except Exception as exc:
                self._event_queue.put(("error", exc))
        threading.Thread(target=worker, daemon=True).start()
        self._poll_events()

    def _poll_events(self) -> None:
        try:
            while True:
                event = self._event_queue.get_nowait()
                if event[0] == "progress":
                    self._progress(event[1], event[2])
                elif event[0] == "host":
                    self._add_host(event[1])
                elif event[0] == "finish":
                    self._finish(event[1])
                elif event[0] == "error":
                    self._fail(event[1])
        except queue.Empty:
            pass
        if self.running:
            self.after(40, self._poll_events)

    def _progress(self, value: float, text: str) -> None:
        self.progress.set(max(0, min(100, value)) / 100); self.status.configure(text=text)

    def _stop(self) -> None:
        if self.running:
            self.stop_event.set(); self.stop_button.configure(state="disabled"); self.status.configure(text="Zatrzymywanie po bieżących połączeniach...")

    def _finish(self, result: dict) -> None:
        self.running = False; self.result = result; self.start_button.configure(state="normal"); self.stop_button.configure(state="disabled")
        self.progress.set(1 if not result.get("cancelled") else self.progress.get())
        self.status.configure(text=f"Zakończono w {result['elapsed_seconds']} s" if not result.get("cancelled") else "Skan zatrzymany")
        for host in result.get("hosts", []):
            self._add_host(host)
        self.summary.configure(text=f"Hosty online: {result['online']}  |  Wiersze: {len(result.get('hosts', []))}  |  Adresy: {result['addresses']}")
        self.export_button.configure(state="normal" if result.get("hosts") else "disabled")
        if self.tree.get_children(): self.tree.selection_set(self.tree.get_children()[0]); self._select_host()
        if self.on_result: self.on_result(result)

    def _add_host(self, host: dict) -> None:
        """Dodaje hosta do tabeli natychmiast po zakończeniu jego skanowania."""

        ip = host["ip"]
        self.hosts_by_ip[ip] = host
        ports = ", ".join(str(item["port"]) for item in host.get("open_ports", [])) if host.get("ports_scanned", True) else "Nie skanowano"
        ports = ports or "-"
        values = (ip, host.get("computer_name") or "-", host.get("domain") or "-", host.get("device_type"), host.get("mac") or "-", ports)
        if self.tree.exists(ip):
            self.tree.item(ip, values=values)
        else:
            self.tree.insert("", "end", iid=ip, values=values)
        self.summary.configure(text=f"Wykryto hostów: {len(self.hosts_by_ip)}  |  Online: {sum(1 for item in self.hosts_by_ip.values() if item.get('online'))}")

    def _fail(self, error: Exception) -> None:
        self.running = False; self.start_button.configure(state="normal"); self.stop_button.configure(state="disabled"); self.progress.configure(progress_color=self.colors["red"]); self.status.configure(text=f"Błąd: {error}")
        messagebox.showerror("Skaner sieci", str(error), parent=self)

    def _selected(self) -> dict | None:
        selection = self.tree.selection()
        return self.hosts_by_ip.get(selection[0]) if selection else None

    def _context_menu(self, event) -> str:
        row = self.tree.identify_row(event.y)
        if not row:
            return "break"
        self.tree.selection_set(row)
        self.tree.focus(row)
        self._select_host()
        host = self._selected()
        if not host:
            return "break"
        menu = tk.Menu(self, tearoff=False, background=self.colors["card"], foreground=self.colors["text"], activebackground=self.colors["accent"], activeforeground="#ffffff")
        rdp_state = "normal" if host.get("online") and host.get("device_type") == "Komputer Windows" else "disabled"
        menu.add_command(label="Pulpit zdalny (RDP)", command=self._rdp, state=rdp_state)
        menu.add_command(label="Pomoc zdalna (OfferRA)", command=self._remote_help, state="normal")
        menu.add_separator()
        menu.add_command(label="Kopiuj adres IP", command=lambda: self._copy_text(host.get("ip", "")))
        menu.add_command(label="Kopiuj nazwę komputera", command=lambda: self._copy_text(host.get("computer_name") or host.get("hostname") or ""))
        menu.add_command(label="Kopiuj szczegóły JSON", command=lambda: self._copy_text(json.dumps(host, ensure_ascii=False, indent=2)))
        menu.add_command(label="Eksportuj wyniki JSON/CSV/PDF", command=self._export, state="normal" if self.result else "disabled")
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _copy_text(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update_idletasks()

    def _select_host(self, _event=None) -> None:
        self._show_details(self._selected())

    def _show_details(self, host: dict | None) -> None:
        if not host:
            self.detail_title.configure(text="Szczegóły hosta"); self.detail_type.configure(text="Wybierz host z tabeli"); text=""
            state="disabled"
            self.help_target.set("")
        else:
            self.detail_title.configure(text=f"{host['ip']}  {host.get('computer_name') or ''}")
            self.detail_type.configure(text=f"{host['device_type']}  |  pewność: {host['confidence']}")
            text=json.dumps(host, ensure_ascii=False, indent=2)
            state="normal" if host.get("online") and host.get("device_type")=="Komputer Windows" else "disabled"
            self.help_target.set(host["ip"])
        self.detail_box.configure(state="normal"); self.detail_box.delete("1.0","end"); self.detail_box.insert("1.0",text); self.detail_box.configure(state="disabled")
        self.rdp_button.configure(state=state)
        self._remote_help_state()

    def _remote_help_state(self) -> None:
        try:
            ipaddress.ip_address(self.help_target.get().strip())
            state = "normal"
        except ValueError:
            state = "disabled"
        self.help_button.configure(state=state)

    def _rdp(self) -> None:
        host=self._selected()
        if host and messagebox.askyesno("Pulpit zdalny", f"Uruchomić klienta Pulpitu zdalnego dla {host['ip']}?", parent=self):
            try: winapi.launch_remote_desktop(host["ip"]); self.status.configure(text=f"Uruchomiono RDP: {host['ip']}")
            except Exception as exc: messagebox.showerror("Pulpit zdalny",str(exc),parent=self)

    def _remote_help(self) -> None:
        target = self.help_target.get().strip()
        try:
            ipaddress.ip_address(target)
        except ValueError:
            messagebox.showwarning("Pomoc zdalna - OfferRA", "Wpisz poprawny adres IPv4 komputera, któremu chcesz pomóc.", parent=self)
            return
        message=(f"Uruchomić zaawansowany tryb Pomocy zdalnej dla {target}?\n\nProgram uruchomi wyłącznie MSRA /offerra. Na komputerze docelowym muszą być skonfigurowane zasady Offer Remote Assistance i wyjątki zapory. Pojawi się okno UAC.")
        if messagebox.askyesno("Pomoc zdalna - OfferRA",message,parent=self):
            try: winapi.launch_remote_assistance_offer(target); self.status.configure(text=f"Uruchomiono OfferRA: {target}")
            except Exception as exc: messagebox.showerror("Pomoc zdalna - OfferRA",str(exc),parent=self)

    def _export(self) -> None:
        if not self.result: return
        try:
            exported=network.export_scan(self.result); self.export_folder=Path(exported["folder"]); self.open_folder_button.configure(state="normal"); self.status.configure(text=f"Eksport gotowy: {self.export_folder}")
            if self.on_result: self.on_result({**self.result,"export":exported})
        except Exception as exc: messagebox.showerror("Eksport skanu",str(exc),parent=self)

    def _open_folder(self) -> None:
        if self.export_folder: winapi.open_path(self.export_folder)
