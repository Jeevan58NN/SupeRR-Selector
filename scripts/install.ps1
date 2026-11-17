Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) { throw "Install Python 3.11+ and add it to PATH." }
& python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'; print(sys.version)"
if ($LASTEXITCODE -ne 0) { throw "Install Python 3.11+ and retry." }
& python -m venv (Join-Path $Root ".venv")
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "${Root}[dev]"
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
$Npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $Npm) { throw "Install Node.js 20+ (includes npm) and retry." }
Push-Location (Join-Path $Root "frontend")
try { npm ci; if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." } }
finally { Pop-Location }
Write-Host "Installation complete. Run scripts/run_pipeline.ps1, then scripts/run_all.ps1."
