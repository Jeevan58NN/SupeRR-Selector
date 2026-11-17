Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Npm=Get-Command npm -ErrorAction SilentlyContinue
if(-not $Npm){throw "Install Node.js 20+ and npm."}
$Deps=Join-Path $Root "frontend\node_modules"
if(-not(Test-Path $Deps)){throw "Frontend dependencies missing. Run scripts/install.ps1 first."}
Set-Location (Join-Path $Root "frontend")
npm run dev
