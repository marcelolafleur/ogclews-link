#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# ogclews-link test drive (macOS / Linux) — zero-input, resume-safe.
#
# Does the whole Philippine example in one go:
#   1. makes ./ogclews-test and works inside it
#   2. downloads the solved CLEWS case (Philippines_v9)
#   3. clones OG-PHL on the m8 multi-industry calibration and builds its env
#   4. clones + installs ogclews-link and registers OG-PHL
#   5. runs the coupled example (~20 minutes, mostly solver iterations)
#   6. points you at the results deck
#
# Safe to re-run: every step skips itself if already done (a rerun after the
# first solve reuses the cached baseline and takes ~8 minutes).
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

if [ -t 1 ]; then B=$'\033[1m'; G=$'\033[32m'; R=$'\033[31m'; N=$'\033[0m'; else B=""; G=""; R=""; N=""; fi
step() { printf "\n%s==> %s%s\n" "$B" "$*" "$N"; }
ok()   { printf "%s  ok%s %s\n" "$G" "$N" "$*"; }
die()  { printf "%s  x %s %s\n" "$R" "$N" "$*" >&2; exit 1; }

for tool in curl git unzip; do
  command -v "$tool" >/dev/null || die "'$tool' is required — install it and re-run."
done
export PATH="$HOME/.local/bin:$PATH"   # where the setup script puts uv if it has to install it

CASE_ZIP="https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip"
LINK_REPO="https://github.com/marcelolafleur/ogclews-link.git"
OG_REPO="https://github.com/EAPD-DRB/OG-PHL.git"

step "Working folder"
[ "$(basename "$PWD")" = "ogclews-test" ] || { mkdir -p ogclews-test; cd ogclews-test; }
ok "$PWD"

step "1/5 ogclews-link (installs its own environment, including Python)"
[ -d ogclews-link ] || git clone --quiet "$LINK_REPO" ogclews-link
( cd ogclews-link && ./scripts/setup.sh )
ok "link installed"

step "2/5 Philippine CLEWS case (already solved -- no MUIOGO needed)"
if [ ! -d Philippines_v9 ]; then
  curl -fL --progress-bar -o Philippines_v9.zip "$CASE_ZIP"
  unzip -q Philippines_v9.zip && rm -f Philippines_v9.zip
fi
[ -d Philippines_v9/res/Base_v9/csv ] || die "Philippines_v9/res/Base_v9/csv missing after unzip."
ok "case in place"

step "3/5 OG-PHL on the m8 multi-industry calibration"
[ -d OG-PHL ] || git clone --quiet "$OG_REPO" OG-PHL
( cd OG-PHL
  git rev-parse --verify --quiet m8 >/dev/null || git fetch --quiet origin pull/63/head:m8
  git checkout --quiet m8
  uv sync --quiet )
ok "OG-PHL ready"

step "4/5 Register OG-PHL with the link"
( cd ogclews-link && ./scripts/setup.sh --og-path ../OG-PHL )
( cd ogclews-link && uv run ogclews-link models list ) | grep -q "og-phl" \
  || die "og-phl did not register -- run: cd ogclews-link && ./scripts/setup.sh --og-path ../OG-PHL --key og-phl"
ok "registered"

step "5/5 Run the coupled example (~20 min first time; it prints solver iterations -- it is working)"
( cd ogclews-link && uv run ogclews-link run coupled \
    --clews-base   ../Philippines_v9/res/Base_v9/csv \
    --clews-reform ../Philippines_v9/res/PEP_v9/csv \
    --out ./ogclews_runs </dev/null )

DECK="$PWD/ogclews-link/ogclews_runs/coupled/index.html"
step "Done"
echo "Results: $PWD/ogclews-link/ogclews_runs/coupled/"
echo "Open the figure deck: $DECK"
command -v open >/dev/null && open "$DECK" 2>/dev/null || true
command -v xdg-open >/dev/null && xdg-open "$DECK" 2>/dev/null || true
