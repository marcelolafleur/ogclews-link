#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# ogclews-link setup (macOS / Linux) — thin wrapper.
#
# All installer logic lives in the cross-platform scripts/setup.py (same flags;
# see `./scripts/setup.sh --help`). This wrapper only finds a Python to run it
# with — the system python3 if present, else uv's managed one (installing uv
# first if needed), so a machine with nothing but git/curl still works.
# Windows: python scripts\setup.py  (or scripts\setup.ps1).
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/setup.py" "$@"
fi

# no system python3: bootstrap uv, whose managed python runs the installer
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo "==> uv not found — installing it (https://astral.sh/uv)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null 2>&1 || { echo "  x uv install failed; install it manually, then re-run (https://docs.astral.sh/uv/)" >&2; exit 1; }
fi
exec uv run --no-project python "$SCRIPT_DIR/setup.py" "$@"
