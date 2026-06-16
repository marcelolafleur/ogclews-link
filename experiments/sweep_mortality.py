"""Disentangle whether the mortality SS failure is SIGN (lives saved vs added) or MAGNITUDE.
Uses the built-in get_pop_objs + disease_pop's exact additive age-profile shock construction, with
a directly-controlled shock_scale, reusing the saved baseline. Reports year-5 deaths change +
convergence for each. (negative shock_scale = mortality DOWN = lives saved = the pollution direction.)

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/sweep_mortality.py
"""
from __future__ import annotations

import copy
import importlib.util
import os

import numpy as np
from ogcore import demographics
from ogcore.utils import safe_read_pickle

from ogclews_link import channels, health_profile, report  # noqa: F401 (registers channels)
from ogclews_link.country import PHL
from ogclews_link.runtime import Runtime

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/validate_health"
BASE = os.path.join(OUT, "health", "baseline")

_spec = importlib.util.spec_from_file_location(
    "cod_get_pop_data", "/Users/mlafleur/Projects/CostOfDisease/code/get_pop_data.py")
cod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cod)


def main():
    rt = Runtime(num_workers=7, show_progress=False)
    p0, _ = rt.build_baseline(PHL, BASE)
    base_tpi = safe_read_pickle(os.path.join(BASE, "TPI", "TPI_vars.pkl"))
    aux = {k: np.asarray(v) for k, v in p0._pop_aux.items()}
    ny, nage = 5, aux["mort_rates"].shape[1]
    h = health_profile.placeholder_profile(num_ages=nage)
    fert = cod.extrapolate_demographics(aux["fert_rates"], ny)
    mort = cod.extrapolate_demographics(aux["mort_rates"], ny)
    imm = cod.extrapolate_demographics(aux["imm_rates"], ny)
    infm = cod.extrapolate_demographics(aux["infmort_rates"], ny)
    pop_dist, pre = aux["pop_dist"], aux["pre_pop_dist"]
    base_d = cod.total_deaths(pop_dist, fert, mort, infm, imm, num_years=ny)[ny - 1].sum()

    def run(scale):
        alt = mort.copy()
        for i in range(ny):
            alt[i, :] = np.minimum(mort[i, :] + scale * h * ((i + 1) / ny), 1.0)
        d = cod.total_deaths(pop_dist, fert, alt, infm, imm, num_years=ny)[ny - 1].sum() - base_d
        pd = demographics.get_pop_objs(
            p0.E, p0.S, p0.T, 0, 99, country_id=PHL.un_code, fert_rates=fert, mort_rates=alt,
            infmort_rates=infm, imm_rates=imm, infer_pop=True, pop_dist=pop_dist[:1, :],
            pre_pop_dist=pre, initial_data_year=p0.start_year,
            final_data_year=p0.start_year + ny - 1, GraphDiag=False)
        pr = copy.deepcopy(p0)
        pr.baseline = False
        pr.baseline_dir = BASE
        pr.output_base = os.path.join(OUT, f"sweep_{scale:+.5f}".replace(".", "p"))
        pr.__dict__.pop("_e_long_cache", None)
        pr.update_specifications(pd)
        tag = f"shock_scale={scale:+.5f}  (year-5 deaths {d:+,.0f} -> {'lives saved' if d < 0 else 'deaths added'})"
        print(f"\n=== SOLVING {tag} ===")
        try:
            tpi = rt.solve(pr)
            print(f"[CONVERGED] {tag}  Y={np.nanmean(report.macro_pct_diff(base_tpi, tpi)['Y']):+.3f}%")
        except Exception as e:  # noqa: BLE001
            print(f"[FAILED]    {tag}  {type(e).__name__}")

    for scale in (-0.0002, -0.002, +0.0002):   # small down, larger down, small up
        run(scale)


if __name__ == "__main__":
    main()
