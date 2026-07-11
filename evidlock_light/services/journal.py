"""Dziennik operacji EvidLock Light.

Dziennik jest wspólny dla GUI i konsoli wbudowanej. Zapis jest prosty,
czytelny i łatwy do eksportu: JSONL jako źródło oraz TXT/JSON jako raport.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from ..config import LOGS_DIR, ensure_runtime_dirs


JOURNAL_PATH = LOGS_DIR / "evidlock_light_journal.jsonl"


def log_event(level: str, module: str, message: str, details: dict | None = None) -> dict:
    ensure_runtime_dirs()
    entry = {
        "time": dt.datetime.now().isoformat(timespec="seconds"),
        "level": level.upper(),
        "module": module,
        "message": message,
        "details": details or {},
    }
    with JOURNAL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_events(limit: int | None = 500) -> list[dict]:
    if not JOURNAL_PATH.exists():
        return []
    lines = JOURNAL_PATH.read_text(encoding="utf-8").splitlines()
    if limit:
        lines = lines[-limit:]
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def export_journal(output_dir: str | Path | None = None) -> dict:
    ensure_runtime_dirs()
    out = Path(output_dir or LOGS_DIR / "exports")
    out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    events = read_events(limit=None)
    json_path = out / f"dziennik_evidlock_light_{stamp}.json"
    txt_path = out / f"dziennik_evidlock_light_{stamp}.txt"
    json_path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = []
    for event in events:
        lines.append(f"[{event['time']}] {event['level']} | {event['module']} | {event['message']}")
        if event.get("details"):
            lines.append(json.dumps(event["details"], ensure_ascii=False))
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    return {"events": len(events), "json": str(json_path), "txt": str(txt_path)}
