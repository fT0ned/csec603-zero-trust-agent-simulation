param([string]$Python = '')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $Python) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    $Python = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { 'python' }
}
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE) { throw 'Install Python3.12 and rerun with -Python C:\path\to\python.exe' }
}
& .venv\Scripts\python.exe -m pip install -r requirements.lock.txt
if ($LASTEXITCODE) { throw 'Python dependency installation failed' }
& .venv\Scripts\python.exe -m scripts.spire bootstrap
if ($LASTEXITCODE) { throw 'SPIRE bootstrap failed. Start Docker Desktop and retry.' }
& docker compose up -d --build --wait
if ($LASTEXITCODE) { throw 'Testbed build/health check failed' }
Write-Host 'Ready. Launch with: powershell -ExecutionPolicy Bypass -File scripts/launch.ps1'
