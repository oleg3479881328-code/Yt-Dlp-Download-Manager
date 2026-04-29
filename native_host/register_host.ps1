param(
    [Parameter(Mandatory = $true)]
    [string]$ExtensionId
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$HostExe = Join-Path $ProjectRoot "dist_v2\ytdlp_host\ytdlp_host.exe"
$ManifestPath = Join-Path $PSScriptRoot "com.oleg.ytdlp.json"

if (-not (Test-Path $HostExe)) {
    throw "Host executable not found. Run native_host\build_host.ps1 first."
}

$manifest = @{
    name = "com.oleg.ytdlp"
    description = "yt-dlp native messaging host"
    path = $HostExe
    type = "stdio"
    allowed_origins = @(
        "chrome-extension://$ExtensionId/"
    )
} | ConvertTo-Json -Depth 5

Set-Content -Path $ManifestPath -Value $manifest -Encoding UTF8

$registryPath = "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.oleg.ytdlp"
reg add $registryPath /ve /t REG_SZ /d $ManifestPath /f | Out-Null

Write-Output "Native host manifest written to $ManifestPath"
Write-Output "Registered host for extension id: $ExtensionId"
