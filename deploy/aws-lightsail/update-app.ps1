param(
    [string]$DeploymentOutput = "",
    [string]$Profile = "",
    [string]$Region = "us-east-2",
    [string]$InstanceName = "olga-review-portal",
    [string]$RepositoryBranch = "feature/review-portal-aws",
    [string]$KeyFile = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

function Invoke-Aws {
    param([string[]]$Arguments)
    $all = @($Arguments) + @("--region", $Region)
    if ($Profile) {
        $all += @("--profile", $Profile)
    }
    $all += @("--no-cli-pager", "--output", "json")
    $raw = & aws @all 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI failed: aws $($all -join ' ')`n$raw"
    }
    return (($raw | Out-String).Trim() | ConvertFrom-Json)
}

if (-not $DeploymentOutput) {
    $DeploymentOutput = Join-Path $PSScriptRoot "deployment-output.json"
}
if (Test-Path $DeploymentOutput) {
    $deployment = Get-Content -Raw $DeploymentOutput | ConvertFrom-Json
    if ($deployment.region) { $Region = [string]$deployment.region }
    if ($deployment.instance_name) { $InstanceName = [string]$deployment.instance_name }
}

foreach ($command in @("aws", "ssh")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command was not found: $command"
    }
}

$instanceResponse = Invoke-Aws -Arguments @("lightsail", "get-instance", "--instance-name", $InstanceName)
$instance = $instanceResponse.instance
$hostAddress = [string]$instance.publicIpAddress
$sshUser = [string]$instance.username
if (-not $hostAddress -or -not $sshUser) {
    throw "Could not resolve the Lightsail instance SSH address."
}

$createdTemporaryKey = $false
if (-not $KeyFile) {
    $keyResponse = Invoke-Aws -Arguments @("lightsail", "download-default-key-pair")
    $keyBytes = [Convert]::FromBase64String([string]$keyResponse.privateKeyBase64)
    $KeyFile = Join-Path ([System.IO.Path]::GetTempPath()) "lightsail-$Region-$([guid]::NewGuid().ToString('N')).pem"
    [System.IO.File]::WriteAllBytes($KeyFile, $keyBytes)
    $createdTemporaryKey = $true
    if ($IsWindows) {
        & icacls $KeyFile /inheritance:r /grant:r "$env:USERNAME`:R" | Out-Null
    }
}
else {
    $KeyFile = (Resolve-Path $KeyFile).Path
}

$sshTarget = "$sshUser@$hostAddress"
$sshOptions = @("-i", $KeyFile, "-o", "StrictHostKeyChecking=accept-new")
$remoteCommand = @"
set -euo pipefail
cd /opt/video-review-portal
sudo git fetch origin '$RepositoryBranch'
sudo git checkout '$RepositoryBranch'
sudo git reset --hard 'origin/$RepositoryBranch'
sudo /opt/video-review-portal/.venv/bin/pip install -r /opt/video-review-portal/review_portal/requirements.txt
sudo systemctl restart video-review-portal
for attempt in `$(seq 1 30); do
  if curl --fail --silent http://127.0.0.1/health >/dev/null; then
    echo 'Portal update is healthy.'
    exit 0
  fi
  sleep 2
done
sudo systemctl status video-review-portal --no-pager
exit 1
"@

try {
    Write-Host "Updating $InstanceName from branch $RepositoryBranch..."
    & ssh @sshOptions $sshTarget $remoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Remote application update failed."
    }
    Write-Host "Application update completed without changing videos, comments, or voice notes."
}
finally {
    if ($createdTemporaryKey) {
        Remove-Item $KeyFile -Force -ErrorAction SilentlyContinue
    }
}
