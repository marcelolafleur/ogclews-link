"""Option A test: price forest-conversion carbon in the PHL CALIBRATED case.

Design (docs/design/phl-testcase-plan.md §12): forest must stay FREE -- no constraint
touches it. Conversion carbon enters through OSeMOSYS's inter-year activity-change
emission (E10 in model.v.5.4.txt):

    (Activity[t,m,y] - Activity[t,m,y-1]) * EACR[t,e,m,y] = EmissionByActivityChange

so EACR = -29.2 MTon CO2e per 10^3 km^2 on (LNDFORTOT, mode 1) makes each unit of
forest DECLINE emit +29.2 MTon = 292 tCO2/ha, the Philippine FRL gross deforestation
factor (UNFCCC FCCC/TAR/2023/PHL). Sign note: the mechanism is symmetric, so forest
regrowth would earn a credit at the same rate; in this model forest only declines.
First model year is zeroed by E11 (no phantom emission from initial allocation).

Three single-edit copies of Philippines_v12_CALIBRATED, one solve each; the control
is the source case's already-solved Base_v12:

    FC_ACCT    EACR only, unpriced   -> allocation must be IDENTICAL to control;
                                        CO2e rises by ~29.2 x annual forest decline
    FC_TAX     EP=30 USD/tCO2 only   -> the energy system responds to a carbon price
                                        that cannot see land carbon
    FC_TAXLUC  both                  -> TAXLUC vs TAX isolates the forest response

Units verified against the case: currency USD (values in millions), emissions MTon,
so EP=30 (million USD per MTon) = $30/tCO2 exactly, and 29.2 MTon/10^3km^2 = 292 t/ha.
The CO2e AEL is a 999999 placeholder in every year (never binding; solved max 243.2).

Usage (from the worktree, its own venv):
    uv run python experiments/forest_carbon_patch.py           # copy + patch + verify
    uv run python experiments/forest_carbon_patch.py --solve   # ... then solve all three

Copies are created fresh; the script refuses to overwrite an existing copy so a
re-run cannot clobber solved results. The source case is never written to.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ogclews_link.clews_driver import copy_case

DATA_STORAGE = "/Users/marcelolafleur/muiogoai/MUIOGO/WebAPP/DataStorage"
SRC = "Philippines_v12_CALIBRATED"

FOREST_TECH = "TEC_hjgww"   # LNDFORTOT, operates in mode 1 only (IAR/OAR verified)
CO2E = "EMI_0"              # CO2e, MTon
FOREST_MODE = 1
EACR_VALUE = -29.2          # MTon CO2e per 10^3 km^2 of forest CHANGE (see docstring)
EP_VALUE = 30.0             # million USD per MTon = $30/tCO2
RUN = "Base_v12"            # activates only the BASE scenario in every copy

# The CALIBRATED case's solved forest path jumps 72.32 -> 161.45 between 2020 and
# 2021 (a first-optimized-year artefact of the calibration), then declines
# monotonically to 112.34 by 2053. E11 zeroes only the first model year, so a
# symmetric EACR would book a ~2,600 Mt phantom CREDIT on the 2021 jump. Gate the
# ratio to 0 through EACR_START_YEAR-1 and price changes from 2022 onward, where
# the path is a genuine, monotone deforestation trajectory (~49.1 units).
EACR_START_YEAR = 2022

# Two known limitations of this representation, disclosed here on purpose:
# (1) symmetry -- if forest GREW after 2022 the same ratio would credit 292 t/ha
#     for regrowth, which overstates young-forest sequestration (~6.81 tCO2e/ha/yr
#     per the PHL FRL); acceptable here only because the post-2021 path declines.
# (2) the -10.0 forest reward stays in place: this experiment measures the carbon
#     price's marginal effect ON TOP OF the current calibration, not a replacement.

VARIANTS = {
    "Philippines_v12_FC_ACCT": {"eacr": True, "ep": False},
    "Philippines_v12_FC_TAX": {"eacr": False, "ep": True},
    "Philippines_v12_FC_TAXLUC": {"eacr": True, "ep": True},
}


def _years(rows: list[dict]) -> list[str]:
    """Year columns of a parameter grid, taken from its first row."""
    return [k for k in rows[0] if k not in ("TechId", "EmisId", "CommId", "MoId")]


def patch_eacr(case_dir: Path) -> None:
    """Wire the forest conversion-carbon emission into the case.

    Three coordinated edits, all required:
      1. genData.json: declare CO2e on LNDFORTOT's `EAR` attribute. MUIOGO's
         datafile generator filters ALL RYTEM rows (EAR and EACR alike) by
         `tech['EAR']` (OsemosysClass.py:475), so an EACR row on a tech with an
         empty EAR list is silently dropped -- verified the hard way: the first
         solve produced `param EmissionToActivityChangeRatio default 0 := ;`.
      2. RYTEM.json: an all-zero EAR row for (LNDFORTOT, CO2e, mode 1), so the
         generator's EAR lookup for the now-declared tech finds data.
      3. RYTEM.json: the EACR row -- 0 before EACR_START_YEAR, EACR_VALUE after.

    Values live in the base slice (SC_0); other scenario slices get all-None
    rows so the grid stays structurally parallel across scenarios. Idempotent:
    re-running on a patched case is a no-op, so --repair can fix live copies.
    """
    gd_path = case_dir / "genData.json"
    gd = json.loads(gd_path.read_text())
    tech = next(t for t in gd["osy-tech"] if t["TechId"] == FOREST_TECH)
    if CO2E not in tech.get("EAR", []):
        tech.setdefault("EAR", []).append(CO2E)
        gd_path.write_text(json.dumps(gd))

    # The datafile writer iterates EVERY mode in the case and does a raw nested
    # lookup (DataFileClass.gen_RYTEM: `rytem[id][sc][year][tech][emis][mod]`),
    # so a (tech, emis) pair must carry a row for ALL modes or generation dies
    # with a KeyError mid-write, truncating data.txt -- verified: 53 of 54
    # params, the file ending inside the EACR block. UI-created grids always
    # carry the full mode set (30 here); hand-added rows must too.
    n_modes = int(json.loads((case_dir / "genData.json").read_text())["osy-mo"])

    path = case_dir / "RYTEM.json"
    data = json.loads(path.read_text())
    for code in ("EAR", "EACR"):
        for sc, rows in data[code].items():
            mine = {
                int(r["MoId"]): r
                for r in rows
                if r.get("TechId") == FOREST_TECH and r.get("EmisId") == CO2E
            }
            for mode in range(1, n_modes + 1):
                row = mine.get(mode)
                if row is None:
                    row = {"TechId": FOREST_TECH, "EmisId": CO2E, "MoId": mode}
                    rows.append(row)
                # (Re)write values in place -- repairs earlier partial patches.
                for y in _years(rows):
                    if sc != "SC_0":
                        row[y] = None
                    elif code == "EACR" and mode == FOREST_MODE:
                        row[y] = EACR_VALUE if int(y) >= EACR_START_YEAR else 0
                    else:
                        row[y] = 0
    path.write_text(json.dumps(data))


def patch_ep(case_dir: Path) -> None:
    """Set the CO2e emissions penalty to EP_VALUE in the base slice."""
    path = case_dir / "RYE.json"
    data = json.loads(path.read_text())
    rows = data["EP"]["SC_0"]
    hits = [r for r in rows if r.get("EmisId") == CO2E]
    if len(hits) != 1:
        raise RuntimeError(f"{path}: expected exactly one EP row for {CO2E}, got {len(hits)}")
    for y in _years(rows):
        hits[0][y] = EP_VALUE
    path.write_text(json.dumps(data))


def verify(case_dir: Path, want_eacr: bool, want_ep: bool) -> list[str]:
    """Read the edits back from disk and report what is actually there."""
    report = []
    gd = json.loads((case_dir / "genData.json").read_text())
    tech = next(t for t in gd["osy-tech"] if t["TechId"] == FOREST_TECH)
    rytem = json.loads((case_dir / "RYTEM.json").read_text())
    eacr_rows = [
        r for r in rytem["EACR"]["SC_0"]
        if r.get("TechId") == FOREST_TECH and r.get("EmisId") == CO2E
    ]
    if want_eacr:
        ear_ok = CO2E in tech.get("EAR", [])
        report.append(f"genData EAR declared: {'OK' if ear_ok else 'WRONG -- generator will drop the row'}")
        n_modes = int(gd["osy-mo"])
        by_mode = {int(r["MoId"]): r for r in eacr_rows}
        forest = by_mode.get(FOREST_MODE, {})
        pre = {v for y, v in forest.items()
               if y not in ("TechId", "EmisId", "MoId") and int(y) < EACR_START_YEAR}
        post = {v for y, v in forest.items()
                if y not in ("TechId", "EmisId", "MoId") and int(y) >= EACR_START_YEAR}
        others = {v for m, r in by_mode.items() if m != FOREST_MODE
                  for y, v in r.items() if y not in ("TechId", "EmisId", "MoId")}
        ok = (len(by_mode) == n_modes and pre <= {0}
              and post == {EACR_VALUE} and others <= {0})
        report.append(
            f"EACR rows: {'OK' if ok else 'WRONG'} "
            f"({len(by_mode)}/{n_modes} modes, forest pre-{EACR_START_YEAR} {pre or '{}'}, "
            f"after {post}, other modes {others or '{}'})"
        )
    else:
        report.append(f"EACR absent: {'OK' if not eacr_rows else 'WRONG -- row present'}")

    rye = json.loads((case_dir / "RYE.json").read_text())
    ep_row = next(r for r in rye["EP"]["SC_0"] if r.get("EmisId") == CO2E)
    ep_vals = {v for k, v in ep_row.items() if k != "EmisId"}
    if want_ep:
        report.append(f"EP: {'OK' if ep_vals == {EP_VALUE} else 'WRONG'} (values {ep_vals})")
    else:
        report.append(f"EP zero: {'OK' if ep_vals <= {0, None} else 'WRONG'} (values {ep_vals})")
    return report


def main(argv: list[str]) -> int:
    solve = "--solve" in argv
    for name, edits in VARIANTS.items():
        dst = Path(DATA_STORAGE) / name
        if not dst.exists():
            print(f"== {name}: copying from {SRC} (4.1 GB, takes a minute)...")
            copy_case(DATA_STORAGE, SRC, name)
        else:
            print(f"== {name}: exists -- re-applying patches (idempotent)")
        if edits["eacr"]:
            patch_eacr(dst)
        if edits["ep"]:
            patch_ep(dst)
        for line in verify(dst, edits["eacr"], edits["ep"]):
            print(f"   {line}")

    if not solve:
        print("\npatched only; re-run with --solve to launch the three solves")
        return 0

    for name in VARIANTS:
        print(f"\n== solving {name} / {RUN} ...")
        r = subprocess.run(
            ["muiogo-ai", "run", "--case", name, "--run", RUN],
            capture_output=True, text=True, timeout=3600, check=False,
        )
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        print("   " + "\n   ".join(tail))
        if r.returncode != 0:
            print(f"   SOLVE FAILED for {name} -- stopping; see output above")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
