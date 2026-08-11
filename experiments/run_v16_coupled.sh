#!/bin/bash
# The v16 "run" button: solve both CLEWs runs, verify them, then the coupled OG run.
#
# Prepared 2026-08-11. Everything up to the solves is already staged:
#   - Philippines_v16_CALIBRATED: v16 (checksum-verified against the repo's SHA256SUMS)
#     + the full calibration (calibrate_phl_case.py, water factor 14.4128 -- valid because
#     v16's land/water block is byte-identical to v12's source) + the coal moratorium
#     (add_coal_moratorium.py: no new coal from 2027; the shipped layer only banned it
#     from 2031 and the LP front-loaded 10.2 GW into the gap).
#   - Runs Base_v16 (BASE) and PEP_v16 (BASE+COAL_PHASEOUT+RE+EV) defined.
#   - OG stack: OG-PHL calib/multi-industry-remittances, ogcore 0.19.1 + PR#1189 +
#     revert of PR#1184 (the payroll double count, PSLmodels/OG-Core#1199).
#   - OG baseline cache is stack-keyed and CLEWS-independent -> reused, so the coupled
#     step is a reform-only solve.
#
# Usage: run_v16_coupled.sh [workers]
set -u
cd "$(dirname "$0")/.." || exit 1
LINK="$PWD"
W="${1:-7}"
CASE_NAME="Philippines_v16_CALIBRATED"
DS="$(muiogo-ai status 2>/dev/null | awk '/^model data/{print $3}')"
CASE="$DS/$CASE_NAME"
PHLPY="/Users/marcelolafleur/Projects/OG-PHL/.venv/bin/python"

fail() { echo "PREFLIGHT FAILED: $*" >&2; exit 1; }

echo "=== PREFLIGHT ==="
# 1. ogcore build fingerprint: the payroll revert must be active, #1189 present.
$PHLPY - <<'PY' || fail "ogcore fingerprint"
import inspect, ogcore
from ogcore import aggregates
from ogcore.parameters import Specifications
src = inspect.getsource(aggregates)
assert "iit_payroll_tax_revenue += payroll_tax_revenue" not in src, \
    "payroll double count present -- ogcore was reinstalled (uv sync?); reinstall ~/Projects/OG-Core-1189"
assert hasattr(Specifications(), "initial_wealth_ratio"), "PR#1189 missing from installed ogcore"
print(f"  ogcore {ogcore.__version__}: #1184 reverted, #1189 present  OK")
PY
# 2. Repo positions (informational + hard assert on the OG-PHL branch).
for d in /Users/marcelolafleur/Projects/OG-PHL /Users/marcelolafleur/Projects/OG-Core-1189 "$LINK"; do
    echo "  $(basename $d): $(git -C $d rev-parse --abbrev-ref HEAD) @ $(git -C $d rev-parse --short HEAD) ($(git -C $d status --porcelain | wc -l | tr -d ' ') dirty)"
done
[ "$(git -C /Users/marcelolafleur/Projects/OG-PHL rev-parse --abbrev-ref HEAD)" = "calib/multi-industry-remittances" ] \
    || fail "OG-PHL is not on calib/multi-industry-remittances"
# 3. Link stack: couplable model, GBD data.
(cd "$LINK" && .venv/bin/ogclews-link models list 2>/dev/null | grep -q "couplable=1") || fail "no couplable OG model registered"
ls "$LINK"/IHME-GBD_2023_DATA/*.csv >/dev/null 2>&1 || fail "GBD export missing"
# 4. Case staged: calibration marker (discount rate 0.10) + moratorium cells.
python3 - "$CASE" <<'PY' || fail "case staging"
import json, sys
C = sys.argv[1]
r = json.load(open(f"{C}/R.json"))
assert abs(r["DR"]["SC_0"][0]["value"] - 0.10) < 1e-9, "calibration not applied (DR != 0.10)"
g = json.load(open(f"{C}/genData.json"))
t = {x["Tech"]: x["TechId"] for x in g["osy-tech"]}
d = json.load(open(f"{C}/RYT.json"))
row = next(x for x in d["TAMaxCI"]["SC_3hgjb"] if x.get("TechId") == t["PHL_POW_PP_COAL"])
assert row.get("2027") == 0 and row.get("2026") == 999999, "moratorium cells wrong"
print("  case: calibration + moratorium staged  OK")
PY
echo "=== PREFLIGHT PASSED ==="

echo; echo "=== CLEWS SOLVES ==="
for r in Base_v16 PEP_v16; do
    bash "$LINK/experiments/solve_watchdog.sh" "$CASE_NAME" "$r" 400 5 || exit 1
done

echo; echo "=== CLEWS VERIFICATION GATES ==="
python3 - "$CASE" <<'PY' || { echo "CLEWS GATES FAILED -- do not couple these results" >&2; exit 1; }
import csv, json, sys
C = sys.argv[1]
def col(run, fname, tech=None):
    out = {}
    val = fname[:-4]
    for row in csv.DictReader(open(f"{C}/res/{run}/csv/{fname}")):
        if tech is None or row["t"] == tech:
            out[row["y"]] = out.get(row["y"], 0.0) + float(row[val])
    return out
# gate 1: no new coal after 2026 in PEP (the moratorium, end to end)
nc = col("PEP_v16", "NewCapacity.csv", "PHL_POW_PP_COAL")
late = {y: v for y, v in nc.items() if int(y) >= 2027 and v > 1e-6}
assert not late, f"moratorium violated: new coal {late}"
pre = sum(v for y, v in nc.items() if int(y) <= 2026)
print(f"  gate moratorium: no new coal 2027+; pre-2027 pipeline {pre:.2f} GW  OK")
# gate 2: offshore wind respects the ESMAP cap (PJ activity)
for run in ("Base_v16", "PEP_v16"):
    pa = col(run, "TotalTechnologyAnnualActivity.csv", "PHL_POW_PP_WOF_T1")
    mx = max(pa.values() or [0])
    assert mx <= 823.0 + 1e-6, f"{run}: offshore wind activity {mx:.1f} > 823 PJ cap"
print("  gate offshore cap: <= 823 PJ in both runs  OK")
# gate 3: land closure (total land activity vs the national total)
la = col("Base_v16", "TotalTechnologyAnnualActivity.csv", "MINLNDTOT")
v2020 = la.get("2020", 0)
assert abs(v2020 - 295.8131) < 0.01, f"land closure {v2020} != 295.8131"
print(f"  gate land closure: {v2020:.4f}  OK")
print("  (energy-mix and water-withdrawal comparisons: report, not gate -- see analysis step)")
PY

echo; echo "=== COUPLED RUN ==="
cd "$LINK"
.venv/bin/ogclews-link run coupled \
    --country phl \
    --clews-base   "$CASE/res/Base_v16/csv" \
    --clews-reform "$CASE/res/PEP_v16/csv" \
    --clews-run    "$CASE_NAME/PEP_v16" \
    --workers "$W" \
    --out ./ogclews_runs_v16 || exit 1

echo; echo "=== RESULT ==="
cat ./ogclews_runs_v16/coupled/macro_table.csv
echo; echo "figures: ./ogclews_runs_v16/coupled/figures/"
