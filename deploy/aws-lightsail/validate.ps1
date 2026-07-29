param(
    [string]$DeploymentOutput = "",
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $DeploymentOutput) {
    $DeploymentOutput = Join-Path $PSScriptRoot "deployment-output.json"
}
if (-not (Test-Path $DeploymentOutput)) {
    throw "Deployment output was not found: $DeploymentOutput"
}

$deployment = Get-Content -Raw $DeploymentOutput | ConvertFrom-Json
$clientUrl = [string]$deployment.client_url
$adminUrl = [string]$deployment.admin_url
if (-not $clientUrl -or -not $adminUrl) {
    throw "deployment-output.json does not contain client_url and admin_url."
}

Write-Host "Checking client page..."
$client = Invoke-WebRequest -Uri $clientUrl -TimeoutSec $TimeoutSeconds -UseBasicParsing
if ($client.StatusCode -ne 200 -or $client.Content -notmatch "Видео на согласование") {
    throw "Client page validation failed."
}

Write-Host "Checking admin page..."
$admin = Invoke-WebRequest -Uri $adminUrl -TimeoutSec $TimeoutSeconds -UseBasicParsing
if ($admin.StatusCode -ne 200 -or $admin.Content -notmatch "Замечания") {
    throw "Admin page validation failed."
}

$healthUrl = "https://$($deployment.distribution_domain)/health"
Write-Host "Checking health endpoint..."
$health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec $TimeoutSeconds
if (-not $health.ok) {
    throw "Health endpoint returned an unhealthy result."
}

Write-Host "Automated HTTP validation passed."
Write-Host "Manual phone gate remains: play a real video, pin a timecode, record a microphone note, submit it, and play it from the admin page."
