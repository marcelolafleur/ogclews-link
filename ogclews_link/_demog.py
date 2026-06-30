"""Vendored demographic helpers — the pure, in-repo replacement for the two external
``get_pop_data.py`` copies this package used to load by absolute path (CostOfDisease and
CLEWS-OG/OG_simulations). Vendoring removes the machine-bound ``sys.path`` hacks so the
solve path runs on CI / a teammate's box / any checkout.

Provenance (all three functions are dependency-light, numpy-only at the math level):
  * ``total_deaths`` — byte-identical across the CostOfDisease and CLEWS-OG copies (verified).
  * ``extrapolate_demographics`` — from CostOfDisease ``get_pop_data.py`` (the brentq calibration
    in :mod:`ogclews_link.health_pop` reuses it, so the construction matches the paper exactly).
  * ``baseline_pop`` — from CLEWS-OG ``get_pop_data.py`` (reads the PHL ``demographic_data/`` CSVs
    vendored alongside this module). ``ogcore`` is imported lazily inside it so importing
    ``ogclews_link`` stays numpy-only for the transform tests.
"""
from __future__ import annotations

import os

import numpy as np

DEMOG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "demographic_data")


def total_deaths(pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, num_years=200):
    """Total deaths each year for ``num_years`` (forward cohort iteration). Returns a
    (num_years, n_ages) array. Verbatim from CostOfDisease/CLEWS-OG ``get_pop_data.total_deaths``."""
    initial_years = mort_rates.shape[0]
    deaths = np.zeros((num_years, mort_rates.shape[1]))
    pop_t = pop_dist[0, :]
    for y in range(initial_years):
        deaths[y, :] = pop_t * mort_rates[y, :]
        pop_tp1 = np.zeros_like(pop_t)
        pop_tp1[1:] = pop_t[:-1] * (1 - mort_rates[y, :-1]) + pop_t[:-1] * imm_rates[y, :-1]
        pop_tp1[0] = (pop_t * fert_rates[y, :]).sum() * (1 - infmort_rates[y])
        pop_t = pop_tp1
    for yy in range(initial_years, num_years):
        deaths[yy, :] = pop_t * mort_rates[-1, :]
        pop_tp1 = np.zeros_like(pop_t)
        pop_tp1[1:] = pop_t[:-1] * (1 - mort_rates[-1, :-1]) + pop_t[:-1] * imm_rates[-1, :-1]
        pop_tp1[0] = (pop_t * fert_rates[-1, :]).sum() * (1 - infmort_rates[-1])
        pop_t = pop_tp1
    return deaths


def extrapolate_demographics(rates, num_years):
    """Extend a demographic rate path (year on axis 0) to ``num_years`` rows by repeating the
    final observed row. Verbatim from CostOfDisease ``get_pop_data.extrapolate_demographics``."""
    if rates.shape[0] >= num_years:
        return rates[:num_years].copy()
    extra_rows = np.repeat(rates[-1:], num_years - rates.shape[0], axis=0)
    return np.concatenate((rates, extra_rows), axis=0)


def baseline_pop(p, un_country_code="608", download=False, download_path=None):
    """Baseline population objects via ogcore.demographics. With ``download=True`` (the path the link
    uses) ogcore fetches from the UN data portal and falls back to the github EAPD-DRB/Population-Data
    repo, writing the raw CSVs to ``download_path`` (a per-run cache, NOT the package source). Returns
    ``(pop_dict, pop_dist, pre_pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, deaths)``.
    ``ogcore`` is imported lazily so this module stays numpy-only at import time.

    ogcore 0.16.3 API: ``get_pop`` now returns a SINGLE array (the population distribution; in the
    download/non-infer path its rows are start_year .. end_year+1, i.e. ``end_year + 2 - start_year``
    rows) and ``get_pop_objs`` no longer takes ``pre_pop_dist``. We seed the population inference with
    the actual start_year UN row (``pop_dist[:1, :]`` with ``infer_pop=True``); ogcore then infers the
    distribution forward from that seed using the supplied rates -- the same seed the pre-0.16.3 call
    used, so the demographics are unchanged modulo ogcore's own internal updates. ``pre_pop_dist`` is
    derived as the leading row of the fetched distribution purely to preserve the return contract /
    ``_pop_aux`` (no consumer feeds it back to get_pop_objs anymore)."""
    from ogcore import demographics

    dp = download_path or DEMOG_PATH
    os.makedirs(dp, exist_ok=True)
    if download:
        pop_dist = demographics.get_pop(
            p.E, p.S, 0, 99, country_id=un_country_code,
            start_year=p.start_year, end_year=p.start_year + 1, download_path=dp)
        pre_pop_dist = pop_dist[:1, :].copy()   # leading (pre-period) row -- contract only; see docstring
        fert_rates = demographics.get_fert(
            p.E + p.S, 0, 99, country_id=un_country_code,
            start_year=p.start_year, end_year=p.start_year + 1, graph=False, download_path=dp)
        mort_rates, infmort_rates = demographics.get_mort(
            p.E + p.S, 0, 99, country_id=un_country_code,
            start_year=p.start_year, end_year=p.start_year + 1, graph=False, download_path=dp)
        imm_rates = demographics.get_imm_rates(
            p.E + p.S, 0, 99, country_id=un_country_code, fert_rates=fert_rates,
            mort_rates=mort_rates, infmort_rates=infmort_rates, pop_dist=pop_dist,
            start_year=p.start_year, end_year=p.start_year + 1, graph=False, download_path=dp)
    else:
        pop_dist = np.loadtxt(os.path.join(dp, "population_distribution.csv"), delimiter=",")
        pre_pop_dist = pop_dist[:1, :].copy()   # 0.16.3 no longer materializes a separate pre-period file
        fert_rates = np.loadtxt(os.path.join(dp, "fert_rates.csv"), delimiter=",")
        mort_rates = np.loadtxt(os.path.join(dp, "mort_rates.csv"), delimiter=",")
        infmort_rates = np.loadtxt(os.path.join(dp, "infmort_rates.csv"), delimiter=",")
        imm_rates = np.loadtxt(os.path.join(dp, "immigration_rates.csv"), delimiter=",")

    deaths = total_deaths(pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, num_years=200)
    pop_dict = demographics.get_pop_objs(
        p.E, p.S, p.T, 0, 99, country_id=un_country_code,
        fert_rates=fert_rates, mort_rates=mort_rates, infmort_rates=infmort_rates, imm_rates=imm_rates,
        infer_pop=True, pop_dist=pop_dist[:1, :],
        initial_data_year=p.start_year, final_data_year=p.start_year + 1, GraphDiag=False)
    return (pop_dict, pop_dist, pre_pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, deaths)
