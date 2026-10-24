# AccessLoop setup for Windows 10/11 (PowerShell 5.1 or 7). Tested in CI on Windows Server 2022.
#
#   .\setup_windows.cmd            venv, pinned packages, Chromium, axe-core, tests, smoke test
#   .\setup_windows.cmd -AI        also install the optional AI drafting packages (Gemini / local model)
#   .\setup_windows.cmd -Quick     skip the tests (not recommended the first time)
#
# Needs Python 3.11+ (python.org installer, "Add python.exe to PATH" ticked) and Node.js LTS (nodejs.org).
param([switch]$AI, [switch]$Quick)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = '1'          # UTF-8 everywhere (Hindi interface, arrows in reports) regardless of the code page

function Say($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Run {
    # PowerShell does not stop on a failing program by itself: check every exit code.
    $exe, $rest = $args
    & $exe @rest
    if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE): $($args -join ' ')" }
}

# Find Python 3.11+: the py launcher first, then python on PATH (skipping the Microsoft Store stub).
$python = $null
foreach ($candidate in @('py -3', 'python')) {
    $parts = $candidate -split ' '
    if (-not (Get-Command $parts[0] -ErrorAction SilentlyContinue)) { continue }
    $pre = @($parts | Select-Object -Skip 1)
    $ErrorActionPreference = 'Continue'
    & $parts[0] @pre -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = 'Stop'
    if ($ok) { $python = $parts; break }
}
if (-not $python) {
    throw 'Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".'
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'Node.js with npm is required. Install the LTS version from https://nodejs.org and open a new terminal.'
}

Say 'Creating the virtual environment (.venv)'
$pyExe = $python[0]; $pyPre = @($python | Select-Object -Skip 1)
Run $pyExe @pyPre -m venv .venv
$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Run $venvPy -m pip install --upgrade pip -q

Say 'Installing the exact package versions AccessLoop is tested with (requirements.lock)'
Run $venvPy -m pip install -r requirements.lock
if ($AI) {
    Say 'Installing the optional AI drafting packages'
    Run $venvPy -m pip install -r requirements-ai.txt
}

Say 'Installing Chromium (the sandboxed scanner browser)'
Run $venvPy -m playwright install chromium

Say 'Installing axe-core locally (no CDN is used during scans)'
if (Test-Path package-lock.json) { Run npm ci --no-audit --no-fund } else { Run npm install --no-audit --no-fund }

if (-not $Quick) {
    Say 'Running the tests'
    Run $venvPy -m pytest -q
    Say 'Real-browser smoke test (scan, approve, patch, re-scan)'
    Run $venvPy -m accessloop.smoke
}

Write-Host "`nSetup complete. Start AccessLoop with:  .\start_windows.cmd" -ForegroundColor Green
