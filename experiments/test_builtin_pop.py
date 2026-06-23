"""Decisive test: do the BUILT-IN population functions (CostOfDisease `disease_pop` age-profile,
and the PHL `health_pop` uniform) converge with PHL data, where my hand-rolled apply_health_shock
failed? Reuses the saved baseline (no re-solve). If the built-ins converge, the fix is to call
them (and the failure was my hand-roll / the under-calibrated kappa).

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/test_builtin_pop.py
"""
from __future__ import annotations

import copy
import importlib.util
import os
import sys

import numpy as np
from ogcore.utils import safe_read_pickle

from ogclews_link import channels, health_profile, report  # noqa: F401
from ogclews_link.country import PHL
from ogclews_link.runtime import Runtime

CLEWS_OG_SIM = "/Users/mlafleur/Projects/CLEWS-OG/OG_simulations"  # PHL get_pop_data lives here
OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/validate_health"
BASE = os.path.join(OUT, "health", "baseline")

# CostOfDisease disease_pop (age-profile + brentq deaths target) -- load WITHOUT the get_pop_data
# name clash against the PHL one.
_spec = importlib.util.spec_from_file_location(
    "cod_get_pop_data", "/Users/mlafleur/Projects/CostOfDisease/code/get_pop_data.py")
cod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cod)

sys.path.insert(0, CLEWS_OG_SIM)
import get_pop_data as phl_gpd  # noqa: E402 (PHL health_pop, baseline_pop)


def main():
    rt = Runtime(num_workers=7, show_progress=False)
    p0, _ = rt.build_baseline(PHL, BASE)
    base_tpi = safe_read_pickle(os.path.join(BASE, "TPI", "TPI_vars.pkl"))
    aux = {k: np.asarray(v) for k, v in p0._pop_aux.items()}
    nage = aux["mort_rates"].shape[1]
    h = health_profile.placeholder_profile(num_ages=nage)
    print(f"[baseline] REUSED. mort_rates shape={aux['mort_rates'].shape}, profile len={len(h)}")

    def solve_variant(tag, pop_dict):
        rdir = os.path.join(OUT, tag)
        pr = copy.deepcopy(p0)
        pr.baseline = False
        pr.baseline_dir = BASE
        pr.output_base = rdir
        pr.__dict__.pop("_e_long_cache", None)
        pr.update_specifications(pop_dict)
        print(f"\n=== SOLVING {tag} ===")
        try:
            tpi = rt.solve(pr)
            macro = report.macro_pct_diff(base_tpi, tpi)
            print(f"[{tag}] CONVERGED.  macro %: "
                  + ", ".join(f"{k}={np.nanmean(v):+.3f}" for k, v in macro.items()))
        except Exception as e:  # noqa: BLE001
            print(f"[{tag}] FAILED: {type(e).__name__}: {e}")

    # A) built-in disease_pop -- age profile + brentq to a deaths target (here +2000 as a test)
    try:
        pd_disease, _ = cod.disease_pop(
            p0, aux["pop_dist"], aux["pre_pop_dist"], aux["fert_rates"], aux["mort_rates"],
            aux["infmort_rates"], aux["imm_rates"], un_country_code=PHL.un_code,
            excess_deaths=2000, hiv_mortality_profile=h, phase_in_years=5)
        solve_variant("builtin_disease_pop", pd_disease)
    except Exception as e:  # noqa: BLE001
        print(f"[disease_pop BUILD failed] {type(e).__name__}: {e}")

    # B) built-in PHL health_pop -- uniform proportional mortality change
    try:
        pd_health, _ = phl_gpd.health_pop(
            p0, aux["pop_dist"], aux["pre_pop_dist"], aux["fert_rates"], aux["mort_rates"],
            aux["infmort_rates"], aux["imm_rates"], un_country_code=PHL.un_code,
            mort_effect=-0.01, time_horizon=5)
        solve_variant("builtin_health_pop", pd_health)
    except Exception as e:  # noqa: BLE001
        print(f"[health_pop BUILD failed] {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
