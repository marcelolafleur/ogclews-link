#!/bin/bash
# Run a MUIOGO solve with an expected duration and abort on overrun.
#
# Why this exists: a calibrated PHL case was left solving for 2.5 hours against a
# 2-4 minute baseline before anyone noticed. The information needed to catch it was
# already available -- earlier solves of the same case had been timed at 114s and
# 260s -- but the wait condition was "does results.txt exist yet", which is silent
# about elapsed time. A wait that cannot fail is not supervision.
#
# Usage:
#   solve_watchdog.sh <case> <run> [expected_seconds] [multiplier]
#
# Aborts when elapsed > expected * multiplier (default 5x), kills the solver, and
# exits 2 so a caller can distinguish overrun from solver failure.
#
# Exit codes: 0 optimal · 1 solver/setup failure · 2 overrun, aborted

set -u
CASE="${1:?case name}"
RUN="${2:?run name}"
EXPECT="${3:-300}"          # seconds; 300 is a safe default for this model family
MULT="${4:-5}"
LIMIT=$(( EXPECT * MULT ))

DS="$(muiogo-ai status 2>/dev/null | awk '/^model data/{print $3}')"
[ -n "$DS" ] || { echo "watchdog: cannot locate model data dir"; exit 1; }
RESULTS="$DS/$CASE/res/$RUN/results.txt"
LOG="$(mktemp -t solve_XXXX.log)"

rm -f "$RESULTS"
echo "watchdog: $CASE/$RUN  expect ${EXPECT}s  abort at ${LIMIT}s"
muiogo-ai run --case "$CASE" --run "$RUN" > "$LOG" 2>&1 &
CLI=$!
START=$(date +%s)

while :; do
    sleep 10
    NOW=$(( $(date +%s) - START ))

    if [ -f "$RESULTS" ]; then
        HEAD="$(head -1 "$RESULTS")"
        echo "watchdog: finished in ${NOW}s -- $HEAD"
        case "$HEAD" in
            Optimal*) exit 0 ;;
            *) echo "watchdog: NOT optimal"; exit 1 ;;
        esac
    fi

    if grep -qiE "infeasible|unbounded|error|traceback" "$LOG" 2>/dev/null; then
        echo "watchdog: solver reported a failure at ${NOW}s"
        grep -iE "infeasible|unbounded|error" "$LOG" | head -3
        exit 1
    fi

    # progress line every minute, so a stall is visible rather than silent
    if [ $(( NOW % 60 )) -lt 10 ]; then
        echo "  ... ${NOW}s elapsed (limit ${LIMIT}s)"
    fi

    if [ "$NOW" -gt "$LIMIT" ]; then
        echo "watchdog: OVERRUN -- ${NOW}s exceeds ${LIMIT}s (${MULT}x the ${EXPECT}s expectation)."
        echo "watchdog: this usually means the constraint set is over-determined."
        echo "watchdog: check slack -- sum(pins) + exogenous demand must be < the resource total."
        pkill -f "cbc .*$CASE/res/$RUN" 2>/dev/null
        kill $CLI 2>/dev/null
        exit 2
    fi
done
