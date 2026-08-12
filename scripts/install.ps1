# ──────────────────────────────────────────────────────────────────────────────
# ogclews-link bootstrap installer (Windows).
#
# Fetches (or updates) the link to ~\.muiogo\ogclews-link and runs its setup
# there (scripts\setup.py: link venv + CLI verify). MUIOGO's post-run hook
# auto-discovers that location, and the link auto-discovers the OG models
# MUIOGO installed (~\.muiogo\og-state register) -- so after this script, a
# MUIOGO machine needs NO further configuration.
#
# NOTE: while the repo is private this clone uses your ambient git auth.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File install.ps1 [-Dest DIR] [-RepoUrl URL] [-Branch BR]
# ──────────────────────────────────────────────────────────────────────────────
param(
    [string]$Dest = (Join-Path $env:USERPROFILE ".muiogo\ogclews-link"),
    [string]$RepoUrl = "https://github.com/marcelolafleur/ogclews-link.git",
    [string]$Branch = "",
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$SetupArgs = @()
)
$ErrorActionPreference = "Stop"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is required (https://git-scm.com)"
}

if (Test-Path (Join-Path $Dest ".git")) {
    Write-Host "==> Existing install at $Dest -- updating (git pull --ff-only)"
    git -C $Dest pull --ff-only
    if ($LASTEXITCODE -ne 0) { Write-Error "update failed (local changes or diverged history at $Dest)" }
} elseif (Test-Path $Dest) {
    Write-Error "$Dest exists but is not a git checkout; remove it or pass -Dest elsewhere"
} else {
    Write-Host "==> Cloning $RepoUrl -> $Dest"
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
    $cloneArgs = @("clone")
    if ($Branch) { $cloneArgs += @("--branch", $Branch) }
    $cloneArgs += @($RepoUrl, $Dest)
    git @cloneArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "clone failed. While the repo is private you need git auth (ssh key or credential helper)."
    }
}

python (Join-Path $Dest "scripts\setup.py") @SetupArgs
exit $LASTEXITCODE
