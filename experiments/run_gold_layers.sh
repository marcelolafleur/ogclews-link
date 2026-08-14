#!/bin/bash
# Policy-LAYER macro decomposition (Marcelo, 2026-08-14): each blessed CLEWs layer run
# (GOLD_CP coal phase-out, GOLD_RE renewables, GOLD_EV electric vehicles) alone vs
# GOLD_BASE, through the SAME full coupled composition as the headline run. No CLEWs
# solves — the layer results are blessed and read-only. The OG baseline is REUSED via a
# symlinked cache (it is CLEWS-independent; re-solving it three times would be waste).
#
# Run AFTER the channel battery (one solve at a time on this machine).
# Usage: run_gold_layers.sh [--run] [workers]   (default: verify only, like the main script)
set -u
cd "$(dirname "$0")/.." || exit 1
LINK="$PWD"
W=7
GO=""
for arg in "$@"; do
    case "$arg" in
        --run) GO=1 ;;
        [0-9]|[0-9][0-9]) W="$arg" ;;
        *) echo "unknown argument: $arg" >&2; exit 2 ;;
    esac
done
CASE="$(muiogo-ai case-path --case 'Philippines_v18_GOLD')" || exit 1
MAIN_CACHE="$LINK/ogclews_runs_v18gold/_og_baseline_cache"
[ -d "$MAIN_CACHE" ] || { echo "no baseline cache at $MAIN_CACHE -- run the headline pair first" >&2; exit 1; }

# The blessed layer objectives, byte-for-byte (gold-baseline-v18_0_1.md).
# (macOS /bin/bash is 3.2: no associative arrays — plain function instead.)
blessed_obj() {
    case "$1" in
        GOLD_CP) echo "369762636.65183932" ;;
        GOLD_RE) echo "369754434.60797173" ;;
        GOLD_EV) echo "369741574.29423273" ;;
    esac
}

for L in GOLD_CP GOLD_RE GOLD_EV; do
    line="$(head -1 "$CASE/res/$L/results.txt")"
    case "$line" in
        *Optimal*"$(blessed_obj "$L")"*) echo "  $L: Optimal, objective matches the blessed record  OK" ;;
        *) echo "  $L: blessed objective NOT matched: $line" >&2; exit 1 ;;
    esac
done
[ -z "$GO" ] && { echo "verify-only (pass --run to launch)"; exit 0; }

for L in GOLD_CP GOLD_RE GOLD_EV; do
    OUT="$LINK/ogclews_runs_v18gold_layers/${L#GOLD_}"
    mkdir -p "$OUT"
    ln -sfn "$MAIN_CACHE" "$OUT/_og_baseline_cache"
    echo; echo "=== LAYER $L vs GOLD_BASE ==="
    (cd "$LINK" && .venv/bin/ogclews-link run coupled \
        --country phl \
        --clews-base   "$CASE/res/GOLD_BASE/csv" \
        --clews-reform "$CASE/res/$L/csv" \
        --clews-run    "Philippines_v18_GOLD/$L" \
        --workers "$W" \
        --out "$OUT") || { echo "$L FAILED" >&2; exit 1; }
    # Health gate: the EV layer plausibly RAISES PM2.5 (coal-heavy grid) — health must still
    # APPLY (nonzero, either sign); only a skip fails the gate.
    python3 - "$OUT" "$L" <<'PY' || { echo "$L: HEALTH GATE FAILED" >&2; exit 1; }
import glob, json, sys
hits = glob.glob(f"{sys.argv[1]}/coupled/**/*manifest*.json", recursive=True)
assert hits, "no manifest"
man = json.load(open(max(hits)))
hp = [pr for pr in man.get("provenance", []) if pr.get("channel") == "health"]
assert hp and not hp[0].get("skipped"), f"health skipped: {hp[0].get('reason') if hp else 'no record'}"
assert hp[0].get("mortality_excess_deaths") not in (None, 0), hp[0]
print(f"  {sys.argv[2]}: health APPLIED, excess deaths {hp[0]['mortality_excess_deaths']:+.1f}  OK")
PY
    cp "$LINK/ogclews_runs_v18gold/coupled/RUN_NOTES.md" "$OUT/coupled/RUN_NOTES.md"
    echo "  macro table: $OUT/coupled/macro_table.csv"
done
echo; echo "=== ALL THREE LAYERS DONE ==="
