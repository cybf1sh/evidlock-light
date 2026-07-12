"""Lekki skaner TCP, rozpoznawanie hostów i integracja TShark."""

from __future__ import annotations

import csv
import datetime as dt
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

from .. import reports, winapi
from ..config import EXPORTS_DIR


PORT_PROFILES = {
    "Szybki": "22,53,80,135,139,443,445,515,631,3389,5900,8080,9100",
    "Windows": "53,88,135,137-139,389,445,464,593,636,3268-3269,3389,5985-5986",
    "Infrastruktura": "21,22,23,25,53,67,68,80,110,123,161,162,443,514,515,631,993,995,8080,8443,9100",
    "Urządzenia": "80,81,443,515,554,631,1883,5000,5001,8000,8080,8081,8443,8554,9100",
    "Rozszerzony": "20-23,25,53,67-68,80,88,110,123,135,137-139,143,161-162,389,443,445,464,515,554,587,593,631,636,993,995,1433,1883,2049,3268-3269,3306,3389,5000-5001,5432,5900,5985-5986,8000,8080-8081,8443,8554,9100",
}


@dataclass
class PortResult:
    host: str
    port: int
    open: bool
    service: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def parse_ports(text: str) -> list[int]:
    ports: set[int] = set()
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(value.strip()) for value in part.split("-", 1)]
            if start > end:
                start, end = end, start
            if end - start > 10000:
                raise ValueError("Pojedynczy zakres portów nie może przekraczać 10000 pozycji.")
            ports.update(range(start, end + 1))
        else:
            ports.add(int(part))
    result = sorted(port for port in ports if 1 <= port <= 65535)
    if not result:
        raise ValueError("Podaj co najmniej jeden poprawny port TCP.")
    return result


def _service_name(port: int) -> str:
    known = {
        22: "SSH", 53: "DNS", 80: "HTTP", 88: "Kerberos", 135: "RPC", 139: "NetBIOS",
        161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB", 515: "LPD", 554: "RTSP",
        631: "IPP", 1433: "MSSQL", 1883: "MQTT", 2049: "NFS", 3306: "MySQL",
        3389: "RDP", 5000: "HTTP/UPnP", 5432: "PostgreSQL", 5900: "VNC",
        5985: "WinRM", 5986: "WinRM HTTPS", 8080: "HTTP alternatywny", 8443: "HTTPS alternatywny",
        9100: "JetDirect",
    }
    if port in known:
        return known[port]
    try:
        return socket.getservbyport(port, "tcp").upper()
    except OSError:
        return "TCP"


def _tcp_port(host: str, port: int, timeout: float) -> dict:
    started = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        is_open = sock.connect_ex((host, port)) == 0
    return {"port": port, "service": _service_name(port), "latency_ms": round((time.perf_counter() - started) * 1000, 1), "open": is_open}


def scan_tcp(host: str, ports: list[int], timeout: float = 0.7) -> list[dict]:
    return [PortResult(host, port, item["open"], item["service"]).to_dict() for port in ports for item in [_tcp_port(host, port, timeout)]]


def _targets(value: str, max_hosts: int = 1024) -> list[str]:
    target = str(value or "").strip()
    if not target:
        raise ValueError("Podaj adres IP, nazwę hosta albo podsieć CIDR.")
    if "/" in target:
        network = ipaddress.ip_network(target, strict=False)
        if network.version != 4:
            raise ValueError("Skaner podsieci obsługuje obecnie IPv4.")
        hosts = [str(host) for host in network.hosts()]
        if len(hosts) > max_hosts:
            raise ValueError(f"Podsieć zawiera {len(hosts)} hostów. Limit jednego skanu wynosi {max_hosts}.")
        return hosts
    try:
        return [str(ipaddress.ip_address(target))]
    except ValueError:
        try:
            return [socket.gethostbyname(target)]
        except OSError as exc:
            raise ValueError(f"Nie można rozwiązać hosta: {target}") from exc


def _identity(ip: str) -> tuple[str, str, str]:
    try:
        fqdn = socket.gethostbyaddr(ip)[0].rstrip(".")
    except OSError:
        fqdn = ""
    computer = fqdn.split(".", 1)[0] if fqdn else ""
    domain = fqdn.split(".", 1)[1] if "." in fqdn else ""
    return fqdn, computer, domain


def _device_type(open_ports: set[int], hostname: str) -> tuple[str, str]:
    name = hostname.lower()
    if open_ports & {515, 631, 9100} or any(marker in name for marker in ("printer", "druk", "xerox", "canon", "epson", "brother", "hp-")):
        return "Drukarka", "wysoka"
    if open_ports & {554, 8554} or any(marker in name for marker in ("camera", "kamera", "cam-", "nvr", "dvr")):
        return "Kamera / monitoring", "wysoka"
    if 3389 in open_ports or ({135, 139, 445} & open_ports and 445 in open_ports) or open_ports & {5985, 5986}:
        return "Komputer Windows", "wysoka" if 3389 in open_ports or 445 in open_ports else "średnia"
    if open_ports & {2049, 5000, 5001} and open_ports & {139, 445}:
        return "NAS / serwer plików", "wysoka"
    if 53 in open_ports and open_ports & {80, 443, 8080, 8443}:
        return "Router / urządzenie sieciowe", "średnia"
    if 22 in open_ports and open_ports & {80, 443, 8080, 8443}:
        return "Serwer / urządzenie Linux", "średnia"
    if open_ports & {1883, 8000, 8081}:
        return "Urządzenie IoT", "niska"
    if open_ports:
        return "Inne urządzenie sieciowe", "niska"
    return "Host bez rozpoznanych usług", "niska"


def _scan_host(ip: str, ports: list[int], timeout: float, parallel_ports: bool, stop_event=None) -> dict:
    started = time.perf_counter()
    ping = winapi.icmp_echo(ip, int(timeout * 1000))
    port_results: list[dict] = []
    if parallel_ports:
        with ThreadPoolExecutor(max_workers=min(32, len(ports))) as executor:
            futures = {executor.submit(_tcp_port, ip, port, timeout): port for port in ports}
            for future in as_completed(futures):
                if stop_event is not None and stop_event.is_set():
                    break
                port_results.append(future.result())
    else:
        for port in ports:
            if stop_event is not None and stop_event.is_set():
                break
            port_results.append(_tcp_port(ip, port, timeout))
    port_results.sort(key=lambda item: item["port"])
    open_services = [item for item in port_results if item["open"]]
    hostname, computer, domain = _identity(ip) if ping or open_services else ("", "", "")
    mac = winapi.mac_address(ip) if ping or open_services else ""
    device_type, confidence = _device_type({item["port"] for item in open_services}, hostname)
    return {
        "ip": ip, "online": bool(ping or open_services), "icmp": ping, "hostname": hostname,
        "computer_name": computer, "domain": domain, "mac": mac, "device_type": device_type,
        "confidence": confidence, "open_ports": open_services, "open_port_count": len(open_services),
        "scanned_port_count": len(port_results), "scan_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def scan_network(target: str, ports: list[int], timeout: float = 0.45, workers: int = 32, include_offline: bool = False, callback=None, stop_event=None) -> dict:
    addresses = _targets(target)
    timeout = max(0.1, min(5.0, float(timeout)))
    workers = max(1, min(128, int(workers)))
    started = time.perf_counter()
    results: list[dict] = []
    if len(addresses) == 1:
        results.append(_scan_host(addresses[0], ports, timeout, True, stop_event))
        if callback: callback(100, f"Przeskanowano {addresses[0]}")
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(addresses))) as executor:
            futures = {executor.submit(_scan_host, ip, ports, timeout, False, stop_event): ip for ip in addresses}
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if stop_event is not None and stop_event.is_set():
                    break
                result = future.result()
                if include_offline or result["online"]:
                    results.append(result)
                if callback:
                    callback(completed / len(addresses) * 100, f"Host {completed}/{len(addresses)}: {result['ip']}")
    results.sort(key=lambda item: ipaddress.ip_address(item["ip"]))
    return {
        "target": target, "addresses": len(addresses), "online": sum(1 for item in results if item["online"]),
        "ports": ports, "timeout": timeout, "workers": workers, "cancelled": bool(stop_event and stop_event.is_set()),
        "elapsed_seconds": round(time.perf_counter() - started, 2), "hosts": results,
    }


def export_scan(result: dict, output_dir: str | Path | None = None) -> dict:
    directory = Path(output_dir) if output_dir else EXPORTS_DIR / "network"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = directory / f"skan_sieci_{stamp}.json"
    csv_path = directory / f"skan_sieci_{stamp}.csv"
    pdf_path = directory / f"skan_sieci_{stamp}.pdf"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["IP", "Online", "ICMP", "Nazwa komputera", "FQDN", "Domena", "MAC", "Typ", "Pewność", "Otwarte porty", "Czas ms"])
        for host in result.get("hosts", []):
            ports = ", ".join(f"{item['port']}/{item['service']}" for item in host.get("open_ports", []))
            writer.writerow([host.get("ip"), host.get("online"), host.get("icmp"), host.get("computer_name"), host.get("hostname"), host.get("domain"), host.get("mac"), host.get("device_type"), host.get("confidence"), ports, host.get("scan_ms")])
    rows = []
    for host in result.get("hosts", []):
        ports = ", ".join(f"{item['port']}/{item['service']}" for item in host.get("open_ports", [])) or "-"
        rows.append([
            host.get("ip", "-"), host.get("computer_name") or "-", host.get("hostname") or "-",
            host.get("domain") or "-", host.get("device_type") or "-", host.get("mac") or "-", ports,
        ])
    reports.write_professional_pdf(
        "Raport zaawansowanego skanu sieci TCP",
        [{
            "title": "Wykryte hosty",
            "headers": ["Adres IP", "Komputer", "FQDN", "Domena", "Typ urządzenia", "MAC", "Otwarte porty"],
            "table": rows or [["-", "Brak hostów online", "-", "-", "-", "-", "-"]],
            "widths": [72, 82, 108, 85, 105, 105, 165],
            "wide": True,
        }],
        pdf_path,
        subtitle="ICMP, TCP, DNS/FQDN, MAC i heurystyczna klasyfikacja urządzeń.",
        metadata={"Zakres": result.get("target"), "Adresy": result.get("addresses"), "Online": result.get("online"), "Czas [s]": result.get("elapsed_seconds")},
    )
    return {"json": str(json_path.resolve()), "csv": str(csv_path.resolve()), "pdf": str(pdf_path.resolve()), "folder": str(directory.resolve())}


def tshark_status() -> dict:
    candidates = [
        shutil.which("tshark"),
        os.path.join(os.environ.get("ProgramFiles", "C:/Program Files"), "Wireshark", "tshark.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"), "Wireshark", "tshark.exe"),
    ]
    path = next((str(candidate) for candidate in candidates if candidate and Path(candidate).is_file()), "")
    return {"available": bool(path), "path": path, "install_available": bool(shutil.which("winget"))}


def install_tshark() -> dict:
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError("Brak winget. Zainstaluj Wireshark ręcznie z wireshark.org/download.html.")
    command = [winget, "install", "--id", "WiresharkFoundation.Wireshark", "-e", "--accept-source-agreements", "--accept-package-agreements"]
    subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    return {"started": True, "command": command, "message": "Uruchomiono instalację Wireshark. Po zakończeniu odśwież status."}


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
