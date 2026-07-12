param(
    [switch]$Clean,
    [switch]$PauseOnExit
)

try {
    $ErrorActionPreference = "Stop"
    $Root = Split-Path -Parent $MyInvocation.MyCommand.Path
    $Dist = Join-Path $Root "dist"
    $Build = Join-Path $Root "build"
    $ReleaseDir = Join-Path $Root "releases"
    $RootExe = Join-Path $Root "EvidLockLight.exe"
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $PreviousBackup = $null

if (Get-Process -Name "EvidLockLight" -ErrorAction SilentlyContinue) {
    throw "EvidLockLight jest uruchomiony. Zamknij aplikacje przed rozpoczeciem buildu."
}

# Jak w EvidLockV2: przed podmiana oryginalu zachowujemy poprzedni build.
if (Test-Path -LiteralPath $RootExe) {
    $PreviousBackup = Join-Path $Root "EvidLockLight_backup_$Stamp.exe"
    Copy-Item -LiteralPath $RootExe -Destination $PreviousBackup -Force
    Write-Host "Kopia poprzedniej wersji: $PreviousBackup"
}

if ($Clean) {
    Remove-Item -LiteralPath $Dist -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Build -Recurse -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $Dist | Out-Null
New-Item -ItemType Directory -Force -Path $Build | Out-Null

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Brak samodzielnego srodowiska .venv. Uruchom najpierw .\setup_dev.ps1."
}

& $Python -c "import customtkinter, tkinterdnd2, openpyxl, PyInstaller, pypdf, cryptography, pyzipper, py7zr" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Brak zaleznosci buildu. Zainstaluj customtkinter i pyinstaller w .venv."
}

Write-Host "Budowanie EvidLock Light GUI..."
& $Python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --collect-all tkinterdnd2 `
    --add-data "$Root\evidlock_light\assets;evidlock_light\assets" `
    --name EvidLockLight `
    --distpath $Dist `
    --workpath (Join-Path $Build "gui") `
    --specpath $Build `
    (Join-Path $Root "run_gui.py")

if ($LASTEXITCODE -ne 0) {
    throw "Build EvidLock Light nie powiodl sie (kod: $LASTEXITCODE)."
}

$Exe = Join-Path $Dist "EvidLockLight.exe"
if (-not (Test-Path -LiteralPath $Exe)) {
    throw "PyInstaller zakonczyl prace bez pliku EvidLockLight.exe."
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
Copy-Item -LiteralPath $Exe -Destination $RootExe -Force
$ReleaseExe = Join-Path $ReleaseDir "EvidLockLight_$Stamp.exe"
Copy-Item -LiteralPath $Exe -Destination $ReleaseExe -Force

@($Exe, $RootExe, $ReleaseExe, $PreviousBackup) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | ForEach-Object {
    $file = Get-Item -LiteralPath $_
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName
    "$($hash.Hash)  $($file.Name)" | Set-Content -Encoding ASCII -LiteralPath "$($file.FullName).sha256"
}

Write-Host "Gotowe. Artefakty: $Dist"
Write-Host "Oryginal: $RootExe"
Write-Host "Kopia release: $ReleaseExe"
if ($PreviousBackup) {
    Write-Host "Backup poprzedniej wersji: $PreviousBackup"
}

    if ($PauseOnExit) {
        Read-Host "Build zakonczony. Nacisnij Enter, aby zamknac okno"
    }
}
catch {
    $message = "Build EvidLock Light nie powiodl sie." + [Environment]::NewLine + [Environment]::NewLine + $_.Exception.Message
    Write-Host $message -ForegroundColor Red
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($message, "EvidLock Light - build", "OK", "Error") | Out-Null
    }
    catch {
        # In a non-GUI environment the PowerShell text remains available.
    }
    if ($PauseOnExit) {
        Read-Host "Nacisnij Enter, aby zamknac okno"
    }
    exit 1
}
