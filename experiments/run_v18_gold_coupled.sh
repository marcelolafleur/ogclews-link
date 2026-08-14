#!/bin/bash
# The v18 GOLD "run" button: verify the blessed CLEWs results READ-ONLY, then the coupled OG run.
#
# Patterned on run_v16_coupled.sh (ieem branch) with the differences the gold blessing dictates:
#   - NO CLEWs solves here. Philippines_v18_GOLD runs GOLD_BASE / GOLD_PEP are solved and
#     BLESSED (docs/design/gold-baseline-v18_0_1.md, ieem branch, 2026-08-14). This script only
#     re-verifies them read-only (status Optimal + the blessed objectives, byte-for-byte) and
#     re-checks the physical gates from the CSVs before coupling.
#   - Coal moratorium gate year is 2028 (v18 GOLD: DOE 2024b exemption window), not v16's 2027.
#   - CONVERSION CARBON IS EXCLUDED from everything downstream (blessing constraint 1): the
#     -104 Mt land series is identical in both runs (verified below), is unpriced, and MUST NOT
#     be quoted or fed to any channel. The coupled run's carbon inputs are combustion-only.
#   - Carbon/investment MAGNITUDES carry the "illustrative until audited" unit-deflator caveat
#     (blessing constraint 2); share-of-GDP numbers are fine. The caveat is stamped into the
#     run notes file next to the manifest.
#
# Usage: run_v18_gold_coupled.sh [--run] [workers]
# DEFAULT IS PREFLIGHT-ONLY: without an explicit --run the script verifies everything and
# stops before the solve (adversarial review F2/F9 -- a multi-hour solve must never start
# because someone invoked the script expecting a refusal or mistyped an argument).
set -u
cd "$(dirname "$0")/.." || exit 1
LINK="$PWD"
W=7
PREFLIGHT_ONLY=1
for arg in "$@"; do
    case "$arg" in
        --run) PREFLIGHT_ONLY="" ;;
        --preflight-only) PREFLIGHT_ONLY=1 ;;
        [0-9]|[0-9][0-9]) W="$arg" ;;
        *) echo "unknown argument: $arg (usage: run_v18_gold_coupled.sh [--run] [workers])" >&2; exit 2 ;;
    esac
done
CASE_NAME="Philippines_v18_GOLD"
CASE="$(muiogo-ai case-path --case "$CASE_NAME")" || { echo "case not found in the muiogo-ai world" >&2; exit 1; }
OUT="$LINK/ogclews_runs_v18gold"

fail() { echo "PREFLIGHT FAILED: $*" >&2; exit 1; }

echo "=== PREFLIGHT ==="
# 0. Import shadowing: the link venv must resolve ogclews_link inside THIS worktree.
"$LINK"/.venv/bin/python - "$LINK" <<'PY' || fail "link import shadowed"
import os, sys, ogclews_link
res = os.path.realpath(os.path.dirname(ogclews_link.__file__))
want = os.path.realpath(sys.argv[1])
assert res.startswith(want + os.sep), f"ogclews_link resolved OUTSIDE this worktree: {res}"
print(f"  ogclews_link -> {res}  OK")
PY
# 1. HEALTH-FIX GUARD: the coupled/health runs must NOT launch on link code that predates the
#    income_percentiles fixes (main lacks them; they live on the ieem branch, commits eb63dad,
#    28d83d4, a23e0ae, 034b662). Without them the health mortality shock silently skips or
#    crashes — the pre-2026-08-11 defect the coordination file warns about.
grep -q "income_percentiles" "$LINK/ogclews_link/health_pop.py" \
    || fail "health fixes absent from this checkout (income_percentiles not in health_pop.py) — merge the ieem branch's link fixes before running"
echo "  health fixes present (income_percentiles in health_pop.py)  OK"
# 2. ogcore build fingerprint via the registry's own interpreter: payroll revert + #1189.
PHLPY="$("$LINK"/.venv/bin/python -c "
from ogclews_link import registry
from ogclews_link.country import PHL
print(registry.lookup(PHL).env_python)")" || fail "registry lookup"
"$PHLPY" - <<'PY' || fail "ogcore fingerprint"
import inspect, ogcore
from ogcore import aggregates
from ogcore.parameters import Specifications
src = inspect.getsource(aggregates)
assert "iit_payroll_tax_revenue += payroll_tax_revenue" not in src, \
    "payroll double count present -- ogcore was reinstalled (uv sync?); reinstall the fixed build"
assert hasattr(Specifications(), "initial_wealth_ratio"), "PR#1189 missing from installed ogcore"
print(f"  ogcore {ogcore.__version__}: #1184 reverted, #1189 present  OK")
PY
# 3. Repo positions (informational + hard asserts on both branches).
OGPHL_DIR="$(dirname "$(dirname "$PHLPY")")"; OGPHL_DIR="$(dirname "$OGPHL_DIR")"  # .venv/bin/python -> repo
for d in "$OGPHL_DIR" "$LINK"; do
    echo "  $(basename "$d"): $(git -C "$d" rev-parse --abbrev-ref HEAD) @ $(git -C "$d" rev-parse --short HEAD) ($(git -C "$d" status --porcelain | wc -l | tr -d ' ') dirty)"
done
[ "$(git -C "$OGPHL_DIR" rev-parse --abbrev-ref HEAD)" = "calib/multi-industry-remittances" ] \
    || fail "OG-PHL is not on calib/multi-industry-remittances"
# 4. The two open OG-PHL calibration PRs (Marcelo, 2026-08-14): the local branch must contain
#    the head of EAPD-DRB/OG-PHL#63 (the 8-sector SAM calibration) and #85 (remittances +
#    revenue side). Live check via gh; degrade to a loud warning offline.
for pr in 63 85; do
    oid="$(gh pr view "$pr" --repo EAPD-DRB/OG-PHL --json headRefOid --jq .headRefOid 2>/dev/null)"
    if [ -n "$oid" ]; then
        git -C "$OGPHL_DIR" merge-base --is-ancestor "$oid" HEAD \
            || fail "OG-PHL branch does not contain PR#$pr head $oid -- fetch and merge before running"
        echo "  OG-PHL contains PR#$pr head ${oid:0:8}  OK"
    else
        echo "  WARNING: could not query PR#$pr head (offline?) -- ancestry unverified" >&2
    fi
done
# 5. The registry must serve the 8-sector multisector calibration, and the Anderson house
#    rule must be active in the runner (every SS solve; examples-script path, nothing bespoke).
"$LINK"/.venv/bin/python - "$OGPHL_DIR" <<'PY' || fail "registry calibration / Anderson config"
import json, sys, os
r = json.load(open("og_model_registry.json"))
m = r["models"]["og-phl"]
assert m["calibration"] == "ogphl_multisector_default_parameters.json", m["calibration"]
cand = [c for c in m["discovered"]["candidates"] if c["file"] == m["calibration"]][0]
assert cand["M"] == 8 and cand["couplable"], (cand["M"], cand["couplable"])
# Anderson where it is PROVEN: the calibration must pin the TPI outer loop to anderson
# (nu=0.2) and must NOT have its explicit SS hybr choice force-overridden (the forced
# SS-anderson crashed the first GOLD baseline -- scipy's line search raises on NaN trial
# residuals; see og_runner._load_calibration).
over = json.load(open(os.path.join(sys.argv[1], "ogphl",
                                   "ogphl_multisector_default_parameters.json")))
assert over.get("TPI_outer_method") == "anderson" and over.get("nu") == 0.2, \
    (over.get("TPI_outer_method"), over.get("nu"))
src = open("ogclews_link/og_runner.py").read()
assert '"SS_root_method": "anderson"' not in src or "OGCLEWS_SS_ROOT_METHOD" in src, \
    "forced SS-anderson override present in og_runner"
print("  registry: 8-sector multisector calibration, couplable; TPI Anderson (nu=0.2) pinned "
      "by the calibration; SS root = calibration's hybr  OK")
PY
# 6. Link stack: couplable model, GBD data.
(cd "$LINK" && .venv/bin/ogclews-link models list 2>/dev/null | grep -q "couplable=1") || fail "no couplable OG model registered"
ls "$LINK"/IHME-GBD_2023_DATA/*.csv >/dev/null 2>&1 || fail "GBD export missing"
# 7. HEALTH CHANNEL ACTIVE (Marcelo, 2026-08-14): the blessed export must resolve (a2dc02fe,
#    the one every blessed health number used -- NOT main's a20a92ea; the resolver takes
#    min(glob), so both being present would silently pick the wrong one), the PHL
#    dose-response must exist, and health must be in the coupled composition. The run-time
#    skip (demographics fallback -> _pop_aux None) is caught POST-SOLVE below.
"$LINK"/.venv/bin/python - <<'PY' || fail "health channel activation"
import json
from ogclews_link.country import _resolve_gbd_csv
p = _resolve_gbd_csv()
assert p and "a2dc02fe" in p, f"GBD export is not the blessed a2dc02fe: {p}"
d = json.load(open("ogclews_link/data/pm25_health.json", encoding="utf-8-sig"))
m = (d["countries"].get("PHL") or d["countries"].get("Philippines"))["multiplier_M"]
assert m and m > 0, "PHL dose-response multiplier missing"
src = open("ogclews_link/experiments.py").read()
body = src[src.index("def coupled("):]
body = body[:body.index("\ndef ", 10)]
assert "channels.health(ctx)" in body, "health not in the coupled composition"
print(f"  health channel: GBD a2dc02fe resolves, PHL M={m}, in coupled composition  OK")
PY

echo; echo "=== GOLD RESULTS VERIFICATION (read-only) ==="
# Objectives must match the blessed record byte-for-byte (gold-baseline-v18_0_1.md).
# A mismatch means the case was re-solved or touched since the blessing: STOP, do not couple.
python3 - "$CASE" <<'PY' || { echo "GOLD VERIFICATION FAILED -- do not couple" >&2; exit 1; }
import csv, sys
C = sys.argv[1]
BLESSED = {"GOLD_BASE": "369743573.76858455", "GOLD_PEP": "369768776.18807554"}
for run, obj in BLESSED.items():
    line = open(f"{C}/res/{run}/results.txt").readline()
    assert "Optimal" in line and obj in line, f"{run}: blessed objective not found: {line.strip()}"
    print(f"  {run}: Optimal, objective matches the blessed record  OK")

def col(run, fname, tech=None):
    out, val = {}, fname[:-4]
    for row in csv.DictReader(open(f"{C}/res/{run}/csv/{fname}")):
        if tech is None or row["t"] == tech:
            out[row["y"]] = out.get(row["y"], 0.0) + float(row[val])
    return out

# gate: no new coal from 2028 in PEP (v18 GOLD moratorium year)
nc = col("GOLD_PEP", "NewCapacity.csv", "PHL_POW_PP_COAL")
assert nc, "no PHL_POW_PP_COAL rows in NewCapacity.csv -- tech name changed?"
late = {y: v for y, v in nc.items() if int(y) >= 2028 and v > 1e-6}
assert not late, f"moratorium violated: new coal {late}"
print(f"  gate moratorium: no new coal 2028+ in GOLD_PEP  OK")
# gate: offshore wind <= 823 PJ activity, both runs, every year (v18 exports activity
# BY MODE only, col() sums the modes; v18 tech name is PHL_POW_PP_WOF, no _T1 suffix)
for run in ("GOLD_BASE", "GOLD_PEP"):
    pa = col(run, "TotalAnnualTechnologyActivityByMode.csv", "PHL_POW_PP_WOF")
    mx = max(pa.values() or [0])
    assert pa, f"{run}: no PHL_POW_PP_WOF rows -- tech name changed again?"
    assert mx <= 823.0 + 1e-6, f"{run}: offshore activity {mx:.1f} > 823 PJ"
print("  gate offshore cap: <= 823 PJ in both runs  OK")
# CONVERSION-CARBON EXCLUSION GUARD (blessing constraint 1): the land series must be
# identical in both runs (so excluding it cannot change any base-vs-policy difference),
# and this script must state its exclusion rather than let it pass silently.
try:
    fb = col("GOLD_BASE", "AnnualTechnologyEmission.csv", "LNDFORTOT")
    fp = col("GOLD_PEP",  "AnnualTechnologyEmission.csv", "LNDFORTOT")
    assert all(abs(fb[y] - fp.get(y, 0.0)) < 1e-9 for y in fb), \
        "conversion-carbon series DIFFERS between runs -- the exclusion assumption broke; STOP"
    print("  conversion carbon: identical in both runs; EXCLUDED from all coupled inputs "
          "(v18.0.1 net-growing forest + symmetric EACR; one-way redesign pending)  OK")
except FileNotFoundError:
    print("  conversion carbon: no emission CSV -- nothing to exclude  OK")
PY

[ -n "${PREFLIGHT_ONLY:-}" ] && { echo; echo "=== PREFLIGHT-ONLY: stopping before the coupled solve ==="; exit 0; }

echo; echo "=== COUPLED RUN (GOLD_BASE vs GOLD_PEP) ==="
cd "$LINK"
.venv/bin/ogclews-link run coupled \
    --country phl \
    --clews-base   "$CASE/res/GOLD_BASE/csv" \
    --clews-reform "$CASE/res/GOLD_PEP/csv" \
    --clews-run    "$CASE_NAME/GOLD_PEP" \
    --workers "$W" \
    --out "$OUT" || exit 1

# POST-SOLVE GATE: health must have actually APPLIED (the 2026-08-11 defect was a SILENT skip).
# The manifest's channels list + provenance are the authoritative applied-channels record.
python3 - "$OUT" <<'PY' || { echo "HEALTH DID NOT APPLY -- do not bless this run" >&2; exit 1; }
import glob, json, sys
hits = glob.glob(f"{sys.argv[1]}/coupled/**/*manifest*.json", recursive=True)
assert hits, "no run manifest found under the coupled output"
man = json.load(open(max(hits)))
ids = [c.get("id") for c in man.get("channels", [])]
assert "health" in ids, f"health missing from applied channels: {ids}"
hp = [pr for pr in man.get("provenance", []) if pr.get("channel") == "health"]
assert hp, "no health provenance record"
assert not hp[0].get("skipped"), f"health SKIPPED: {hp[0].get('reason')}"
tgt = hp[0].get("mortality_excess_deaths")
assert tgt not in (None, 0), f"health applied but mortality_excess_deaths is empty: {hp[0]}"
print(f"  post-solve gate: health APPLIED, mortality_excess_deaths {tgt}  OK")
PY

# Stamp the blessing caveats next to the manifest so no deliverable is built without them.
cat > "$OUT/coupled/RUN_NOTES.md" <<'NOTES'
# Run notes — coupled GOLD_BASE vs GOLD_PEP (Philippines, current calibration)
- PRICE SIGN: in this calibration the policy package makes electricity MORE expensive
  (reform/base levelized price ~1.13 rising to ~1.24 over the window) — the OPPOSITE
  sign of earlier iterations' "cheaper power". No sign expectation carried over from
  prior run records is valid; every deliverable states the direction from THIS record.
- Conversion carbon (land series, −104 Mt, identical in both runs) is EXCLUDED from every
  input and every deliverable of this run. Where a land-carbon channel would have appeared,
  say that it is excluded pending the one-way accounting redesign.
- Carbon and investment MAGNITUDES are illustrative until the unit deflator is audited;
  share-of-GDP numbers are fine to quote.
- Results prose describes the current calibration only — no version tags in any deliverable.
NOTES

echo; echo "=== RESULT ==="
cat "$OUT/coupled/macro_table.csv"
echo; echo "figures: $OUT/coupled/figures/   notes: $OUT/coupled/RUN_NOTES.md"
