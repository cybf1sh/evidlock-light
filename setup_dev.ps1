$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) {
    python -m venv (Join-Path $Root ".venv")
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
Write-Host "Srodowisko EvidLock Light jest gotowe."
