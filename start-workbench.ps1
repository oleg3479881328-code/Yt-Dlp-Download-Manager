param(
    [switch]$NoBrowser,
    [int]$Port = 8012
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Step($message) {
    Write-Host "[workbench] $message" -ForegroundColor Cyan
}

function Find-PythonCommand() {
    $candidates = @(
        @{ Command = "py"; Arguments = @("-3.12", "-c", "print('ok')"); Launch = @("-3.12") },
        @{ Command = "python"; Arguments = @("-c", "import sys; print(sys.version)"); Launch = @() }
    )

    foreach ($candidate in $candidates) {
        try {
            $null = & $candidate.Command @($candidate.Arguments) 2>$null
            return $candidate
        } catch {
            continue
        }
    }

    throw "Python 3.12+ was not found. Install Python and make sure `py` or `python` is available in PATH."
}

function Test-PortBusy([int]$TargetPort) {
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $TargetPort)
        $listener.Start()
        return $false
    } catch {
        return $true
    } finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

if (Test-PortBusy $Port) {
    throw "Port $Port is already in use on 127.0.0.1. Stop the other process or rerun with -Port <free-port>."
}

$pythonSpec = Find-PythonCommand
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$requirementsFile = Join-Path $ProjectRoot "requirements.txt"
$installStamp = Join-Path $ProjectRoot ".venv\.requirements-installed"
$url = "http://127.0.0.1:$Port/"

if (-not (Test-Path $venvPython)) {
    Write-Step "Creating local virtual environment"
    & $pythonSpec.Command @($pythonSpec.Launch + @("-m", "venv", ".venv"))
}

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment creation failed. Expected $venvPython"
}

$needsInstall = $true
if ((Test-Path $installStamp) -and (Test-Path $requirementsFile)) {
    $needsInstall = (Get-Item $installStamp).LastWriteTimeUtc -lt (Get-Item $requirementsFile).LastWriteTimeUtc
}

if ($needsInstall) {
    Write-Step "Installing Python dependencies"
    & $venvPython -m pip install -r $requirementsFile
    New-Item -ItemType File -Path $installStamp -Force | Out-Null
} else {
    Write-Step "Using existing virtual environment dependencies"
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -and -not (Test-Path "C:\yt-dlp\ffmpeg.exe")) {
    Write-Warning "ffmpeg was not found in PATH or C:\yt-dlp\ffmpeg.exe. The Workbench UI will still open, but clip merge/cut operations may fail until ffmpeg is installed."
}

Write-Step "Opening browser at $url"
if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($TargetUrl)
        Start-Sleep -Seconds 2
        Start-Process $TargetUrl
    } -ArgumentList $url | Out-Null
}

Write-Step "Starting AI Reels Workbench on $url"
& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
