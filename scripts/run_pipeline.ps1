Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw "Run scripts/install.ps1 first." }
$env:PYTHONPATH = Join-Path $Root "src"
& $Python -m superr_selector.pipeline --root $Root
if ($LASTEXITCODE -ne 0) { throw "Pipeline failed." }
