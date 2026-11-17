param(
    [ValidateSet('Analyse','Collect')][string]$Mode = 'Analyse',
    [string]$Output = ''
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$studyPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studyPython)) {
    python -m venv .venv
    if ($LASTEXITCODE) { throw 'Python 3.12 environment creation failed' }
    & $studyPython -m pip install -r requirements.lock.txt
    if ($LASTEXITCODE) { throw 'Pinned dependency installation failed' }
}
if ($Mode -eq 'Analyse') {
    if (-not $Output) { $Output = 'results/extension-study-001' }
    & $studyPython -m testbed.extension.analyse --input $Output
    if ($LASTEXITCODE) { throw 'Sealed evidence analysis failed' }
    exit 0
}
if (-not (Test-Path -LiteralPath '.env')) { throw 'Create ignored .env with provider keys and STUDY_BUDGET_USD=25 first; never put keys in command arguments' }
docker desktop start
if ($LASTEXITCODE) { throw 'Docker Desktop did not start' }
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
if ($LASTEXITCODE) { throw 'Bootstrap/health check failed' }
$studyOllama = docker inspect --format '{{.Image}}' csec603-extension-ollama 2>$null
if (-not $studyOllama) {
    $studyModels = Join-Path (Get-Location) '.runtime\extension-tools'
    New-Item -ItemType Directory -Force -Path $studyModels | Out-Null
    docker run -d --name csec603-extension-ollama --gpus all -p 127.0.0.1:11434:11434 --mount "type=bind,source=$studyModels,target=/root/.ollama" 'ollama/ollama@sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592'
    if ($LASTEXITCODE) { throw 'Pinned Ollama container did not start' }
} elseif ($studyOllama.Trim() -ne 'sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592') {
    throw 'Existing Ollama container differs from frozen image; refusing a silent substitution'
} else {
    docker start csec603-extension-ollama | Out-Null
}
foreach ($studyModel in @('qwen2.5:7b-instruct','qwen2.5:3b-instruct')) {
    docker exec csec603-extension-ollama ollama pull $studyModel
    if ($LASTEXITCODE) { throw 'Model pull failed' }
}
& $studyPython -m testbed.extension.preflight
if ($LASTEXITCODE) { throw 'Health, runtime source, local digest, clock or boundary check failed' }
if (-not $Output) { $Output = 'results/extension-reproduction-' + (Get-Date -Format 'yyyyMMddTHHmmss') }
& $studyPython -m testbed.extension.study run --output $Output
if ($LASTEXITCODE) { throw 'Collection stopped; preserve output and ledger, inspect failure before resuming' }
& $studyPython -m testbed.extension.analyse --input $Output
if ($LASTEXITCODE) { throw 'Analysis failed' }
& $studyPython -m testbed.extension.operations approval --output (Join-Path $Output 'operations/approval')
if ($LASTEXITCODE) { throw 'Simulated approval evaluation failed' }
& $studyPython -m testbed.extension.operations network-failure --output (Join-Path $Output 'operations/network-failure')
if ($LASTEXITCODE) { throw 'Network failure probe failed; inspect extension PDP health' }
