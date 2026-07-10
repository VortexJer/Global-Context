# Global Context installer for Windows PowerShell.
# Usage:
#   irm https://raw.githubusercontent.com/YOUR_USER/globalcontext/main/install.ps1 | iex
#   irm ... | iex; install-globalcontext -Ai all

param(
    [string]$Repo = "YOUR_USER/globalcontext",
    [string]$Branch = "main",
    [string]$InstallDir = "$env:USERPROFILE\.globalcontext",
    [string]$Ai = ""
)

$ErrorActionPreference = "Stop"

$binDir = Join-Path $InstallDir "bin"

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
    & python3 "$binDir\globalcontext.py" @args
}
"@ | Out-File -FilePath $PROFILE -Append -Encoding utf8
    Write-Host "Added globalcontext function to PowerShell profile: $PROFILE"
}

# Run AI integrations setup
$globalcontext = Join-Path $binDir "globalcontext.py"
if ($Ai) {
    & python3 $globalcontext install --ai $Ai
} else {
    & python3 $globalcontext install
}

Write-Host ""
Write-Host "Global Context installed at $InstallDir"
Write-Host "Restart your terminal for PATH changes to take effect."
