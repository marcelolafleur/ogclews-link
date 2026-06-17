"""Bidirectional ``disease_pop``: the CostOfDisease age-profile mortality method, generalized so the
excess-deaths target may be NEGATIVE (lives saved -- the cleaner-air / pollution direction) as well
as positive (the HIV / disease-burden direction the published code handles).

    rho(s,t) = rho0(s,t) + shock_scale * h(s) * (t+1)/phase_years        (clipped to [0, 1])

``shock_scale`` is solved so the realized year-``phase_years`` excess deaths equal the (signed)
target; then the population path is recomputed with the built-in ``ogcore.demographics.get_pop_objs``.
The demographic helpers (``total_deaths`` / ``extrapolate_demographics``) are vendored in
:mod:`ogclews_link._demog` (identical to the CostOfDisease construction) so this module no longer
loads CostOfDisease by absolute path.

Two generalizations over the published ``disease_pop``: a 0.0 floor (so a reduction can't drive a
rate negative) and a signed root search that does not assume monotonicity. The realized
year-``phase_years`` excess-deaths curve need NOT be monotone in ``shock_scale`` (survivorship
feedback: people whose deaths are averted in early years age into other mortality bands; the 0.0 clip
saturates), so the search scans a geometric grid outward from 0 and brackets the FIRST sign change --
the smallest-magnitude shock that hits the target -- then reports the true achievable extremum if the
target is infeasible. This is correct whenever the curve is monotone up to the first root (the
realistic mortality case) and tolerates a turn-around after it; it does not chase a second root that
rises and falls entirely within one grid interval (not a regime real age profiles produce).
"""
from __future__ import annotations

import numpy as np

from ._demog import extrapolate_demographics, total_deaths

# Geometric |scale| grid scanned outward from 0: fine near 0 (catches ~1e-4 roots) up to a cap.
_MIN_MAG = 1e-6
_MAX_MAG = 1e6


def calibrate_shock_scale(target, pop_dist, fert, mort, infmort, imm, profile, phase_years,
                          total_deaths_fn=total_deaths):
    """Solve the additive age-profile shock scale that hits a SIGNED year-``phase_years``
    excess-deaths target. ``target > 0`` adds deaths (positive scale); ``target < 0`` saves lives
    (negative scale); ``target == 0`` is a no-op. Returns ``(shock_scale, shocked_mortality_path)``.
    Pure -- no ogcore. Robust to a non-monotone gap (see module docstring)."""
    from scipy.optimize import brentq

    profile = np.asarray(profile, dtype=float)
    if profile.ndim != 1 or np.any(profile < 0) or not np.all(np.isfinite(profile)):
        raise ValueError("disease_pop: profile must be a finite, nonnegative 1-D age shape "
                         "(a negative h(s) would let the shock add deaths where it should remove them).")
    ny = phase_years
    base_d = total_deaths_fn(pop_dist, fert, mort, infmort, imm, num_years=ny)[ny - 1].sum()

    def shock_path(scale):
        alt = mort.copy()
        for t in range(ny):
            alt[t, :] = np.clip(mort[t, :] + scale * profile * ((t + 1) / ny), 0.0, 1.0)
        return alt

    def gap(scale):  # realized year-ny excess deaths minus the target (root at gap == 0)
        d = total_deaths_fn(pop_dist, fert, shock_path(scale), infmort, imm, num_years=ny)
        return d[ny - 1].sum() - base_d - target

    if target == 0:
        return 0.0, shock_path(0.0)

    direction = 1.0 if target > 0 else -1.0
    # Scan outward from 0 on the correct half-line; brentq the FIRST sign-change sub-interval so the
    # smallest-magnitude root is returned even if the gap curve later turns around.
    mags = []
    mag = _MIN_MAG
    while mag < _MAX_MAG:
        mags.append(mag)
        mag *= 2.0
    mags.append(_MAX_MAG)                  # ensure the scan actually reaches the cap
    prev_s, prev_g = 0.0, gap(0.0)        # gap(0) == -target (opposite sign to the search direction)
    best_excess = 0.0                     # most extreme realized excess seen, in the search direction
    for mag in mags:
        s = direction * mag
        gs = gap(s)
        realized = gs + target            # realized excess deaths at this scale
        best_excess = max(best_excess, realized) if direction > 0 else min(best_excess, realized)
        if gs == 0.0:
            return s, shock_path(s)
        if np.sign(gs) != np.sign(prev_g):
            scale = brentq(gap, prev_s, s)
            return scale, shock_path(scale)
        prev_s, prev_g = s, gs

    kind = "added" if direction > 0 else "avertable"
    raise RuntimeError(
        f"disease_pop: target {target:+,.0f} exceeds the achievable {kind} deaths for this profile "
        f"(max ~= {best_excess:+,.0f}); the age shape cannot reach it even fully saturated.")


def disease_pop(p, aux, excess_deaths, profile, phase_years=5, un_country_code="608"):
    """Recompute the population under a (signed) excess-deaths age-profile mortality shock.

    ``aux`` is the stashed baseline demographic dict (pop_dist, pre_pop_dist, fert_rates, mort_rates,
    infmort_rates, imm_rates). Returns ``(pop_dict, shock_scale)``: the pop_dict goes straight into
    ``p.update_specifications(...)`` before solving, exactly as CostOfDisease/main.py does.
    """
    from ogcore import demographics

    ny = int(phase_years)
    fert = extrapolate_demographics(np.asarray(aux["fert_rates"], dtype=float), ny)
    mort = extrapolate_demographics(np.asarray(aux["mort_rates"], dtype=float), ny)
    imm = extrapolate_demographics(np.asarray(aux["imm_rates"], dtype=float), ny)
    infmort = extrapolate_demographics(np.asarray(aux["infmort_rates"], dtype=float), ny)
    pop_dist = np.asarray(aux["pop_dist"], dtype=float)
    pre = np.asarray(aux["pre_pop_dist"], dtype=float)

    h = np.asarray(profile, dtype=float)
    nage = mort.shape[1]
    if h.shape[0] != nage:                 # match the profile to the model's age dimension
        h = np.interp(np.linspace(0, 1, nage), np.linspace(0, 1, h.shape[0]), h)

    scale, alt_mort = calibrate_shock_scale(
        float(excess_deaths), pop_dist, fert, mort, infmort, imm, h, ny, total_deaths)

    pop_dict = demographics.get_pop_objs(
        p.E, p.S, p.T, 0, 99, country_id=un_country_code,
        fert_rates=fert, mort_rates=alt_mort, infmort_rates=infmort, imm_rates=imm,
        infer_pop=True, pop_dist=pop_dist[:1, :], pre_pop_dist=pre,
        initial_data_year=p.start_year, final_data_year=p.start_year + ny - 1, GraphDiag=False)
    return pop_dict, scale
