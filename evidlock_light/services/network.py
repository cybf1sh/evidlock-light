"""Narzędzia Network dla EvidLock Light.

Na start moduł zawiera skaner TCP i kontrolę TShark. Analizator PCAP będzie
rozbudowywany tutaj bez mieszania kodu z GUI.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import os
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class PortResult:
    host: str
    port: int
    open: bool
    service: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def scan_tcp(host: str, ports: list[int], timeout: float = 0.7) -> list[dict]:
    results: list[dict] = []
    for port in ports:
        service = ""
        try:
            service = socket.getservbyport(port)
        except Exception:
            pass
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            is_open = sock.connect_ex((host, port)) == 0
        results.append(PortResult(host, port, is_open, service).to_dict())
    return results


def parse_ports(text: str) -> list[int]:
    ports: set[int] = set()
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(x.strip()) for x in part.split("-", 1)]
            ports.update(range(start, end + 1))
        else:
            ports.add(int(part))
    return sorted(p for p in ports if 1 <= p <= 65535)


def tshark_status() -> dict:
    candidates = [
        shutil.which("tshark"),
        os.path.join(os.environ.get("ProgramFiles", "C:/Program Files"), "Wireshark", "tshark.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"), "Wireshark", "tshark.exe"),
    ]
    path = next((str(candidate) for candidate in candidates if candidate and Path(candidate).is_file()), "")
    return {"available": bool(path), "path": path, "install_available": bool(shutil.which("winget"))}


def install_tshark() -> dict:
    """Uruchamia oficjalny instalator Wireshark zawierający TShark."""

    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError("Brak winget. Zainstaluj Wireshark ręcznie z wireshark.org/download.html.")
    command = [winget, "install", "--id", "WiresharkFoundation.Wireshark", "-e", "--accept-source-agreements", "--accept-package-agreements"]
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(command, creationflags=flags)
    return {"started": True, "command": command, "message": "Uruchomiono instalację Wireshark. Po zakończeniu kliknij Odśwież status."}


def analyze_pcap_basic(pcap: str | Path, output: str | Path | None = None) -> dict:
    status = tshark_status()
    if not status["available"]:
        raise RuntimeError("TShark nie jest dostępny w PATH.")
    target = Path(pcap)
    if not target.exists():
        raise FileNotFoundError(str(target))
    command = [status["path"], "-r", str(target), "-q", "-z", "io,phs"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
    result = {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
    if output:
        Path(output).write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
    return result
