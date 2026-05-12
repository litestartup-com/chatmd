# ChatMarkdown one-line installer for Windows (PowerShell)
# Usage: irm https://www.chatmarkdown.org/install.ps1 | iex
#
# This script:
#   1. Detects Python >= 3.10 (offers to install if missing/outdated)
#   2. Installs pipx if not present
#   3. Installs chatmd via pipx
#   4. Verifies installation
#   5. Prints Quick Start guide
#
# Compatibility: ASCII-only on purpose. Some PowerShell 5.1 hosts decode
# scripts piped via `irm | iex` with the system ANSI code page when the
# server does not advertise UTF-8, which corrupts non-ASCII characters and
# breaks parsing. Do not introduce box-drawing or other Unicode glyphs here.
#
# License: MIT

$ErrorActionPreference = "Stop"

# --- Configuration ----------------------------------------------------------

$RequiredPythonMajor = 3
$RequiredPythonMinor = 10
$PackageName = "chatmd"
$PythonInstallerUrl = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
$PythonWingetId = "Python.Python.3.12"

# --- Helpers ------------------------------------------------------------------

function Write-Info { param([string]$Message) Write-Host "[info] " -ForegroundColor Blue -NoNewline; Write-Host $Message }
function Write-Ok { param([string]$Message) Write-Host "[ok] " -ForegroundColor Green -NoNewline; Write-Host $Message }
function Write-Warn { param([string]$Message) Write-Host "[warn] " -ForegroundColor Yellow -NoNewline; Write-Host $Message }
function Write-Err { param([string]$Message) Write-Host "[error] " -ForegroundColor Red -NoNewline; Write-Host $Message; exit 1 }

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Test-IsStorePythonStub {
    # Windows 10/11 ship a 0-byte python.exe shim under WindowsApps that
    # opens the Microsoft Store on first run. Detect and skip it; otherwise
    # the installer appears to hang while the Store window pops up.
    param([string]$Command)
    try {
        $info = Get-Command $Command -ErrorAction SilentlyContinue
        if (-not $info) { return $false }
        $path = $info.Source
        if (-not $path) { return $false }
        if ($path -like "*\WindowsApps\*") { return $true }
        # 0-byte App Execution Alias also indicates a stub.
        if ((Test-Path $path) -and ((Get-Item $path).Length -eq 0)) { return $true }
    }
    catch {}
    return $false
}

function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
    # User-site Scripts dir is where pip --user and pipx land binaries.
    # Add the most common locations explicitly in case PATH propagation lags.
    $candidates = @()
    if ($env:APPDATA) {
        $candidates += (Join-Path $env:APPDATA "Python\Scripts")
        # AppData\Roaming\Python\PythonXY\Scripts (per-version dirs)
        $pyRoot = Join-Path $env:APPDATA "Python"
        if (Test-Path $pyRoot) {
            $candidates += (Get-ChildItem $pyRoot -Directory -ErrorAction SilentlyContinue |
                ForEach-Object { Join-Path $_.FullName "Scripts" })
        }
    }
    if ($env:USERPROFILE) {
        $candidates += (Join-Path $env:USERPROFILE ".local\bin")
    }
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p) -and ($env:Path -notlike "*$p*")) {
            $env:Path = "$p;$env:Path"
        }
    }
}

function Confirm-Action {
    param([string]$Prompt)
    $answer = Read-Host "$Prompt [Y/n]"
    if ($answer -match '^[nN]') { return $false }
    return $true
}

# --- Python Detection & Installation -----------------------------------------

function Find-Python {
    # Try common Python binary names on Windows. Skip Microsoft Store stub.
    foreach ($cmd in @("py", "python", "python3")) {
        if (-not (Test-Command $cmd)) { continue }
        if (Test-IsStorePythonStub $cmd) {
            Write-Warn "Skipping Microsoft Store stub: $cmd (would open the Store and hang)."
            continue
        }
        # Validate that the binary actually runs (--version succeeds).
        try {
            $probe = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $probe -match 'Python (\d+)\.(\d+)') {
                $script:PythonCmd = $cmd
                return $true
            }
        }
        catch {}
    }
    return $false
}

function Test-PythonVersion {
    try {
        $versionOutput = & $script:PythonCmd --version 2>&1
        if ($versionOutput -match 'Python (\d+)\.(\d+)') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge $RequiredPythonMajor -and $minor -ge $RequiredPythonMinor) {
                return $true
            }
        }
    }
    catch {}
    return $false
}

function Install-PythonViaWinget {
    Write-Info "Installing Python via winget..."
    winget install -e --id $PythonWingetId --accept-package-agreements --accept-source-agreements
    Refresh-Path
}

function Install-PythonViaDownload {
    Write-Info "Downloading Python installer from python.org..."
    $installerPath = "$env:TEMP\python-installer.exe"

    try {
        Invoke-WebRequest -Uri $PythonInstallerUrl -OutFile $installerPath -UseBasicParsing
    }
    catch {
        Write-Err "Failed to download Python installer: $_"
    }

    Write-Info "Running Python installer (silent, adds to PATH)..."
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait -NoNewWindow
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    Refresh-Path
}

function Ensure-Python {
    if ((Find-Python) -and (Test-PythonVersion)) {
        $version = & $script:PythonCmd --version 2>&1
        Write-Ok "Python found: $version"
        return
    }

    if (Find-Python) {
        $version = & $script:PythonCmd --version 2>&1
        Write-Warn "Python found but version too low: $version"
        Write-Warn "Python ${RequiredPythonMajor}.${RequiredPythonMinor}+ is required."
    }
    else {
        Write-Warn "Python not found on this system."
        Write-Warn "Python ${RequiredPythonMajor}.${RequiredPythonMinor}+ is required."
    }

    if (-not (Confirm-Action "Install/update Python now?")) {
        Write-Host ""
        Write-Host "To install Python manually:"
        Write-Host "  1. Visit https://www.python.org/downloads/"
        Write-Host "  2. Download Python 3.12+"
        Write-Host "  3. Run installer with 'Add python.exe to PATH' checked"
        Write-Host "  Or: winget install -e --id Python.Python.3.12"
        exit 1
    }

    # Prefer winget if available
    if (Test-Command "winget") {
        Install-PythonViaWinget
    }
    else {
        Install-PythonViaDownload
    }

    # Re-detect after install
    Refresh-Path
    if (-not (Find-Python)) {
        Write-Err "Python installation failed. Please install Python ${RequiredPythonMajor}.${RequiredPythonMinor}+ manually."
    }
    if (-not (Test-PythonVersion)) {
        $version = & $script:PythonCmd --version 2>&1
        Write-Err "Installed Python version still does not meet requirements: $version"
    }

    $version = & $script:PythonCmd --version 2>&1
    Write-Ok "Python installed: $version"
}

# --- pipx Detection & Installation -------------------------------------------

function Ensure-Pipx {
    # Prefer `python -m pipx` over the `pipx` shim since the latter may not
    # be on PATH in the current session even after a successful install.
    & $script:PythonCmd -m pipx --version > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = & $script:PythonCmd -m pipx --version 2>&1
        Write-Ok "pipx found: $version"
        return
    }

    Write-Info "Installing pipx via pip (this may take 30-60 seconds, please wait)..."
    # Stream pip output so the user can see progress; do NOT suppress stderr.
    & $script:PythonCmd -m pip install --user --no-warn-script-location --upgrade pipx
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "pip install --user failed (exit $LASTEXITCODE). Retrying with --break-system-packages..."
        & $script:PythonCmd -m pip install --break-system-packages --user --no-warn-script-location --upgrade pipx
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Failed to install pipx. See the pip output above for details."
        }
    }

    Write-Info "Configuring PATH for pipx..."
    & $script:PythonCmd -m pipx ensurepath 2>&1 | Out-Host
    Refresh-Path

    & $script:PythonCmd -m pipx --version > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = & $script:PythonCmd -m pipx --version 2>&1
        Write-Ok "pipx installed: $version"
    }
    else {
        Write-Err "pipx was installed but cannot be invoked. Please open a new terminal and re-run the installer."
    }
}

# --- ChatMD Installation -----------------------------------------------------

function Install-ChatMD {
    Write-Info "Installing $PackageName via pipx (downloading dependencies, please wait)..."
    # Always use `python -m pipx` to avoid relying on PATH inside the
    # current PowerShell session.
    & $script:PythonCmd -m pipx install --force $PackageName
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to install $PackageName. See the pipx output above for details."
    }
}

function Test-Installation {
    Refresh-Path

    if (Test-Command "chatmd") {
        $version = chatmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "chatmd installed: $version"
            return
        }
    }

    # Try via python -m
    try {
        $version = & $script:PythonCmd -m chatmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "chatmd available via: $script:PythonCmd -m chatmd"
            Write-Warn "Open a new terminal for the 'chatmd' command to be on PATH directly."
            return
        }
    }
    catch {}

    Write-Warn "Could not verify 'chatmd' in this session. This is usually a PATH refresh issue."
    Write-Warn "Open a new PowerShell window and run: chatmd --version"
}

# --- Quick Start --------------------------------------------------------------

function Show-QuickStart {
    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Ok "ChatMarkdown installed successfully!"
    Write-Host ""
    Write-Host "  Quick Start:"
    Write-Host "    chatmd init my-workspace"
    Write-Host "    cd my-workspace"
    Write-Host "    chatmd config init"
    Write-Host "    chatmd start"
    Write-Host ""
    Write-Host "  Documentation: https://chatmarkdown.org"
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host ""
}

# --- Main ---------------------------------------------------------------------

function Main {
    Write-Host ""
    Write-Info "ChatMarkdown Installer"
    Write-Host ""

    Ensure-Python
    Ensure-Pipx
    Install-ChatMD
    Test-Installation
    Show-QuickStart
}

# Run
Main
