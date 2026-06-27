param(
    [string]$WorkDir = "",
    [int]$Port = 8765,
    [switch]$NoBrowser,
    [switch]$DiagnosticsOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host "[VIDEO MIX] $Message"
}

function Fail-WithMessage {
    param([string]$Message)
    Write-Host ""
    Write-Host "Ошибка: $Message" -ForegroundColor Red
    Write-Host "Следующий шаг: сначала проверьте диагностику или передайте корректный -WorkDir." -ForegroundColor Yellow
    exit 1
}

function Get-PythonCommand {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        return "$($pyCommand.Source) -3"
    }

    return $null
}

function Invoke-Diagnostics {
    param(
        [string]$PythonCommand,
        [string]$RequestedWorkDir
    )

    $arguments = @("-m", "video_mix.dashboard_launcher", "--project-root", $ProjectRoot, "--json")
    if ($RequestedWorkDir) {
        $arguments += @("--work-dir", $RequestedWorkDir)
    }

    if ($PythonCommand -like "* -3") {
        $parts = $PythonCommand -split " "
        $exe = $parts[0]
        $prefixArgs = $parts[1..($parts.Length - 1)]
        $output = & $exe @prefixArgs @arguments 2>&1
        $code = $LASTEXITCODE
    } else {
        $output = & $PythonCommand @arguments 2>&1
        $code = $LASTEXITCODE
    }

    $raw = ($output | Out-String).Trim()
    if (-not $raw) {
        Fail-WithMessage "диагностика не вернула результат"
    }

    try {
        $json = $raw | ConvertFrom-Json
    } catch {
        Write-Host $raw
        Fail-WithMessage "не удалось разобрать результат диагностики"
    }

    return @{
        ExitCode = $code
        Payload = $json
    }
}

function Test-DashboardUrl {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Wait-ForDashboard {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-DashboardUrl -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

$pythonCommand = Get-PythonCommand
if (-not $pythonCommand) {
    Fail-WithMessage "Python не найден. Установите Python или создайте .venv."
}

Write-Step "Запускаю диагностику launcher..."
$diagnostics = Invoke-Diagnostics -PythonCommand $pythonCommand -RequestedWorkDir $WorkDir
$payload = $diagnostics.Payload

if ($DiagnosticsOnly) {
    Write-Host ""
    Write-Host "Диагностика VIDEO MIX dashboard:" -ForegroundColor Cyan
    $payload.checks.PSObject.Properties | ForEach-Object {
        $name = $_.Name
        $item = $_.Value
        $status = if ($item.ok) { "OK" } else { "FAIL" }
        Write-Host ("- {0}: {1} :: {2}" -f $name, $status, $item.detail)
    }
    if ($payload.ok) {
        Write-Host ""
        Write-Host "Итог: launcher готов к запуску." -ForegroundColor Green
        exit 0
    }
    Fail-WithMessage "диагностика не пройдена"
}

if (-not $payload.work_dir) {
    Write-Host ""
    Write-Host "VIDEO MIX work_dir не найден." -ForegroundColor Yellow
    Write-Host "Что сделать:" -ForegroundColor Yellow
    Write-Host "1. Сначала создайте work_dir через plan/review."
    Write-Host "2. Затем запустите launcher так:"
    Write-Host "   .\start_video_mix_dashboard.ps1 -WorkDir C:\path\to\your\work"
    exit 1
}

if (-not $payload.checks.uvicorn.ok) {
    Fail-WithMessage "uvicorn не импортируется. Установите зависимости проекта."
}

if (-not $payload.checks.app_import.ok) {
    Fail-WithMessage "app.main не импортируется. Проверьте зависимости и состояние репозитория."
}

$resolvedWorkDir = [string]$payload.work_dir
$encodedWorkDir = [uri]::EscapeDataString($resolvedWorkDir)
$dashboardUrl = "http://127.0.0.1:$Port/video-mix?work_dir=$encodedWorkDir"

$serverStarted = $false
if (Test-DashboardUrl -Url $dashboardUrl) {
    Write-Step "Dashboard уже отвечает на $dashboardUrl"
} else {
    Write-Step "Поднимаю локальный FastAPI server на 127.0.0.1:$Port"

    if ($pythonCommand -like "* -3") {
        $parts = $pythonCommand -split " "
        $exe = $parts[0]
        $prefixArgs = $parts[1..($parts.Length - 1)]
        $process = Start-Process -FilePath $exe -ArgumentList (@($prefixArgs) + @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port")) -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden
    } else {
        $process = Start-Process -FilePath $pythonCommand -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden
    }
    $serverStarted = $true

    if (-not (Wait-ForDashboard -Url $dashboardUrl)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id
        }
        Fail-WithMessage "сервер не поднялся вовремя. Запустите .\start_video_mix_dashboard.ps1 -DiagnosticsOnly"
    }
}

Write-Host ""
Write-Host "VIDEO MIX dashboard готов." -ForegroundColor Green
Write-Host "work_dir: $resolvedWorkDir"
Write-Host "URL: $dashboardUrl"
if ($serverStarted -and $process) {
    Write-Host "PID сервера: $($process.Id)"
}
if (-not $payload.checks.ffmpeg.ok) {
    Write-Host "Предупреждение: ffmpeg не найден в PATH. Review/export части могут не работать." -ForegroundColor Yellow
}
if (-not $payload.checks.ffprobe.ok) {
    Write-Host "Предупреждение: ffprobe не найден в PATH. Планирование media probe может не работать." -ForegroundColor Yellow
}

if (-not $NoBrowser) {
    Write-Step "Открываю браузер..."
    Start-Process $dashboardUrl
} else {
    Write-Step "Browser auto-open отключён. Откройте URL вручную."
}

