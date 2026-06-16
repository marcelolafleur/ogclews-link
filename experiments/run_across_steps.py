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
            "welfare_by_J": [round(float(x), 2) for x in inc["welfare_by_J"]],
            "energy_by_J": [round(float(x), 2) for x in inc["energy_by_J"]],
            "fiscal": {k: round(float(v), 4) for k, v in fc.items()},
            "channels": [r.get("channel") for r in ctx.provenance],
        }
        layered.append(row)
        print(f"\n>>> {label}: energy {row['energy_demand_pct']}% | "
              f"GDP {row['macro'].get('Y')}% | welfare_by_J {row['welfare_by_J']}")

    out_dir = os.path.join(OUT, "across_steps")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "layered_results.json"), "w") as f:
        json.dump(layered, f, indent=2, default=str)
    print(f"\nWrote {out_dir}/layered_results.json ({len(layered)} steps)")


if __name__ == "__main__":
    main()
