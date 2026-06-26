"""The OG-env runner: the ONLY module that imports ogcore + a country OG package. It ships in the link
repo but is EXECUTED BY the OG model's own interpreter --

    <env_python> -m ogclews_link.og_runner export-baseline --og-package ogphl --out-dir ...
    <env_python> -m ogclews_link.og_runner solve-reform   --baseline-dir ... --reform-dir ... --overrides ...

-- with PYTHONPATH pointing at the link source so this module (and the pure-python serde/_demog/health_pop/
_calibration/progress it uses) import here, while ogcore + the country package come from the OG env. The
link never imports any of this. Boundary I/O is via serde (JSON in, .npz out); no ogcore object is ever
serialized (cloudpickle can pickle a Specifications but corrupts its paramtools validation schema on
reload), so the reform REBUILDS the baseline fresh instead of reloading one.

Two modes:
  export-baseline -- build the country baseline (generic via --og-package), solve it, and write the param
                     arrays + solution the link needs.
  solve-reform    -- rebuild the same baseline fresh, apply the link's parameter overrides (+ a health
                     mortality re-solve if present), solve the reform, write the reform solution.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.resources
import json
import os
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


def _discover_concordance(og_package, model_M):
    """The energy-port concordance for this country, discovered from the package's own PROD_DICT/CONS_DICT
    (electricity must be an ISOLATED industry -- see contract.Concordance.from_dicts). Returned as a plain
    dict for export, because the link's env cannot import the country package to compute it. A
    single-industry (M<=1) baseline has no electricity industry, so it is unconditionally unavailable."""
    from dataclasses import asdict

    from .contract import Concordance

    if int(model_M) <= 1:
        why = f"{og_package} ran at M={int(model_M)} (no multisector calibration) -- no electricity industry"
        return {"energy_industry_index": None, "energy_good_index": None,
                "unavailable": {"energy_industry_index": why, "energy_good_index": why}}
    pkg = importlib.import_module(og_package)
    prod, cons = getattr(pkg, "PROD_DICT", None), getattr(pkg, "CONS_DICT", None)
    if prod is None or cons is None:
        why = f"{og_package} exposes no PROD_DICT/CONS_DICT to locate electricity"
        return {"energy_industry_index": None, "energy_good_index": None,
                "unavailable": {"energy_industry_index": why, "energy_good_index": why}}
    # The concordance index is a POSITIONAL offset into PROD_DICT; it only lines up with the model's
    # Z/gamma/io_matrix columns if the loaded calibration was built at this exact aggregation. Refuse to
    # emit a possibly-misaligned index when the group count disagrees with the baseline's realized M.
    if len(prod) != int(model_M):
        why = (f"{og_package} PROD_DICT has {len(prod)} groups but the baseline solved at M={int(model_M)} "
               "-- the aggregation the concordance is read from does not match the model's columns, so the "
               "energy-port indices would be misaligned")
        return {"energy_industry_index": None, "energy_good_index": None,
                "unavailable": {"energy_industry_index": why, "energy_good_index": why}}
    return asdict(Concordance.from_dicts(prod, cons))


def _read_solution(output_base, ss):
    from ogcore.utils import safe_read_pickle
    sub = ("SS", "SS_vars.pkl") if ss else ("TPI", "TPI_vars.pkl")
    return safe_read_pickle(os.path.join(output_base, *sub))


def _build_baseline_specs(og_package, params_resource, og_start_year, num_workers, out_dir,
                          calibration=None):
    """Build the country baseline by LOADING the country model's OWN calibration -- the link no longer
    authors any aggregation or sector factors. Load the single-industry DEFAULT (``params_resource``) as
    the base, then OVERLAY the chosen multisector ``calibration`` if any. Country packages ship their
    multisector JSON as an update_specifications OVERLAY on the default: it sets M/I + the sector arrays
    but INHERITS scalars (e.g. initial_Kg_ratio) from the default, so loading it standalone fails
    paramtools cross-validation (e.g. gamma_g>0 requires initial_Kg_ratio>0). This mirrors the country's
    own load order (see ogphl examples/run_og_phl_multi_industry_calibrated). When ``calibration`` is None
    the baseline stays single-industry (the energy channels skip). Demographics are layered on
    (country-generic); the UN code is the package's own (ogphl.UN_COUNTRY_CODE), never the link's."""
    from ogcore.parameters import Specifications

    pkg = importlib.import_module(og_package)
    un_code = str(getattr(pkg, "UN_COUNTRY_CODE", "") or "")
    if not un_code:
        raise ValueError(f"{og_package} does not expose UN_COUNTRY_CODE; the demographic build needs it.")
    os.makedirs(out_dir, exist_ok=True)
    p = Specifications(baseline=True, num_workers=num_workers, baseline_dir=out_dir, output_base=out_dir)
    with importlib.resources.open_text(og_package, params_resource) as f:
        p.update_specifications(json.load(f))         # base: single-industry default (scalars like initial_Kg_ratio)
    if calibration:
        with importlib.resources.open_text(og_package, calibration) as f:
            p.update_specifications(json.load(f))     # overlay: the chosen multisector calibration
    kind = (f"{params_resource} + {calibration} overlay" if calibration
            else f"{params_resource} (single-industry -> energy channels skip)")
    print(f"[og_runner] {og_package}: loaded {kind} (M={p.M}, I={p.I})", file=sys.stderr)
    pop = baseline_pop(p, un_country_code=un_code, download=False)
    p.update_specifications(pop[0])
    if int(getattr(p, "start_year", og_start_year)) != og_start_year:
        print(f"[og_runner] WARNING: OG start_year {p.start_year} != scenario og_start_year {og_start_year}; "
              "CLEWS year-alignment will be off.", file=sys.stderr)
    p._un_code = un_code
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

def inprocess_callables(og_package, params_resource, og_start_year, *,
                        num_workers=7, show_progress=False, ss=False, calibration=None):
    """Return (export_baseline, solve_reform) closures that build/solve in-process via ogcore.
    ``calibration`` is the chosen multisector param resource (None -> single-industry default)."""
    def export_baseline(country, out_root):
        base_dir = os.path.join(out_root, "baseline")
        p = _build_baseline_specs(og_package, params_resource, og_start_year,
                                  num_workers, base_dir, calibration=calibration)
        base = _solve(p, num_workers, ss, show_progress, "baseline")
        # Export the discovered concordance next to the baseline (same file the subprocess path writes),
        # so framework._load_concordance + the viz driver find the run's energy ports either way.
        with open(os.path.join(base_dir, "baseline_meta.json"), "w") as f:
            json.dump({"schema_version": serde.BASELINE_META_SCHEMA,
                       "og_package": og_package, "M": int(p.M), "I": int(p.I),
                       "concordance": _discover_concordance(og_package, p.M)}, f)
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
    p = _build_baseline_specs(a.og_package, a.params_resource, a.og_start_year,
                              a.num_workers, a.out_dir, calibration=a.calibration)
    sol = _solve(p, a.num_workers, a.ss, not a.no_progress, "baseline")
    serde.save_params_npz(os.path.join(a.out_dir, "baseline_params.npz"), p)
    serde.save_solution_npz(os.path.join(a.out_dir, "baseline_solution.npz"), sol)
    if not a.ss:   # a TPI solve also wrote SS_vars; export the SS slice so SS-mode reforms compare SS->SS
        with contextlib.suppress(Exception):
            serde.save_solution_npz(os.path.join(a.out_dir, "baseline_solution_ss.npz"),
                                    _read_solution(a.out_dir, ss=True))
    # NB: we do NOT pickle the baseline Specifications. cloudpickle can serialize it but CORRUPTS
    # paramtools' validation schema on reload (update_specifications then fails), which the reform's
    # health re-solve needs. solve-reform rebuilds a FRESH baseline instead (deterministic, clean
    # paramtools state) and points baseline_dir at the solved solution written here.
    import ogcore
    # The energy-port concordance is discovered in the OG env (it needs the country package's PROD_DICT/
    # CONS_DICT, which the link env can't import) and EXPORTED here for the link to read -- tied to the
    # baseline's realized M, so a single-industry baseline reports the ports unavailable (channels skip).
    meta = {"schema_version": serde.BASELINE_META_SCHEMA,
            "og_package": a.og_package, "un_code": getattr(p, "_un_code", ""), "M": int(p.M), "I": int(p.I),
            "S": int(p.S), "start_year": int(getattr(p, "start_year", a.og_start_year)),
            "ogcore_version": getattr(ogcore, "__version__", None), "ss_only": bool(a.ss),
            "concordance": _discover_concordance(a.og_package, p.M)}
    with open(os.path.join(a.out_dir, "baseline_meta.json"), "w") as f:
        json.dump(meta, f)
    print(f"[og_runner] exported baseline -> {a.out_dir}", file=sys.stderr)


def solve_reform(a):
    # Rebuild the baseline Specifications FRESH (deterministic; same calibration the export solved) rather
    # than reloading a pickle -- a fresh object has clean paramtools state, so the health re-solve's
    # update_specifications works (a cloudpickled one's doesn't). baseline_dir points at the solved
    # baseline solution on disk, which OG-Core reads for the reform.
    r = _build_baseline_specs(a.og_package, a.params_resource, a.og_start_year,
                              a.num_workers, a.reform_dir, calibration=a.calibration)
    r.baseline = False
    r.baseline_dir = a.baseline_dir
    r.output_base = a.reform_dir
    # Apply the channel overrides by DIRECT attribute assignment -- exactly what the channels do
    # in-process (p.tau_c = ..., p.alpha_I = ..., p.e = ...). Routing them through update_specifications
    # re-runs paramtools validation that direct assignment never triggers (it rejects the full morbidity
    # e array); OG-Core's solver reads these numpy attributes directly, so setattr reproduces the old
    # in-process semantics exactly.
    for name, value in serde.read_overrides_json(a.overrides).items():
        setattr(r, name, value)
    r.__dict__.pop("_e_long_cache", None)        # e may have been replaced; drop ogcore's memoized long-e
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
    e.add_argument("--params-resource", required=True,
                   help="the package's single-industry default params (loaded when no --calibration is chosen)")
    e.add_argument("--calibration", default=None,
                   help="chosen multisector param resource (from discovery); omit for single-industry")
    e.add_argument("--og-start-year", type=int, required=True)
    e.add_argument("--num-workers", type=int, default=1)
    e.add_argument("--out-dir", required=True)
    e.add_argument("--ss", action="store_true")
    e.add_argument("--no-progress", action="store_true")
    e.set_defaults(func=export_baseline)

    s = sub.add_parser("solve-reform")
    s.add_argument("--baseline-dir", required=True)
    s.add_argument("--reform-dir", required=True)
    s.add_argument("--overrides", required=True)
    s.add_argument("--health-shock", default=None)
    s.add_argument("--num-workers", type=int, default=1)
    # the reform rebuilds the baseline fresh (clean paramtools state), so it needs the same build inputs:
    s.add_argument("--og-package", required=True)
    s.add_argument("--params-resource", required=True)
    s.add_argument("--calibration", default=None,
                   help="MUST match the calibration the baseline was exported with (fresh rebuild)")
    s.add_argument("--og-start-year", type=int, required=True)
    s.add_argument("--ss", action="store_true")
    s.add_argument("--no-progress", action="store_true")
    s.set_defaults(func=solve_reform)

    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
