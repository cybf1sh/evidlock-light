param(
    [string]$DestinationRoot = "$env:USERPROFILE\Google Drive\EvidLockLight_Backup",
    [string]$ChangeName = "backup EvidLock Light"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Target = Join-Path $DestinationRoot "evidlock_light_$Stamp"

New-Item -ItemType Directory -Force -Path $Target | Out-Null

$Excluded = @(".git", ".venv", "build", "dist", "releases", "__pycache__", "logi", "raporty", "eksport")
Get-ChildItem -LiteralPath $Root -Force | Where-Object {
    $Excluded -notcontains $_.Name
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Target -Recurse -Force
}

$meta = [ordered]@{
    name = $ChangeName
    source = $Root
    created = (Get-Date).ToString("s")
    target = $Target
}
$meta | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $Target "backup_meta.json")

Write-Host "Kopia EvidLock Light gotowa: $Target"
