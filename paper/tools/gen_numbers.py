#!/usr/bin/env python3
"""Derive the paper's quoted numbers from a coupled run's own record.

Reads a run directory (macro_table.csv + ogclews_manifest.json) and emits TeX
includes under paper/generated/:

  numbers.tex            \newcommand macros for every quoted magnitude
  table_coupled.tex      tabular body for the coupled-run table
  table_attribution.tex  tabular body for the matched-battery attribution table
                         (static v12 data carried here with its base label,
                         until the matched-leg pair is re-run on the final base)

Prose must reference the macros, never retype numbers: on an evidence-base
change, re-run this against the new run directory and recompile. If any sign
flips relative to the previous generated file, the script says so loudly —
a sign flip means prose needs review, not just recompilation.

Stdlib only. Usage:
  python3 paper/tools/gen_numbers.py --run-dir <coupled run dir> \
      --base-label "CLEWs Philippines v16 (Base_v16/PEP_v16)" \
      [--employed 49000000] [--out paper/generated]
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# The matched real-price battery (steady state, % vs baseline).
# Evidence base: CLEWs Philippines v12 CALIBRATED, 11-experiment battery,
# recorded in the calibration record's attribution table (2026-08-11).
# Re-verification on the final evidence base is queued; when it lands, replace
# this block with a reader over that battery's own macro tables.
# The deliverables discuss the CURRENT calibration only (Marcelo, 2026-08-13):
# no iteration tags in prose, and no number quoted from an older iteration.
# While the matched composition battery on the current calibration is pending,
# every attribution macro and the attribution table render an explicit
# MISSING flag; flip PENDING_ATTRIBUTION to False (and repoint the data below
# at the new battery's own record) when those runs land.
PENDING_ATTRIBUTION = True

# Prior-generation data, retained ONLY for the sign-comparison check when the
# new battery lands — never emitted while PENDING_ATTRIBUTION is True.
ATTRIBUTION_V12 = {
    "base_label": "matched real-price battery (prior iteration; not quotable)",
    # (name, Y, C, w, in_methods_table)
    "rows": [
        ("coupled",                        -0.525, -0.385, -0.486, True),
        ("energy composite",               -0.525, -0.385, -0.487, True),
        ("inter-industry cost-push leg",   -0.496, -0.426, -0.559, True),
        ("household wedge leg",            -0.026, -0.225, -0.032, True),
        ("structural TFP alternative",     +0.026, -0.210, -0.045, True),
        # standalone experiments from the same battery (macros only):
        ("carbon",                         -0.032, +0.019, +0.086, False),
        ("clean incidence",                -0.022, -0.064, +0.050, False),
        ("capital intensity",              -0.000, +0.276, +0.029, False),
        ("energy capex",                   -0.023, +0.080, +0.007, False),
    ],
}

MACRO_ROWS = ("Y", "C", "K", "L", "r", "w")


def read_macro_table(run_dir: Path):
    rows = {}
    with open(run_dir / "macro_table.csv", newline="") as fh:
        for rec in csv.DictReader(fh):
            rows[rec["Year"]] = {k: rec[k] for k in MACRO_ROWS}
    ss = rows.get("SS")
    window_key = next((k for k in rows if re.fullmatch(r"\d{4}-\d{4}", k)), None)
    if ss is None or window_key is None:
        sys.exit("macro_table.csv: need an 'SS' row and a 'YYYY-YYYY' window row")
    return ss, window_key, rows[window_key]


def read_manifest(run_dir: Path):
    man = json.loads((run_dir / "ogclews_manifest.json").read_text())
    prov = {p["channel"]: p for p in man.get("provenance", [])}
    return man, prov


def texnum(x, nd=3):
    return f"{float(x):+.{nd}f}".replace("+", "")  # keep the minus, drop the plus


def macro(name, value, comment=""):
    tail = f"  % {comment}" if comment else ""
    return f"\\newcommand{{\\{name}}}{{{value}}}{tail}"


def missing(name, what, pending=False):
    """Absent source -> a macro that RENDERS a visible flag.

    Never skip an expected macro: skipping leaves stale prose compiling
    against an old generation, and absent must never read as resolved.
    ``pending=True`` renders the compact [PENDING: ...] form for runs that
    are expected and will be generated; the severe MISSING form is for
    sources that should exist now and do not.
    """
    cmd = "genPENDING" if pending else "genMISSING"
    return (f"\\newcommand{{\\{name}}}{{\\{cmd}{{{what}}}}}"
            f"  % SOURCE {'PENDING' if pending else 'ABSENT'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--base-label", required=True,
                    help="evidence-base label printed on tables/figures")
    ap.add_argument("--employed", type=float, default=None,
                    help="employed persons for the morbidity FTE/yr figure; "
                         "SUPPLIED, not derived from any run artifact — omit "
                         "to omit the FTE macro")
    ap.add_argument("--battery", type=Path, default=None,
                    help="matched-battery record (JSON of {run: {base,reform}} "
                         "SS levels) on the SAME calibration as --run-dir; "
                         "when given, attribution macros/table derive from it "
                         "and PENDING mode is off")
    ap.add_argument("--out", type=Path, default=Path("paper/generated"))
    args = ap.parse_args()

    ss, window_key, window = read_macro_table(args.run_dir)
    man, prov = read_manifest(args.run_dir)
    args.out.mkdir(parents=True, exist_ok=True)

    health = prov.get("health", {})
    wedge = prov.get("energy_price", {})
    invest = prov.get("investment", {})

    lines = [
        "% GENERATED by paper/tools/gen_numbers.py — do not edit by hand.",
        f"% Run record: {args.run_dir}",
        f"% CLEWs run: {man.get('clews_run', 'UNKNOWN')}",
        "% A \\genMISSING render in the compiled paper means a macro's source",
        "% artifact was absent at generation time — absent never reads as resolved.",
        "\\providecommand{\\genMISSING}[1]{\\textbf{[MISSING, NOT RESOLVED: #1]}}",
        "\\providecommand{\\genPENDING}[1]{\\textbf{[PENDING: #1]}}",
        macro("cplBase", args.base_label, "evidence base, print on-face"),
        macro("cplWindow", window_key.replace("-", "--"), "transition window"),
    ]
    for var in MACRO_ROWS:
        lines.append(macro(f"cpl{var.upper()}ss", texnum(ss[var])))
        lines.append(macro(f"cpl{var.upper()}win", texnum(window[var])))

    if wedge:
        lines.append(macro("cplWedgePct", texnum(100 * wedge["dtau_mean"], 1),
                           "mean household electricity-price wedge, %"))
    else:
        lines.append(missing("cplWedgePct", "energy-price provenance"))

    if health:
        lines.append(macro("cplPMPct", texnum(100 * health["emissions_change"], 2),
                           f"{health.get('emissions_species', '?')} change, %"))
        lines.append(macro("cplDeaths",
                           f"{abs(health['mortality_excess_deaths']):.0f}",
                           "avoided deaths (GBD-anchored), magnitude"))
        if args.employed:
            fte = abs(health["morbidity_benefit"]) * args.employed
            lines.append(macro("cplMorbFTE", f"{fte:,.0f}",
                               f"FTE/yr = morbidity x {args.employed:,.0f} "
                               "employed (employment SUPPLIED, not derived)"))
        else:
            lines.append(missing("cplMorbFTE",
                                 "employment count not supplied (--employed)"))
    else:
        lines.append(missing("cplPMPct", "health provenance"))
        lines.append(missing("cplDeaths", "health provenance"))
        lines.append(missing("cplMorbFTE", "health provenance"))

    if invest:
        lines.append(macro("cplInvestCumPctGDP",
                           texnum(invest["cumulative_pct_gdp"], 3),
                           "cumulative public-investment delta, % of GDP"))
    else:
        lines.append(missing("cplInvestCumPctGDP", "investment provenance"))

    (args.out / "numbers.tex").write_text("\n".join(lines) + "\n")

    coupled_rows = "\n".join(
        f"{label:18s}& ${texnum(window[var])}$ & ${texnum(ss[var])}$ \\\\"
        for var, label in zip(MACRO_ROWS, (
            "output $Y$", "consumption $C$", "capital $K$",
            "labour $L$", "return $r$", "wage $w$"))
    )
    (args.out / "table_coupled.tex").write_text(
        "% GENERATED — see numbers.tex header.\n"
        f"% Evidence base: {args.base_label}\n"
        "\\begin{tabular}{@{}lrr@{}}\n\\toprule\n"
        f" & {window_key.replace('-', '--')} average & steady state \\\\\n"
        "\\midrule\n" + coupled_rows + "\n\\bottomrule\n\\end{tabular}\n"
    )

    # Prose-facing macros for the battery rows (same static v12 data as the
    # table — one source, two renderings). \atr<Row><Var> for every row/var.
    with open(args.out / "numbers.tex", "a") as fh:
        fh.write(macro("cplEmitDRPct",
                       texnum(100 * prov["emit_discount_rate"]
                              ["clews_discount_rate"], 1),
                       "emitted planning discount rate, %")
                 if "emit_discount_rate" in prov else
                 missing("cplEmitDRPct", "discount-rate provenance"))
        fh.write("\n")
        fh.write(macro("cplDemandMeanPct",
                       texnum(100 * (prov["emit_energy_demand"]
                                     ["mean_ratio"] - 1), 1),
                       "emitted mean demand-path change, %")
                 if "emit_energy_demand" in prov else
                 missing("cplDemandMeanPct", "demand provenance"))
        fh.write("\n")
        def pct(rec, var):
            b, r = rec["base"], rec["reform"]
            return 100 * (r[f"{var}_ss"] / b[f"{var}_ss"] - 1)

        attr_rows_out = []
        if args.battery:
            bat = json.loads(args.battery.read_text())
            fh.write(macro("atrBase", "matched battery on the current "
                           "calibration (see the run record)") + "\n")
            # coupled row comes from the coupled run's own macro table
            fh.write(macro("atrCoupledY", texnum(ss["Y"])) + "\n")
            fh.write(macro("atrCoupledC", texnum(ss["C"])) + "\n")
            fh.write(macro("atrCoupledW", texnum(ss["w"])) + "\n")
            attr_rows_out.append(("coupled", float(ss["Y"]),
                                  float(ss["C"]), float(ss["w"])))
            for stem, key, label in (
                    ("atrComposite", "gold_energy_full", "energy composite"),
                    ("atrCostPush", "gold_energy_cost_push",
                     "inter-industry cost-push leg"),
                    ("atrWedge", "gold_energy_price", "household wedge leg"),
                    ("atrCarbon", "gold_carbon", None),
                    ("atrCleanInc", "gold_clean_incidence", None),
                    ("atrCapex", "gold_energy_capex", None)):
                if key not in bat:
                    for var in ("Y", "C", "W"):
                        fh.write(missing(stem + var,
                                         f"{key} absent from battery record")
                                 + "\n")
                    continue
                vals = tuple(pct(bat[key], v) for v in ("Y", "C", "w"))
                for var, val in zip(("Y", "C", "W"), vals):
                    fh.write(macro(stem + var, texnum(val)) + "\n")
                if label:
                    attr_rows_out.append((label,) + vals)
        else:
            fh.write(missing("atrBase", "matched battery", pending=True)
                     + "\n")
            for stem in ("atrCoupled", "atrComposite", "atrCostPush",
                         "atrWedge", "atrCarbon", "atrCleanInc", "atrCapex"):
                for var in ("Y", "C", "W"):
                    fh.write(missing(stem + var, "matched battery",
                                     pending=True) + "\n")

    if attr_rows_out:
        rows_tex = "\n".join(
            f"{name:32s}& ${texnum(y)}$ & ${texnum(c)}$ & ${texnum(w)}$ \\\\"
            for name, y, c, w in attr_rows_out)
        (args.out / "table_attribution.tex").write_text(
            "% GENERATED — see numbers.tex header. Derived from the matched\n"
            "% battery record on the same calibration as the coupled run.\n"
            "\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n"
            "experiment & $Y$ & $C$ & $w$ \\\\\n\\midrule\n"
            + rows_tex + "\n\\bottomrule\n\\end{tabular}\n")
    else:
        (args.out / "table_attribution.tex").write_text(
            "% GENERATED — see numbers.tex header. Composition battery pending.\n"
            "\\begin{tabular}{@{}c@{}}\n"
            "\\genPENDING{matched composition battery on the current "
            "calibration}\\\\\n"
            "\\end{tabular}\n")

    # Loud sign check vs whatever numbers.tex said before this run.
    prev = {}
    old_file = args.out / "numbers.prev.tex"
    if old_file.exists():
        for m in re.finditer(r"\\newcommand\{\\(cpl\w+)\}\{(-?[\d.]+)\}",
                             old_file.read_text()):
            prev[m.group(1)] = float(m.group(2))
        flips = []
        for m in re.finditer(r"\\newcommand\{\\(cpl\w+)\}\{(-?[\d.]+)\}",
                             (args.out / "numbers.tex").read_text()):
            name, val = m.group(1), float(m.group(2))
            if name in prev and prev[name] * val < 0:
                flips.append(f"  {name}: {prev[name]} -> {val}")
        if flips:
            print("SIGN FLIPS vs previous generation — prose needs review:")
            print("\n".join(flips))
        else:
            print("No sign flips vs previous generation.")
    (args.out / "numbers.prev.tex").write_text(
        (args.out / "numbers.tex").read_text())
    print(f"Wrote numbers.tex, table_coupled.tex, table_attribution.tex "
          f"to {args.out} (base: {args.base_label})")


if __name__ == "__main__":
    main()
