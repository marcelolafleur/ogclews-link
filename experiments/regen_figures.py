"""Regenerate every figure for an existing across-steps run from the pickles already on disk
-- no model solve. Use to iterate on figure STYLE without re-running OG-Core.

I/O is parameterized so the viz lane reads the SHARED solved pickles but writes figures to a
VIZ-LOCAL dir (never stomping the health lane's figures). Resolution order for each path is
CLI flag > env var > default:

    --run-dir / OGCLEWS_RUN_DIR   input  (read-only): the solved across-steps tree
    --fig-dir / OGCLEWS_FIG_DIR   output (viz-local): where figures are written
    --gbd-csv / OGCLEWS_GBD_CSV   input  (read-only): IHME GBD burden CSV for health profiles

Defaults: read from the shared health-lane run, write to <repo>/figs, find the GBD CSV in the
shared repo's IHME-GBD_2023_DATA/.

    PYTHONPATH=$PWD /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/regen_figures.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os

from ogcore.utils import safe_read_pickle

from ogclews_link import (channels, figures, report_html,  # noqa: F401
                          viz_dashboard, viz_distribution, viz_health, viz_transition, viz_welfare)
from ogclews_link.country import PHL

# The shared, solved across-steps tree (health lane). Read-only for the viz lane.
SHARED_RUN = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/across_steps"
# This worktree's root (experiments/ -> repo root), for the viz-local figure dir default.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOTE = ("Illustrative: +20% energy-price wedge (a cost-index proxy, not the CLEWS dual); "
        "investment/carbon magnitudes uncalibrated; carbon revenue not recycled.")
# The headline reform for OG-Core's own default suite + lifecycle/transition figures.
HEADLINE_STEP = "+ health"


def _resolve(cli_val, env_key, default):
    return cli_val or os.environ.get(env_key) or default


def _default_gbd_csv():
    """The GBD burden CSV in the SHARED repo (the viz worktree has no IHME export of its own)."""
    shared_repo = os.path.normpath(os.path.join(SHARED_RUN, "..", ".."))
    hits = [h for h in glob.glob(os.path.join(shared_repo, "IHME-GBD_2023_DATA", "*.csv"))
            if "citation" not in os.path.basename(h).lower()]
    return sorted(hits)[0] if hits else (getattr(PHL, "gbd_burden_csv", None) or None)


def _tpi(run_dir, label):
    p = os.path.join(run_dir, label, "TPI", "TPI_vars.pkl")
    return safe_read_pickle(p) if os.path.isfile(p) else None


def _params(run_dir, label):
    p = os.path.join(run_dir, label, "model_params.pkl")
    return safe_read_pickle(p) if os.path.isfile(p) else None


def _ss(run_dir, label):
    p = os.path.join(run_dir, label, "SS", "SS_vars.pkl")
    return safe_read_pickle(p) if os.path.isfile(p) else None


def _start_year(base_dir, default=2026):
    """Calendar start year for the transition x-axis, from the run's model_params."""
    try:
        p = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
        return int(getattr(p, "start_year", default))
    except Exception:  # noqa: BLE001
        return int(getattr(PHL.scenario, "og_start_year", default) or default)


def _try(fn, *a, **k):
    """Run a figure builder, never let one failure abort the regen sweep."""
    try:
        return fn(*a, **k)
    except Exception as e:  # noqa: BLE001
        print(f"  [skip] {getattr(fn, '__name__', fn)}: {type(e).__name__}: {e}")
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", help="input solved across-steps tree (read-only)")
    ap.add_argument("--fig-dir", help="output dir for figures (viz-local)")
    ap.add_argument("--gbd-csv", help="IHME GBD burden CSV for health age-profile figures")
    args = ap.parse_args(argv)

    run_dir = _resolve(args.run_dir, "OGCLEWS_RUN_DIR", SHARED_RUN)
    fig_dir = _resolve(args.fig_dir, "OGCLEWS_FIG_DIR", os.path.join(REPO_ROOT, "figs"))
    gbd_csv = _resolve(args.gbd_csv, "OGCLEWS_GBD_CSV", _default_gbd_csv())
    os.makedirs(fig_dir, exist_ok=True)
    print(f"regen: read {run_dir}\n       write {fig_dir}")
    print(f"       gbd  {gbd_csv if gbd_csv and os.path.isfile(gbd_csv) else '(none — health profiles skipped)'}")

    ie = PHL.concordance.energy_good_index
    layered = json.load(open(os.path.join(run_dir, "layered_results.json")))

    # --- top-level figures (across steps) ---------------------------------------
    _try(figures.across_steps_waterfall, layered, fig_dir, note=NOTE)
    _try(figures.macro_honest, layered, fig_dir, note=NOTE)
    _try(figures.energy_physical, PHL, fig_dir)
    _try(figures.across_steps_table, layered, os.path.join(fig_dir, "across_steps_summary.csv"))
    _try(report_html.write_html_report, layered, os.path.join(fig_dir, "report.html"))

    # --- OG-Core's own canonical suite (free reference set) for the headline reform ----
    base_dir = os.path.join(run_dir, "baseline")
    headline_dir = os.path.join(run_dir, HEADLINE_STEP)
    if os.path.isdir(headline_dir):
        _try(figures.og_default_outputs, base_dir, headline_dir,
             os.path.join(fig_dir, "og_suite"), plots=True)

    base_tpi = _tpi(run_dir, "baseline")
    try:
        factor = float(safe_read_pickle(os.path.join(run_dir, "baseline", "SS", "SS_vars.pkl"))["factor"])
    except Exception:  # noqa: BLE001
        factor = None
    start_year = _start_year(base_dir)

    # --- editorial transition-path figures for the headline reform --------------
    headline_tpi = _tpi(run_dir, HEADLINE_STEP)
    if base_tpi is not None and headline_tpi is not None:
        for fn in (viz_transition.macro_transition, viz_transition.fiscal_transition,
                   viz_transition.revenue_transition, viz_transition.rates_transition):
            _try(fn, base_tpi, headline_tpi, fig_dir, start_year=start_year, note=NOTE)

    # --- health-channel visuals -------------------------------------------------
    if gbd_csv and os.path.isfile(gbd_csv):
        _try(viz_health.gbd_age_profiles, gbd_csv, PHL.name, int(PHL.gbd_year), fig_dir, note=NOTE)
    base_params, headline_params = _params(run_dir, "baseline"), _params(run_dir, HEADLINE_STEP)
    if base_params is not None and headline_params is not None:
        _try(viz_health.mortality_by_age, base_params, headline_params, fig_dir, note=NOTE)
    _try(viz_health.gdp_split, layered, fig_dir, note=NOTE)

    # --- welfare: consumption-equivalent variation (CEV) ------------------------
    base_ss, headline_ss = _ss(run_dir, "baseline"), _ss(run_dir, HEADLINE_STEP)
    if None not in (base_ss, headline_ss, base_params, headline_params):
        _try(viz_welfare.cev_by_group, base_ss, headline_ss, base_params, headline_params,
             fig_dir, note=NOTE)
    if base_tpi is not None and headline_tpi is not None and None not in (base_params, headline_params):
        _try(viz_welfare.cev_by_age, base_tpi, headline_tpi, base_params, headline_params,
             fig_dir, note=NOTE)

    # --- distributional richness ------------------------------------------------
    _try(viz_distribution.energy_demand_by_group, layered, fig_dir, note=NOTE)
    if None not in (base_ss, headline_ss, base_params):
        _try(viz_distribution.consumption_by_age, base_ss, headline_ss, base_params, fig_dir, note=NOTE)

    # --- one-page headline dashboard --------------------------------------------
    if None not in (base_tpi, headline_tpi, base_ss, headline_ss, base_params, headline_params):
        _try(viz_dashboard.headline_dashboard, layered, base_tpi, headline_tpi, base_ss, headline_ss,
             base_params, headline_params, PHL, fig_dir, start_year=start_year, note=NOTE)

    # --- per-step incidence hero ------------------------------------------------
    made = []
    for r in layered:
        label = r.get("step")
        if "macro" not in r or label == "baseline":
            continue
        reform_tpi = _tpi(run_dir, label)
        if base_tpi is None or reform_tpi is None:
            print(f"  (skip incidence for {label!r}: pickle missing)")
            continue
        sdir = os.path.join(fig_dir, "per_step", _slug(label))
        if _try(figures.incidence_hero, base_tpi, reform_tpi, ie, sdir,
                title=f"{PHL.name}: {label}", note=NOTE, factor=factor) is not None:
            made.append(label)
    print(f"Regenerated top-level figures in {fig_dir}/ + incidence for: {made}")


def _slug(label):
    return label.strip().lstrip("+ ").replace(" ", "_") or "step"


if __name__ == "__main__":
    main()
