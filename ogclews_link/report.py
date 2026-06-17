"""Reporting: turn a finished ExperimentContext into macro, demand, and incidence
read-outs. Import-light (numpy only) so it is testable on array fixtures without ogcore.
"""
from __future__ import annotations

import numpy as np

from . import og_wedge


def macro_pct_diff(base_tpi, reform_tpi, var_list=("Y", "C", "K", "L", "r", "w"), n=10):
    """% change reform vs base for aggregate paths, first n periods (r/w shown as level diff)."""
    out = {}
    for v in var_list:
        if v not in base_tpi:
            continue
        b, r = np.asarray(base_tpi[v]), np.asarray(reform_tpi[v])
        T = min(len(b), len(r), n)
        if v in ("r", "w", "r_p", "r_gov"):
            out[v] = (r[:T] - b[:T])  # level difference for rates
        else:
            out[v] = 100.0 * (r[:T] - b[:T]) / np.where(b[:T] == 0, np.nan, b[:T])
    return out


def demand_response(base_tpi, reform_tpi, i_energy):
    """% change in aggregate energy-good consumption, by period."""
    return og_wedge.energy_demand_response(base_tpi["C_i"], reform_tpi["C_i"], i_energy)


def incidence(base_tpi, reform_tpi, i_energy, n=10):
    """Energy-consumption and composite-consumption % change by lifetime-income group J.

    NB: ``consumption_by_J`` is the % change in average composite CONSUMPTION (the TPI ``c`` array,
    averaged over the first ``n`` periods and all ages) -- NOT a lifetime-utility / equivalent-
    variation welfare measure. The thinnest top-income group is the most GE-sensitive, so read its
    swings as consumption incidence, not utility."""
    eJ = og_wedge.energy_demand_response_by_group(base_tpi["c_i"], reform_tpi["c_i"], i_energy, n)
    cb, cr = np.asarray(base_tpi["c"]), np.asarray(reform_tpi["c"])  # (T, S, J)
    cJ = 100.0 * (cr[:n].mean(axis=(0, 1)) - cb[:n].mean(axis=(0, 1))) / cb[:n].mean(axis=(0, 1))
    return {"energy_by_J": np.round(eJ, 2), "consumption_by_J": np.round(cJ, 2)}


def fiscal_check(base_tpi, reform_tpi, n=10):
    """Consumption-tax revenue change (the phantom-revenue diagnostic) + resource-constraint error."""
    out = {}
    if "cons_tax_revenue" in base_tpi:
        b, r = np.asarray(base_tpi["cons_tax_revenue"]), np.asarray(reform_tpi["cons_tax_revenue"])
        out["cons_tax_revenue_pct"] = float(100 * np.nanmean((r[:n] - b[:n]) / b[:n]))
    for tag, tpi in (("base", base_tpi), ("reform", reform_tpi)):
        if "resource_constraint_error" in tpi:
            out[f"rc_error_{tag}"] = float(np.max(np.abs(tpi["resource_constraint_error"])))
    return out


def print_report(ctx):
    """Human-readable summary of a finished run."""
    i_e = ctx.country.concordance.energy_good_index
    b, r = ctx.base_tpi, ctx.reform_tpi
    print("\n" + "=" * 70)
    print(f"REPORT: {ctx.country.name}  ({len(ctx.provenance)} channel(s) applied)")
    print("=" * 70)
    print("\nChannels + provenance:")
    for rec in ctx.provenance:
        print(f"  - {rec}")
    if b is None or r is None:
        print("\n(no solve results in context)")
        return
    print("\nMacro (Δ first 10 yrs):")
    for k, v in macro_pct_diff(b, r).items():
        unit = "pp" if k in ("r", "w", "r_p", "r_gov") else "%"
        print(f"  {k:4} {np.round(v.mean(), 3)} {unit}")
    print(f"\nEnergy-good demand response: {np.nanmean(demand_response(b, r, i_e)[:10]):.2f}%")
    inc = incidence(b, r, i_e)
    print("Incidence by income group J (j0 low .. high):")
    print("  energy %chg     :", inc["energy_by_J"])
    print("  consumption %chg:", inc["consumption_by_J"])
    fc = fiscal_check(b, r)
    if fc:
        print("\nFiscal/solve checks:", {k: round(v, 4) for k, v in fc.items()})
    if ctx.clews_inputs:
        print("\nCLEWS inputs produced (for the loop-closure / re-run):", list(ctx.clews_inputs))
