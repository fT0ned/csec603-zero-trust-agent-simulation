$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.env')) { throw 'Create ignored .env with provider keys and STUDY_BUDGET_USD=25; never put keys in arguments' }
docker desktop start | Out-Null
if ($LASTEXITCODE) { throw 'Docker Desktop unavailable' }
if (-not (Test-Path -LiteralPath '.runtime/control.env')) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
    if ($LASTEXITCODE) { throw 'Original SPIRE/bootstrap setup failed' }
}
docker compose -f compose.yaml -f compose.extension.yaml -f compose.extension2.yaml up -d --build --wait
if ($LASTEXITCODE) { throw 'Study002 services failed health checks' }
$ollamaImage=docker inspect --format '{{.Image}}' csec603-extension-ollama 2>$null
if (-not $ollamaImage) {
    $studyWeights=Join-Path (Get-Location) '.runtime/extension-tools'
    New-Item -ItemType Directory -Force -Path $studyWeights | Out-Null
    docker run -d --name csec603-extension-ollama --gpus all -p 127.0.0.1:11434:11434 --mount "type=bind,source=$studyWeights,target=/root/.ollama" 'ollama/ollama@sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592'
    if ($LASTEXITCODE) { throw 'Pinned Ollama container creation failed' }
} elseif ($ollamaImage.Trim() -ne 'sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592') {
    throw 'Ollama image differs; refusing silent substitution'
} else { docker start csec603-extension-ollama | Out-Null }
$studyConfig=Get-Content -LiteralPath 'configs/extension-study-002.json' -Raw | ConvertFrom-Json
foreach ($studyModel in $studyConfig.local_model_digests.PSObject.Properties.Name) {
    docker exec csec603-extension-ollama ollama pull $studyModel *> .runtime/extension2-reproduction-pull.log
    if ($LASTEXITCODE) { throw "Pinned model pull failed: $studyModel" }
}
& .venv/Scripts/python.exe -m scripts.prepare_extension2_profiles
if ($LASTEXITCODE) { throw 'Pinned tool/system template profile reconstruction failed' }
& .venv/Scripts/python.exe -m testbed.extension2.preflight
if ($LASTEXITCODE) { throw 'Model/source/clock/network preflight failed; no inference performed' }
