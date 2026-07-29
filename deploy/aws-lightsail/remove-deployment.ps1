param(
    [string]$DeploymentOutput = "",
    [string]$Profile = "",
    [string]$Region = "us-east-2",
    [string]$InstanceName = "olga-review-portal",
    [string]$StaticIpName = "olga-review-portal-ip",
    [string]$DistributionName = "olga-review-portal-web",
    [switch]$ConfirmRemoval
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

function Invoke-Aws {
    param([Parameter(Mandatory = $true)][string[]]$Arguments, [string]$CommandRegion)
    $all = @($Arguments) + @("--region", $CommandRegion)
    if ($Profile) {
        $all += @("--profile", $Profile)
    }
    $all += @("--no-cli-pager", "--output", "json")
    $raw = & aws @all 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI failed: aws $($all -join ' ')`n$raw"
    }
    $text = ($raw | Out-String).Trim()
    return $(if ($text) { $text | ConvertFrom-Json } else { $null })
}

if (-not $ConfirmRemoval) {
    throw "This action deletes the AWS review portal and its instance disk. Re-run with -ConfirmRemoval after preserving any required videos, comments, and voice notes."
}
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI v2 was not found."
}
if (-not $DeploymentOutput) {
    $DeploymentOutput = Join-Path $PSScriptRoot "deployment-output.json"
}
if (Test-Path $DeploymentOutput) {
    $deployment = Get-Content -Raw $DeploymentOutput | ConvertFrom-Json
    if ($deployment.region) { $Region = [string]$deployment.region }
    if ($deployment.instance_name) { $InstanceName = [string]$deployment.instance_name }
    if ($deployment.static_ip_name) { $StaticIpName = [string]$deployment.static_ip_name }
    if ($deployment.distribution_name) { $DistributionName = [string]$deployment.distribution_name }
}

[void](Invoke-Aws -Arguments @("sts", "get-caller-identity") -CommandRegion $Region)

Write-Host "Deleting Lightsail distribution '$DistributionName'..."
$distributionResponse = Invoke-Aws -Arguments @("lightsail", "get-distributions", "--distribution-name", $DistributionName) -CommandRegion "us-east-1"
if (@($distributionResponse.distributions).Count -gt 0) {
    [void](Invoke-Aws -Arguments @("lightsail", "delete-distribution", "--distribution-name", $DistributionName) -CommandRegion "us-east-1")
    $deadline = (Get-Date).AddMinutes(20)
    do {
        Start-Sleep -Seconds 15
        $remaining = Invoke-Aws -Arguments @("lightsail", "get-distributions", "--distribution-name", $DistributionName) -CommandRegion "us-east-1"
        if ((Get-Date) -gt $deadline) {
            throw "Timed out waiting for the distribution to be deleted."
        }
    } while (@($remaining.distributions).Count -gt 0)
}
else {
    Write-Host "Distribution was already absent."
}

Write-Host "Deleting Lightsail instance '$InstanceName'..."
try {
    [void](Invoke-Aws -Arguments @("lightsail", "delete-instance", "--instance-name", $InstanceName) -CommandRegion $Region)
}
catch {
    Write-Warning "Instance deletion returned an error. It may already be absent: $($_.Exception.Message)"
}

Write-Host "Releasing static IP '$StaticIpName'..."
try {
    [void](Invoke-Aws -Arguments @("lightsail", "release-static-ip", "--static-ip-name", $StaticIpName) -CommandRegion $Region)
}
catch {
    Write-Warning "Static IP release returned an error. It may already be absent: $($_.Exception.Message)"
}

Remove-Item $DeploymentOutput -Force -ErrorAction SilentlyContinue
Write-Host "AWS review portal removal request completed. Verify the Lightsail console and Billing dashboard."
