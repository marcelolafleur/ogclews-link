"""Regenerate every figure for an existing across-steps run from the pickles already on disk
-- no model solve. Use to iterate on figure STYLE without re-running OG-Core.

This is the general viz DRIVER: point it at any solved across-steps run, for any country model,
and it rebuilds the full figure set. Nothing about the scenario is hardcoded -- the country model
is PASSED IN (--country), the headline reform is AUTO-DETECTED (the last/most-layered step in the
run, override with --headline-step), and the per-run caveat caption comes from --note. Resolution
order for every input is CLI flag > env var > default:

    --country / OGCLEWS_COUNTRY   which CountryConfig to visualize (default: phl). Any CountryConfig
                                  defined in ogclews_link.country is selectable by its attribute
                                  name, .name, or .un_code (e.g. phl / philippines / 608).
    --run-dir / OGCLEWS_RUN_DIR   input  (read-only): the solved across-steps tree
    --fig-dir / OGCLEWS_FIG_DIR   output: where figures are written (default: <run-dir>/figures,
                                  i.e. INTO the run/scenario directory; override for viz iteration)
    --gbd-csv / OGCLEWS_GBD_CSV   input  (read-only): IHME GBD burden CSV for health profiles
    --headline-step / OGCLEWS_HEADLINE_STEP   reform that gets transition/welfare/dashboard/OG-suite
                                  figures (default: the last step in layered_results.json)
    --note    / OGCLEWS_NOTE      honest caveat caption stamped on every figure

Defaults: read from the shared health-lane run, write figures into that run's own figures/ subdir,
find the GBD CSV next to the run. The default --note describes THIS experiment's assumptions; pass
--note for a different scenario. A MUIOGO-OG run saves results in a scenario directory; point
--run-dir at it and the visuals land alongside the results, organized under figures/.

    PYTHONPATH=$PWD /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/regen_plots.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os

from ogcore.utils import safe_read_pickle

from ogclews_link.viz import plots, report, tables  # noqa: F401
from ogclews_link import country as _country_mod
from ogclews_link.country import CountryConfig

# The shared, solved across-steps tree (health lane). Read-only for the viz lane.
SHARED_RUN = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/across_steps"

DEFAULT_COUNTRY = "phl"
# Caveats for the SHARED PHL run's assumptions. Override with --note for any other scenario.
DEFAULT_NOTE = ("Illustrative -- magnitudes are not to be taken literally: assumed ~20% higher energy cost "
                "(a stand-in, not the energy model's detailed price path); investment and carbon sizes "
                "uncalibrated; carbon-tax revenue is not returned to households.")
# The full caveat above is shown in full on the cover. Individual charts carry only this one-line
# credit caveat -- the long note, stamped under every chart, wraps to 2-3 lines and collides with
# the x-axis label, so the detail lives on the cover.
FIG_CAVEAT = "Illustrative -- magnitudes are not to be taken literally."

# index.html / cover organization: a reading order of headline -> how the scenario is built ->
# detailed results. Each section maps to the figure basenames it groups (cover + per-step incidence
# are added automatically by report.write_index). Only files that exist are shown, so a partial
# run degrades gracefully.
_INDEX_SECTIONS = [
    ("Headline",
     ["headline_dashboard", "summary_table", "waterfall_gdp", "waterfall_poorest"]),
    ("How the scenario is built",
     ["channel_inputs", "clews_signal_vs_applied", "capex_by_technology", "emissions_path"]),
    ("Macro & fiscal detail",
     ["macro_transition", "fiscal_transition", "revenue_transition", "rates_transition",
      "public_investment"]),
    ("Health channel",
     ["health_age_profiles", "health_mortality_by_age", "health_morbidity_by_age",
      "health_demography", "health_gdp_split"]),
    ("Welfare -- who wins and loses",
     ["welfare_cev_by_group", "welfare_cev_decomposition", "welfare_cev_by_age"]),
    ("Distribution & composition",
     ["consumption_by_age", "asset_by_age", "income_composition_by_age", "consumption_by_good",
      "consumption_by_good_by_group", "sectoral_reallocation", "energy_by_income"]),
]
# Cover contents list mirrors the index section order (single source of truth).
_DECK_SECTIONS = [title for title, _ in _INDEX_SECTIONS]


def _resolve(cli_val, env_key, default):
    return cli_val or os.environ.get(env_key) or default


def _country_registry():
    """Every CountryConfig instance defined in ogclews_link.country, keyed (lowercased) by its
    module attribute, .name, and .un_code -- so 'phl'/'philippines'/'608' all resolve to PHL.
    Auto-includes any country added to country.py later; this driver never hardcodes the instance."""
    reg = {}
    for attr, obj in vars(_country_mod).items():
        if isinstance(obj, CountryConfig):
            for key in (attr, obj.name, obj.un_code):
                if key:
                    reg[str(key).lower()] = obj
    return reg


def _resolve_country(selector):
    reg = _country_registry()
    obj = reg.get(str(selector).lower())
    if obj is None:
        avail = sorted({c.name for c in reg.values()})
        raise SystemExit(f"unknown country {selector!r}; available: {avail}")
    return obj


def _default_headline(layered):
    """Headline reform = the most-layered (last) non-baseline step in the run."""
    steps = [r.get("step") for r in layered if r.get("step") and r.get("step") != "baseline"]
    return steps[-1] if steps else None


def _default_gbd_csv(run_dir, country):
    """The GBD burden CSV next to the run (../.. from the across-steps tree), else the country's own."""
    repo = os.path.normpath(os.path.join(run_dir, "..", ".."))
    hits = [h for h in glob.glob(os.path.join(repo, "IHME-GBD_2023_DATA", "*.csv"))
            if "citation" not in os.path.basename(h).lower()]
    return sorted(hits)[0] if hits else (getattr(country, "gbd_burden_csv", None) or None)


def _tpi(run_dir, label):
    p = os.path.join(run_dir, label, "TPI", "TPI_vars.pkl")
    return safe_read_pickle(p) if label and os.path.isfile(p) else None


def _params(run_dir, label):
    p = os.path.join(run_dir, label, "model_params.pkl")
    return safe_read_pickle(p) if label and os.path.isfile(p) else None


def _ss(run_dir, label):
    p = os.path.join(run_dir, label, "SS", "SS_vars.pkl")
    return safe_read_pickle(p) if label and os.path.isfile(p) else None


def _start_year(base_dir, country, default=2026):
    """Calendar start year for the transition x-axis, from the run's model_params."""
    try:
        p = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
        return int(getattr(p, "start_year", default))
    except Exception:  # noqa: BLE001
        return int(getattr(country.scenario, "og_start_year", default) or default)


def _try(fn, *a, **k):
    """Run a figure builder, never let one failure abort the regen sweep."""
    try:
        return fn(*a, **k)
    except Exception as e:  # noqa: BLE001
        print(f"  [skip] {getattr(fn, '__name__', fn)}: {type(e).__name__}: {e}")
        return None


def _slug(label):
    return label.strip().lstrip("+ ").replace(" ", "_") or "step"


def build_figures(country, run_dir, fig_dir, gbd_csv, *, headline_step=None, note=DEFAULT_NOTE,
                  illustrative=True):
    """Rebuild the full figure set for `country` from the solved pickles under `run_dir`,
    writing to `fig_dir`. `headline_step` None -> auto-detect (last layered step).

    `illustrative` (default True) is the single switch for the placeholder phase: while True the
    charts carry the short caveat and the unit-labelled "model units" disclosures; flip it to False
    once the run is calibrated and every figure drops that language with no per-figure edits."""
    os.makedirs(fig_dir, exist_ok=True)
    # Charts carry the one-line FIG_CAVEAT; the cover carries the full `note`. Both empty when the
    # run is calibrated (illustrative=False), so the caveat language lives in ONE place.
    full_note = note if illustrative else ""
    note = FIG_CAVEAT if illustrative else ""
    ie = country.concordance.energy_good_index
    with open(os.path.join(run_dir, "layered_results.json"), encoding="utf-8") as f:
        layered = json.load(f)
    if headline_step is None:
        headline_step = _default_headline(layered)
    print(f"regen: read {run_dir}\n       write {fig_dir}")
    print(f"       country {country.name}   headline {headline_step!r}")
    print(f"       gbd  {gbd_csv if gbd_csv and os.path.isfile(gbd_csv) else '(none -- health profiles skipped)'}")

    # --- top-level figures (across steps) ---------------------------------------
    _try(plots.across_steps_waterfall, layered, fig_dir, note=note)
    _try(plots.energy_physical, country, fig_dir, illustrative=illustrative)
    _try(tables.across_steps_table, layered, os.path.join(fig_dir, "across_steps_summary.csv"))
    _try(report.write_html_report, layered, os.path.join(fig_dir, "report.html"))

    # --- OG-Core's own canonical suite (free reference set) for the headline reform ----
    base_dir = os.path.join(run_dir, "baseline")
    headline_dir = os.path.join(run_dir, headline_step) if headline_step else None
    if headline_dir and os.path.isdir(headline_dir):
        _try(plots.og_default_outputs, base_dir, headline_dir,
             os.path.join(fig_dir, "og_suite"), plots=True)

    base_tpi = _tpi(run_dir, "baseline")
    base_ss = _ss(run_dir, "baseline")  # also feeds the CEV/distribution/composition figures below
    factor = float(base_ss["factor"]) if base_ss and "factor" in base_ss else None
    start_year = _start_year(base_dir, country)

    # --- editorial transition-path figures for the headline reform --------------
    base_params = _params(run_dir, "baseline")        # also feeds closure marker, energy, health, welfare
    headline_params = _params(run_dir, headline_step)
    headline_tpi = _tpi(run_dir, headline_step)
    if base_tpi is not None and headline_tpi is not None:
        for fn in (plots.macro_transition, plots.fiscal_transition,
                   plots.revenue_transition, plots.rates_transition,
                   plots.public_investment):
            _try(fn, base_tpi, headline_tpi, fig_dir, start_year=start_year, note=note,
                 params=base_params)

    # --- energy-system linkage (the CLEWS-to-OG inputs) -------------------------
    # The energy-price channel's applied wedge = the FIRST reform step's params (the +20% energy-price
    # proxy), so the flagship compares the CLEWS energy-price ratio to the wedge that channel actually
    # applied -- not the headline's cumulative energy+carbon wedge.
    ep_params = _params(run_dir, layered[0]["step"]) if layered else None
    ep_ref = ep_params if ep_params is not None else headline_params
    if base_params is not None and ep_ref is not None:
        _try(plots.clews_signal_vs_applied, country, base_params, ep_ref, fig_dir, note=note,
             illustrative=illustrative)
    _try(plots.capex_by_technology, country, fig_dir, note=note, illustrative=illustrative)
    if base_tpi is not None:
        _try(plots.channel_inputs_over_time, country, base_tpi, fig_dir, note=note,
             illustrative=illustrative)

    # --- health-channel visuals -------------------------------------------------
    if gbd_csv and os.path.isfile(gbd_csv):
        _try(plots.gbd_age_profiles, gbd_csv, country.name, int(country.gbd_year), fig_dir, note=note)
    if base_params is not None and headline_params is not None:
        _try(plots.mortality_by_age, base_params, headline_params, fig_dir, note=note)
        _try(plots.morbidity_by_age, base_params, headline_params, fig_dir, note=note)
        _try(plots.demographic_transition_by_age, base_params, headline_params, fig_dir, note=note)
    _try(plots.gdp_split, layered, fig_dir, note=note, illustrative=illustrative)

    # --- welfare: consumption-equivalent variation (CEV) ------------------------
    headline_ss = _ss(run_dir, headline_step)  # base_ss loaded once above
    if None not in (base_ss, headline_ss, base_params, headline_params):
        _try(plots.cev_by_group, base_ss, headline_ss, base_params, headline_params,
             fig_dir, note=note)
        _try(plots.cev_decomposition, base_ss, headline_ss, base_params, headline_params,
             fig_dir, note=note)
    if base_tpi is not None and headline_tpi is not None and None not in (base_params, headline_params):
        _try(plots.cev_by_age, base_tpi, headline_tpi, base_params, headline_params,
             fig_dir, note=note)

    # --- distributional richness ------------------------------------------------
    _try(plots.energy_demand_by_group, layered, fig_dir, note=note)
    if None not in (base_ss, headline_ss, base_params):
        _try(plots.consumption_by_age, base_ss, headline_ss, base_params, fig_dir, note=note)
        _try(plots.asset_by_age, base_ss, headline_ss, base_params, fig_dir, note=note)
    if base_tpi is not None and headline_tpi is not None and base_params is not None:
        _try(plots.income_composition_by_age, base_tpi, headline_tpi, base_params, fig_dir, note=note)

    # --- multi-good / multi-sector composition (the GE structure) ---------------
    conc = getattr(country, "concordance", None)  # the run's energy good/industry indices (portable)
    if None not in (base_ss, headline_ss, base_params):
        _try(plots.consumption_by_good, base_ss, headline_ss, base_params, fig_dir, note=note, concordance=conc)
        _try(plots.sectoral_reallocation, base_ss, headline_ss, base_params, fig_dir, note=note, concordance=conc)
    if base_tpi is not None and headline_tpi is not None and base_params is not None:
        _try(plots.consumption_by_good_by_group, base_tpi, headline_tpi, base_params, fig_dir, note=note, concordance=conc)

    # --- one-page headline dashboard --------------------------------------------
    if None not in (base_tpi, headline_tpi, base_ss, headline_ss, base_params, headline_params):
        _try(plots.headline_dashboard, layered, base_tpi, headline_tpi, base_ss, headline_ss,
             base_params, headline_params, country, fig_dir, start_year=start_year, note=note,
             illustrative=illustrative)

    # --- deck front matter & at-a-glance summary --------------------------------
    # The cover carries the FULL caveat + the plain-language scenario description; summary_table is
    # a chart-like page (short caveat).
    _try(tables.summary_table, layered, fig_dir, note=note)
    _try(tables.cover_page, layered, country, _DECK_SECTIONS, fig_dir, note=full_note,
         illustrative=illustrative)

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
        if _try(plots.incidence_hero, base_tpi, reform_tpi, ie, sdir,
                title=f"{country.name}: {label}", note=note, factor=factor) is not None:
            made.append(label)
    print(f"Regenerated top-level figures in {fig_dir}/ + incidence for: {made}")

    # --- scenario entry point: one index.html at the run-dir root linking the whole deck --------
    index = _try(report.write_index, fig_dir, os.path.join(run_dir, "index.html"),
                 _INDEX_SECTIONS, country=country, note=full_note)
    if index:
        print(f"Wrote scenario index -> {index}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", help="country model to visualize (default: phl)")
    ap.add_argument("--run-dir", help="input solved across-steps tree (read-only)")
    ap.add_argument("--fig-dir", help="output dir for figures (viz-local)")
    ap.add_argument("--gbd-csv", help="IHME GBD burden CSV for health age-profile figures")
    ap.add_argument("--headline-step", help="reform step for transition/welfare/dashboard figures "
                                            "(default: last step in layered_results.json)")
    ap.add_argument("--note", help="honest caveat caption stamped on every figure")
    ap.add_argument("--calibrated", action="store_true",
                    help="drop the illustrative/model-units caveats (use once results are real)")
    args = ap.parse_args(argv)

    country = _resolve_country(_resolve(args.country, "OGCLEWS_COUNTRY", DEFAULT_COUNTRY))
    run_dir = _resolve(args.run_dir, "OGCLEWS_RUN_DIR", SHARED_RUN)
    # Default: write figures INTO the run/scenario directory (organized under figures/), so a
    # MUIOGO-OG run's results and its visuals live together. Override --fig-dir for viz iteration.
    fig_dir = _resolve(args.fig_dir, "OGCLEWS_FIG_DIR", os.path.join(run_dir, "figures"))
    gbd_csv = _resolve(args.gbd_csv, "OGCLEWS_GBD_CSV", _default_gbd_csv(run_dir, country))
    note = _resolve(args.note, "OGCLEWS_NOTE", DEFAULT_NOTE)
    headline_step = _resolve(args.headline_step, "OGCLEWS_HEADLINE_STEP", None)  # None -> auto-detect

    illustrative = not args.calibrated
    build_figures(country, run_dir, fig_dir, gbd_csv, headline_step=headline_step, note=note,
                  illustrative=illustrative)


if __name__ == "__main__":
    main()
