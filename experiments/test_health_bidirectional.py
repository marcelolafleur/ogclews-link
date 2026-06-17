"""Decisive test: does OG-PHL SOLVE under a LIVES-SAVED (negative excess_deaths) mortality shock
via the bidirectional disease_pop -- and is the down-direction 'failure' merely the ultra-tight
RC_SS=1e-8 tripping on a ~1e-6 aggregate-resource-constraint residual? Reuses the saved baseline;
SS-only (the failure is an SS check, so no transition path needed).

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/test_health_bidirectional.py
"""
from __future__ import annotations

import copy
import os

import numpy as np

from ogclews_link import channels, health_pop, health_profile, report  # noqa: F401 (registers channels)
from ogclews_link.country import PHL
from ogclews_link.runtime import Runtime

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/validate_health"
BASE = os.path.join(OUT, "health", "baseline")


def main():
    rt = Runtime(num_workers=7, show_progress=False)
    p0, _ = rt.build_baseline(PHL, BASE)
    aux = {k: np.asarray(v) for k, v in p0._pop_aux.items()}
    h = health_profile.placeholder_profile(aux["mort_rates"].shape[1])

    def run(target, rc_ss):
        pd, scale = health_pop.disease_pop(p0, aux, target, h, phase_years=5,
                                           un_country_code=PHL.un_code)
        pr = copy.deepcopy(p0)
        pr.baseline = False
        pr.baseline_dir = BASE
        pr.output_base = os.path.join(OUT, f"bidir_{target:+.0f}_rc{rc_ss:.0e}".replace("+", ""))
        pr.RC_SS = rc_ss
        pr.__dict__.pop("_e_long_cache", None)
        pr.update_specifications(pd)
        tag = f"target={target:+,.0f} (shock_scale {scale:+.4g})  RC_SS={rc_ss:.0e}"
        try:
            rt.solve(pr, time_path=False)
            print(f"[CONVERGED] {tag}")
        except Exception as e:  # noqa: BLE001
            print(f"[FAILED]    {tag}  {type(e).__name__}: {str(e)[:90]}")

    print("=== control: deaths added (UP), default RC_SS=1e-8 ===")
    run(+2000.0, 1e-8)
    print("\n=== lives saved (DOWN), default RC_SS=1e-8 (the reported failure) ===")
    run(-2000.0, 1e-8)
    print("\n=== lives saved (DOWN), loosened RC_SS=1e-4 (tolerance-near-miss hypothesis) ===")
    run(-2000.0, 1e-4)


if __name__ == "__main__":
    main()
