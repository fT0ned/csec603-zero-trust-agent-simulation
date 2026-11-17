param(
    [ValidateSet('Analyse','Collect')][string]$Mode = 'Analyse',
    [string]$Output = 'results/extension-study-001'
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$studyPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studyPython)) {
    python -m venv .venv
    if ($LASTEXITCODE) { throw 'Python environment creation failed' }
    & $studyPython -m pip install -r requirements.lock.txt
    if ($LASTEXITCODE) { throw 'Pinned dependency installation failed' }
}
& $studyPython -m scripts.prepare_extension_fonts
if ($LASTEXITCODE) { throw 'Pure-Python PDF font support unavailable' }
if ($Mode -eq 'Collect' -and $Output -eq 'results/extension-study-001') {
    $Output = 'results/extension-reproduction-' + (Get-Date -Format 'yyyyMMddTHHmmss')
}
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reproduce_extension.ps1 -Mode $Mode -Output $Output
if ($LASTEXITCODE) { throw 'Frozen experiment/reanalysis command failed' }
$studyPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $studyPython -m analysis.extension_quality --input $Output
if ($LASTEXITCODE) { throw 'Completeness/receipt review failed' }
& $studyPython -m analysis.extension_publication --input $Output
if ($LASTEXITCODE) { throw 'Publication artifact generation failed' }
