Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Py=Join-Path $Root ".venv\Scripts\python.exe"
if(-not(Test-Path $Py)){throw "Python virtual environment missing. Run install.ps1."}
& $Py -c "import fastapi,pandas,numpy,uvicorn; print('Python dependencies available')"
if($LASTEXITCODE -ne 0){throw "Python dependencies need installation."}
$Node=Get-Command node -ErrorAction SilentlyContinue
$Npm=Get-Command npm -ErrorAction SilentlyContinue
if(-not $Node -or -not $Npm){throw "Install Node.js 20+ and npm."}
node --version
npm --version
if(-not(Test-Path (Join-Path $Root "frontend\node_modules"))){Write-Host "Frontend packages not installed. Run npm install in frontend."}
Write-Host "Project path: $Root"
