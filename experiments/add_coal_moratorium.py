"""Encode the DOE coal moratorium in a PHL CLEWs case's COAL_PHASEOUT scenario layer.

Why: the PEP scenario package (BASE + COAL_PHASEOUT + RE + EV) reproduces the official
plan's RE share trajectory (35% by 2030, 50% by 2040), the nuclear program (1.2 GW by
2032, 2.4 by 2035, 4.8 by 2050) and an EV ramp -- but nothing encodes the October 2020
DOE moratorium on new greenfield coal plants. The RE-share rule is a SHARE constraint,
so the solved PEP run built 10.2 GW of NEW coal by 2030, which the real policy forbids
(only the already-committed pipeline, roughly 3 GW, was exempt).

What: writes TotalAnnualMaxCapacityInvestment (RYT.json TAMaxCI) for PHL_POW_PP_COAL in
the COAL_PHASEOUT scenario layer -- 999999 (open) through MORATORIUM_FROM-1 so the
committed pipeline can complete, 0 (forbidden) from MORATORIUM_FROM on. Every year cell
is written explicitly: MUIO persists/expands sparse cells, and an explicit row is
unambiguous under any fill convention (the all-zero PHL_POW_PP_NU row in the exported
datafile is the working exemplar that explicit zeros mean "forbidden").

Scenario-layer edit, not a base-case calibration -- deliberately NOT part of
calibrate_phl_case.py, which only touches SC_0 values. The base scenario keeps coal
investable so BASE remains a true no-policy counterfactual.

Usage:
    python add_coal_moratorium.py --case <path to a COPY of the case>
"""
import argparse
import json
from pathlib import Path

MORATORIUM_FROM = 2027   # committed-pipeline completion window ends 2026; DOE Advisory Oct 2020
OPEN = 999999            # the parameter's own default: unconstrained
TECH = "PHL_POW_PP_COAL"
SCENARIO = "COAL_PHASEOUT"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", required=True, type=Path, help="a COPY of the case")
    args = ap.parse_args()
    C = args.case
    if not (C / "genData.json").is_file():
        raise SystemExit(f"not a MUIO case: {C}")
    g = json.load(open(C / "genData.json"))
    sid = {s["Scenario"]: s["ScenarioId"] for s in g["osy-scenarios"]}[SCENARIO]
    tid = {t["Tech"]: t["TechId"] for t in g["osy-tech"]}[TECH]
    years = [str(y) for y in g["osy-years"]] if all(isinstance(y, (int, str)) for y in g["osy-years"]) else None
    if years and isinstance(g["osy-years"][0], dict):
        years = [str(y.get("Year") or y.get("year")) for y in g["osy-years"]]
    p = C / "RYT.json"
    d = json.load(open(p))
    rows = d["TAMaxCI"].setdefault(sid, [])
    row = next((r for r in rows if r.get("TechId") == tid), None)
    if row is None:
        row = {"TechId": tid}
        rows.append(row)
    already = {k: v for k, v in row.items() if k.isdigit() and isinstance(v, (int, float))}
    if already:
        print(f"note: overwriting {len(already)} existing cells: {already}")
    yr_keys = years or [k for k in row if k.isdigit()] or [str(y) for y in range(2020, 2054)]
    n_open = n_zero = 0
    for y in yr_keys:
        if int(y) < MORATORIUM_FROM:
            row[y] = OPEN; n_open += 1
        else:
            row[y] = 0; n_zero += 1
    json.dump(d, open(p, "w"), indent=1)
    print(f"moratorium written: {TECH} TAMaxCI in {SCENARIO} ({sid})")
    print(f"  {yr_keys[0]}..{MORATORIUM_FROM-1} = {OPEN} (committed pipeline)  [{n_open} cells]")
    print(f"  {MORATORIUM_FROM}..{yr_keys[-1]} = 0 (no new coal)              [{n_zero} cells]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
