#!/bin/bash
# Run every channel of the PHL coupled analysis, one experiment per solve.
#
# Why a battery and not just `coupled`: `coupled` fires four channels at once, so
# its headline number cannot be attributed without running each channel alone
# under the SAME signal. The trap here is real and I fell into it: the stock
# energy_* experiments hard-code price_ratio=1.20 as a controlled demo stimulus,
# so summing them against a real-signal `coupled` compares a hypothetical with an
# actual. Every energy component below is a *_real variant driven by
# _auto_price_ratio, the same source `coupled` uses.
#
# All runs read the CLEWs case re-solved WITH the offshore wind cap (823 PJ).
# Reform-only solves: the OG baseline is cached under $OUT/_og_baseline_cache.
#
# Usage: run_battery.sh [workers]
set -u
cd "$(dirname "$0")/.." || exit 1
LINK="$PWD"
W="${1:-7}"                       # min(7, cores-2); the link builds a Dask client
OUT="$LINK/ogclews_runs"          # only when --workers > 1, silently otherwise
CASE="$(muiogo-ai case-path --case 'Philippines_v12_CALIBRATED' 2>/dev/null | tail -1)"
[ -d "$CASE" ] || { echo "battery: cannot resolve case path"; exit 1; }
BASE="$CASE/res/Base_v12/csv"
REFORM="$CASE/res/PEP_v12/csv"
for d in "$BASE" "$REFORM"; do
    [ -d "$d" ] || { echo "battery: missing solved run $d"; exit 1; }
done

export OGCLEWS_MUIOGO_HOME="$(muiogo-ai status 2>/dev/null | awk '/^MUIOGO/{print $2}')"
export OGCLEWS_CLEWS_CASE="Philippines_v12_CALIBRATED"

# Ordered so the headline and its own decomposition land first: if the machine is
# lost partway, what survives is still interpretable.
EXPERIMENTS=(
    coupled                 # the full soft-link -- energy + investment + carbon + health
    energy_full_real        # the energy half of `coupled` alone (both transmission halves)
    energy_price            # route A: the household electricity wedge
    energy_cost_push_real   # route B: the inter-industry cost-push
    carbon                  # carbon price: OG consumption tax + CLEWS emissions penalty
    investment              # grid/transmission capex -> public capital
    health                  # PM2.5 -> mortality and morbidity (GBD 2023, now on disk)
    energy_price_tfp_real   # the price rise as electricity-industry productivity
    clean_incidence         # distributional incidence, revenue recycled
    capital_intensity       # permanent rise in the energy industry's capital share
    energy_capex            # generation buildout financed by an investment tax credit
)

LOGDIR="$LINK/ogclews_runs/_battery_logs"
mkdir -p "$LOGDIR"
SUMMARY="$LOGDIR/summary.tsv"
printf 'experiment\tstatus\tseconds\n' > "$SUMMARY"

echo "battery: ${#EXPERIMENTS[@]} experiments, workers=$W"
echo "battery: case   $CASE"
echo "battery: out    $OUT"
echo

for e in "${EXPERIMENTS[@]}"; do
    LOG="$LOGDIR/$e.log"
    # figures only for the headline; the component decks are not read and each
    # costs minutes across eleven runs
    FIG="--no-figures"; [ "$e" = "coupled" ] && FIG=""
    echo "=== $e  start $(date +%H:%M:%S) ==="
    T0=$(date +%s)
    "$LINK/.venv/bin/ogclews-link" run "$e" \
        --country phl \
        --clews-base "$BASE" \
        --clews-reform "$REFORM" \
        --clews-run "Philippines_v12_CALIBRATED/PEP_v12" \
        --workers "$W" \
        --out "$OUT" \
        $FIG > "$LOG" 2>&1
    RC=$?
    T=$(( $(date +%s) - T0 ))
    if [ $RC -eq 0 ]; then
        echo "=== $e  OK in ${T}s ==="
        printf '%s\tOK\t%s\n' "$e" "$T" >> "$SUMMARY"
    else
        # keep going: one channel failing must not cost the other ten
        echo "=== $e  FAILED rc=$RC after ${T}s (see $LOG) ==="
        tail -5 "$LOG" | sed 's/^/    /'
        printf '%s\tFAIL(%s)\t%s\n' "$e" "$RC" "$T" >> "$SUMMARY"
    fi
done

echo
echo "=== BATTERY COMPLETE ==="
column -t -s $'\t' "$SUMMARY"
