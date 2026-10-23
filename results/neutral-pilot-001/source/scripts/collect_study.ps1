param([string]$Output = 'results/study-001')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$studyPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studyPython)) { throw 'Run scripts/setup.ps1 first' }
$studyStarted = [DateTime]::UtcNow.ToString('o')
& $studyPython -m testbed.cli run --config configs/study.json --output $Output
$studyCollectionExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath (Join-Path $Output 'manifest.json'))) { exit $studyCollectionExit }
& $studyPython -m analysis.cli --input $Output --verify-raw
$studyAnalysisExit = $LASTEXITCODE
& $studyPython -m scripts.validate_collection --input $Output
$studyValidationExit = $LASTEXITCODE
& $studyPython -m scripts.provider_balance --output (Join-Path $Output 'provider-balance-after.json')
$studyBalanceExit = $LASTEXITCODE
$studyStatus = [ordered]@{
    started_at_utc = $studyStarted
    finished_at_utc = [DateTime]::UtcNow.ToString('o')
    collection_exit_code = $studyCollectionExit
    analysis_exit_code = $studyAnalysisExit
    validation_exit_code = $studyValidationExit
    balance_snapshot_exit_code = $studyBalanceExit
    review_status = 'Preserved measured collection; final evidence review and browser/export verification still required.'
}
$studyStatus | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath (Join-Path $Output 'pipeline-status.json')
$studyStatus | ConvertTo-Json
if ($studyCollectionExit -ne 0 -or $studyAnalysisExit -ne 0 -or $studyValidationExit -ne 0 -or $studyBalanceExit -ne 0) { exit 2 }
