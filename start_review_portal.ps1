param(
    [string]$MediaDir = "",
    [string]$DataDir = "",
    [string]$Token = "",
    [string]$AdminToken = "",
    [int]$Port = 8770,
    [switch]$Lan,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $MediaDir) {
    $MediaDir = Join-Path $PSScriptRoot "review_portal_media"
}
if (-not $DataDir) {
    $DataDir = Join-Path $PSScriptRoot "data\review_portal"
}
if (-not $AdminToken) {
    $AdminToken = $Token
}

New-Item -ItemType Directory -Force -Path $MediaDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

$env:REVIEW_PORTAL_MEDIA_DIR = (Resolve-Path $MediaDir).Path
$env:REVIEW_PORTAL_DATA_DIR = (Resolve-Path $DataDir).Path
$env:REVIEW_PORTAL_TOKEN = $Token
$env:REVIEW_PORTAL_ADMIN_TOKEN = $AdminToken

$bindHost = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }
$clientUrl = "http://127.0.0.1:$Port/"
if ($Token) {
    $clientUrl += "?token=$([System.Uri]::EscapeDataString($Token))"
}

Write-Host "VIDEO MIX Review Portal"
Write-Host "Media: $env:REVIEW_PORTAL_MEDIA_DIR"
Write-Host "Data:  $env:REVIEW_PORTAL_DATA_DIR"
Write-Host "Client: $clientUrl"
Write-Host "Admin:  http://127.0.0.1:$Port/admin"
if ($Lan) {
    Write-Warning "LAN mode is enabled. Use access tokens and expose this port only on a trusted network."
}

if (-not $NoBrowser) {
    Start-Process $clientUrl
}

python -m uvicorn review_portal.app:app --host $bindHost --port $Port
