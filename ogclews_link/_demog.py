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


def baseline_pop(p, un_country_code="608", download=False):
    """Baseline population objects from the vendored ``demographic_data/`` CSVs (or the UN portal
    if ``download=True``). Returns ``(pop_dict, pop_dist, pre_pop_dist, fert_rates, mort_rates,
    infmort_rates, imm_rates, deaths)``. From CLEWS-OG ``get_pop_data.baseline_pop``; ``ogcore`` is
    imported lazily so this module stays numpy-only at import time."""
    from ogcore import demographics

    if download:
        pop_dist, pre_pop_dist = demographics.get_pop(
            p.E, p.S, 0, 99, country_id=un_country_code,
            start_year=p.start_year, end_year=p.start_year + 1, download_path=DEMOG_PATH)
        fert_rates = demographics.get_fert(
            p.E + p.S, 0, 99, country_id=un_country_code,
            start_year=p.start_year, end_year=p.start_year + 1, graph=False, download_path=DEMOG_PATH)
        mort_rates, infmort_rates = demographics.get_mort(
            p.E + p.S, 0, 99, country_id=un_country_code,
            start_year=p.start_year, end_year=p.start_year + 1, graph=False, download_path=DEMOG_PATH)
        imm_rates = demographics.get_imm_rates(
            p.E + p.S, 0, 99, country_id=un_country_code, fert_rates=fert_rates,
            mort_rates=mort_rates, infmort_rates=infmort_rates, pop_dist=pop_dist,
            start_year=p.start_year, end_year=p.start_year + 1, graph=False, download_path=DEMOG_PATH)
    else:
        pop_dist = np.loadtxt(os.path.join(DEMOG_PATH, "population_distribution.csv"), delimiter=",")
        pre_pop_dist = np.loadtxt(
            os.path.join(DEMOG_PATH, "pre_period_population_distribution.csv"), delimiter=",")
        fert_rates = np.loadtxt(os.path.join(DEMOG_PATH, "fert_rates.csv"), delimiter=",")
        mort_rates = np.loadtxt(os.path.join(DEMOG_PATH, "mort_rates.csv"), delimiter=",")
        infmort_rates = np.loadtxt(os.path.join(DEMOG_PATH, "infmort_rates.csv"), delimiter=",")
        imm_rates = np.loadtxt(os.path.join(DEMOG_PATH, "immigration_rates.csv"), delimiter=",")

    deaths = total_deaths(pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, num_years=200)
    pop_dict = demographics.get_pop_objs(
        p.E, p.S, p.T, 0, 99, country_id=un_country_code,
        fert_rates=fert_rates, mort_rates=mort_rates, infmort_rates=infmort_rates, imm_rates=imm_rates,
        infer_pop=True, pop_dist=pop_dist[:1, :], pre_pop_dist=pre_pop_dist,
        initial_data_year=p.start_year, final_data_year=p.start_year + 1, GraphDiag=False)
    return (pop_dict, pop_dist, pre_pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, deaths)
