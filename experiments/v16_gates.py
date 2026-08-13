"""Post-solve verification gates for the v16 runs, against MUIOGO's ACTUAL export set.

Extracted from run_v16_coupled.sh after two lessons: (1) the inline gates raced the CSV
export -- the watchdog returns on results.txt, the csv/ dir fills just after, so gates must
wait for the export to settle; (2) the v16 export set differs from v12's (activity comes
per-mode via TotalAnnualTechnologyActivityByMode; EmissionByActivityChange is exported
directly now that the case carries EACR). Filenames here are verified against a real
PEP_v16 result, not assumed.

Exit 0 = all gates pass. Reports (stickiness, zero-trap) always print; they are not gates.
"""
import csv
import os
import sys
import time

CASE = sys.argv[1] if len(sys.argv) > 1 else \
    "/Users/marcelolafleur/muiogoai/MUIOGO/WebAPP/DataStorage/Philippines_v16_CALIBRATED"
LAND_TOTAL = 295.8131


def settle(run, files, timeout=120):
    """Wait until every expected export exists and sizes stop changing."""
    d = f"{CASE}/res/{run}/csv"
    t0 = time.time()
    prev = None
    while time.time() - t0 < timeout:
        sizes = {f: os.path.getsize(os.path.join(d, f)) for f in files
                 if os.path.exists(os.path.join(d, f))}
        if len(sizes) == len(files) and sizes == prev:
            return
        prev = sizes
        time.sleep(3)
    missing = [f for f in files if not os.path.exists(os.path.join(d, f))]
    raise SystemExit(f"export did not settle for {run}: missing {missing}")


def by_year(run, fname, tech, val=None, where=None):
    """Sum a result variable per year for one technology (over modes/emissions if present)."""
    val = val or fname[:-4]
    out = {}
    with open(f"{CASE}/res/{run}/csv/{fname}") as fh:
        for row in csv.DictReader(fh):
            if row["t"] != tech:
                continue
            if where and not where(row):
                continue
            out[row["y"]] = out.get(row["y"], 0.0) + float(row[val])
    return out


NEEDED = ["NewCapacity.csv", "TotalAnnualTechnologyActivityByMode.csv",
          "EmissionByActivityChange.csv", "AccumulatedNewCapacity.csv"]
for run in ("Base_v16", "PEP_v16"):
    settle(run, NEEDED)

ok = True

# gate 1: the coal moratorium, end to end -- no NEW coal capacity from 2027 in PEP.
nc = by_year("PEP_v16", "NewCapacity.csv", "PHL_POW_PP_COAL")
late = {y: v for y, v in nc.items() if int(y) >= 2027 and v > 1e-6}
pre = sum(v for y, v in nc.items() if int(y) <= 2026)
if late:
    ok = False
    print(f"GATE FAIL moratorium: new coal after 2026: {dict(sorted(late.items())[:4])}")
else:
    print(f"  gate moratorium: no new coal 2027+; pre-2027 pipeline {pre:.2f} GW  OK")

# gate 2: offshore wind activity respects the ESMAP cap in both runs.
for run in ("Base_v16", "PEP_v16"):
    act = by_year(run, "TotalAnnualTechnologyActivityByMode.csv", "PHL_POW_PP_WOF_T1")
    mx = max(act.values() or [0.0])
    if mx > 823.0 + 1e-6:
        ok = False
        print(f"GATE FAIL offshore cap ({run}): {mx:.1f} PJ > 823")
    else:
        print(f"  gate offshore cap ({run}): max {mx:.1f} <= 823 PJ  OK")

# gate 3: land closure every year, plus the country-area sanity band on summed classes.
la = by_year("Base_v16", "TotalAnnualTechnologyActivityByMode.csv", "MINLNDTOT")
bad = {y: v for y, v in la.items() if abs(v - LAND_TOTAL) > 0.01}
if bad:
    ok = False
    print(f"GATE FAIL land closure: {dict(sorted(bad.items())[:3])}")
else:
    print(f"  gate land closure (all {len(la)} years): {LAND_TOTAL}  OK")
tot = {}
with open(f"{CASE}/res/Base_v16/csv/TotalAnnualTechnologyActivityByMode.csv") as fh:
    for row in csv.DictReader(fh):
        t = row["t"]
        if t.startswith("LND") and t.endswith("TOT") and t != "LNDWATTOT" and t != "MINLNDTOT" \
           or t == "LNDWATTOT":
            pass  # class techs enumerated below instead; naming varies by build
allland = {}
with open(f"{CASE}/res/Base_v16/csv/TotalAnnualTechnologyActivityByMode.csv") as fh:
    for row in csv.DictReader(fh):
        if row["t"].startswith("LND"):
            allland.setdefault(row["t"], {})
            y = row["y"]
            allland[row["t"]][y] = allland[row["t"]].get(y, 0.0) + \
                float(row["TotalAnnualTechnologyActivityByMode"])
# NOTE on the sanity band: the LND*TOT techs are NOT a disjoint partition in this build
# (per-crop/per-input-level aggregates overlap the cover classes), so summing them is
# meaningless -- the first version of this gate failed on exactly that. The physical
# accounting check IS the closure gate above: MINLNDTOT pinned to the endowment on both
# sides and verified equal every year. A plausibility band on any one class (e.g. forest
# within FRA-neighbourhood) belongs to analysis, not a hard gate.

# gate 4: the EACR gate-year assumption -- forest declines monotonically from 2021.
fo = allland.get("LNDFORTOT", {})
ys = sorted(fo)
rises = [(ys[i], ys[i + 1]) for i in range(1, len(ys) - 1) if fo[ys[i + 1]] > fo[ys[i]] + 0.5]
if rises:
    ok = False
    print(f"GATE FAIL forest path rises after 2021 at {rises[:3]} -- re-derive the EACR gate year "
          f"or move to the one-way flow tech (plan section 14 priority 3)")
else:
    print(f"  gate forest path: monotone decline from 2021 ({fo[ys[1]]:.1f} -> {fo[ys[-1]]:.1f})  OK")

# gate 5: conversion carbon is actually booked (EACR survived the generator, end to end).
ebc = by_year("Base_v16", "EmissionByActivityChange.csv", "LNDFORTOT",
              where=lambda r: r.get("e") in ("EMI_0", "CO2e"))
booked = sum(v for y, v in ebc.items() if int(y) >= 2022)
if booked <= 100:
    ok = False
    print(f"GATE FAIL conversion carbon: only {booked:.1f} Mt booked 2022+ -- EACR dropped?")
else:
    print(f"  gate conversion carbon: {booked:.0f} Mt CO2e booked 2022-2053  OK")

# report: stickiness diagnostic (not a gate) -- feeds land-stickiness-options.md b/c/f.
steps = sorted(((fo[ys[i]] - fo[ys[i + 1]], f"{ys[i]}->{ys[i + 1]}")
                for i in range(1, len(ys) - 1)), reverse=True)
if steps:
    mean = sum(v for v, _ in steps) / len(steps)
    print(f"  report forest stickiness: max annual loss {steps[0][0]:.2f} kkm2 ({steps[0][1]}), "
          f"top3 {[f'{v:.1f}@{y}' for v, y in steps[:3]]}, mean {mean:.2f}")

# report: LU3 zero-trap candidates.
zeros = sorted(t for t, yrs in allland.items() if sum(abs(v) for v in yrs.values()) < 1e-9)
print(f"  report LU3 zero-trap candidates: {zeros or 'none'}")

sys.exit(0 if ok else 1)
