# Global Context installer for Windows PowerShell.
# Usage:
#   irm https://raw.githubusercontent.com/VortexJer/Global-Context/main/install.ps1 | iex
#   irm ... | iex; install-globalcontext -Ai all

param(
    [string]$Repo = "VortexJer/Global-Context",
    [string]$Branch = "main",
    [string]$InstallDir = "$env:USERPROFILE\.globalcontext",
    [string]$Ai = "",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$binDir = Join-Path $InstallDir "bin"

# Resolve a Python launcher: py -3, then python, then python3.
# ("python3" frequently does not exist on native Windows.)
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyExe = "py"; $pyPre = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyExe = "python"; $pyPre = @()
} else {
    $pyExe = "python3"; $pyPre = @()
}

function Remove-GlobalContext {
    param([string]$InstallDir, [string]$BinDir, [string]$PyExe, [string[]]$PyPre)

    Write-Host "Uninstalling Global Context ..."

    # 1. Remove AI integrations (Claude hooks, Kimi/Codex/Gemini skills).
    $gc = Join-Path $BinDir "globalcontext.py"
    if (Test-Path $gc) {
        try { & $PyExe @PyPre $gc uninstall --ai all } catch { Write-Host "  (integration uninstall skipped: $_)" }
    }

    # 2. Remove the bin directory from the persistent user PATH.
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath) {
        $kept = ($userPath -split ';' | Where-Object { $_ -and ($_.TrimEnd('\') -ne $BinDir.TrimEnd('\')) })
        [Environment]::SetEnvironmentVariable("Path", ($kept -join ';'), "User")
        Write-Host "  Removed $BinDir from user PATH"
    }

    # 3. Remove the globalcontext function block from the PowerShell profile.
    if (Test-Path $PROFILE) {
        $content = Get-Content $PROFILE -Raw
        $cleaned = [regex]::Replace($content, '(?ms)\r?\n?# Global Context\r?\nfunction globalcontext \{.*?\r?\n\}', '')
        if ($cleaned -ne $content) {
            Set-Content -Path $PROFILE -Value $cleaned -Encoding utf8
            Write-Host "  Removed globalcontext function from $PROFILE"
        }
    }

    # 4. Remove the install directory (keeps nothing behind).
    if (Test-Path $InstallDir) {
        Remove-Item -Recurse -Force $InstallDir
        Write-Host "  Removed $InstallDir"
    }

    Write-Host "Global Context uninstalled. Restart your terminal to clear PATH."
}

if ($Uninstall) {
    Remove-GlobalContext -InstallDir $InstallDir -BinDir $binDir -PyExe $pyExe -PyPre $pyPre
    return
}

if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "Installing Global Context from https://github.com/$Repo ..."
    if (Test-Path $InstallDir) {
        Remove-Item -Recurse -Force $InstallDir
    }
    git clone --depth 1 --branch $Branch "https://github.com/$Repo.git" $InstallDir
} else {
    Write-Host "Git not found. Downloading tarball from GitHub ..."
    $url = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"
    $zip = "$env:TEMP\globalcontext.zip"
    Invoke-WebRequest -Uri $url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath "$env:TEMP\globalcontext" -Force
    if (Test-Path $InstallDir) {
        Remove-Item -Recurse -Force $InstallDir
    }
    Move-Item -Path "$env:TEMP\globalcontext\globalcontext-$Branch" -Destination $InstallDir -Force
}

# Add to PATH for current session and persistently
$pathEntry = $binDir
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$pathEntry*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$pathEntry", "User")
    Write-Host "Added $pathEntry to user PATH"
}
$env:Path = "$pathEntry;$env:Path"

# Add PowerShell function to profile
$profileDir = Split-Path -Parent $PROFILE
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}
if (-not (Test-Path $PROFILE) -or (Get-Content $PROFILE -Raw) -notlike "*# Global Context*") {
    @"

# Global Context
function globalcontext {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 "$binDir\globalcontext.py" @args }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python "$binDir\globalcontext.py" @args }
    else { & python3 "$binDir\globalcontext.py" @args }
}
"@ | Out-File -FilePath $PROFILE -Append -Encoding utf8
    Write-Host "Added globalcontext function to PowerShell profile: $PROFILE"
}

# Best-effort: install filelock for robust cross-process locking (the fallback
# lockfile protocol races on Windows). Failure is non-fatal.
try {
    & $pyExe @pyPre -m pip install --quiet --disable-pip-version-check filelock
} catch {
    Write-Host "  (filelock not installed; using fallback lock)"
}

# Run AI integrations setup
$globalcontext = Join-Path $binDir "globalcontext.py"
if ($Ai) {
    & $pyExe @pyPre $globalcontext install --ai $Ai
} else {
    & $pyExe @pyPre $globalcontext install
}

Write-Host ""
Write-Host "Global Context installed at $InstallDir"
Write-Host "Restart your terminal for PATH changes to take effect."
