"""Pelny eksport rejestru Windows: hive, dane tekstowe i raporty."""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

from .. import reports, winapi
from ..config import EXPORTS_DIR
from .hashing import sha256_file


HIVES = [
    {"id": "SYSTEM", "label": "SYSTEM", "key": r"HKLM\SYSTEM", "file": "SYSTEM.hiv", "description": "Konfiguracja systemu, usługi, sterowniki i ControlSet."},
    {"id": "SOFTWARE", "label": "SOFTWARE", "key": r"HKLM\SOFTWARE", "file": "SOFTWARE.hiv", "description": "Programy oraz ustawienia Windows i aplikacji."},
    {"id": "SAM", "label": "SAM", "key": r"HKLM\SAM", "file": "SAM.hiv", "description": "Lokalna baza kont. Wymaga administratora."},
    {"id": "SECURITY", "label": "SECURITY", "key": r"HKLM\SECURITY", "file": "SECURITY.hiv", "description": "Polityki zabezpieczeń i sekrety LSA."},
    {"id": "NTUSER", "label": "NTUSER.DAT", "key": r"HKCU", "file": "NTUSER_CURRENT_USER.hiv", "description": "Hive profilu bieżącego użytkownika."},
]

FULL_BRANCHES = [
    ("HKLM_SYSTEM", r"HKLM\SYSTEM"),
    ("HKLM_SOFTWARE", r"HKLM\SOFTWARE"),
    ("HKLM_SAM", r"HKLM\SAM"),
    ("HKLM_SECURITY", r"HKLM\SECURITY"),
    ("HKLM_HARDWARE", r"HKLM\HARDWARE"),
    ("HKLM_BCD", r"HKLM\BCD00000000"),
    ("HKU", r"HKU"),
]


def _run_reg(arguments: list[str], timeout: int = 900) -> tuple[int, str]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(["reg.exe", *arguments], capture_output=True, text=True, encoding="mbcs", errors="replace", timeout=timeout, creationflags=flags)
    return result.returncode, ((result.stdout or "") + "\n" + (result.stderr or "")).strip()


def _parse_reg(path: Path, branch: str) -> list[dict]:
    records: list[dict] = []
    current_key = ""
    try:
        text = path.read_text(encoding="utf-16")
    except UnicodeError:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_key = line[1:-1]
        elif line and not line.startswith(("Windows Registry Editor", ";")):
            name, separator, value = line.partition("=")
            records.append({"branch": branch, "key": current_key, "name": name.strip('"') if separator else "", "value": value if separator else line})
    return records


def _write_reports(output: Path, hive_results: list[dict], records: list[dict], files: list[Path]) -> dict:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output / f"rejestr_dane_{stamp}.csv"
    txt_path = output / f"rejestr_raport_{stamp}.txt"
    xlsx_path = output / f"rejestr_raport_{stamp}.xlsx"
    json_path = output / f"rejestr_raport_{stamp}.json"
    pdf_path = output / f"rejestr_raport_{stamp}.pdf"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["branch", "key", "name", "value"])
        writer.writeheader(); writer.writerows(records)
    payload = {"created": dt.datetime.now().isoformat(timespec="seconds"), "admin": winapi.is_admin(), "hives": hive_results, "records": len(records)}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["EVIDLOCK LIGHT - EKSPORT REJESTRU WINDOWS", "=" * 52, f"Data: {payload['created']}", f"Administrator: {'TAK' if payload['admin'] else 'NIE'}", f"Rekordy danych: {len(records)}", "", "HIVE:"]
    lines.extend(f"- {item['label']}: {item['status']} | {item.get('sha256') or 'BRAK SHA-256'} | {item.get('path') or item.get('message')}" for item in hive_results)
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    try:
        from openpyxl import Workbook
        workbook = Workbook(); summary = workbook.active; summary.title = "Podsumowanie"
        summary.append(["Nazwa", "Klucz", "Status", "Plik", "Rozmiar", "SHA-256", "Komunikat"])
        for item in hive_results: summary.append([item.get("label"), item.get("key"), item.get("status"), item.get("path"), item.get("size"), item.get("sha256"), item.get("message")])
        data_sheet = workbook.create_sheet("Dane rejestru"); data_sheet.append(["Gałąź", "Klucz", "Nazwa", "Wartość"])
        for record in records: data_sheet.append([record["branch"], record["key"], record["name"], record["value"]])
        data_sheet.freeze_panes = "A2"; data_sheet.auto_filter.ref = data_sheet.dimensions
        workbook.save(xlsx_path)
    except Exception as exc:
        xlsx_path.write_text(f"Nie udało się utworzyć XLSX: {exc}", encoding="utf-8")
    rows = [("Data", payload["created"]), ("Administrator", "TAK" if payload["admin"] else "NIE"), ("Liczba rekordów", str(len(records)))]
    rows.extend((item.get("label", "Hive"), f"{item.get('status')} | {item.get('path') or item.get('message')}") for item in hive_results)
    reports.write_simple_pdf("EvidLock Light - eksport rejestru Windows", rows, pdf_path)
    report_files = [csv_path, txt_path, xlsx_path, json_path, pdf_path]
    checksum_path = output / f"rejestr_sumy_sha256_{stamp}.txt"
    checksum_lines = []
    for file_path in [*files, *report_files]:
        if file_path.exists(): checksum_lines.append(f"{sha256_file(file_path)}  {file_path.name}")
    checksum_path.write_text("\n".join(checksum_lines), encoding="ascii")
    for file_path in [*files, *report_files, checksum_path]:
        try: winapi.set_readonly(file_path, True)
        except Exception: pass
    return {"csv": str(csv_path), "txt": str(txt_path), "xlsx": str(xlsx_path), "json": str(json_path), "pdf": str(pdf_path), "checksums": str(checksum_path)}


def export_registry(
    selected_hives: list[str] | None = None,
    selected_branches: list[str] | None = None,
    export_hives: bool = True,
    export_data: bool = True,
    output_dir: str | Path | None = None,
    callback=None,
) -> dict:
    if os.name != "nt": raise RuntimeError("Eksport rejestru jest dostępny tylko w Windows.")
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output = Path(output_dir) if output_dir else EXPORTS_DIR / "Registry"
    output = base_output / f"registry_{stamp}"
    output.mkdir(parents=True, exist_ok=True)
    selected_hives = selected_hives or [item["id"] for item in HIVES]
    selected_branches = selected_branches or [item[0] for item in FULL_BRANCHES]
    hive_defs = [item for item in HIVES if item["id"] in selected_hives]
    branch_defs = [item for item in FULL_BRANCHES if item[0] in selected_branches]
    operations = max(1, (len(hive_defs) if export_hives else 0) + (len(branch_defs) if export_data else 0))
    done = 0; hive_results: list[dict] = []; records: list[dict] = []; evidence_files: list[Path] = []
    if callback: callback(1, f"Katalog eksportu: {output}")
    if export_hives:
        for definition in hive_defs:
            target = output / definition["file"]
            if callback: callback(done / operations * 85, f"Eksport hive {definition['label']}...")
            code, message = _run_reg(["save", definition["key"], str(target), "/y"])
            success = code == 0 and target.is_file()
            item = {"id": definition["id"], "label": definition["label"], "key": definition["key"], "status": "OK" if success else "BŁĄD", "path": str(target) if success else "", "size": target.stat().st_size if success else 0, "sha256": sha256_file(target) if success else "", "message": message}
            hive_results.append(item)
            if success: evidence_files.append(target)
            done += 1
    if export_data:
        for branch_id, key in branch_defs:
            target = output / f"{branch_id}.reg"
            if callback: callback(done / operations * 85, f"Eksport danych {key}...")
            code, message = _run_reg(["export", key, str(target), "/y"])
            success = code == 0 and target.is_file()
            if success:
                evidence_files.append(target); records.extend(_parse_reg(target, key))
            else:
                records.append({"branch": key, "key": "", "name": "BŁĄD", "value": message})
            done += 1
    if callback: callback(90, "Generowanie CSV, XLSX, TXT, PDF, JSON i sum SHA-256...")
    report_files = _write_reports(output, hive_results, records, evidence_files)
    result = {"ok": all(item["status"] == "OK" for item in hive_results) if hive_results else True, "output_dir": str(output), "admin": winapi.is_admin(), "hives": hive_results, "record_count": len(records), **report_files}
    if callback: callback(100, "Eksport rejestru zakończony")
    return result
