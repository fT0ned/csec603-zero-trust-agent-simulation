$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'Run scripts/setup.ps1 first' }
& .venv\Scripts\python.exe -m dashboard
