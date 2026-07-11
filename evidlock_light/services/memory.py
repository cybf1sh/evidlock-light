"""Kontrola WinPmem i Volatility 3 dla wersji Light."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def dependency_status(repo_root: str | Path | None = None) -> dict:
    root = Path(repo_root or Path.cwd())
    winpmem_candidates = list(root.glob("tools/memory/src/WinPmem/src/binaries/winpmem_x64.sys"))
    volatility_candidates = list(root.glob("tools/memory/src/volatility3/vol.py"))
    return {
        "winpmem_present": bool(winpmem_candidates),
        "winpmem_path": str(winpmem_candidates[0]) if winpmem_candidates else "",
        "volatility_present": bool(volatility_candidates),
        "volatility_path": str(volatility_candidates[0]) if volatility_candidates else "",
        "python": shutil.which("python") or "",
    }


def run_volatility(image: str | Path, plugin: str, repo_root: str | Path | None = None) -> dict:
    status = dependency_status(repo_root)
    if not status["volatility_present"]:
        raise RuntimeError("Nie znaleziono Volatility 3 w tools/memory.")
    command = [status["python"] or "python", status["volatility_path"], "-f", str(image), plugin]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=300)
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
