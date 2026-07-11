"""Konsolowy interfejs EvidLock Light."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import APP_NAME, APP_VERSION
from . import winapi
from .reports import write_json
from .services import archive, copying, docs, hashing, journal, media, memory, network, readonly, registry, windows_logs


def _print(data: object, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if isinstance(data, list):
        for item in data:
            print(item)
    elif isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidlock-light", description=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument("--json", action="store_true", help="Zwróć wynik jako JSON.")
    parser.add_argument("--admin", action="store_true", help="Uruchom ponownie z uprawnieniami administratora.")
    sub = parser.add_subparsers(dest="command", required=True)

    media_parser = sub.add_parser("media", help="Nośniki i raporty.")
    media_sub = media_parser.add_subparsers(dest="media_command", required=True)
    media_sub.add_parser("list", help="Lista nośników.")
    media_report = media_sub.add_parser("report", help="Raport PDF nośników.")
    media_report.add_argument("--drive", help="Litera dysku, np. E:")
    media_report.add_argument("--out", help="Ścieżka PDF.")

    hash_parser = sub.add_parser("hash", help="SHA-256 i manifesty.")
    hash_sub = hash_parser.add_subparsers(dest="hash_command", required=True)
    hash_file = hash_sub.add_parser("file", help="Hash pliku.")
    hash_file.add_argument("path")
    manifest = hash_sub.add_parser("manifest", help="Zapis manifestu katalogu/pliku.")
    manifest.add_argument("path")
    manifest.add_argument("--out", required=True)
    verify = hash_sub.add_parser("verify", help="Weryfikacja manifestu.")
    verify.add_argument("manifest")
    verify.add_argument("--root")

    copy_parser = sub.add_parser("copy", help="Kopia i porównanie.")
    copy_sub = copy_parser.add_subparsers(dest="copy_command", required=True)
    copy_one = copy_sub.add_parser("one-to-one", help="Kopia 1:1.")
    copy_one.add_argument("--src", required=True)
    copy_one.add_argument("--dst", required=True)
    compare = copy_sub.add_parser("compare", help="Porównanie A/B.")
    compare.add_argument("--a", required=True)
    compare.add_argument("--b", required=True)

    archive_parser = sub.add_parser("archive", help="Archiwizacja ZIP.")
    archive_parser.add_argument("--src", required=True)
    archive_parser.add_argument("--out", required=True)

    ro_parser = sub.add_parser("readonly", help="Atrybut tylko do odczytu.")
    ro_sub = ro_parser.add_subparsers(dest="readonly_command", required=True)
    ro_set = ro_sub.add_parser("set")
    ro_set.add_argument("path")
    ro_clear = ro_sub.add_parser("clear")
    ro_clear.add_argument("path")
    ro_check = ro_sub.add_parser("check")
    ro_check.add_argument("path")

    net_parser = sub.add_parser("network", help="Network analyzer i skaner.")
    net_sub = net_parser.add_subparsers(dest="network_command", required=True)
    scan = net_sub.add_parser("scan", help="Skan portów TCP.")
    scan.add_argument("--host", required=True)
    scan.add_argument("--ports", default="22,80,443,445,3389")
    pcap = net_sub.add_parser("pcap", help="Podstawowa analiza PCAP przez TShark.")
    pcap.add_argument("path")
    pcap.add_argument("--out")
    net_sub.add_parser("deps", help="Status TShark.")
    net_sub.add_parser("install", help="Instalacja Wireshark/TShark przez winget.")

    mem_parser = sub.add_parser("memory", help="WinPmem i Volatility 3.")
    mem_sub = mem_parser.add_subparsers(dest="memory_command", required=True)
    mem_sub.add_parser("deps")
    vol = mem_sub.add_parser("volatility")
    vol.add_argument("--image", required=True)
    vol.add_argument("--plugin", required=True)
    compare_memory = mem_sub.add_parser("compare")
    compare_memory.add_argument("--a", required=True)
    compare_memory.add_argument("--b", required=True)
    acquire = mem_sub.add_parser("acquire")
    acquire.add_argument("--out", required=True)
    mem_sub.add_parser("install-volatility")

    system_parser = sub.add_parser("system", help="Rejestr, logi, diagnostyka.")
    system_sub = system_parser.add_subparsers(dest="system_command", required=True)
    system_sub.add_parser("diagnostics")
    system_sub.add_parser("journal-export")
    reg = system_sub.add_parser("registry-export")
    reg.add_argument("--out")
    logs = system_sub.add_parser("logs-export")
    logs.add_argument("--out")

    docs_parser = sub.add_parser("docs", help="Dokumentacja tekstowa.")
    docs_parser.add_argument("--search", default="")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.admin and not winapi.is_admin():
        winapi.relaunch_as_admin()
        return 0

    result: object
    if args.command == "media":
        if args.media_command == "list":
            result = media.list_media()
        else:
            result = {"pdf": str(media.report_media(args.drive, args.out))}
    elif args.command == "hash":
        if args.hash_command == "file":
            result = {"path": args.path, "sha256": hashing.sha256_file(args.path)}
        elif args.hash_command == "manifest":
            result = {"manifest": str(hashing.save_manifest(args.path, args.out))}
        else:
            result = hashing.verify_manifest(args.manifest, args.root)
    elif args.command == "copy":
        result = copying.copy_1to1(args.src, args.dst) if args.copy_command == "one-to-one" else copying.compare_paths(args.a, args.b)
    elif args.command == "archive":
        result = {"archive": str(archive.create_zip(args.src, args.out))}
    elif args.command == "readonly":
        if args.readonly_command == "set":
            result = readonly.apply_readonly(args.path)
        elif args.readonly_command == "clear":
            result = readonly.clear_readonly(args.path)
        else:
            result = readonly.check_readonly(args.path)
    elif args.command == "network":
        if args.network_command == "scan":
            result = network.scan_tcp(args.host, network.parse_ports(args.ports))
        elif args.network_command == "pcap":
            result = network.analyze_pcap_basic(args.path, args.out)
        elif args.network_command == "deps":
            result = network.tshark_status()
        else:
            result = network.install_tshark()
    elif args.command == "memory":
        if args.memory_command == "deps":
            result = memory.dependency_status(Path.cwd())
        elif args.memory_command == "volatility":
            result = memory.run_volatility(args.image, args.plugin, Path.cwd())
        elif args.memory_command == "compare":
            result = memory.compare_dumps(args.a, args.b)
        elif args.memory_command == "acquire":
            result = memory.acquire_memory(args.out)
        else:
            result = memory.install_volatility()
    elif args.command == "system":
        if args.system_command == "diagnostics":
            result = {"app": APP_NAME, "version": APP_VERSION, "admin": winapi.is_admin(), "media_count": len(media.list_media())}
        elif args.system_command == "journal-export":
            result = journal.export_journal()
        elif args.system_command == "registry-export":
            result = registry.export_registry(args.out)
        else:
            result = windows_logs.export_logs(args.out)
    elif args.command == "docs":
        result = docs.search_docs(args.search)
    else:
        parser.error("Nieznana komenda.")
        return 2

    if args.json:
        _print(result, True)
    else:
        if isinstance(result, (dict, list)):
            _print(result, False)
        else:
            print(result)
    return 0
