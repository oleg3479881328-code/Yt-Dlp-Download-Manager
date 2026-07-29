param(
    [string]$Profile = "",
    [string]$Region = "us-east-2",
    [string]$AvailabilityZone = "",
    [string]$InstanceName = "olga-review-portal",
    [string]$StaticIpName = "olga-review-portal-ip",
    [string]$DistributionName = "olga-review-portal-web",
    [string]$BlueprintId = "",
    [string]$InstanceBundleId = "",
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

function Get-ExistingInstance {
    try {
        $response = Invoke-Aws -Arguments @(
            "lightsail", "get-instance", "--instance-name", $InstanceName
        ) -CommandRegion $Region
        return $response.instance
    }
    catch {
        return $null
    }
}

function Get-ExistingDistribution {
    try {
        $response = Invoke-Aws -Arguments @(
            "lightsail", "get-distributions", "--distribution-name", $DistributionName
        ) -CommandRegion "us-east-1"
        return @($response.distributions) | Select-Object -First 1
    }
    catch {
        return $null
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
if ($ReviewToken -eq $AdminToken) {
    throw "Client and admin tokens must be different."
}

Write-Host "Checking AWS credentials..."
[void](Invoke-Aws -Arguments @("sts", "get-caller-identity") -CommandRegion $Region)

if (-not $BlueprintId) {
    $blueprints = Invoke-Aws -Arguments @(
        "lightsail", "get-blueprints", "--include-inactive"
    ) -CommandRegion $Region
    $selectedBlueprint = $blueprints.blueprints |
        Where-Object {
            $_.isActive -and
            $_.platform -eq "LINUX_UNIX" -and
            $_.blueprintId -match '^ubuntu_'
        } |
        Sort-Object -Property @{ Expression = {
            try { [version]$_.version } catch { [version]"0.0" }
        }; Descending = $true } |
        Select-Object -First 1
    if (-not $selectedBlueprint) {
        throw "No active Ubuntu Lightsail blueprint was found in $Region."
    }
    $BlueprintId = [string]$selectedBlueprint.blueprintId
}

if (-not $InstanceBundleId) {
    $instanceBundles = Invoke-Aws -Arguments @(
        "lightsail", "get-bundles", "--include-inactive"
    ) -CommandRegion $Region
    $selectedInstanceBundle = $instanceBundles.bundles |
        Where-Object {
            $_.isActive -and
            @($_.supportedPlatforms) -contains "LINUX_UNIX"
        } |
        Sort-Object -Property price |
        Select-Object -First 1
    if (-not $selectedInstanceBundle) {
        throw "No active Linux Lightsail instance bundle was found in $Region."
    }
    $InstanceBundleId = [string]$selectedInstanceBundle.bundleId
}

if (-not $DistributionBundleId) {
    $distributionBundles = Invoke-Aws -Arguments @(
        "lightsail", "get-distribution-bundles"
    ) -CommandRegion "us-east-1"
    $selectedDistributionBundle = $distributionBundles.bundles |
        Where-Object { $_.isActive } |
        Sort-Object -Property price |
        Select-Object -First 1
    if (-not $selectedDistributionBundle) {
        throw "No active Lightsail distribution bundle was found."
    }
    $DistributionBundleId = [string]$selectedDistributionBundle.bundleId
}

if (Get-ExistingInstance) {
    throw "Lightsail instance '$InstanceName' already exists. Choose another name or remove the existing resource intentionally."
}
if (Get-ExistingDistribution) {
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
    Write-Host "Selected Ubuntu blueprint: $BlueprintId"
    Write-Host "Selected instance bundle: $InstanceBundleId"
    Write-Host "Selected distribution bundle: $DistributionBundleId"
    Write-Host "Creating Lightsail instance '$InstanceName' in $AvailabilityZone..."
    [void](Invoke-Aws -Arguments @(
        "lightsail", "create-instances",
        "--instance-names", $InstanceName,
        "--availability-zone", $AvailabilityZone,
        "--blueprint-id", $BlueprintId,
        "--bundle-id", $InstanceBundleId,
        "--ip-address-type", "ipv4",
        "--user-data", "file://$tempBootstrap",
        "--tags", "key=Application,value=VideoReviewPortal"
    ) -CommandRegion $Region)

    Write-Host "Waiting for instance state RUNNING..."
    $deadline = (Get-Date).AddMinutes(15)
    do {
        Start-Sleep -Seconds 10
        $state = Invoke-Aws -Arguments @(
            "lightsail", "get-instance-state", "--instance-name", $InstanceName
        ) -CommandRegion $Region
        Write-Host "Instance state: $($state.state.name)"
        if ((Get-Date) -gt $deadline) {
            throw "Timed out waiting for Lightsail instance to start."
        }
    } until ($state.state.name -eq "running")

    $staticIp = $null
    try {
        $staticIpResponse = Invoke-Aws -Arguments @(
            "lightsail", "get-static-ip", "--static-ip-name", $StaticIpName
        ) -CommandRegion $Region
        $staticIp = $staticIpResponse.staticIp
    }
    catch {
        Write-Host "Allocating static IP '$StaticIpName'..."
        [void](Invoke-Aws -Arguments @(
            "lightsail", "allocate-static-ip", "--static-ip-name", $StaticIpName
        ) -CommandRegion $Region)
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
        '{"fromPort":80,"toPort":80,"protocol":"tcp","cidrs":["0.0.0.0/0"]}',
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
    $staticIpResponse = Invoke-Aws -Arguments @(
        "lightsail", "get-static-ip", "--static-ip-name", $StaticIpName
    ) -CommandRegion $Region
    $staticIp = $staticIpResponse.staticIp
    $originHealthUrl = "http://$($staticIp.ipAddress)/health"
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
            "--origin", "name=$InstanceName,regionName=$Region,protocolPolicy=http-only,responseTimeout=60,ipAddressType=ipv4",
            "--default-cache-behavior", "behavior=dont-cache",
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
        $distribution = Get-ExistingDistribution
        if ($distribution) {
            Write-Host "Distribution status: $($distribution.status)"
        }
        if ((Get-Date) -gt $distributionDeadline) {
            throw "Timed out waiting for the Lightsail distribution."
        }
    } until (
        $distribution -and
        $distribution.domainName -and
        $distribution.status -in @("Enabled", "Deployed")
    )

    $baseUrl = "https://$($distribution.domainName)"
    $clientUrl = "$baseUrl/?token=$([uri]::EscapeDataString($ReviewToken))"
    $adminUrl = "$baseUrl/admin?token=$([uri]::EscapeDataString($AdminToken))"
    $output = [ordered]@{
        created_at = (Get-Date).ToUniversalTime().ToString("o")
        region = $Region
        availability_zone = $AvailabilityZone
        blueprint_id = $BlueprintId
        instance_bundle_id = $InstanceBundleId
        distribution_bundle_id = $DistributionBundleId
        instance_name = $InstanceName
        static_ip_name = $StaticIpName
        static_ip = $staticIp.ipAddress
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
    Write-Warning "deployment-output.json contains access tokens. Do not commit it or share the admin link."
}
finally {
    Remove-Item $tempBootstrap -Force -ErrorAction SilentlyContinue
}
