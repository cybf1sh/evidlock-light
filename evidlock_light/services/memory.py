"""WinPmem, Volatility 3 i operacje managera pamięci Light."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from ..config import RUNTIME_DIR
from .hashing import sha256_file
from .. import winapi


TOOLS_DIR = RUNTIME_DIR / "tools" / "memory"
WINPMEM_RELEASES = "https://github.com/Velocidex/WinPmem/releases/latest"


def _first_file(candidates) -> str:
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return ""


def dependency_status(repo_root: str | Path | None = None) -> dict:
    root = Path(repo_root or RUNTIME_DIR)
    appdata = Path(os.environ.get("APPDATA", Path.home()))
    winpmem = _first_file([
        *TOOLS_DIR.glob("winpmem/winpmem*_x64.exe"),
        *TOOLS_DIR.glob("winpmem/*.exe"),
        *root.glob("tools/memory/src/WinPmem/src/binaries/winpmem*_x64*.exe"),
        shutil.which("winpmem_mini_x64.exe"),
    ])
    volatility = _first_file([
        *TOOLS_DIR.glob("volatility3/vol.py"),
        *root.glob("tools/memory/src/volatility3/vol.py"),
        shutil.which("vol.exe"),
        shutil.which("vol"),
        *appdata.glob("Python/Python*/Scripts/vol.exe"),
    ])
    python = shutil.which("py") or shutil.which("python") or ""
    return {
        "winpmem_present": bool(winpmem),
        "winpmem_path": winpmem,
        "volatility_present": bool(volatility),
        "volatility_path": volatility,
        "python": python,
        "volatility_install_available": bool(python),
        "winpmem_download_url": WINPMEM_RELEASES,
    }


def install_volatility() -> dict:
    status = dependency_status()
    python = status["python"]
    if not python:
        raise RuntimeError("Nie znaleziono Pythona ani launchera py. Zainstaluj Python 3 przed Volatility 3.")
    command = [python, "-m", "pip", "install", "--user", "volatility3"]
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(command, creationflags=flags)
    return {"started": True, "command": command, "message": "Uruchomiono instalację Volatility 3. Po zakończeniu odśwież status."}


def open_winpmem_download() -> dict:
    webbrowser.open(WINPMEM_RELEASES)
    return {"opened": True, "url": WINPMEM_RELEASES, "message": "Pobierz winpmem_mini_x64.exe, a następnie użyj przycisku Wskaż WinPmem."}


def import_winpmem(source: str | Path) -> Path:
    src = Path(source).resolve()
    if not src.is_file() or src.suffix.lower() != ".exe" or "winpmem" not in src.name.lower():
        raise ValueError("Wskaż plik wykonywalny WinPmem, np. winpmem_mini_x64.exe.")
    destination = TOOLS_DIR / "winpmem" / src.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, destination)
    return destination


def _volatility_command(image: str | Path, plugin: str) -> list[str]:
    status = dependency_status()
    executable = status["volatility_path"]
    if not executable:
        raise RuntimeError("Brak Volatility 3. Użyj przycisku Instaluj Volatility 3.")
    if executable.lower().endswith(".py"):
        python = status["python"] or sys.executable
        return [python, executable, "-f", str(image), plugin]
    return [executable, "-f", str(image), plugin]


def run_volatility(image: str | Path, plugin: str, repo_root: str | Path | None = None) -> dict:
    target = Path(image).resolve()
    if not target.is_file():
        raise FileNotFoundError(str(target))
    command = _volatility_command(target, plugin)
    completed = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    return {"returncode": completed.returncode, "command": command, "stdout": completed.stdout, "stderr": completed.stderr}


def compare_dumps(first: str | Path, second: str | Path) -> dict:
    a = Path(first).resolve()
    b = Path(second).resolve()
    if not a.is_file() or not b.is_file():
        raise FileNotFoundError("Wskaż dwa istniejące zrzuty pamięci.")
    hash_a = sha256_file(a)
    hash_b = sha256_file(b)
    return {"file_a": str(a), "sha256_a": hash_a, "file_b": str(b), "sha256_b": hash_b, "identical": hash_a == hash_b}


def acquire_memory(output: str | Path) -> dict:
    status = dependency_status()
    if not status["winpmem_present"]:
        raise RuntimeError("Brak WinPmem. Pobierz i wskaż winpmem_mini_x64.exe.")
    if not winapi.is_admin():
        raise PermissionError("Zrzut pamięci przez WinPmem wymaga trybu administratora.")
    target = Path(output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [status["winpmem_path"], str(target)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=86400)
    result = {"returncode": completed.returncode, "output": str(target), "stdout": completed.stdout, "stderr": completed.stderr}
    if completed.returncode == 0 and target.is_file():
        result["sha256"] = sha256_file(target)
        result["size"] = target.stat().st_size
    return result
