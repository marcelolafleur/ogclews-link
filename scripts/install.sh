#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# ogclews-link bootstrap installer (macOS / Linux).
#
# Fetches (or updates) the link to ~/.muiogo/ogclews-link and runs its setup
# there (scripts/setup.py via setup.sh: link venv + CLI verify). MUIOGO's
# post-run hook auto-discovers that location, and the link auto-discovers the
# OG models MUIOGO installed (~/.muiogo/og-state register) -- so after this
# script, a MUIOGO machine needs NO further configuration.
#
# NOTE: while the repo is private this clone uses your ambient git auth (ssh
# key or credential helper); pass --repo-url git@github.com:... for ssh.
#
# Usage:
#   bash install.sh [--dest DIR] [--repo-url URL] [--branch BR] [-- <setup args>]
#   (everything after `--` is passed to scripts/setup.py, e.g. -- --check)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_URL="https://github.com/marcelolafleur/ogclews-link.git"
DEST="$HOME/.muiogo/ogclews-link"
BRANCH=""
SETUP_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dest)     DEST="$2"; shift 2 ;;
        --repo-url) REPO_URL="$2"; shift 2 ;;
        --branch)   BRANCH="$2"; shift 2 ;;
        --)         shift; SETUP_ARGS=("$@"); break ;;
        -h|--help)  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)          echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
    esac
done

command -v git >/dev/null 2>&1 || { echo "x git is required (https://git-scm.com)" >&2; exit 1; }

if [[ -d "$DEST/.git" ]]; then
    echo "==> Existing install at $DEST -- updating (git pull --ff-only)"
    git -C "$DEST" pull --ff-only || {
        echo "x update failed (local changes or diverged history at $DEST);" \
             "resolve there or reinstall with --dest elsewhere" >&2; exit 1; }
elif [[ -e "$DEST" ]]; then
    echo "x $DEST exists but is not a git checkout; remove it or pass --dest elsewhere" >&2
    exit 1
else
    echo "==> Cloning $REPO_URL -> $DEST"
    mkdir -p "$(dirname "$DEST")"
    git clone ${BRANCH:+--branch "$BRANCH"} "$REPO_URL" "$DEST" || {
        echo "x clone failed. While the repo is private you need git auth" \
             "(ssh key: --repo-url git@github.com:marcelolafleur/ogclews-link.git," \
             "or a credential helper / gh auth for https)." >&2; exit 1; }
fi

exec bash "$DEST/scripts/setup.sh" "${SETUP_ARGS[@]+"${SETUP_ARGS[@]}"}"
