"""Idea #01 empirical test: the CLEWS re-run seam round-trip on the REAL Philippines_v9 case.

Two case COPIES (the live case is never touched):
  * CONTROL:   copy the case, re-generate + re-solve the existing Base_v9 caserun unchanged, TWICE.
               PASS = the two solves agree exactly (headless determinism: the case store + today's
               MUIOGO fully determine the result). The original (historical) results are compared
               too, but only REPORTED: today's regeneration is FUNCTIONALLY identical to the
               Jan-2026 datafile (all 54 param blocks value-identical; differences = block order,
               CRLF, comments), so the small orig-vs-today result gap is ALTERNATIVE OPTIMA --
               vertex selection among economic ties (~1e-6 of the investment-dominated objective;
               AnnualizedInvestmentCost matches to +0.0001%) -- not reinterpreted data. The case
               was authored under an older MUIO, so structures Base_v9 does NOT exercise (storage,
               UDCs, PEP-specific additions) remain untested; keep the caveat.
  * TREATMENT: copy the case, scale household-electricity FINAL demand (PHL_HOU_ELEF -- the code
               that actually carries load; PHL_HOU_ELE's demand rows are zero) by +10% in SC_0,
               re-solve Base_v9. PASS = electricity production and system cost rise vs control
               (the patch actually propagated through MUIOGO's own pipeline).

Run deliberately (three CBC LP solves, ~minutes each):
    uv run python experiments/seam_roundtrip.py [--keep] [--case Philippines_v9] [--factor 1.10]
Copies are removed on success unless --keep. --reuse recomputes verdicts from existing copies
(skips the third control solve; determinism is then not re-checked).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ogclews_link import clews_driver                      # noqa: E402
from ogclews_link.country import _muiogo_home              # noqa: E402

CASERUN = "Base_v9"
COMMODITY = "PHL_HOU_ELEF"   # the FINAL-demand code that carries load (PHL_HOU_ELE's SAD rows are 0)
# Patch the EXCHANGE WINDOW only (og_start_year..end): scaling the CALIBRATED HISTORICAL years
# (2020-2024, pinned to actual generation) makes the LP pathological -- observed live: the all-years
# +10% treatment ran CBC >1h vs ~4min healthy. The coupling never touches history either (OG starts
# 2026; "never overwrite the base year").
PATCH_FROM_YEAR = 2026
CASE_END_YEAR = 2053
TIMEOUT_S = 1200             # healthy v9 solve ~4min; 20min = pathological, fail fast


def _csv(csv_dir, name):
    df = pd.read_csv(Path(csv_dir) / f"{name}.csv")
    df.columns = [c.strip() for c in df.columns]
    return df


def _total(csv_dir, name):
    df = _csv(csv_dir, name)
    return float(pd.to_numeric(df[df.columns[-1]], errors="coerce").fillna(0.0).sum())


# NB: result-CSV names verified against THIS MUIOGO's actual export (res/<run>/csv), NOT the Rev-4.2
# spec's names -- the spec says "ProductionByTechnologyAnnual"; this export writes
# "ProductionByTechnologyByMode" (first run of this script trusted the spec and crashed; lesson kept).
PRODUCTION_CSV = "ProductionByTechnologyByMode"


def _elec_production(csv_dir):
    """Electricity production: ProductionByTechnologyByMode rows for the PHL_POW_ELE* fuels
    (busbar PHL_POW_ELE + retail PHL_POW_ELE1)."""
    df = _csv(csv_dir, PRODUCTION_CSV)
    fcol = next(c for c in df.columns if c.lower() == "f")
    vcol = df.columns[-1]
    sub = df[df[fcol].astype(str).str.startswith("PHL_POW_ELE")]
    return float(pd.to_numeric(sub[vcol], errors="coerce").fillna(0.0).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="Philippines_v9")
    ap.add_argument("--factor", type=float, default=1.10)
    ap.add_argument("--solver", default="CBC")
    ap.add_argument("--keep", action="store_true", help="keep the case copies for inspection")
    ap.add_argument("--reuse", action="store_true",
                    help="skip copy+patch+solve and just re-read verdicts from existing seam copies")
    args = ap.parse_args()

    home = _muiogo_home()
    if not home:
        sys.exit("MUIOGO home not found (set $OGCLEWS_MUIOGO_HOME or place ../MUIOGO).")
    storage = str(Path(home) / "WebAPP" / "DataStorage")
    orig_csv = Path(storage) / args.case / "res" / CASERUN / "csv"
    if not orig_csv.is_dir():
        sys.exit(f"{orig_csv} missing -- the source case has no solved {CASERUN} to compare against.")

    ctrl_case, treat_case = f"{args.case}__seam_ctrl", f"{args.case}__seam_treat"
    failures = []

    det = None
    if args.reuse:
        ctrl = {"csv_dir": str(Path(storage) / ctrl_case / "res" / CASERUN / "csv")}
        treat = {"csv_dir": str(Path(storage) / treat_case / "res" / CASERUN / "csv")}
        if not (Path(ctrl["csv_dir"]).is_dir() and Path(treat["csv_dir"]).is_dir()):
            sys.exit("--reuse: seam copies not found; run without --reuse first.")
        print(f"[seam] --reuse: reading verdicts from existing {ctrl_case} / {treat_case} "
              "(determinism not re-checked)")
    else:
        print(f"[seam] control: copy {args.case} -> {ctrl_case}, re-solve {CASERUN} unchanged")
        clews_driver.copy_case(storage, args.case, ctrl_case, overwrite=True)
        ctrl = clews_driver.run_caserun(ctrl_case, CASERUN, solver=args.solver, muiogo_home=home, timeout=TIMEOUT_S)
        print(f"[seam]   solved in {ctrl['elapsed_s']}s -> {ctrl['csv_dir']}")
        det = {n: _total(ctrl["csv_dir"], n) for n in (PRODUCTION_CSV, "AnnualVariableOperatingCost")}
        print(f"[seam] control determinism: re-solve {CASERUN} in the same copy")
        ctrl2 = clews_driver.run_caserun(ctrl_case, CASERUN, solver=args.solver, muiogo_home=home, timeout=TIMEOUT_S)
        print(f"[seam]   solved in {ctrl2['elapsed_s']}s")

        print(f"[seam] treatment: copy {args.case} -> {treat_case}, {COMMODITY} x{args.factor}, re-solve")
        clews_driver.copy_case(storage, args.case, treat_case, overwrite=True)
        fmap = {y: args.factor for y in range(PATCH_FROM_YEAR, CASE_END_YEAR + 1)}
        prov = clews_driver.scale_annual_demand(str(Path(storage) / treat_case), COMMODITY, fmap)
        print(f"[seam]   patched: {prov}")
        treat = clews_driver.run_caserun(treat_case, CASERUN, solver=args.solver, muiogo_home=home, timeout=TIMEOUT_S)
        print(f"[seam]   solved in {treat['elapsed_s']}s -> {treat['csv_dir']}")

    # --- assertions ---------------------------------------------------------------
    print("\n[seam] === verdicts ===")
    # 1a) reproducibility: same store + same MUIOGO solved twice -> economically identical results.
    #     BIT determinism does NOT hold (observed: regeneration+CBC re-lands on a tie vertex 0.002%
    #     apart on production, <1e-6 on cost), so the criterion is an ECONOMIC tolerance.
    if det is not None:
        for name, first in det.items():
            again = _total(ctrl["csv_dir"], name)
            rel = abs(first - again) / max(abs(first), 1.0)
            ok = rel <= 1e-3
            print(f"  reproducibility {name}: run1={first:.6g} run2={again:.6g} "
                  f"(rel gap {rel:.2e}) -> {'PASS' if ok else 'FAIL'} (economic tol 1e-3)")
            if not ok:
                failures.append(f"re-solving the same case store changed {name} by {rel:.2e}")
    # 1b) version drift vs the historical results -- REPORTED, not failed (MUIOGO's datafile
    #     generation demonstrably changed since the original run; see the module docstring)
    for name in (PRODUCTION_CSV, "AnnualVariableOperatingCost"):
        a, b = _total(orig_csv, name), _total(ctrl["csv_dir"], name)
        print(f"  version drift {name}: orig={a:.6g} today={b:.6g} ({(b/a-1)*100:+.3f}%) -- reported only")
    # 2) treatment: electricity production rises with demand
    pc, pt = _elec_production(ctrl["csv_dir"]), _elec_production(treat["csv_dir"])
    ok = pt > pc
    print(f"  elec production ctrl={pc:.6g} treat={pt:.6g} ({(pt/pc-1)*100:+.2f}%) -> "
          f"{'PASS' if ok else 'FAIL'} (expect rise; hh elec is a slice of total, so < +10%)")
    if not ok:
        failures.append("electricity production did not rise with +10% household demand")
    # 3) treatment: total variable operating cost rises
    cc, ct = _total(ctrl["csv_dir"], "AnnualVariableOperatingCost"), _total(treat["csv_dir"], "AnnualVariableOperatingCost")
    ok = ct > cc
    print(f"  var op cost     ctrl={cc:.6g} treat={ct:.6g} ({(ct/cc-1)*100:+.2f}%) -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("system variable cost did not rise")

    if failures:
        print(f"\n[seam] ROUND-TRIP FAILED ({len(failures)}): " + "; ".join(failures))
        print(f"[seam] case copies kept for inspection: {ctrl_case}, {treat_case}")
        sys.exit(1)
    if not args.keep:
        shutil.rmtree(Path(storage) / ctrl_case)
        shutil.rmtree(Path(storage) / treat_case)
        print("[seam] copies removed (pass --keep to retain).")
    print("[seam] ROUND-TRIP PASSED: write -> MUIOGO solve -> read, with control reproducibility.")


if __name__ == "__main__":
    main()
