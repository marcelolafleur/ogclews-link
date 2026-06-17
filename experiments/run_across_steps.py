"""Run the cumulative across-steps batch: baseline solved once, then one reform per
cumulative channel set (energy price -> + investment -> + carbon -> + health). Dumps a
layered_results.json the visual consumes. One-way (each step takes CLEWS as given).

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/run_across_steps.py
"""
from __future__ import annotations

import json
import os

import numpy as np

from ogclews_link import channels, report  # noqa: F401 (channels import registers them)
from ogclews_link.country import PHL
from ogclews_link.experiments import ACROSS_STEPS
from ogclews_link.framework import ExperimentContext
from ogclews_link.runtime import Runtime

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs"


def main():
    rt = Runtime(num_workers=7, show_progress=True)  # multiprocess; never --workers 1 (threaded trap)
    runner = rt.runner_for(PHL)
    results = runner.run_across_steps(ACROSS_STEPS, PHL, out_root=OUT)

    ie = PHL.concordance.energy_good_index
    layered = []
    for label, ctx in results:
        if ctx.reform_tpi is None:  # step did not solve -> record and skip the report math
            layered.append({"step": label, "error": ctx.extras.get("error", "did not solve")})
            print(f"\n>>> {label}: DID NOT SOLVE ({ctx.extras.get('error')})")
            continue
        macro = report.macro_pct_diff(ctx.base_tpi, ctx.reform_tpi)
        inc = report.incidence(ctx.base_tpi, ctx.reform_tpi, ie)
        dC = report.demand_response(ctx.base_tpi, ctx.reform_tpi, ie)
        fc = report.fiscal_check(ctx.base_tpi, ctx.reform_tpi)
        row = {
            "step": label,
            "macro": {k: round(float(np.nanmean(v)), 3) for k, v in macro.items()},
            "energy_demand_pct": round(float(np.nanmean(dC[:10])), 2),
            "consumption_by_J": [round(float(x), 2) for x in inc["consumption_by_J"]],
            "energy_by_J": [round(float(x), 2) for x in inc["energy_by_J"]],
            "fiscal": {k: round(float(v), 4) for k, v in fc.items()},
            "channels": [r.get("channel") for r in ctx.provenance],
        }
        layered.append(row)
        print(f"\n>>> {label}: energy {row['energy_demand_pct']}% | "
              f"GDP {row['macro'].get('Y')}% | consumption_by_J {row['consumption_by_J']}")

    # Decompose the health step's GDP bar into mortality + morbidity for the stacked waterfall:
    # re-solve the SAME cumulative reform with health = mortality-only (1 extra solve); the figure
    # takes morbidity as the remainder. Reuses the framework's own pre-solve chain so the
    # mortality-only reform is built identically to the combined one.
    health = next(((lbl, ch) for lbl, ch in ACROSS_STEPS if any(c[0] == "health" for c in ch)), None)
    base_tpi = next((ctx.base_tpi for _, ctx in results if ctx.base_tpi is not None), None)
    if health is not None and base_tpi is not None:
        lbl, chans = health
        base_dir = os.path.join(OUT, "across_steps", "baseline")
        p, _ = rt.build_baseline(PHL, base_dir)
        mort_only = [(cid, {**opts, "affects": ("mortality",)}) if cid == "health" else (cid, opts)
                     for cid, opts in chans]
        ctx_m = ExperimentContext(country=PHL, base_tpi=base_tpi)
        ctx_m.og_reform = runner._fresh_reform(p, base_dir, os.path.join(OUT, "across_steps", lbl + "__mortonly"))
        try:
            runner._apply_pre_solve(ctx_m, mort_only, 0, step=lbl)
            tpi_m = rt.solve(ctx_m.og_reform)
            y_mort = round(float(np.nanmean(report.macro_pct_diff(base_tpi, tpi_m)["Y"])), 4)
            for row in layered:
                if row.get("step") == lbl and "macro" in row:
                    row["health_split"] = {"mortality": y_mort, "combined": row["macro"]["Y"]}
                    print(f"\n>>> {lbl} decomposition: mortality-only GDP {y_mort:+.4f}% | "
                          f"combined {row['macro']['Y']:+.4f}% | morbidity (rest) "
                          f"{row['macro']['Y'] - y_mort:+.4f}%")
        except Exception as e:  # noqa: BLE001  (decomposition is a nicety; never kill the main run)
            print(f"[decompose] mortality-only solve failed: {type(e).__name__}: {e}")

    out_dir = os.path.join(OUT, "across_steps")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "layered_results.json"), "w") as f:
        json.dump(layered, f, indent=2, default=str)
    from ogcore.utils import safe_read_pickle

    from ogclews_link import figures, report_html
    note = ("Illustrative: +20% energy-price wedge (a cost-index proxy, not the CLEWS dual); "
            "investment/carbon magnitudes uncalibrated; carbon revenue not recycled.")
    report_html.write_html_report(layered, os.path.join(out_dir, "report.html"))
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    figures.across_steps_waterfall(layered, fig_dir, note=note)   # marginal channel contributions
    figures.macro_honest(layered, fig_dir, note=note)             # fixed-axis: effects are ~0
    figures.energy_physical(PHL, fig_dir)                         # the physical energy side
    figures.across_steps_table(layered, os.path.join(fig_dir, "across_steps_summary.csv"))
    base_dir = os.path.join(out_dir, "baseline")
    try:  # the income factor (model units -> currency) lives in the baseline SS output
        factor = float(safe_read_pickle(os.path.join(base_dir, "SS", "SS_vars.pkl"))["factor"])
    except Exception:  # noqa: BLE001
        factor = None
    for label, ctx in results:  # per step: the incidence hero + OG-Core's macro table
        if ctx.reform_tpi is None:
            continue
        sdir = os.path.join(out_dir, label, "figures")
        figures.incidence_hero(ctx.base_tpi, ctx.reform_tpi, ie, sdir,
                               title=f"{PHL.name}: {label}", note=note, factor=factor)
        figures.og_default_outputs(base_dir, os.path.join(out_dir, label), sdir)
    print(f"\nWrote {out_dir}/ : layered_results.json, report.html, figures/ (incidence, waterfall, "
          f"macro, emissions) + per-step incidence ({len(layered)} steps)")


if __name__ == "__main__":
    main()
