"""Decisive test: does OG-PHL SOLVE under a LIVES-SAVED (negative excess_deaths) mortality shock
via the bidirectional disease_pop -- and is the down-direction 'failure' merely the ultra-tight
RC_SS=1e-8 tripping on a ~1e-6 aggregate-resource-constraint residual? Reuses the saved baseline;
SS-only (the failure is an SS check, so no transition path needed).

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/test_health_bidirectional.py

Runs UNDER the OG model's interpreter (it pokes the disease_pop demographic re-solve directly), using
og_runner's in-process build/solve helpers.
"""
from __future__ import annotations

import copy
import os

import numpy as np

from ogclews_link import (channels, health_pop, health_profile,  # noqa: F401 (registers channels)
                          og_runner, registry, report)
from ogclews_link.country import PHL

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/validate_health"
BASE = os.path.join(OUT, "health", "baseline")


def main():
    entry = registry.lookup(PHL)
    p0 = og_runner._build_baseline_specs(entry.og_package, entry.params_resource_name, PHL.un_code,
                                         PHL.scenario.og_start_year, 7, BASE)
    og_runner._solve(p0, 7, ss=True, show_progress=False, label="baseline")   # solve baseline SS into BASE
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
            og_runner._solve(pr, 7, ss=True, show_progress=False, label=f"bidir {target:+.0f}")
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
