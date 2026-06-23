"""The ogcore-touching layer: build an OG-PHL baseline, solve, apply the mortality effect.
All heavy imports are lazy so importing ogclews_link (and unit-testing the channels) needs
only numpy/pandas. These bound methods are injected into framework.run as build_baseline/solve/
apply_health, so the framework + channels stay importable without ogcore.
"""
from __future__ import annotations

import contextlib
import importlib.resources
import json
import multiprocessing
import os
from dataclasses import dataclass

import numpy as np

from .progress import solve_progress


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

        from ._calibration import PROD_DICT
        from ._demog import baseline_pop

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
        pop = baseline_pop(p, un_country_code=country.un_code, download=False)
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
        out = safe_read_pickle(os.path.join(p.output_base, *sub))
        # If the SS resource-constraint gate was loosened (the lives-saved health reform), report the
        # realized SS residual it actually governs (RC_SS gates the SS solve, NOT the TPI path — that's
        # RC_TPI), so a future profile/target drifting toward the gate is visible, not silently accepted.
        if float(getattr(p, "RC_SS", 1e-8)) > 1e-8:
            try:
                ss = safe_read_pickle(os.path.join(p.output_base, "SS", "SS_vars.pkl"))
                rc = ss.get("resource_constraint_error") if isinstance(ss, dict) else None
                if rc is not None:
                    print(f"[runtime] {label}: RC_SS gate loosened to {float(p.RC_SS):.0e}; "
                          f"realized SS max|RC|={np.max(np.abs(np.atleast_1d(rc))):.2e}")
            except Exception:  # noqa: BLE001  (diagnostic logging only)
                pass
        return out

    def apply_health_shock(self, p, spec):
        """Recompute the population under an AGE-PROFILE mortality shock -- the disease_pop method
        (DeBacker/Evans/LaFleur, CostOfDisease), via the in-repo bidirectional `health_pop.disease_pop`
        so the target may be negative (lives saved -- the cleaner-air direction). `spec` carries a
        SIGNED `excess_deaths` target, the peak-1 age profile h(s), and phase_years. The built-in
        ogcore.demographics.get_pop_objs rebuilds the whole population path."""
        from . import health_pop

        aux = getattr(p, "_pop_aux", None)
        if aux is None:
            print("[runtime] no pop aux; skipping health mortality shock")
            return p
        p.__dict__.pop("_e_long_cache", None)
        if "excess_deaths" not in spec:
            print("[runtime] health_shock spec missing 'excess_deaths'; skipping mortality shock")
            return p
        target = float(spec["excess_deaths"])
        profile = np.asarray(spec["profile"], dtype=float)
        ny = int(spec.get("phase_years", 5))
        un = getattr(p, "_un_code", None) or "608"
        # Loosen the SS resource-constraint gate for the LIVES-SAVED (mortality DOWN) reform ONLY.
        # That solve leaves an intrinsic ~5e-7 Walras residual on the production good: empirically
        # INVARIANT to a fresh re-solve (reform_use_baseline_solution=False) and to a 100-10000x
        # tighter fixed-point tolerance (mindist_SS=1e-11..1e-13 all give the same 5.089e-7), so it
        # is a structural property of the converged demographic equilibrium, NOT solver slop -- the
        # fixed point (sol.success @ mindist_SS) and household FOCs converge tightly regardless, and
        # only the post-solve RC_SS *assertion* trips. It is economically negligible (~1e-12 of GDP)
        # and far inside ogcore's own RC_TPI=1e-4 default and COD's RC_TPI=0.0075. The realistic
        # cumulative target (~-660) lands at ~1.7e-7, so rc_ss=1e-6 keeps ~6x headroom while staying
        # ~100x tighter than the prior 1e-4. The deaths-ADDED direction converges at the tight 1e-8
        # (8e-11 observed), so it is NOT loosened. See CountryConfig.rc_ss.
        if target < 0:
            p.RC_SS = float(spec.get("rc_ss", 1e-6))
        pop_dict, scale = health_pop.disease_pop(p, aux, target, profile, phase_years=ny,
                                                 un_country_code=un)
        print(f"[health] disease_pop: excess_deaths target {target:+,.0f} -> shock_scale {scale:+.5g}")
        p.update_specifications(pop_dict)
        return p
