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

from ogclews_link.viz import plots, report, tables  # noqa: F401
from ogclews_link import report as og_report  # MODEL report (report.layered_entry); `report` above is viz's HTML/index module
from ogclews_link import country as _country_mod


def safe_read_pickle(path):
    """Read an OG-Core output pickle. Lazy ogcore import: building a deck off OG's native pkl outputs
    runs under the OG model's interpreter (where ogcore lives); the link env imports viz without it."""
    from ogcore.utils import safe_read_pickle as _srp
    return _srp(path)

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


def _resolve_country(selector, config_file=None):
    """Delegate to the canonical registry (country.resolve_country): module-defined instances PLUS
    countries-JSON entries (--countries / $OGCLEWS_COUNTRIES / ./ogclews_countries.json), keyed by
    attr/name/un-code/og-repo -- the SAME resolution `run` uses, so a JSON-onboarded country (and the
    'og-phl'-style selectors) reach the portal build too."""
    return _country_mod.resolve_country(selector, config_file=config_file)


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


def _tpi(d):
    p = os.path.join(d, "TPI", "TPI_vars.pkl") if d else None
    return safe_read_pickle(p) if p and os.path.isfile(p) else None


def _params(d):
    p = os.path.join(d, "model_params.pkl") if d else None
    return safe_read_pickle(p) if p and os.path.isfile(p) else None


def _ss(d):
    p = os.path.join(d, "SS", "SS_vars.pkl") if d else None
    return safe_read_pickle(p) if p and os.path.isfile(p) else None


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


def _run_concordance(base_dir):
    """The PER-RUN energy-port concordance the OG runner discovered + exported next to the baseline
    (`<base_dir>/baseline_meta.json`). Returns a contract.Concordance, or None when the run predates
    the export or solved at a single industry -- callers then degrade to no energy marker."""
    from ogclews_link.contract import Concordance
    meta_path = os.path.join(base_dir, "baseline_meta.json") if base_dir else None
    if not meta_path or not os.path.isfile(meta_path):
        return None
    try:
        with open(meta_path, encoding="utf-8") as f:
            con = json.load(f).get("concordance")
        return Concordance(**con) if con else None
    except (OSError, ValueError, TypeError):
        return None


def _render_deck(country, dir_of, layered, fig_dir, index_path, *, headline_step=None,
                 gbd_csv=None, note=DEFAULT_NOTE, illustrative=True):
    """Render the full figure deck + index, resolving each role (``"baseline"`` and the step
    labels) to a solved-pickle directory through the ``dir_of(label) -> dir`` callable. This is
    the layout-agnostic core: the across-steps driver and the coupled-run bridge differ only in
    how they map labels to directories, so any country/model that produces a (baseline, reform)
    pair can be visualized -- nothing about the on-disk layout is assumed here.

    `illustrative` (default True) is the single switch for the placeholder phase: while True the
    charts carry the short caveat and the unit-labelled "model units" disclosures; flip it to False
    once the run is calibrated and every figure drops that language with no per-figure edits."""
    os.makedirs(fig_dir, exist_ok=True)
    # Charts carry the one-line FIG_CAVEAT; the cover carries the full `note`. Both empty when the
    # run is calibrated (illustrative=False), so the caveat language lives in ONE place.
    full_note = note if illustrative else ""
    note = FIG_CAVEAT if illustrative else ""
    base_dir = dir_of("baseline")
    conc = _run_concordance(base_dir)             # per-run energy ports (None / unset -> no energy marker)
    ie = conc.energy_good_index if conc is not None else None
    if headline_step is None:
        headline_step = _default_headline(layered)
    print(f"       country {country.name}   headline {headline_step!r}")
    print(f"       gbd  {gbd_csv if gbd_csv and os.path.isfile(gbd_csv) else '(none -- health profiles skipped)'}")

    # --- top-level figures (across steps) ---------------------------------------
    _try(plots.across_steps_waterfall, layered, fig_dir, note=note)
    _try(plots.energy_physical, country, fig_dir, illustrative=illustrative)
    _try(tables.across_steps_table, layered, os.path.join(fig_dir, "across_steps_summary.csv"))
    _try(report.write_html_report, layered, os.path.join(fig_dir, "report.html"))

    # --- OG-Core's own canonical suite (free reference set) for the headline reform ----
    headline_dir = dir_of(headline_step)
    if headline_dir and os.path.isdir(headline_dir):
        _try(plots.og_default_outputs, base_dir, headline_dir,
             os.path.join(fig_dir, "og_suite"), plots=True)

    base_tpi = _tpi(base_dir)
    base_ss = _ss(base_dir)  # also feeds the CEV/distribution/composition figures below
    factor = float(base_ss["factor"]) if base_ss and "factor" in base_ss else None
    start_year = _start_year(base_dir, country)

    # --- editorial transition-path figures for the headline reform --------------
    base_params = _params(base_dir)                   # also feeds closure marker, energy, health, welfare
    headline_params = _params(headline_dir)
    headline_tpi = _tpi(headline_dir)
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
    ep_params = _params(dir_of(layered[0]["step"])) if layered else None
    ep_ref = ep_params if ep_params is not None else headline_params
    if base_params is not None and ep_ref is not None:
        _try(plots.clews_signal_vs_applied, country, base_params, ep_ref, fig_dir, note=note,
             concordance=conc, illustrative=illustrative)
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
    headline_ss = _ss(headline_dir)  # base_ss loaded once above
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
    # `conc` (the run's energy good/industry indices) was loaded once at the top from baseline_meta.json
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
    # the incidence hero keys off the energy good (energy budget share); with no isolated energy good
    # (the country can't be coupled on energy) there is nothing to attribute incidence to, so skip it.
    made = []
    if ie is None:
        print("  (skip per-step incidence: this run has no isolated energy good)")
    for r in layered if ie is not None else []:
        label = r.get("step")
        if "macro" not in r or label == "baseline":
            continue
        reform_tpi = _tpi(dir_of(label))
        if base_tpi is None or reform_tpi is None:
            print(f"  (skip incidence for {label!r}: pickle missing)")
            continue
        sdir = os.path.join(fig_dir, "per_step", _slug(label))
        if _try(plots.incidence_hero, base_tpi, reform_tpi, ie, sdir,
                title=f"{country.name}: {label}", note=note, factor=factor) is not None:
            made.append(label)
    print(f"Regenerated top-level figures in {fig_dir}/ + incidence for: {made}")

    # --- scenario entry point: one index.html at the run-dir root linking the whole deck --------
    index = _try(report.write_index, fig_dir, index_path,
                 _INDEX_SECTIONS, country=country, note=full_note)
    if index:
        print(f"Wrote scenario index -> {index}")


def build_figures(country, run_dir, fig_dir, gbd_csv, *, headline_step=None, note=DEFAULT_NOTE,
                  illustrative=True):
    """Rebuild the full figure set from a solved ACROSS-STEPS tree under `run_dir` (``baseline/`` +
    per-step dirs + ``layered_results.json``), writing to `fig_dir`. A thin wrapper over
    `_render_deck` that just resolves the on-disk across-steps layout; `headline_step` None ->
    auto-detect (last layered step)."""
    with open(os.path.join(run_dir, "layered_results.json"), encoding="utf-8") as f:
        layered = json.load(f)
    print(f"regen: read {run_dir}\n       write {fig_dir}")
    _render_deck(country, lambda label: os.path.join(run_dir, label) if label else None,
                 layered, fig_dir, os.path.join(run_dir, "index.html"),
                 headline_step=headline_step, gbd_csv=gbd_csv, note=note, illustrative=illustrative)


def _read_manifest(coupled_dir):
    """The `ogclews_manifest.json` a `run coupled` writes (concordance, channels, scenario, model)."""
    p = os.path.join(coupled_dir, "ogclews_manifest.json")
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _discover_baseline_cache(coupled_dir, manifest):
    """Locate the cached baseline solve for a coupled run -- general, no hardcoded cache tag. The
    runner writes it to ``<run-root>/_og_baseline_cache/<og-pkg>-<ver>-<calib>/``; the run root is
    some ancestor of the experiment dir, so walk up looking for it, and, when several caches exist,
    keep those whose `baseline_meta.json` concordance matches the run's manifest, newest first."""
    cands, d = [], coupled_dir
    for _ in range(4):                       # the cache lives at the run root, an ancestor of this dir
        cands += glob.glob(os.path.join(d, "_og_baseline_cache", "*"))
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    cands = [c for c in cands if os.path.isfile(os.path.join(c, "model_params.pkl"))
             and os.path.isfile(os.path.join(c, "SS", "SS_vars.pkl"))]
    if len(cands) <= 1:
        return cands[0] if cands else None
    want = manifest.get("concordance")

    def _meta_conc(c):
        try:
            with open(os.path.join(c, "baseline_meta.json"), encoding="utf-8") as f:
                return json.load(f).get("concordance")
        except (OSError, ValueError):
            return None
    matched = [c for c in cands if want and _meta_conc(c) == want] or cands
    return max(matched, key=os.path.getmtime)


def _note_from_manifest(manifest):
    """Honest caveat for a coupled run: the electricity price is the REAL CLEWS signal (not a +20%
    stand-in); carbon/investment magnitudes are still uncalibrated and carbon revenue is unrecycled."""
    name = (manifest.get("scenario") or {}).get("name") or "the CLEWS scenario"
    return (f"Coupled run: electricity price from {name} (the CLEWS signal, not a +20% stand-in); "
            "carbon and investment magnitudes uncalibrated; carbon-tax revenue not recycled.")


def build_deck_from_coupled_run(coupled_dir, country, *, fig_dir=None, gbd_csv=None,
                                step_label=None, note=None, illustrative=True):
    """Build the full rich deck from ONE solved `run coupled` output dir, with NO new solve.

    General over country/model: the baseline is the run's own cached solve and the single reform is
    the coupled reform already on disk; the energy concordance and applied channels are READ from the
    run's manifest + baseline_meta.json. Nothing country- or path-specific is hardcoded. Figures that
    need a baseline+reform pair (macro/fiscal/welfare/health/distribution/composition) are the genuine
    current-calibration deck; the across-steps multi-bar waterfall is intentionally omitted (it needs
    >=2 solved steps to span), so for the layered view only the single-row summary table renders."""
    coupled_dir = os.path.abspath(coupled_dir)
    manifest = _read_manifest(coupled_dir)
    # The run records the country it was solved for; --country is an override -> warn on a mismatch
    # so a wrong --country can't silently render one country's labels over another's pickles.
    m_country = manifest.get("un_code") or manifest.get("country")
    if m_country and str(m_country) not in (str(country.un_code), country.name):
        print(f"  [warn] --country {country.name}/{country.un_code} != the run's manifest "
              f"({m_country}); rendering with the passed-in country")
    reform_dir = os.path.join(coupled_dir, "reform")
    base_dir = _discover_baseline_cache(coupled_dir, manifest)
    if not os.path.isdir(reform_dir):
        raise SystemExit(f"no reform/ under {coupled_dir}")
    if base_dir is None:
        raise SystemExit(f"no cached baseline solve found for {coupled_dir} "
                         "(looked under <run-root>/_og_baseline_cache/*)")
    base_tpi, reform_tpi = _tpi(base_dir), _tpi(reform_dir)
    if base_tpi is None or reform_tpi is None:
        raise SystemExit("baseline or reform TPI pickle missing -- cannot build the deck")
    # Energy good: the baseline's exported concordance (baseline_meta.json) is the single source --
    # _render_deck re-derives the SAME value for the marker/incidence, so the layered row's energy
    # rows and the deck's energy figures stay consistent (no separate manifest fallback to diverge).
    conc = _run_concordance(base_dir)
    ie = conc.energy_good_index if conc is not None else None
    channels = [c.get("id") for c in manifest.get("channels", [])]
    label = step_label or (manifest.get("experiment") or {}).get("name") or "reform"
    if label == "baseline":                  # reserved role name -> keep the reform step distinct
        label = "reform"
    layered = [og_report.layered_entry(label, base_tpi, reform_tpi,
                                       energy_good_index=ie, channels=channels)]

    def dir_of(which):
        return base_dir if which == "baseline" else (reform_dir if which == label else None)

    fig_dir = fig_dir or os.path.join(coupled_dir, "figures")
    gbd_csv = gbd_csv or _default_gbd_csv(coupled_dir, country)
    note = _note_from_manifest(manifest) if note is None else note
    print(f"coupled-deck: read {coupled_dir}\n       baseline {base_dir}\n       write {fig_dir}")
    _render_deck(country, dir_of, layered, fig_dir, os.path.join(coupled_dir, "index.html"),
                 headline_step=label, gbd_csv=gbd_csv, note=note, illustrative=illustrative)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", help="country model to visualize (default: phl)")
    ap.add_argument("--countries", default=None,
                    help="countries JSON defining your own CountryConfig entries (default: "
                         "$OGCLEWS_COUNTRIES, else ./ogclews_countries.json if present) -- the same "
                         "file `run --countries` reads")
    src = ap.add_mutually_exclusive_group()   # one input layout or the other, not both
    src.add_argument("--run-dir", help="input solved across-steps tree (read-only)")
    src.add_argument("--coupled-run", help="build the deck from a single solved `run coupled` output "
                                           "dir (uses its cached baseline + reform; no new solve)")
    ap.add_argument("--fig-dir", help="output dir for figures (viz-local)")
    ap.add_argument("--gbd-csv", help="IHME GBD burden CSV for health age-profile figures")
    ap.add_argument("--headline-step", help="reform step for transition/welfare/dashboard figures "
                                            "(default: last step in layered_results.json)")
    ap.add_argument("--note", help="honest caveat caption stamped on every figure")
    ap.add_argument("--calibrated", action="store_true",
                    help="drop the illustrative/model-units caveats (use once results are real)")
    args = ap.parse_args(argv)

    country = _resolve_country(_resolve(args.country, "OGCLEWS_COUNTRY", DEFAULT_COUNTRY),
                               config_file=args.countries)
    illustrative = not args.calibrated

    # A single coupled run (the live `run coupled` output): build the deck off its cached baseline +
    # reform, no new solve. fig-dir/gbd-csv None -> the function defaults them under the coupled dir;
    # note None -> a manifest-derived caveat (the energy price is the real CLEWS signal).
    coupled = _resolve(args.coupled_run, "OGCLEWS_COUPLED_RUN", None)
    if coupled:
        build_deck_from_coupled_run(
            coupled, country,
            fig_dir=_resolve(args.fig_dir, "OGCLEWS_FIG_DIR", None),
            gbd_csv=_resolve(args.gbd_csv, "OGCLEWS_GBD_CSV", None),
            note=_resolve(args.note, "OGCLEWS_NOTE", None),
            illustrative=illustrative)
        return

    run_dir = _resolve(args.run_dir, "OGCLEWS_RUN_DIR", SHARED_RUN)
    # Default: write figures INTO the run/scenario directory (organized under figures/), so a
    # MUIOGO-OG run's results and its visuals live together. Override --fig-dir for viz iteration.
    fig_dir = _resolve(args.fig_dir, "OGCLEWS_FIG_DIR", os.path.join(run_dir, "figures"))
    gbd_csv = _resolve(args.gbd_csv, "OGCLEWS_GBD_CSV", _default_gbd_csv(run_dir, country))
    note = _resolve(args.note, "OGCLEWS_NOTE", DEFAULT_NOTE)
    headline_step = _resolve(args.headline_step, "OGCLEWS_HEADLINE_STEP", None)  # None -> auto-detect

    build_figures(country, run_dir, fig_dir, gbd_csv, headline_step=headline_step, note=note,
                  illustrative=illustrative)


if __name__ == "__main__":
    main()
