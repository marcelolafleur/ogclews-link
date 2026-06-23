"""The OG-env runner: the ONLY module that imports ogcore + a country OG package. It ships in the link
repo but is EXECUTED BY the OG model's own interpreter --

    <env_python> -m ogclews_link.og_runner export-baseline --og-package ogphl --un-code 608 --out-dir ...
    <env_python> -m ogclews_link.og_runner solve-reform   --baseline-dir ... --reform-dir ... --overrides ...

-- with PYTHONPATH pointing at the link source so this module (and the pure-python serde/_demog/health_pop/
_calibration/progress it uses) import here, while ogcore + the country package come from the OG env. The
link never imports any of this. Boundary I/O is via serde (JSON in, .npz out); the baseline Specifications
is pickled only WITHIN this env (never sent to the link).

Two modes:
  export-baseline -- build the country baseline (generic via --og-package), solve it, and write the param
                     arrays + solution the link needs (+ the pickled Specifications for the reform step).
  solve-reform    -- reload the baseline, apply the link's parameter overrides (+ a health mortality
                     re-solve if present), solve the reform, write the reform solution.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.resources
import json
import os
import pickle
import sys

import numpy as np

from . import health_pop, serde
from ._demog import baseline_pop
from .progress import solve_progress


@contextlib.contextmanager
def _client(num_workers):
    from distributed import Client
    if num_workers and num_workers > 1:
        c = Client(n_workers=num_workers, threads_per_worker=1, dashboard_address=None)
    else:
        c = Client(processes=False, dashboard_address=None)
    try:
        yield c
    finally:
        c.close()


def _resolve_prod_dict(og_package, un_code, prod_dict_path):
    """The COUPLING's M-industry aggregation (sector -> SAM activity codes) used to build the I-O matrix.
    This is a LINK decision -- which OG industries the channels map to (M=4 for PHL, with Electricity
    isolated for the energy channel) -- NOT the country OG package's own PROD_DICT (e.g. ogphl ships a
    finer 7-group disaggregation; using it would give the wrong io_matrix shape and break the solve).
    Preference: (1) an explicit --prod-dict JSON override, (2) the vendored per-country coupling dict."""
    if prod_dict_path:
        with open(prod_dict_path) as f:
            return json.load(f)
    from ._calibration import PROD_DICT as VENDORED   # the PHL coupling aggregation (matches golden)
    if str(un_code) != "608":
        print(f"[og_runner] WARNING: using the vendored PHL coupling PROD_DICT for un_code {un_code}; "
              "pass --prod-dict with this country's coupling aggregation.", file=sys.stderr)
    return VENDORED


def _read_solution(output_base, ss):
    from ogcore.utils import safe_read_pickle
    sub = ("SS", "SS_vars.pkl") if ss else ("TPI", "TPI_vars.pkl")
    return safe_read_pickle(os.path.join(output_base, *sub))


def _build_baseline_specs(og_package, params_resource, un_code, og_start_year, num_workers,
                          out_dir, prod_dict_path=None, M=None, I=None):
    """Port of the former Runtime.build_baseline, made country-generic (import via og_package).

    Dimensions are DISCOVERED from the coupling calibration, not hardcoded: M = the number of OG
    industries in the coupling PROD_DICT (the aggregation that isolates electricity as its own column
    -- see contract.Concordance, which discovers the energy index from the same dict and refuses to run
    if electricity is split, e.g. ogphl's native 'Utilities' = electricity+water); I = the number of
    consumption goods in alpha_c. For PHL this is M=4, I=5 -- but it falls out of the aggregation, so a
    new country supplies its own electricity-isolating PROD_DICT and M/I follow. M/I args override only
    for diagnostics."""
    from ogcore.parameters import Specifications

    io = importlib.import_module(f"{og_package}.input_output")
    os.makedirs(out_dir, exist_ok=True)
    p = Specifications(baseline=True, num_workers=num_workers, baseline_dir=out_dir, output_base=out_dir)
    with importlib.resources.open_text(og_package, params_resource) as f:
        p.update_specifications(json.load(f))
    prod_dict = _resolve_prod_dict(og_package, un_code, prod_dict_path)
    alpha_c = io.get_alpha_c()
    io_df = io.get_io_matrix(prod_dict=prod_dict)
    p.M = M if M is not None else len(prod_dict)         # OG industries = coupling PROD_DICT groups
    p.I = I if I is not None else len(alpha_c)            # consumption goods = alpha_c entries
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
    pop = baseline_pop(p, un_country_code=un_code, download=False)
    p.update_specifications(pop[0])
    if int(getattr(p, "start_year", og_start_year)) != og_start_year:
        print(f"[og_runner] WARNING: OG start_year {p.start_year} != scenario og_start_year {og_start_year}; "
              "CLEWS year-alignment will be off.", file=sys.stderr)
    p._un_code = str(un_code)
    p._pop_aux = {"pop_dist": pop[1], "pre_pop_dist": pop[2], "fert_rates": pop[3],
                  "mort_rates": pop[4], "infmort_rates": pop[5], "imm_rates": pop[6]}
    return p


def _solve(p, num_workers, ss, show_progress, label):
    from ogcore.execute import runner
    with _client(num_workers) as client, \
            solve_progress(getattr(p, "mindist_TPI", 1e-5), label, enabled=show_progress):
        runner(p, time_path=not ss, client=client)
    out = _read_solution(p.output_base, ss)
    if float(getattr(p, "RC_SS", 1e-8)) > 1e-8:
        with contextlib.suppress(Exception):
            from ogcore.utils import safe_read_pickle
            ss_vars = safe_read_pickle(os.path.join(p.output_base, "SS", "SS_vars.pkl"))
            rc = ss_vars.get("resource_constraint_error") if isinstance(ss_vars, dict) else None
            if rc is not None:
                print(f"[og_runner] {label}: RC_SS gate loosened to {float(p.RC_SS):.0e}; realized SS "
                      f"max|RC|={np.max(np.abs(np.atleast_1d(rc))):.2e}", file=sys.stderr)
    return out


def _apply_health(p, health):
    """Port of Runtime.apply_health_shock: the signed-target disease_pop re-solve, RC_SS loosened ONLY
    for the lives-saved (excess_deaths<0) direction. Runs here because it needs a real Specifications +
    ogcore.demographics."""
    aux = getattr(p, "_pop_aux", None)
    if aux is None or "excess_deaths" not in health:
        print("[og_runner] health spec without pop aux / excess_deaths; skipping mortality shock",
              file=sys.stderr)
        return p
    p.__dict__.pop("_e_long_cache", None)
    target = float(health["excess_deaths"])
    profile = np.asarray(health["profile"], dtype=float)
    ny = int(health.get("phase_years", 5))
    un = getattr(p, "_un_code", None) or "608"
    if target < 0:
        p.RC_SS = float(health.get("rc_ss", 1e-6))
    pop_dict, scale = health_pop.disease_pop(p, aux, target, profile, phase_years=ny, un_country_code=un)
    print(f"[og_runner] disease_pop: excess_deaths target {target:+,.0f} -> shock_scale {scale:+.5g}",
          file=sys.stderr)
    p.update_specifications(pop_dict)
    return p


# --- in-process framework callables (OG env only) --------------------------------
# Same contract as runtime.export_baseline / solve_reform, but solving IN THIS PROCESS (no subprocess).
# For scripts that already run under the OG model's interpreter and want OG-Core's native plotting too
# (e.g. run_across_steps' full deck). framework.run works with either pair injected.

def inprocess_callables(og_package, params_resource, un_code, og_start_year, *,
                        num_workers=7, show_progress=False, ss=False, M=None, I=None):
    """Return (export_baseline, solve_reform) closures that build/solve in-process via ogcore."""
    def export_baseline(country, out_root):
        base_dir = os.path.join(out_root, "baseline")
        p = _build_baseline_specs(og_package, params_resource, un_code, og_start_year,
                                  num_workers, base_dir, None, M=M, I=I)
        base = _solve(p, num_workers, ss, show_progress, "baseline")
        return p, base, base_dir, {}        # template = real Specifications; baseline_arrays unused here

    def solve_reform(og_reform, baseline_arrays, health_shock, base_dir, reform_dir, country):
        og_reform.baseline = False
        og_reform.baseline_dir = base_dir
        og_reform.output_base = reform_dir
        og_reform.__dict__.pop("_e_long_cache", None)
        os.makedirs(reform_dir, exist_ok=True)
        if health_shock is not None:
            og_reform = _apply_health(og_reform, health_shock)
        return _solve(og_reform, num_workers, ss, show_progress, "reform")

    return export_baseline, solve_reform


# --- subprocess modes (invoked by the link via the CLI) --------------------------

def export_baseline(a):
    p = _build_baseline_specs(a.og_package, a.params_resource, a.un_code, a.og_start_year,
                              a.num_workers, a.out_dir, a.prod_dict, M=a.m, I=a.i)
    sol = _solve(p, a.num_workers, a.ss, not a.no_progress, "baseline")
    serde.save_params_npz(os.path.join(a.out_dir, "baseline_params.npz"), p)
    serde.save_solution_npz(os.path.join(a.out_dir, "baseline_solution.npz"), sol)
    if not a.ss:   # a TPI solve also wrote SS_vars; export the SS slice so SS-mode reforms compare SS->SS
        with contextlib.suppress(Exception):
            serde.save_solution_npz(os.path.join(a.out_dir, "baseline_solution_ss.npz"),
                                    _read_solution(a.out_dir, ss=True))
    with open(os.path.join(a.out_dir, "baseline_p.pkl"), "wb") as f:
        pickle.dump(p, f)
    import ogcore
    meta = {"og_package": a.og_package, "un_code": str(a.un_code), "M": int(p.M), "I": int(p.I),
            "S": int(p.S), "start_year": int(getattr(p, "start_year", a.og_start_year)),
            "ogcore_version": getattr(ogcore, "__version__", None), "ss_only": bool(a.ss)}
    with open(os.path.join(a.out_dir, "baseline_meta.json"), "w") as f:
        json.dump(meta, f)
    print(f"[og_runner] exported baseline -> {a.out_dir}", file=sys.stderr)


def solve_reform(a):
    import copy
    with open(os.path.join(a.baseline_dir, "baseline_p.pkl"), "rb") as f:
        base_p = pickle.load(f)
    r = copy.deepcopy(base_p)
    r.baseline = False
    r.baseline_dir = a.baseline_dir
    r.output_base = a.reform_dir
    r.__dict__.pop("_e_long_cache", None)
    os.makedirs(a.reform_dir, exist_ok=True)
    r.update_specifications(serde.read_overrides_json(a.overrides))
    if a.health_shock and os.path.exists(a.health_shock):
        r = _apply_health(r, serde.read_health_json(a.health_shock))
    sol = _solve(r, a.num_workers, a.ss, not a.no_progress, "reform")
    serde.save_solution_npz(os.path.join(a.reform_dir, "reform_solution.npz"), sol)
    print(f"[og_runner] solved reform -> {a.reform_dir}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ogclews_link.og_runner")
    sub = ap.add_subparsers(dest="mode", required=True)

    e = sub.add_parser("export-baseline")
    e.add_argument("--og-package", required=True)
    e.add_argument("--params-resource", required=True)
    e.add_argument("--un-code", required=True)
    e.add_argument("--m", type=int, default=None, help="override OG industry count (default: len(PROD_DICT))")
    e.add_argument("--i", type=int, default=None, help="override consumption-good count (default: len(alpha_c))")
    e.add_argument("--og-start-year", type=int, required=True)
    e.add_argument("--num-workers", type=int, default=1)
    e.add_argument("--out-dir", required=True)
    e.add_argument("--prod-dict", default=None)
    e.add_argument("--ss", action="store_true")
    e.add_argument("--no-progress", action="store_true")
    e.set_defaults(func=export_baseline)

    s = sub.add_parser("solve-reform")
    s.add_argument("--baseline-dir", required=True)
    s.add_argument("--reform-dir", required=True)
    s.add_argument("--overrides", required=True)
    s.add_argument("--health-shock", default=None)
    s.add_argument("--num-workers", type=int, default=1)
    s.add_argument("--ss", action="store_true")
    s.add_argument("--no-progress", action="store_true")
    s.set_defaults(func=solve_reform)

    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
