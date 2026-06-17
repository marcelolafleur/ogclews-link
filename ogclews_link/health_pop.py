"""Bidirectional `disease_pop`: the CostOfDisease age-profile mortality method, generalized so the
excess-deaths target may be NEGATIVE (lives saved -- the cleaner-air / pollution direction) as well
as positive (the HIV / disease-burden direction the published code handles).

    rho(s,t) = rho0(s,t) + shock_scale * h(s) * (t+1)/phase_years        (clipped to [0, 1])

`shock_scale` is solved by brentq so the realized year-`phase_years` excess deaths equal the (signed)
target; then the population path is recomputed with the built-in `ogcore.demographics.get_pop_objs`.
We reuse CostOfDisease's EXACT `total_deaths` / `extrapolate_demographics` so the construction is
identical to the paper; the only generalization is the two changes the published `disease_pop` lacks:
a 0.0 floor (so a reduction can't drive a rate negative) and a negative-target search branch.
"""
from __future__ import annotations

import importlib.util

import numpy as np

# CostOfDisease lives outside this repo; load its pure demographic helpers on demand (so importing
# ogclews_link stays numpy-only for the transform tests). Same path the diagnostics use.
_COD_PATH = "/Users/mlafleur/Projects/CostOfDisease/code/get_pop_data.py"


def _cod():
    spec = importlib.util.spec_from_file_location("cod_get_pop_data", _COD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def calibrate_shock_scale(target, pop_dist, fert, mort, infmort, imm, profile, phase_years,
                          total_deaths_fn):
    """Solve the additive age-profile shock scale that hits a SIGNED year-`phase_years` excess-deaths
    target. target>0 searches [0, +inf) (add deaths); target<0 searches (-inf, 0] (save lives);
    target==0 is a no-op. Returns (shock_scale, shocked_mortality_path). Pure -- no ogcore."""
    from scipy.optimize import brentq

    profile = np.asarray(profile, dtype=float)
    if profile.ndim != 1 or np.any(profile < 0) or not np.all(np.isfinite(profile)):
        raise ValueError("disease_pop: profile must be a finite, nonnegative 1-D age shape "
                         "(the monotonicity that brackets the brentq root assumes h(s) >= 0).")
    ny = phase_years
    base_d = total_deaths_fn(pop_dist, fert, mort, infmort, imm, num_years=ny)[ny - 1].sum()

    def shock_path(scale):
        alt = mort.copy()
        for t in range(ny):
            alt[t, :] = np.clip(mort[t, :] + scale * profile * ((t + 1) / ny), 0.0, 1.0)
        return alt

    def gap(scale):
        d = total_deaths_fn(pop_dist, fert, shock_path(scale), infmort, imm, num_years=ny)
        return d[ny - 1].sum() - base_d - target

    if target == 0:
        scale = 0.0
    elif target > 0:                       # add deaths -- the published direction, unchanged
        lo, hi = 0.0, 1.0
        while gap(hi) < 0:
            hi *= 2
            if hi > 1e6:
                raise RuntimeError("disease_pop: cannot bracket the target (exceeds feasible deaths).")
        scale = brentq(gap, lo, hi)
    else:                                  # save lives -- mirror onto the negative half-line
        lo, hi = -1.0, 0.0                 # gap is increasing with gap(0)=-target>0; walk lo down
        while gap(lo) > 0:                 # until the gap turns negative, then bracket [lo, 0]
            lo *= 2
            if lo < -1e6:
                raise RuntimeError("disease_pop: cannot bracket the target (exceeds avertable deaths).")
        scale = brentq(gap, lo, hi)
    return scale, shock_path(scale)


def disease_pop(p, aux, excess_deaths, profile, phase_years=5, un_country_code="608"):
    """Recompute the population under a (signed) excess-deaths age-profile mortality shock.

    `aux` is the stashed baseline demographic dict (pop_dist, pre_pop_dist, fert_rates, mort_rates,
    infmort_rates, imm_rates). Returns (pop_dict, shock_scale): the pop_dict goes straight into
    `p.update_specifications(...)` before solving, exactly as CostOfDisease/main.py does.
    """
    from ogcore import demographics

    cod = _cod()
    ny = int(phase_years)
    fert = cod.extrapolate_demographics(np.asarray(aux["fert_rates"], dtype=float), ny)
    mort = cod.extrapolate_demographics(np.asarray(aux["mort_rates"], dtype=float), ny)
    imm = cod.extrapolate_demographics(np.asarray(aux["imm_rates"], dtype=float), ny)
    infmort = cod.extrapolate_demographics(np.asarray(aux["infmort_rates"], dtype=float), ny)
    pop_dist = np.asarray(aux["pop_dist"], dtype=float)
    pre = np.asarray(aux["pre_pop_dist"], dtype=float)

    h = np.asarray(profile, dtype=float)
    nage = mort.shape[1]
    if h.shape[0] != nage:                 # match the profile to the model's age dimension
        h = np.interp(np.linspace(0, 1, nage), np.linspace(0, 1, h.shape[0]), h)

    scale, alt_mort = calibrate_shock_scale(
        float(excess_deaths), pop_dist, fert, mort, infmort, imm, h, ny, cod.total_deaths)

    pop_dict = demographics.get_pop_objs(
        p.E, p.S, p.T, 0, 99, country_id=un_country_code,
        fert_rates=fert, mort_rates=alt_mort, infmort_rates=infmort, imm_rates=imm,
        infer_pop=True, pop_dist=pop_dist[:1, :], pre_pop_dist=pre,
        initial_data_year=p.start_year, final_data_year=p.start_year + ny - 1, GraphDiag=False)
    return pop_dict, scale
