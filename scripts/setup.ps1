# ──────────────────────────────────────────────────────────────────────────────
# ogclews-link setup (Windows) — thin wrapper.
#
# All installer logic lives in the cross-platform scripts/setup.py (same flags;
# see `.\scripts\setup.ps1 --help`). This wrapper only finds a Python to run it
# with — the system python if present, else uv's managed one (installing uv
# first if needed), so a machine with nothing but git still works.
#
# If script execution is blocked, run:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [args]
# ──────────────────────────────────────────────────────────────────────────────
$ErrorActionPreference = "Stop"
$SetupPy = Join-Path $PSScriptRoot "setup.py"

# the Windows Store "python" stub advertises itself on PATH but only opens the Store;
# a real interpreter answers --version with exit code 0
foreach ($py in @("python", "python3", "py")) {
    $cmd = Get-Command $py -ErrorAction SilentlyContinue
    if ($cmd) {
        & $py --version *> $null
        if ($LASTEXITCODE -eq 0) {
            & $py $SetupPy @args
            exit $LASTEXITCODE
        }
    }
}

# no system python: bootstrap uv, whose managed python runs the installer
$uvDirs = @("$env:USERPROFILE\.local\bin", "$env:USERPROFILE\.cargo\bin")
$env:Path = ($uvDirs -join ";") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "==> uv not found - installing it (https://astral.sh/uv)"
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = ($uvDirs -join ";") + ";" + $env:Path
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error "uv install failed; install it manually, then re-run (https://docs.astral.sh/uv/)"
        exit 1
    }
}
& uv run --no-project python $SetupPy @args
exit $LASTEXITCODE
