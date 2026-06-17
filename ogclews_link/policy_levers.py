"""Generic, resource/industry-agnostic policy levers for OG-Core scenarios.

Built energy-first but designed to generalize to other CLEWS resources (agriculture, land, water, ...):
every lever targets an industry by index, so the same primitive serves an energy ITC, an agriculture
investment subsidy, a water-sector incentive, etc. Two families, both using EXISTING OG-Core params
(NO model change):

  * `set_investment_incentive` — bias PRIVATE capex in an industry by lowering its cost of capital
    (investment tax credit `inv_tax_credit`, accelerated tax depreciation `delta_tau`, and/or a
    corporate-tax `tau_b` multiplier). Firm responds via its FOC; OG has no exogenous private-investment
    quantity, so this is the correct (incentive) channel.
  * `route_revenue` — direct a revenue stream (as a %-GDP path) to one of: transfers (`alpha_T`),
    public investment / infrastructure (`alpha_I` -> K_g), government consumption (`alpha_G`), or
    `deficit` (no-op: the budget closure absorbs it as lower debt / per the debt-ratio rule).

These are the reusable primitives a scenario builder / UI assembles into experiments. Each is a pure
param mutation on a duck-typed Specifications (numpy attrs), so it is unit-testable without a solve.
"""
from __future__ import annotations

import numpy as np

# --- industry catalog: the generality hook --------------------------------------
# Maps a friendly resource/industry name to its index in the shipped M=4 calibration
# [Natural Resources, Electricity, Construction/Trade/Services, Manufacturing] and whether it is
# SEPARABLE there. Agriculture, water, mining are bundled into "Natural Resources" in M=4, so to target
# them specifically you need a finer/purpose-built aggregation (a calibration choice; see
# docs/design/energy-as-production-input-spec.md). The catalog makes that explicit so a UI can grey out
# non-separable targets until the calibration supports them.
INDUSTRY_CATALOG = {
    "natural_resources": {"m4_index": 0, "separable_m4": True,
                          "sam_activities": ["amine", "afore", "afish", "awatr", "amaiz", "arice"]},
    "energy":            {"m4_index": 1, "separable_m4": True, "sam_activities": ["aelec"]},
    "construction_trade_services": {"m4_index": 2, "separable_m4": True, "sam_activities": ["acons", "atrad"]},
    "manufacturing":     {"m4_index": 3, "separable_m4": True, "sam_activities": ["achem", "ametl", "afood"]},
    # not separable in M=4 (bundled in Natural Resources) -- need a finer aggregation to target:
    "agriculture": {"m4_index": 0, "separable_m4": False, "sam_activities": ["amaiz", "arice", "avege"],
                    "note": "bundled in Natural Resources in M=4; needs a purpose-built aggregation"},
    "water":       {"m4_index": 0, "separable_m4": False, "sam_activities": ["awatr"],
                    "note": "bundled in Natural Resources in M=4; needs a purpose-built aggregation"},
}


def resolve_industry(industry, p=None):
    """Resolve a name (from INDUSTRY_CATALOG) or an int index to an industry column index, warning if
    the target is not separable in the current M aggregation."""
    if isinstance(industry, str):
        info = INDUSTRY_CATALOG.get(industry)
        if info is None:
            raise ValueError(f"unknown industry '{industry}'; known: {sorted(INDUSTRY_CATALOG)}")
        if not info.get("separable_m4", True):
            print(f"[policy_levers] WARNING: '{industry}' is not separable in M=4 "
                  f"({info.get('note', '')}); targeting its bundle index {info['m4_index']}.")
        return info["m4_index"]
    return int(industry)


def _as_TS_M(arr, TpS, M):
    a = np.array(arr, dtype=float)
    if a.ndim == 1:                      # (M,) or (TpS,) -> tile to (TpS, M)
        a = np.tile(a.reshape(1, -1) if a.shape[0] == M else a.reshape(-1, 1), (1, M) if a.shape[0] != M else (TpS, 1))
    if a.shape != (TpS, M):
        a = np.broadcast_to(a, (TpS, M)).copy()
    return a


def set_investment_incentive(p, industry, *, inv_tax_credit=None, delta_tau=None, tau_b_mult=None,
                             phase_years=None):
    """Bias PRIVATE capex in `industry` by lowering its cost of capital, over the first `phase_years`
    periods (or all if None). Sets the existing per-industry (T+S, M) firm-tax params:
      - inv_tax_credit: investment tax credit (positive = subsidy on capital) for that industry;
      - delta_tau: tax depreciation rate (raise for accelerated depreciation -> bigger tax shield);
      - tau_b_mult: multiply that industry's business tax (e.g. 0.5 = halve the CIT).
    Returns a provenance dict. Pure param mutation (duck-typed p)."""
    m = resolve_industry(industry, p)
    TpS = np.asarray(p.Z).shape[0]
    M = np.asarray(p.Z).shape[1]
    end = TpS if phase_years is None else min(int(phase_years), TpS)
    prov = {"industry": industry, "m": m, "phase_years": end}
    if inv_tax_credit is not None:
        itc = _as_TS_M(p.inv_tax_credit, TpS, M)
        itc[:end, m] = float(inv_tax_credit)
        p.inv_tax_credit = itc
        prov["inv_tax_credit"] = float(inv_tax_credit)
    if delta_tau is not None:
        dt = _as_TS_M(p.delta_tau, TpS, M)
        dt[:end, m] = float(delta_tau)
        p.delta_tau = dt
        prov["delta_tau"] = float(delta_tau)
    if tau_b_mult is not None:
        tb = _as_TS_M(p.tau_b, TpS, M)
        tb[:end, m] = tb[:end, m] * float(tau_b_mult)
        p.tau_b = tb
        prov["tau_b_mult"] = float(tau_b_mult)
    return prov


def route_revenue(p, pct_gdp_path, *, to="transfers", fill_ss_tail=True):
    """Direct a revenue stream (a per-period %-of-GDP path) to a fiscal destination. `to` in
    {'transfers' (alpha_T), 'public_investment' (alpha_I -> K_g), 'government_consumption' (alpha_G),
    'deficit' (no-op -> the budget closure / debt rule absorbs it)}. Returns a provenance dict."""
    valid = {"transfers": "alpha_T", "public_investment": "alpha_I", "government_consumption": "alpha_G",
             "deficit": None}
    if to not in valid:
        raise ValueError(f"unknown revenue destination '{to}'; choose from {sorted(valid)}")
    attr = valid[to]
    if attr is None:                      # deficit: do nothing; un-recycled revenue lowers debt via closure
        return {"to": to, "param": None, "note": "budget closure absorbs revenue (debt-ratio rule applies)"}
    base = np.array(getattr(p, attr), dtype=float)
    n = base.shape[0]
    bump = np.array(pct_gdp_path, dtype=float)
    bump = bump[:n] if bump.shape[0] >= n else np.concatenate([bump, np.full(n - bump.shape[0],
                                                                             bump[-1] if fill_ss_tail else 0.0)])
    setattr(p, attr, base + bump)         # additive %-GDP share (permanent policy fills the SS tail)
    return {"to": to, "param": attr, "mean_pct_gdp": float(np.mean(bump[:10]))}
