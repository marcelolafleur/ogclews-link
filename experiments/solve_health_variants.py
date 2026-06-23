"""Isolate the health-channel SS failure by solving each side separately, REUSING the saved
baseline solve (rebuild params for _pop_aux only -- NO baseline re-solve). Tells us whether the
mortality (demographics) side or the morbidity (e) side breaks the steady-state resource
constraint.

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/solve_health_variants.py
"""
from __future__ import annotations

import copy
import os

import numpy as np
from ogcore.utils import safe_read_pickle

from ogclews_link import channels, report  # noqa: F401
from ogclews_link.country import PHL
from ogclews_link.framework import ExperimentContext
from ogclews_link.runtime import Runtime

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/validate_health"
BASE = os.path.join(OUT, "health", "baseline")  # the saved baseline solve to REUSE


def main():
    rt = Runtime(num_workers=7, show_progress=False)
    p0, _ = rt.build_baseline(PHL, BASE)   # rebuild params (fast, NO solve) for _pop_aux
    base_tpi = safe_read_pickle(os.path.join(BASE, "TPI", "TPI_vars.pkl"))
    print(f"[baseline] REUSED saved solve at {BASE} (no baseline re-solve)")

    for tag, aff in (("mortality_only", ("mortality",)), ("morbidity_only", ("e",))):
        rdir = os.path.join(OUT, tag)
        pr = copy.deepcopy(p0)
        pr.baseline = False
        pr.baseline_dir = BASE
        pr.output_base = rdir
        pr.__dict__.pop("_e_long_cache", None)
        ctx = ExperimentContext(country=PHL, og_reform=pr, base_tpi=base_tpi)
        prov = channels.health(ctx, affects=aff)
        if ctx.extras.get("health_shock") is not None:
            ctx.og_reform = rt.apply_health_shock(ctx.og_reform, ctx.extras["health_shock"])
        print(f"\n=== SOLVING {tag}  affects={aff} ===")
        try:
            tpi = rt.solve(ctx.og_reform)
            macro = report.macro_pct_diff(base_tpi, tpi)
            print(f"[{tag}] CONVERGED.  macro %: "
                  + ", ".join(f"{k}={np.nanmean(v):+.3f}" for k, v in macro.items()))
        except Exception as e:  # noqa: BLE001
            print(f"[{tag}] FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
