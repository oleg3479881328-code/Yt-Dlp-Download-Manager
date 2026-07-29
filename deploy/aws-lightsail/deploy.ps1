param(
    [string]$Profile = "",
    [string]$Region = "us-east-2",
    [string]$AvailabilityZone = "",
    [string]$InstanceName = "olga-review-portal",
    [string]$StaticIpName = "olga-review-portal-ip",
    [string]$DistributionName = "olga-review-portal-web",
    [string]$BlueprintId = "",
    [string]$InstanceBundleId = "nano_3_0",
    [string]$DistributionBundleId = "",
    [string]$RepositoryUrl = "https://github.com/oleg3479881328-code/Yt-Dlp-Download-Manager.git",
    [string]$RepositoryBranch = "feature/review-portal-aws",
    [string]$ReviewToken = "",
    [string]$AdminToken = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

function New-SecureToken {
    param([int]$ByteCount = 24)
    $bytes = New-Object byte[] $ByteCount
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

function Invoke-Aws {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$CommandRegion = ""
    )
    $all = @($Arguments)
    if ($CommandRegion) {
        $all += @("--region", $CommandRegion)
    }
    if ($Profile) {
        $all += @("--profile", $Profile)
    }
    $all += @("--no-cli-pager", "--output", "json")
    $raw = & aws @all 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI failed: aws $($all -join ' ')`n$raw"
    }
    $text = ($raw | Out-String).Trim()
    if (-not $text) {
        return $null
    }
    return $text | ConvertFrom-Json
}

function Test-AwsResource {
    param([string[]]$Arguments, [string]$CommandRegion)
    try {
        [void](Invoke-Aws -Arguments $Arguments -CommandRegion $CommandRegion)
        return $true
    }
    catch {
        return $false
    }
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI v2 was not found. Install and configure it before running this script."
}

if (-not $AvailabilityZone) {
    $AvailabilityZone = "${Region}a"
}
if (-not $ReviewToken) {
    $ReviewToken = New-SecureToken
}
if (-not $AdminToken) {
    $AdminToken = New-SecureToken
}

Write-Host "Checking AWS credentials..."
[void](Invoke-Aws -Arguments @("sts", "get-caller-identity") -CommandRegion $Region)

if (-not $BlueprintId) {
    $blueprints = Invoke-Aws -Arguments @("lightsail", "get-blueprints", "--include-inactive") -CommandRegion $Region
    $selectedBlueprint = $blueprints.blueprints |
        Where-Object { $_.isActive -and $_.platform -eq "LINUX_UNIX" -and $_.blueprintId -match '^ubuntu_' } |
        Sort-Object -Property version -Descending |
        Select-Object -First 1
    if (-not $selectedBlueprint) {
        throw "No active Ubuntu Lightsail blueprint was found in $Region."
    }
    $BlueprintId = $selectedBlueprint.blueprintId
}

if (-not $DistributionBundleId) {
    $distributionBundles = Invoke-Aws -Arguments @("lightsail", "get-distribution-bundles") -CommandRegion "us-east-1"
    $selectedDistributionBundle = $distributionBundles.bundles |
        Where-Object { $_.isActive } |
        Sort-Object -Property price |
        Select-Object -First 1
    if (-not $selectedDistributionBundle) {
        throw "No active Lightsail distribution bundle was found."
    }
    $DistributionBundleId = $selectedDistributionBundle.bundleId
}

if (Test-AwsResource -Arguments @("lightsail", "get-instance", "--instance-name", $InstanceName) -CommandRegion $Region) {
    throw "Lightsail instance '$InstanceName' already exists. Choose another name or remove the existing resource intentionally."
}
if (Test-AwsResource -Arguments @("lightsail", "get-distributions", "--distribution-name", $DistributionName) -CommandRegion "us-east-1") {
    throw "Lightsail distribution '$DistributionName' already exists. Choose another name or remove the existing resource intentionally."
}

$templatePath = Join-Path $PSScriptRoot "bootstrap.sh"
if (-not (Test-Path $templatePath)) {
    throw "Missing bootstrap template: $templatePath"
}
$bootstrap = Get-Content -Raw -Path $templatePath
$bootstrap = $bootstrap.Replace("__REPOSITORY_URL__", $RepositoryUrl)
$bootstrap = $bootstrap.Replace("__REPOSITORY_BRANCH__", $RepositoryBranch)
$bootstrap = $bootstrap.Replace("__REVIEW_TOKEN__", $ReviewToken)
$bootstrap = $bootstrap.Replace("__ADMIN_TOKEN__", $AdminToken)
$tempBootstrap = Join-Path ([System.IO.Path]::GetTempPath()) "video-review-bootstrap-$([guid]::NewGuid().ToString('N')).sh"
[System.IO.File]::WriteAllText($tempBootstrap, $bootstrap, [System.Text.UTF8Encoding]::new($false))

try {
    Write-Host "Creating Lightsail instance '$InstanceName' in $AvailabilityZone..."
    [void](Invoke-Aws -Arguments @(
        "lightsail", "create-instances",
        "--instance-names", $InstanceName,
        "--availability-zone", $AvailabilityZone,
        "--blueprint-id", $BlueprintId,
        "--bundle-id", $InstanceBundleId,
        "--ip-address-type", "dualstack",
        "--user-data", "file://$tempBootstrap",
        "--tags", "key=Application,value=VideoReviewPortal"
    ) -CommandRegion $Region)

    Write-Host "Waiting for instance state RUNNING..."
    $deadline = (Get-Date).AddMinutes(15)
    do {
        Start-Sleep -Seconds 10
        $state = Invoke-Aws -Arguments @("lightsail", "get-instance-state", "--instance-name", $InstanceName) -CommandRegion $Region
        Write-Host "Instance state: $($state.state.name)"
        if ((Get-Date) -gt $deadline) {
            throw "Timed out waiting for Lightsail instance to start."
        }
    } until ($state.state.name -eq "running")

    if (-not (Test-AwsResource -Arguments @("lightsail", "get-static-ip", "--static-ip-name", $StaticIpName) -CommandRegion $Region)) {
        Write-Host "Allocating static IP '$StaticIpName'..."
        [void](Invoke-Aws -Arguments @("lightsail", "allocate-static-ip", "--static-ip-name", $StaticIpName) -CommandRegion $Region)
    }
    Write-Host "Attaching static IP..."
    [void](Invoke-Aws -Arguments @(
        "lightsail", "attach-static-ip",
        "--static-ip-name", $StaticIpName,
        "--instance-name", $InstanceName
    ) -CommandRegion $Region)

    $portInfoPath = Join-Path ([System.IO.Path]::GetTempPath()) "video-review-port-$([guid]::NewGuid().ToString('N')).json"
    [System.IO.File]::WriteAllText(
        $portInfoPath,
        '{"fromPort":80,"toPort":80,"protocol":"tcp","cidrs":["0.0.0.0/0"],"ipv6Cidrs":["::/0"]}',
        [System.Text.UTF8Encoding]::new($false)
    )
    try {
        Write-Host "Opening HTTP origin port 80..."
        [void](Invoke-Aws -Arguments @(
            "lightsail", "open-instance-public-ports",
            "--instance-name", $InstanceName,
            "--port-info", "file://$portInfoPath"
        ) -CommandRegion $Region)
    }
    finally {
        Remove-Item $portInfoPath -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Waiting for application health on the origin..."
    $staticIp = Invoke-Aws -Arguments @("lightsail", "get-static-ip", "--static-ip-name", $StaticIpName) -CommandRegion $Region
    $originHealthUrl = "http://$($staticIp.staticIp.ipAddress)/health"
    $healthDeadline = (Get-Date).AddMinutes(15)
    do {
        try {
            $health = Invoke-RestMethod -Uri $originHealthUrl -TimeoutSec 10
            if ($health.ok) { break }
        }
        catch {
            Write-Host "Portal is still bootstrapping..."
        }
        if ((Get-Date) -gt $healthDeadline) {
            throw "Timed out waiting for $originHealthUrl. Check /var/log/video-review-portal-bootstrap.log on the instance."
        }
        Start-Sleep -Seconds 15
    } while ($true)

    $cacheSettingsPath = Join-Path ([System.IO.Path]::GetTempPath()) "video-review-cache-$([guid]::NewGuid().ToString('N')).json"
    $cacheSettings = @{
        defaultTTL = 0
        minimumTTL = 0
        maximumTTL = 0
        allowedHTTPMethods = "GET,HEAD,OPTIONS,PUT,PATCH,POST,DELETE"
        cachedHTTPMethods = "GET,HEAD"
        forwardedCookies = @{ option = "none"; cookiesAllowList = @() }
        forwardedHeaders = @{ option = "none"; headersAllowList = @() }
        forwardedQueryStrings = @{ option = $true; queryStringsAllowList = @() }
    } | ConvertTo-Json -Depth 5 -Compress
    [System.IO.File]::WriteAllText($cacheSettingsPath, $cacheSettings, [System.Text.UTF8Encoding]::new($false))

    try {
        Write-Host "Creating HTTPS Lightsail distribution '$DistributionName'..."
        [void](Invoke-Aws -Arguments @(
            "lightsail", "create-distribution",
            "--distribution-name", $DistributionName,
            "--origin", "name=$InstanceName,regionName=$Region,protocolPolicy=http-only",
            "--default-cache-behavior", "behavior=cache",
            "--cache-behavior-settings", "file://$cacheSettingsPath",
            "--bundle-id", $DistributionBundleId,
            "--ip-address-type", "dualstack",
            "--viewer-minimum-tls-protocol-version", "TLSv1.2_2021",
            "--tags", "key=Application,value=VideoReviewPortal"
        ) -CommandRegion "us-east-1")
    }
    finally {
        Remove-Item $cacheSettingsPath -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Waiting for HTTPS distribution domain..."
    $distributionDeadline = (Get-Date).AddMinutes(20)
    do {
        Start-Sleep -Seconds 15
        $distributionResponse = Invoke-Aws -Arguments @(
            "lightsail", "get-distributions",
            "--distribution-name", $DistributionName
        ) -CommandRegion "us-east-1"
        $distribution = $distributionResponse.distributions | Select-Object -First 1
        Write-Host "Distribution status: $($distribution.status)"
        if ((Get-Date) -gt $distributionDeadline) {
            throw "Timed out waiting for the Lightsail distribution."
        }
    } until ($distribution.domainName -and $distribution.status -notin @("InProgress", "Unknown"))

    $baseUrl = "https://$($distribution.domainName)"
    $clientUrl = "$baseUrl/?token=$([uri]::EscapeDataString($ReviewToken))"
    $adminUrl = "$baseUrl/admin?token=$([uri]::EscapeDataString($AdminToken))"
    $output = [ordered]@{
        created_at = (Get-Date).ToUniversalTime().ToString("o")
        region = $Region
        instance_name = $InstanceName
        static_ip_name = $StaticIpName
        static_ip = $staticIp.staticIp.ipAddress
        distribution_name = $DistributionName
        distribution_domain = $distribution.domainName
        review_token = $ReviewToken
        admin_token = $AdminToken
        client_url = $clientUrl
        admin_url = $adminUrl
    }
    $outputPath = Join-Path $PSScriptRoot "deployment-output.json"
    $output | ConvertTo-Json -Depth 4 | Set-Content -Path $outputPath -Encoding UTF8

    Write-Host ""
    Write-Host "AWS deployment created."
    Write-Host "Client link: $clientUrl"
    Write-Host "Admin link:  $adminUrl"
    Write-Host "Saved locally: $outputPath"
    Write-Warning "deployment-output.json contains access tokens. Do not commit or share the admin link."
}
finally {
    Remove-Item $tempBootstrap -Force -ErrorAction SilentlyContinue
}
