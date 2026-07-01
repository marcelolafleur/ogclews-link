"""Run the cumulative across-steps batch: baseline solved once, then one reform per
cumulative channel set (energy price -> + investment -> + carbon -> + health). Dumps a
layered_results.json the visual consumes. One-way (each step takes CLEWS as given).

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/run_across_steps.py

Runs UNDER the OG model's interpreter (it builds the full deck, which needs OG-Core's native plotting
and the SS income factor). It injects og_runner's IN-PROCESS solve callables into the same generic
framework the link drives cross-env -- only the injected callables differ between the two environments.
"""
from __future__ import annotations

import json
import os

import numpy as np

from ogclews_link import channels, framework, og_runner, registry, report, signals  # noqa: F401
from ogclews_link.country import PHL
from ogclews_link.experiments import ACROSS_STEPS

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs"


def main():
    entry = registry.lookup(PHL)
    export_baseline, solve_reform = og_runner.inprocess_callables(
        entry.package, entry.params_resource_name, PHL.scenario.og_start_year,
        num_workers=7, show_progress=True,        # multiprocess; never 1 worker (threaded trap)
        calibration=entry.calibration)            # chosen multisector calibration (None -> single-industry)
    results = framework.run_across_steps(ACROSS_STEPS, PHL, export_baseline=export_baseline,
                                         solve_reform=solve_reform, out_root=OUT)

    # the energy good index is the PER-RUN concordance the engine discovered (exported via
    # baseline_meta.json), not a country literal; None when the country can't isolate electricity (e.g.
    # PHL at a single-industry calibration) -> the energy-good demand/incidence rows are simply omitted.
    ie = next((ctx.concordance.energy_good_index for _, ctx in results
               if ctx.concordance is not None and ctx.concordance.energy_good_index is not None), None)
    layered = []
    for label, ctx in results:
        if ctx.reform_tpi is None:  # step did not solve -> record and skip the report math
            layered.append({"step": label, "error": ctx.extras.get("error", "did not solve")})
            print(f"\n>>> {label}: DID NOT SOLVE ({ctx.extras.get('error')})")
            continue
        row = report.layered_entry(label, ctx.base_tpi, ctx.reform_tpi, energy_good_index=ie,
                                    channels=[r.get("channel") for r in ctx.provenance])
        layered.append(row)
        _energy = f"energy {row['energy_demand_pct']}% | " if ie is not None else ""
        print(f"\n>>> {label}: {_energy}GDP {row['macro'].get('Y')}% | "
              f"consumption_by_J {row.get('consumption_by_J', '(no energy good)')}")

    # Decompose the +health step's GDP bar into mortality + morbidity for the stacked waterfall: re-solve
    # the SAME cumulative reform with health = mortality-only (1 extra solve); the figure takes morbidity
    # as the remainder. The mortality-only step mirrors the combined +health step (experiments._across_health).
    base_tpi = next((ctx.base_tpi for _, ctx in results if ctx.base_tpi is not None), None)
    health_row = next((r for r in layered if r.get("step") == "+ health" and "macro" in r), None)
    if health_row is not None and base_tpi is not None:
        def _mortonly(ctx, solve):
            # mirror the real +health layer (experiments._across_health) but health = mortality-only
            from ogclews_link.experiments import _apply_energy_composite, _auto_price_ratio, _public_capex
            _apply_energy_composite(ctx, _auto_price_ratio(ctx))
            channels.investment(ctx, _public_capex(ctx))
            channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
            channels.health(ctx, enable_mortality=True, enable_morbidity=False)
            solve(ctx)
        try:
            mres = framework.run_across_steps([("+ health (mortality only)", _mortonly)], PHL,
                                              export_baseline=export_baseline,
                                              solve_reform=solve_reform, out_root=OUT)
            ctx_m = mres[0][1]
            if ctx_m.reform_tpi is not None:
                y_mort = round(float(np.nanmean(report.macro_pct_diff(base_tpi, ctx_m.reform_tpi)["Y"])), 4)
                health_row["health_split"] = {"mortality": y_mort, "combined": health_row["macro"]["Y"]}
                print(f"\n>>> +health decomposition: mortality-only GDP {y_mort:+.4f}% | "
                      f"combined {health_row['macro']['Y']:+.4f}% | morbidity (rest) "
                      f"{health_row['macro']['Y'] - y_mort:+.4f}%")
        except Exception as e:  # noqa: BLE001  (decomposition is a nicety; never kill the main run)
            print(f"[decompose] mortality-only solve failed: {type(e).__name__}: {e}")

    out_dir = os.path.join(OUT, "across_steps")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "layered_results.json"), "w") as f:
        json.dump(layered, f, indent=2, default=str)
    from ogcore.utils import safe_read_pickle

    from ogclews_link.viz import plots, tables
    from ogclews_link.viz import report as viz_report
    note = ("Illustrative: +20% energy-price wedge (a cost-index proxy, not the CLEWS dual); "
            "investment/carbon magnitudes uncalibrated; carbon revenue not recycled.")
    viz_report.write_html_report(layered, os.path.join(out_dir, "report.html"))
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    plots.across_steps_waterfall(layered, fig_dir, note=note)   # marginal channel contributions
    plots.macro_honest(layered, fig_dir, note=note)             # fixed-axis: effects are ~0
    plots.energy_physical(PHL, fig_dir)                         # the physical energy side
    tables.across_steps_table(layered, os.path.join(fig_dir, "across_steps_summary.csv"))
    base_dir = os.path.join(out_dir, "baseline")
    try:  # the income factor (model units -> currency) lives in the baseline SS output
        factor = float(safe_read_pickle(os.path.join(base_dir, "SS", "SS_vars.pkl"))["factor"])
    except Exception:  # noqa: BLE001
        factor = None
    for label, ctx in results:  # per step: the incidence hero + OG-Core's macro table
        if ctx.reform_tpi is None:
            continue
        sdir = os.path.join(out_dir, label, "figures")
        if ie is not None:       # incidence keys off the energy good; skip when none is isolated
            plots.incidence_hero(ctx.base_tpi, ctx.reform_tpi, ie, sdir,
                                 title=f"{PHL.name}: {label}", note=note, factor=factor)
        plots.og_default_outputs(base_dir, os.path.join(out_dir, label), sdir)
    print(f"\nWrote {out_dir}/ : layered_results.json, report.html, figures/ (incidence, waterfall, "
          f"macro, emissions) + per-step incidence ({len(layered)} steps)")


if __name__ == "__main__":
    main()
