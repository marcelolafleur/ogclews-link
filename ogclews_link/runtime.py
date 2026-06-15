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

    def solve(self, p):
        from ogcore.execute import runner
        from ogcore.utils import safe_read_pickle

        label = "baseline" if p.baseline else "reform"
        with make_client(self.num_workers) as client, \
                solve_progress(getattr(p, "mindist_TPI", 1e-5), label, enabled=self.show_progress):
            runner(p, time_path=True, client=client)
        return safe_read_pickle(os.path.join(p.output_base, "TPI", "TPI_vars.pkl"))

    def apply_mortality(self, p, effect, time_horizon=15):
        """Recompute the population with an air-quality mortality effect (health channel),
        the way PEP_simulation.py does it (via get_pop_data.health_pop), then update p."""
        sys.path.insert(0, CLEWS_OG_SIM)
        import get_pop_data

        aux = getattr(p, "_pop_aux", None)
        if aux is None:
            print("[runtime] no pop aux on params; skipping mortality effect")
            return p
        p.__dict__.pop("_e_long_cache", None)  # ogcore memoizes e; bust it so reform e edits take effect
        un = getattr(p, "_un_code", None) or "608"
        new_pop, _deaths = get_pop_data.health_pop(
            p, aux["pop_dist"], aux["pre_pop_dist"], aux["fert_rates"], aux["mort_rates"],
            aux["infmort_rates"], aux["imm_rates"], un,
            mort_effect=effect, time_horizon=time_horizon)
        p.update_specifications(new_pop)
        return p

    def runner_for(self, country):
        """A framework.Runner bound to this runtime."""
        from .framework import Runner
        return Runner(build_baseline=self.build_baseline, solve=self.solve,
                      apply_mortality=self.apply_mortality)
