# PowerShell 5.1+
# Single-command VastrAI backend development setup.
#
#   .\run_dev.ps1
#
# Starts EXACTLY ONE clean dev environment in the project's venv:
#   - ONE uvicorn API server (foreground, with --reload)
#   - ONE Celery worker (background, no console window, --pool solo)
#
# No subprocess auto-spawns a worker from inside the API, and no duplicate
# workers/uvicorn are created. Stop everything with Ctrl+C (uvicorn), then the
# worker process ends with the shell. Use -NoWorker to skip the worker.

param(
    [switch]$NoWorker,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Error "Virtualenv python not found at $venvPy . Create it first: python -m venv .venv"
    exit 1
}

# (Optional) clean up any stale worker PID lock from the old autostart design.
$lock = Join-Path $root ".worker.pid"
if (Test-Path -LiteralPath $lock) {
    Remove-Item -LiteralPath $lock -Force
    Write-Host "[run_dev] Removed stale .worker.pid" -ForegroundColor DarkGray
}

if (-not $NoWorker) {
    Write-Host "[run_dev] Starting Celery worker (single, serial pool)..." -ForegroundColor Cyan
    $workerArgs = @(
        "-m", "celery",
        "-A", "app.worker.celery_app",
        "worker",
        "-l", "info",
        "-Q", "vastrai.tryon",
        "--concurrency", "1",
        "--pool", "solo"
    )
    $flags = 0
    $flags = $flags -bor [System.Diagnostics.ProcessWindowStyle]::Hidden
    $proc = Start-Process -FilePath $venvPy -ArgumentList $workerArgs `
        -WorkingDirectory $root -WindowStyle Hidden -PassThru
    Write-Host "[run_dev] Worker started (pid=$($proc.Id))." -ForegroundColor Green
}

Write-Host "[run_dev] Starting API server..." -ForegroundColor Cyan
Push-Location $root
try {
    $uvicornArgs = @("-m", "uvicorn", "app.main:app")
    if (-not $NoReload) {
        $uvicornArgs += "--reload"
    }
    & $venvPy @uvicornArgs
} finally {
    Pop-Location
}