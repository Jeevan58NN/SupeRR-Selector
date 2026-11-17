Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH=Join-Path $Root "src"
$env:SUPERR_ROOT=$Root
$Port=8000
$Probe=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if($Probe){ throw "Port $Port is already in use. Stop that process or edit scripts/run_backend.ps1." }
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if(-not(Test-Path $Python)){throw "Virtual environment missing. Run scripts/install.ps1 first."}
& $Python -m uvicorn superr_selector.api.app:app --host 127.0.0.1 --port $Port
