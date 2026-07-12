param(
    [string]$DestinationRoot = "",
    [string]$ChangeName = "backup EvidLock Light",
    [string]$SourceRoot = "",
    [switch]$AutoDetect,
    [switch]$DetectOnly,
    [switch]$ForceFull
)

$ErrorActionPreference = "Stop"
$Root = if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    [IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path))
} else {
    [IO.Path]::GetFullPath($SourceRoot)
}
$Root = $Root.TrimEnd('\')
$destinationDetected = $false

function Find-GoogleDriveRoot {
    $candidates = @()
    # Budujemy polską nazwę kodem znaku, aby działało również w Windows PowerShell 5.1.
    $folderNames = @("My Drive", ("M" + [char]0x00F3 + "j dysk"))

    # Google Drive for desktop najczęściej montuje się jako osobny dysk.
    foreach ($drive in @(Get-PSDrive -PSProvider FileSystem)) {
        $driveRoot = $drive.Root
        foreach ($folderName in $folderNames) {
            $candidate = Join-Path $driveRoot $folderName
            if (Test-Path -LiteralPath $candidate -PathType Container) {
                $candidates += $candidate
            }
        }
        if (Test-Path -LiteralPath (Join-Path $driveRoot ".shortcut-targets-by-id") -PathType Container) {
            $candidates += $driveRoot
        }
    }

    # Etykieta woluminu jest dostępna dla części instalacji DriveFS.
    try {
        Get-Volume | Where-Object {
            $_.DriveLetter -and $_.FileSystemLabel -match "Google\s*Drive|DriveFS"
        } | ForEach-Object {
            $candidates += "$($_.DriveLetter):\"
        }
    }
    catch {
        # Brak Get-Volume nie blokuje wyszukiwania po ścieżkach.
    }

    $profileCandidates = @(
        (Join-Path $env:USERPROFILE "Google Drive"),
        (Join-Path $env:USERPROFILE "GoogleDrive"),
        (Join-Path $env:USERPROFILE "Google Drive\My Drive"),
        (Join-Path $env:USERPROFILE ("Google Drive\M" + [char]0x00F3 + "j dysk"))
    )
    $candidates += $profileCandidates

    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Container)) {
            continue
        }
        $full = [IO.Path]::GetFullPath($candidate).TrimEnd('\')
        foreach ($folderName in $folderNames) {
            $nested = Join-Path $full $folderName
            if (Test-Path -LiteralPath $nested -PathType Container) {
                return [IO.Path]::GetFullPath($nested).TrimEnd('\')
            }
        }
        return $full
    }
    return $null
}

if ($AutoDetect -or [string]::IsNullOrWhiteSpace($DestinationRoot)) {
    $googleDriveRoot = Find-GoogleDriveRoot
    if ([string]::IsNullOrWhiteSpace($googleDriveRoot)) {
        throw "Nie wykryto dysku Google Drive. Uruchom Google Drive dla komputerów albo podaj -DestinationRoot, np. G:\My Drive\EvidLockLight_Backup."
    }
    $DestinationRoot = Join-Path $googleDriveRoot "EvidLockLight_Backup"
    $destinationDetected = $true
}

$DestinationRoot = [IO.Path]::GetFullPath($DestinationRoot).TrimEnd('\')

if ($DetectOnly) {
    Write-Host "Wykryto Google Drive: $DestinationRoot"
    exit 0
}

$StatePath = Join-Path $DestinationRoot ".evidlock_light_backup_state.json"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
$Target = Join-Path $DestinationRoot "evidlock_light_$Stamp"

if ($DestinationRoot -eq $Root) {
    throw "Katalog docelowy kopii nie może być katalogiem projektu."
}
if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "Nie znaleziono katalogu źródłowego: $Root"
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null

if ($destinationDetected) {
    Write-Host "Wykryto Google Drive: $DestinationRoot"
}

function Copy-BackupItem {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        Copy-Item -LiteralPath $Path -Destination $Target -Recurse -Force
    }
}

function Is-UnderDestination {
    param([Parameter(Mandatory = $true)][string]$Path)

    $fullPath = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    return $fullPath.Equals($DestinationRoot, [StringComparison]::OrdinalIgnoreCase) -or
        $fullPath.StartsWith("$DestinationRoot\", [StringComparison]::OrdinalIgnoreCase)
}

$firstBackup = $ForceFull -or -not (Test-Path -LiteralPath $StatePath)
$mode = if ($firstBackup) { "FULL" } else { "CODE+VERSION" }

if ($firstBackup) {
    # Pierwszy snapshot jest pełną kopią projektu, włącznie z raportami,
    # eksportami, buildami i aktualnymi artefaktami wydania.
    Get-ChildItem -LiteralPath $Root -Force | Where-Object {
        -not (Is-UnderDestination $_.FullName)
    } | ForEach-Object {
        Copy-BackupItem $_.FullName
    }
} else {
    # Kolejne snapshoty zawierają tylko kod, dokumentację, konfigurację,
    # skrypty oraz artefakty wersji. Dane robocze pozostają w pierwszej kopii.
    @("evidlock_light", "docs", "releases") | ForEach-Object {
        Copy-BackupItem (Join-Path $Root $_)
    }

    $codeExtensions = @(
        ".py", ".ps1", ".cmd", ".bat", ".md", ".txt", ".json", ".toml",
        ".ini", ".cfg", ".yml", ".yaml", ".sha256"
    )
    Get-ChildItem -LiteralPath $Root -File -Force | Where-Object {
        $codeExtensions -contains $_.Extension.ToLowerInvariant()
    } | ForEach-Object {
        Copy-BackupItem $_.FullName
    }

    # EXE i kopie EXE są artefaktami wersji, więc są zachowywane w trybie lekkim.
    Get-ChildItem -LiteralPath $Root -File -Force -Filter "EvidLockLight*.exe*" | ForEach-Object {
        Copy-BackupItem $_.FullName
    }
}

$meta = [ordered]@{
    name = $ChangeName
    mode = $mode
    source = $Root
    destination_root = $DestinationRoot
    destination_detected = $destinationDetected
    created = (Get-Date).ToString("s")
    target = $Target
    first_full_copy = $firstBackup
    note = if ($firstBackup) {
        "Pełny snapshot projektu 1:1."
    } else {
        "Kopia kodu, konfiguracji, dokumentacji i artefaktów wersji."
    }
}
$meta | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $Target "backup_meta.json")

$state = [ordered]@{
    schema = 1
    initialized = $true
    first_full_copy = if ($firstBackup -and -not (Test-Path -LiteralPath $StatePath)) { $Target } else {
        try { (Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json).first_full_copy } catch { $Target }
    }
    last_backup = $Target
    last_mode = $mode
    source = $Root
}
$state | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $StatePath

Write-Host "Kopia EvidLock Light gotowa ($mode): $Target"
if ($firstBackup) {
    Write-Host "Pierwsze uruchomienie: pełna kopia 1:1 projektu."
} else {
    Write-Host "Kolejne uruchomienie: zapisano kod i artefakty wersji."
}
