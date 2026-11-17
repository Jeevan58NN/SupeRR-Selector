Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Back=Join-Path $PSScriptRoot "run_backend.ps1"
$Front=Join-Path $PSScriptRoot "run_frontend.ps1"
Start-Process powershell -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$Back) -WorkingDirectory $Root -WindowStyle Hidden
try { Start-Sleep -Seconds 3; & $Front } catch { throw "Frontend could not start. Check Node.js and npm install." }
