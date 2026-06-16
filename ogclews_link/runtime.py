"""The ogcore-touching layer: build an OG-PHL baseline, solve, apply the mortality effect.
All heavy imports are lazy so importing ogclews_link (and unit-testing the channels) needs
only numpy/pandas. The framework Runner is given this object's bound methods.
"""
from __future__ import annotations

import contextlib
import importlib.resources
import json
import multiprocessing
import os
import sys
from dataclasses import dataclass

import numpy as np

from .progress import solve_progress

# calibration_values (M=4 PROD_DICT) and get_pop_data live alongside PEP_simulation.py
CLEWS_OG_SIM = "/Users/mlafleur/Projects/CLEWS-OG/OG_simulations"


@contextlib.contextmanager
def make_client(num_workers):
    from distributed import Client
    if num_workers and num_workers > 1:
        client = Client(n_workers=num_workers, threads_per_worker=1, dashboard_address=None)
    else:
        client = Client(processes=False, dashboard_address=None)
    try:
        yield client
    finally:
        client.close()


@dataclass
class Runtime:
    num_workers: int = min(multiprocessing.cpu_count(), 7)
    show_progress: bool = True

    def build_baseline(self, country, out_dir):
        """OG-PHL M=4/I=5 baseline (mirrors PEP_simulation.py + the c_min length-I fix)."""
        from ogcore.parameters import Specifications
        from ogphl import input_output as io

        sys.path.insert(0, CLEWS_OG_SIM)
        import get_pop_data
        from calibration_values import PROD_DICT

        os.makedirs(out_dir, exist_ok=True)
        p = Specifications(baseline=True, num_workers=self.num_workers,
                           baseline_dir=out_dir, output_base=out_dir)
        with importlib.resources.open_text("ogphl", "ogphl_default_parameters.json") as f:
            p.update_specifications(json.load(f))
        p.M, p.I = 4, 5
        alpha_c = io.get_alpha_c()
        io_df = io.get_io_matrix(prod_dict=PROD_DICT)
        p.update_specifications({
            "gamma_g": [p.gamma_g] * p.M,
            "epsilon": [p.epsilon] * p.M,
            "gamma": [p.gamma] * p.M,
            "cit_rate": [[p.cit_rate[0][0]]],
            "tau_c": [[float(p.tau_c[0][0])] * p.I],
            "c_min": [0.0] * p.I,
            "alpha_c": np.array(list(alpha_c.values())),
            "io_matrix": io_df.values,
            "initial_guess_r_SS": 0.050 * 1.2,
            "initial_guess_TR_SS": 0.2,
            "initial_guess_factor_SS": 144617.0,
        })
        pop = get_pop_data.baseline_pop(p, un_country_code=country.un_code, download=False)
        p.update_specifications(pop[0])
        if int(getattr(p, "start_year", country.scenario.og_start_year)) != country.scenario.og_start_year:
            print(f"[runtime] WARNING: OG start_year {p.start_year} != scenario og_start_year "
                  f"{country.scenario.og_start_year}; CLEWS year-alignment will be off.")
        p._un_code = country.un_code
        # stash the demographic arrays the health channel's mortality effect needs
        p._pop_aux = {"pop_dist": pop[1], "pre_pop_dist": pop[2], "fert_rates": pop[3],
                      "mort_rates": pop[4], "infmort_rates": pop[5], "imm_rates": pop[6]}
        return p, {"io_df": io_df}

    def solve(self, p, time_path=True):
        from ogcore.execute import runner
        from ogcore.utils import safe_read_pickle

        label = "baseline" if p.baseline else "reform"
        with make_client(self.num_workers) as client, \
                solve_progress(getattr(p, "mindist_TPI", 1e-5), label, enabled=self.show_progress):
            runner(p, time_path=time_path, client=client)
        # time_path=False solves the steady state only -- fast, and enough to surface the SS
        # "aggregate resource constraint not satisfied" failure without the full transition path.
        sub = ("TPI", "TPI_vars.pkl") if time_path else ("SS", "SS_vars.pkl")
        return safe_read_pickle(os.path.join(p.output_base, *sub))

    def apply_health_shock(self, p, spec):
        """Recompute the population under an AGE-PROFILE mortality shock -- the disease_pop
        method (DeBacker/Evans/LaFleur, CostOfDisease): alt_mort = clip(mort0 + kappa*g_t*h(s),
        0, 1), phased in over phase_years, then ogcore.demographics.get_pop_objs rebuilds the
        whole population path. h(s) is a peak-1 age shape; kappa carries the magnitude/sign
        (negative kappa = cleaner air -> fewer deaths -> bigger population)."""
        from ogcore import demographics

        aux = getattr(p, "_pop_aux", None)
        if aux is None:
            print("[runtime] no pop aux; skipping health mortality shock")
            return p
        p.__dict__.pop("_e_long_cache", None)
        kappa = float(spec["kappa"])
        h = np.asarray(spec["profile"], dtype=float)
        ny = int(spec.get("phase_years", 5))
        un = getattr(p, "_un_code", None) or "608"

        def _ext_age(a):  # extrapolate an (years, ages) path to ny rows (repeat last row)
            a = np.atleast_2d(np.asarray(a, dtype=float))
            return a[:ny] if a.shape[0] >= ny else np.vstack([a, np.repeat(a[-1:], ny - a.shape[0], 0)])

        def _ext_yr(a):   # extrapolate a per-year scalar series (infant mortality) to ny
            a = np.ravel(np.asarray(a, dtype=float))
            return a[:ny] if a.shape[0] >= ny else np.concatenate([a, np.repeat(a[-1:], ny - a.shape[0])])

        mort = _ext_age(aux["mort_rates"])
        fert, imm = _ext_age(aux["fert_rates"]), _ext_age(aux["imm_rates"])
        infmort = _ext_yr(aux["infmort_rates"])
        nage = mort.shape[1]
        if len(h) != nage:  # match the profile to the model's age dimension
            h = np.interp(np.linspace(0, 1, nage), np.linspace(0, 1, len(h)), h)
        alt_mort = mort.copy()
        for t in range(ny):
            alt_mort[t, :] = np.clip(mort[t, :] + kappa * ((t + 1) / ny) * h, 0.0, 1.0)

        pop_dict = demographics.get_pop_objs(
            p.E, p.S, p.T, 0, 99, fert_rates=fert, mort_rates=alt_mort, infmort_rates=infmort,
            imm_rates=imm, infer_pop=True, pop_dist=np.asarray(aux["pop_dist"])[:1, :],
            pre_pop_dist=aux["pre_pop_dist"], country_id=un, initial_data_year=p.start_year,
            final_data_year=p.start_year + ny - 1, GraphDiag=False)
        p.update_specifications(pop_dict)
        return p

    def runner_for(self, country):
        """A framework.Runner bound to this runtime."""
        from .framework import Runner
        return Runner(build_baseline=self.build_baseline, solve=self.solve,
                      apply_health=self.apply_health_shock)
