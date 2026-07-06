#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# ogclews-link setup (macOS / Linux)
#
# Stands up the link's OWN isolated environment and makes `ogclews-link` runnable.
# The link is deliberately ogcore-free: it never imports ogcore — to solve, it
# SUBPROCESSES an OG model's own interpreter. So this installer:
#   (1) creates the link's uv venv (numpy/pandas/scipy/openpyxl/matplotlib only),
#   (2) verifies the `ogclews-link` CLI,
#   (3) registers an OG country model — installed in ITS OWN env, either an existing
#       checkout or fetched here via the upstream OG-Core universal installer — so
#       `ogclews-link run coupled` has a model to drive.
#
# Usage:
#   ./scripts/setup.sh                     create the link venv + verify the CLI
#   ./scripts/setup.sh --check             verify an existing install only (no changes)
#   ./scripts/setup.sh --dev               also install the dev extra (pytest) + run the tests
#                                          (use --dev on a dev checkout: plain `uv sync` removes extras)
#   ./scripts/setup.sh --og-path <dir>     register an already-installed OG model checkout
#        [--key <k>]                       registry key (default: dir basename; use for worktrees, e.g. og-phl)
#   ./scripts/setup.sh --install-og <key>  STANDALONE convenience (no MUIOGO): fetch+install an OG country
#                                          model via the upstream OG-Core installer, then register it.
#                                          Under MUIOGO, install OG models via its OG tab instead (the link
#                                          then finds them automatically). keys: og-phl|og-eth|og-zaf|og-idn
#        [--og-dest <dir>]                 where to install it (default: the link repo's parent)
#
# Respects $OGCLEWS_MODEL_REGISTRY (registry file location; default ./og_model_registry.json).
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---- pretty output (plain when not a tty) ----
if [ -t 1 ]; then B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'; else B=""; G=""; Y=""; R=""; N=""; fi
info() { printf "%s==>%s %s\n" "$B" "$N" "$*"; }
ok()   { printf "%s  ok%s %s\n" "$G" "$N" "$*"; }
warn() { printf "%s  ! %s %s\n" "$Y" "$N" "$*"; }
die()  { printf "%s  x %s %s\n" "$R" "$N" "$*" >&2; exit 1; }

usage() { sed -n '4,26p' "$0" | sed 's/^# \{0,1\}//'; }

# ---- args ----
CHECK_ONLY=0; DEV=0; OG_PATH=""; INSTALL_OG=""; OG_DEST=""; OG_KEY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --check)      CHECK_ONLY=1 ;;
    --dev)        DEV=1 ;;
    --og-path)    OG_PATH="${2:?--og-path needs a directory}"; shift ;;
    --install-og) INSTALL_OG="${2:?--install-og needs a repo key}"; shift ;;
    --og-dest)    OG_DEST="${2:?--og-dest needs a directory}"; shift ;;
    --key)        OG_KEY="${2:?--key needs a registry key}"; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done
# a dir whose basename isn't the expected repo key (e.g. a worktree) needs --key so
# `run coupled` can look the country up (country og_repo -> registry key, e.g. og-phl)
[ -n "$INSTALL_OG" ] && [ -z "$OG_KEY" ] && OG_KEY="$INSTALL_OG"
[ -z "$OG_DEST" ] && OG_DEST="$(cd "$PROJECT_ROOT/.." && pwd)"

cd "$PROJECT_ROOT"

# ---- guard: an active conda env breaks uv's venv resolution ----
if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
  die "Conda env '${CONDA_DEFAULT_ENV}' is active. Run 'conda deactivate' (until no env shows), then re-run."
fi

ensure_uv() {
  command -v uv >/dev/null 2>&1 && return 0
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null 2>&1 && return 0
  info "uv not found — installing it (https://astral.sh/uv)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv install failed; install it manually, then re-run (https://docs.astral.sh/uv/)"
}

verify_cli() {
  info "Verifying the ogclews-link CLI"
  uv run ogclews-link models list >/dev/null 2>&1 || uv run ogclews-link --help >/dev/null 2>&1 \
    || die "the 'ogclews-link' CLI did not run — see 'uv run ogclews-link --help'"
  ok "CLI runs"
}

have_registered_model() { uv run ogclews-link models list 2>/dev/null | grep -qiE "couplable|\[x\]"; }

# ---- --check: verify an existing install, change nothing ----
if [ "$CHECK_ONLY" -eq 1 ]; then
  command -v uv >/dev/null 2>&1 || { export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"; }
  command -v uv >/dev/null 2>&1 || die "uv not found (run without --check to install it)"
  [ -d "$PROJECT_ROOT/.venv" ] || die "no .venv here (run without --check to create it)"
  verify_cli
  info "Registered OG models:"; uv run ogclews-link models list || true
  exit 0
fi

# ---- 1. the link's own environment ----
ensure_uv
info "Creating the link's isolated venv (uv sync)"
if [ "$DEV" -eq 1 ]; then uv sync --extra dev; else uv sync; fi
ok "link venv ready at $PROJECT_ROOT/.venv (ogcore-free)"

# ---- 2. verify (+ tests in --dev) ----
verify_cli
if [ "$DEV" -eq 1 ]; then info "Running the test suite"; uv run pytest tests/ -q; fi

# ---- 3. OG country model: optional install, then register ----
if [ -n "$INSTALL_OG" ]; then
  case "$INSTALL_OG" in
    og-phl) OG_REPO=OG-PHL ;; og-eth) OG_REPO=OG-ETH ;; og-zaf) OG_REPO=OG-ZAF ;; og-idn) OG_REPO=OG-IDN ;;
    *) die "unknown --install-og key '$INSTALL_OG' (expected og-phl | og-eth | og-zaf | og-idn)" ;;
  esac
  if [ -f "$PROJECT_ROOT/../OG-Core/scripts/install.sh" ]; then
    og_installer="$PROJECT_ROOT/../OG-Core/scripts/install.sh"
    info "Using local OG-Core installer: $og_installer"
  else
    info "Fetching the upstream OG-Core installer"
    og_installer="$(mktemp)"
    curl -fsSL https://raw.githubusercontent.com/PSLmodels/OG-Core/master/scripts/install.sh -o "$og_installer" \
      || die "could not download the OG-Core installer (https://github.com/PSLmodels/OG-Core)"
  fi
  info "Installing $OG_REPO into $OG_DEST via the OG-Core installer (uv sync — can take a minute)"
  bash "$og_installer" --repo "$INSTALL_OG" --dest "$OG_DEST" --yes
  OG_PATH="$OG_DEST/$OG_REPO"
fi

if [ -n "$OG_PATH" ]; then
  [ -x "$OG_PATH/.venv/bin/python" ] || die "no interpreter at $OG_PATH/.venv/bin/python — build the OG model first (its own 'uv sync'), or use --install-og"
  info "Registering the OG model at $OG_PATH"
  uv run ogclews-link models register --path "$OG_PATH" ${OG_KEY:+--key "$OG_KEY"}
  ok "registered"
elif ! have_registered_model; then
  warn "No OG model is registered yet. 'run coupled' needs one — re-run with either:"
  warn "    ./scripts/setup.sh --install-og og-phl       # fetch + register a country model"
  warn "    ./scripts/setup.sh --og-path <OG-checkout>   # register one you already installed"
fi

# ---- summary ----
echo
info "Registered OG models:"; uv run ogclews-link models list || true
echo
ok "ogclews-link is installed."
cat <<EOF
Next — point at your CLEWS scenarios (from a MUIOGO install) and run:
  export OGCLEWS_MUIOGO_HOME=<path to MUIOGO>          # or place MUIOGO at ../MUIOGO
  export OGCLEWS_CLEWS_CASE=Philippines_v9 OGCLEWS_CLEWS_BASE_RUN=Base_v9 OGCLEWS_CLEWS_REFORM_RUN=PEP_v9
  uv run ogclews-link run coupled --out ./ogclews_runs   # (or pass --clews-base/--clews-reform)
EOF
