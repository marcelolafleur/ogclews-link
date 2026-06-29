"""Head-to-head comparison of the THREE energy-price transmissions, on ONE solved baseline.

The SAME controlled +20% electricity-price change is routed three different ways into OG-Core, so the
table isolates the TRANSMISSION (where the shock enters), not the size of the shock:

  tau_c        consumption-tax wedge on the energy good            (households only)            energy_price
  ownZ  (A)    cut the electricity industry's TFP -> p_m rises;     (households + electricity     energy_price_tfp
               the model's Leontief io_matrix carries it            sector's own GE response)
  costpush (A')per-industry TFP haircut weighted by electricity's   (every electricity-           energy_cost_push
               input share phi_j (a reduced-form cost-push proxy)    intensive sector; broadest)

Runs the canonical cross-env way (runtime.export_baseline / solve_reform subprocess the OG model in its
own env). The baseline is solved ONCE and reused for all three reforms. NB this is THREE TPI solves --
minutes of compute; run it deliberately (not on every change):

    /Users/mlafleur/Projects/OG-PHL/.venv/bin/python  # any python; the OG model runs in its own env
    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link python experiments/run_energy_price_comparison.py

Writes a comparison CSV next to the run output and prints a markdown table.
"""
from __future__ import annotations

import os
from functools import partial

import numpy as np

OUT_ROOT = os.environ.get("OGCLEWS_COMPARISON_OUT", "./ogclews_runs_energy_price_comparison")

# (label, experiment name) -- each experiment applies the controlled +20% via one mechanism.
MECHANISMS = [
    ("tau_c", "energy_price"),
    ("ownZ (A)", "energy_price_tfp"),
    ("costpush (A')", "energy_cost_push"),
    ("full (A'+wedge)", "energy_full"),
]

# aggregate solution series compared as a first-decade-mean % difference (reform vs baseline).
MACRO = ["Y", "C", "K", "L", "r", "w"]


def _pct_mean(base, reform, n=10):
    """First-n-period mean % difference of two aligned (T, ...) series (reform vs baseline)."""
    b = np.asarray(base, dtype=float)
    r = np.asarray(reform, dtype=float)
    k = min(n, b.shape[0], r.shape[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        d = np.where(b[:k] != 0, (r[:k] - b[:k]) / b[:k], np.nan)
    return float(np.nanmean(d) * 100.0)


def _extract(label, ctx):
    """One comparison row: macro % diffs + the electricity sector + the energy consumption good."""
    base, reform = ctx.base_tpi, ctx.reform_tpi
    row = {"mechanism": label}
    skipped = reform is None or all(  # a channel that skipped leaves reform == base
        np.allclose(np.asarray(reform.get(k, [])), np.asarray(base.get(k, []))) for k in MACRO if k in base)
    row["status"] = "SKIPPED" if skipped else "ok"
    for k in MACRO:
        row[f"{k}%"] = _pct_mean(base[k], reform[k]) if (reform and k in base and k in reform) else float("nan")
    con = getattr(ctx, "concordance", None)
    mi = getattr(con, "energy_industry_index", None)
    gi = getattr(con, "energy_good_index", None)
    if reform and mi is not None and "Y_m" in base:
        row["elec_Y_m%"] = _pct_mean(np.asarray(base["Y_m"])[:, mi], np.asarray(reform["Y_m"])[:, mi])
    if reform and gi is not None and "p_i" in base:
        row["energy_p_i%"] = _pct_mean(np.asarray(base["p_i"])[:, gi], np.asarray(reform["p_i"])[:, gi])
    if reform and gi is not None and "C_i" in base:
        row["energy_C_i%"] = _pct_mean(np.asarray(base["C_i"])[:, gi], np.asarray(reform["C_i"])[:, gi])
    return row


def _print_table(rows):
    cols = ["mechanism", "status"] + [f"{k}%" for k in MACRO] + ["elec_Y_m%", "energy_p_i%", "energy_C_i%"]
    hdr = " | ".join(cols)
    print("\n" + hdr)
    print(" | ".join("-" * len(c) for c in cols))
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            cells.append(v if isinstance(v, str) else (f"{v:+.2f}" if v == v else "n/a"))  # v!=v -> NaN
        print(" | ".join(cells))


def _write_csv(rows, path):
    import csv
    cols = ["mechanism", "status"] + [f"{k}%" for k in MACRO] + ["elec_Y_m%", "energy_p_i%", "energy_C_i%"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def run():
    from ogclews_link import experiments, framework, runtime, serde
    from ogclews_link.country import PHL

    # OGCLEWS_REBUILD=1 forces a fresh baseline solve -- REQUIRED after a calibration update, since the
    # baseline cache is keyed by {repo}-{version}-{calibration-name} and a same-name content change
    # (e.g. updated gamma/gamma_g) would otherwise silently reuse the stale baseline.
    rebuild = os.environ.get("OGCLEWS_REBUILD") == "1"
    cfg = runtime.RunnerConfig(num_workers=7, show_progress=False, rebuild=rebuild)
    print(f"Exporting the OG baseline once (rebuild={rebuild}) ...")
    template, base_tpi, base_dir, arrays = runtime.export_baseline(PHL, OUT_ROOT, cfg=cfg)
    base_sol = serde.load_solution(os.path.join(base_dir, "baseline_solution.npz"))

    rows = []
    for label, expname in MECHANISMS:
        print(f"Solving reform: {label}  (experiment '{expname}') ...")
        ctx = framework.run(experiments.get(expname), PHL,
                            solve_reform=partial(runtime.solve_reform, cfg=cfg),
                            out_root=os.path.join(OUT_ROOT, expname),
                            prebuilt=(template, base_sol, base_dir, arrays))
        rows.append(_extract(label, ctx))

    _print_table(rows)
    csv_path = os.path.join(OUT_ROOT, "energy_price_comparison.csv")
    _write_csv(rows, csv_path)
    print("\nWrote:", csv_path)
    return rows


if __name__ == "__main__":
    run()
