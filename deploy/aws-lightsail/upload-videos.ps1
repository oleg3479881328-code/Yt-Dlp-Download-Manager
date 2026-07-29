param(
    [Parameter(Mandatory = $true)][string]$SourceDir,
    [string]$DeploymentOutput = "",
    [string]$Profile = "",
    [string]$Region = "us-east-2",
    [string]$InstanceName = "olga-review-portal",
    [string]$KeyFile = "",
    [switch]$KeepExisting
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

$resolvedSource = (Resolve-Path $SourceDir).Path
if (-not (Test-Path $resolvedSource -PathType Container)) {
    throw "Source directory does not exist: $resolvedSource"
}
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI v2 was not found."
}
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw "OpenSSH ssh was not found. Enable the Windows OpenSSH Client feature."
}
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    throw "OpenSSH scp was not found. Enable the Windows OpenSSH Client feature."
}
if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
    throw "tar was not found. Windows 11 normally includes bsdtar."
}

if (-not $DeploymentOutput) {
    $DeploymentOutput = Join-Path $PSScriptRoot "deployment-output.json"
}
if (Test-Path $DeploymentOutput) {
    $deployment = Get-Content -Raw $DeploymentOutput | ConvertFrom-Json
    if ($deployment.region) { $Region = [string]$deployment.region }
    if ($deployment.instance_name) { $InstanceName = [string]$deployment.instance_name }
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

$archive = Join-Path ([System.IO.Path]::GetTempPath()) "video-review-media-$([guid]::NewGuid().ToString('N')).tar.gz"
$remoteArchive = "/tmp/video-review-media.tar.gz"
$sshTarget = "$sshUser@$hostAddress"
$sshOptions = @("-i", $KeyFile, "-o", "StrictHostKeyChecking=accept-new")

try {
    Write-Host "Packing videos from $resolvedSource..."
    & tar -czf $archive -C $resolvedSource .
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create media archive."
    }

    Write-Host "Uploading media archive to $sshTarget..."
    & scp @sshOptions $archive "${sshTarget}:$remoteArchive"
    if ($LASTEXITCODE -ne 0) {
        throw "SCP upload failed."
    }

    $clearCommand = if ($KeepExisting) { "" } else { "sudo find /srv/video-review-portal/media -mindepth 1 -maxdepth 1 -exec rm -rf {} + &&" }
    $remoteCommand = "$clearCommand sudo tar -xzf $remoteArchive -C /srv/video-review-portal/media && sudo chown -R video-review:video-review /srv/video-review-portal/media && rm -f $remoteArchive && curl --fail --silent http://127.0.0.1/health"
    Write-Host "Installing uploaded videos..."
    & ssh @sshOptions $sshTarget $remoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Remote media installation or health check failed."
    }

    Write-Host "Videos uploaded. The portal rescans the media directory automatically."
}
finally {
    Remove-Item $archive -Force -ErrorAction SilentlyContinue
    if ($createdTemporaryKey) {
        Remove-Item $KeyFile -Force -ErrorAction SilentlyContinue
    }
}
