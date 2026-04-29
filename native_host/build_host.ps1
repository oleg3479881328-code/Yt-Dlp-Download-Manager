$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LegacyOneFileExe = Join-Path $ProjectRoot "dist\ytdlp_host.exe"
$DistRoot = Join-Path $ProjectRoot "dist_v2"

if (Test-Path $LegacyOneFileExe) {
    Rename-Item -LiteralPath $LegacyOneFileExe -NewName "ytdlp_host.onefile.bak.exe" -Force
}

& $Python -m pip install -r requirements.txt
& $Python -m pip install pyinstaller
& $Python -m PyInstaller --noconfirm --workpath build\ytdlp_host_onedir --distpath $DistRoot --name ytdlp_host native_host\ytdlp_host.py

Write-Output "Built host executable at dist_v2\ytdlp_host\ytdlp_host.exe"
