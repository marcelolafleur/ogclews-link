#!/bin/bash
# Emit one status line per interval for a running OG-CLEWS stack.
#
# Why: two long runs in this session went unreported -- a CLEWs solve that ran 2.5
# hours against a 4-minute baseline, and an OG steady state that cycled 247 times
# without converging. Both were visible in their logs the whole time. A run with no
# heartbeat is a run nobody is watching.
#
# One line per interval, designed to be read at a glance:
#   [mm:ss] CLEWS base=OK pep=solving | OG ss iter=247 maxerr=2.6e+00 STALLED(13)
#
# Usage: run_status.sh <og-log> [interval_seconds] [case]
set -u
LOG="${1:?og log path}"
INT="${2:-60}"
CASE="${3:-Philippines_v12_CALIBRATED}"
DS="$(muiogo-ai status 2>/dev/null | awk '/^model data/{print $3}')"
START=$(date +%s)
PREV=""
BESTERR=""
NOIMPROVE=0
STALL_INTERVALS=$(( 900 / INT ))   # flag only after ~15 min with no improvement

clews_state() {
    local out=""
    for r in Base_v12 PEP_v12; do
        local f="$DS/$CASE/res/$r/results.txt"
        if [ -f "$f" ]; then
            case "$(head -1 "$f")" in
                Optimal*) out="$out ${r%%_v12}=OK" ;;
                *)        out="$out ${r%%_v12}=NOTOPTIMAL" ;;
            esac
        elif pgrep -f "cbc .*$CASE/res/$r" >/dev/null 2>&1; then
            out="$out ${r%%_v12}=solving"
        else
            out="$out ${r%%_v12}=-"
        fi
    done
    echo "$out"
}

while :; do
    NOW=$(( $(date +%s) - START ))
    MM=$(printf "%02d:%02d" $((NOW/60)) $((NOW%60)))

    # Progress metric: continuation steps and converged SS solves -- NOT "GE loop
    # errors". Those are per-iteration diagnostics, not failures; the og-solver-
    # diagnosis skill names this exact trap and I fell into it, calling a healthy
    # run stalled because a benign diagnostic plateaued. The real convergence signal
    # is the "Distance:" line, which reads ~1e-10 on a converged steady state.
    STEPS=$(grep -c "continuation t=" "$LOG" 2>/dev/null); STEPS=${STEPS:-0}
    GEN=$(grep -c "GE loop errors" "$LOG" 2>/dev/null); GEN=${GEN:-0}
    TPOS=$(grep -oE "continuation t=[0-9.]+" "$LOG" 2>/dev/null | tail -1 | cut -d= -f2)
    [ -n "$TPOS" ] || TPOS="0"
    SSOK=$(grep -cE "^Iteration: 1 " "$LOG" 2>/dev/null); SSOK=${SSOK:-0}
    LASTDIST=$(grep -oE "Distance:\s*[0-9.e+-]+" "$LOG" 2>/dev/null | tail -1 | awk "{print \$2}")
    [ -n "$LASTDIST" ] || LASTDIST="-"
    PHASE="baseline-continuation"
    grep -q "run_TPI\|Time path" "$LOG" 2>/dev/null && PHASE="TPI"
    grep -q "continuation from the baseline" "$LOG" 2>/dev/null && PHASE="reform-continuation"
    MAXERR="$LASTDIST"
    LAST="$STEPS"

    # Liveness test. Two earlier versions of this were wrong, both by watching a
    # metric that does not move during normal work:
    #   v1 watched identical "GE loop errors" vectors -- but the solver plateaus by
    #      design, so identical vectors are not a stall.
    #   v2 watched "best distance so far" -- but distance only updates when a
    #      continuation STEP COMPLETES, so a long step looks like stagnation. It
    #      false-alarmed on a run that was demonstrably alive.
    # The only reliable signal is whether the log is still being written to: GE
    # iterations accumulating, or a step completing. Flag only if BOTH are frozen.
    PROGRESS="${STEPS}:${GEN}"
    if [ "$PROGRESS" = "$PREV" ]; then
        NOIMPROVE=$((NOIMPROVE+1))
    else
        NOIMPROVE=0
    fi
    PREV="$PROGRESS"

    FLAG=""
    # no improvement in the best-ever max error across this many intervals
    [ "$NOIMPROVE" -ge "$STALL_INTERVALS" ] && \
        FLAG=" FROZEN($((NOIMPROVE*INT/60))min: no GE iterations AND no step)"
    # Only real failures. "Failed to retrieve population data from UN" is a benign
    # startup warning that fires on every run and would otherwise flag every line.
    grep -qiE "Traceback|MemoryError|KeyboardInterrupt|Segmentation" "$LOG" 2>/dev/null \
        && FLAG="$FLAG ERROR-IN-LOG"
    ls ogclews_runs/*/macro_table.csv >/dev/null 2>&1 && FLAG="$FLAG OUTPUT-WRITTEN"

    echo "[$MM] CLEWS$(clews_state) | OG $PHASE t=$TPOS steps=$STEPS ge=$GEN dist=$LASTDIST$FLAG"

    # stop when the deliverable exists, or the process is gone
    ls ogclews_runs/*/macro_table.csv >/dev/null 2>&1 && { echo "[$MM] DONE -- macro_table.csv written"; exit 0; }
    pgrep -f "ogclews_link|ogclews-link" >/dev/null 2>&1 || { echo "[$MM] run process gone"; exit 1; }
    sleep "$INT"
done
