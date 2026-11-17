param(
    [ValidateSet('Analyse','Collect')][string]$Mode='Analyse',
    [string]$Output='results/extension-study-002'
)
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$studyPython=Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studyPython)) {
    python -m venv .venv
    if ($LASTEXITCODE) { throw 'Python environment creation failed' }
    & $studyPython -m pip install -r requirements.lock.txt
    if ($LASTEXITCODE) { throw 'Pinned dependency installation failed' }
}
& $studyPython -m scripts.prepare_extension_fonts
if ($LASTEXITCODE) { throw 'Pure-Python PDF support unavailable' }
if ($Mode -eq 'Collect') {
    if ($Output -eq 'results/extension-study-002') { $Output='results/study002-reproduction-'+(Get-Date -Format 'yyyyMMddTHHmmss') }
    & $studyPython -m testbed.extension2.preflight
    if ($LASTEXITCODE) { throw 'Prepare study002 infrastructure/model pins first; preflight failed' }
    & $studyPython -m testbed.extension2.study run --output $Output
    if ($LASTEXITCODE) { throw 'Collection stopped; preserve raw output and ledger' }
}
& $studyPython -m analysis.study002 --input $Output
if ($LASTEXITCODE) { throw 'Study002 sealed reanalysis failed' }
