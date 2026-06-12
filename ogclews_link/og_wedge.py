"""Inject a CLEWS energy-price signal into an OG-Core ``Specifications`` object,
and read back the household demand response.

Theory anchor (OG-Core ``households.md``, EqHH_ciDem2)::

    c_{i,j,s,t} = alpha_i * ( (1 + tau_c_{i,t}) p_{i,t} / p_t )^{-1} * c_{j,s,t} + c_min_i

Households already respond to the *effective* price ``(1 + tau_c_i) p_i`` of the
energy consumption good -- unit-elastic above a Stone-Geary subsistence floor.
The energy good's price ``p_i = sum_m pi_{i,m} p_m`` is built from the energy
*industry's* output price, which is its unit cost and moves only through the
industry TFP ``Z_m`` (``firms.md``, EqFirmFOC_K/L). Three ways to move the
effective energy price the household faces, in increasing rigor:

  (A) tau_c route  [available now, demand-side, cleanest price wedge]:
      raise tau_c on the energy consumption good so the consumer price rises by
      the CLEWS-implied ratio. Routes through government revenue -> must be
      recycled (revenue-neutral) or it becomes a de-facto energy tax.

  (B) Z route  [available now, supply-side]:
      lower the energy *industry* TFP Z_m so its equilibrium price p_m (hence p_i)
      rises. Conflates "costlier" with "less productive"; use deliberately.

  (C) energy-as-CES-input  [structural extension, NOT in shipped OG-Core]:
      add energy as a priced production input so cost passes through endogenously
      without a TFP or tax proxy. The rigor endpoint -- a separate OG-Core PR.

These functions mutate and return ``p`` (duck-typed: anything with ``.tau_c``,
``.Z``, ``.alpha_T`` array attributes). They do NOT run the model, so they are
unit-testable without ogcore. Read-back helpers take TPI output arrays so they
stay decoupled from the solver.
"""
from __future__ import annotations

import numpy as np


def _as_path(value, T: int) -> np.ndarray:
    """Broadcast a scalar or 1-D series to a length-T path (forward-filling short input)."""
    arr = np.atleast_1d(np.asarray(value, dtype=float))
    if arr.shape[0] == 1:
        return np.full(T, arr[0])
    if arr.shape[0] >= T:
        return arr[:T]
    out = np.empty(T)
    out[: arr.shape[0]] = arr
    out[arr.shape[0] :] = arr[-1]  # forward-fill, matching OG-Core's extrapolation convention
    return out


# --- Route (A): consumer price wedge via tau_c -----------------------------------

def effective_price_to_tau_c(price_ratio, tau_c_base):
    """tau_c that scales the *effective* consumer price by ``price_ratio``.

    (1 + tau_c_new) = price_ratio * (1 + tau_c_base); ratio 1.10 == +10% energy price.
    """
    return price_ratio * (1.0 + tau_c_base) - 1.0


def set_energy_consumption_wedge(p, i_energy: int, price_ratio_by_t, *, recycle: bool = False):
    """Make households face a higher energy price via tau_c on good ``i_energy``.

    ``p.tau_c`` is (T, I); ``price_ratio_by_t`` is the reform/base effective-price
    ratio over time (scalar or path). Returns (p, diagnostics).

    The induced consumption-tax revenue is a *mechanical artifact* unless the signal
    truly is a carbon tax. Revenue-neutral recycling needs realized revenue and is a
    POST-SOLVE closure (``recycle_consumption_tax_revenue``); ``recycle`` only records intent.
    """
    tau_c = np.array(p.tau_c, dtype=float)
    T = tau_c.shape[0]
    ratio = _as_path(price_ratio_by_t, T)
    base = tau_c[:, i_energy].copy()
    tau_c[:, i_energy] = effective_price_to_tau_c(ratio, base)
    p.tau_c = tau_c
    return p, {
        "route": "tau_c",
        "i_energy": i_energy,
        "tau_c_base": base,
        "tau_c_new": tau_c[:, i_energy].copy(),
        "price_ratio": ratio,
        "recycle_intent": recycle,
    }


# --- Route (B): supply-side via energy-industry TFP ------------------------------

def set_energy_industry_tfp(p, m_energy: int, cost_ratio_by_t):
    """Raise the energy *industry* output price by lowering its TFP Z_m.

    ``p.Z`` is (T+S, M). ``cost_ratio`` > 1 (energy costlier) divides Z[:, m_energy]
    so the firm's unit cost / price p_m rises. First-order: the equilibrium p_m move
    is not exactly the Z move (it is a GE outcome), so calibrate against the realized
    p_i after a solve. Returns (p, diagnostics).
    """
    Z = np.array(p.Z, dtype=float)
    TpS = Z.shape[0]
    ratio = _as_path(cost_ratio_by_t, TpS)
    base = Z[:, m_energy].copy()
    Z[:, m_energy] = base / ratio
    p.Z = Z
    return p, {"route": "Z", "m_energy": m_energy, "Z_base": base, "Z_new": Z[:, m_energy].copy(),
               "cost_ratio": ratio}


# --- Post-solve closure: neutralize the tau_c phantom revenue --------------------

def recycle_consumption_tax_revenue(p, extra_revenue_by_t):
    """Return the mechanical energy-tax revenue lump-sum via transfers (first-order).

    ``p.alpha_T`` is the transfer-share-of-GDP path. ``extra_revenue_by_t`` is the
    reform-minus-base consumption-tax revenue attributable to the energy wedge,
    expressed as a share of GDP (compute it from a first OG solve). This is the
    minimal revenue-neutral guard against the phantom-revenue artifact; a fuller
    closure would recycle through whichever instrument the scenario specifies.
    """
    alpha_T = np.array(p.alpha_T, dtype=float)
    T = alpha_T.shape[0]
    p.alpha_T = alpha_T + _as_path(extra_revenue_by_t, T)
    return p


# --- Read-back: the demand response and its incidence ---------------------------

def energy_demand_response(base_C_i, reform_C_i, i_energy: int):
    """Percent change in aggregate energy-good consumption, base -> reform.

    ``*_C_i`` are (T, I) aggregate consumption-by-good arrays (OG-Core TPI ``C_i``).
    Returns a length-T array of percent differences for the energy good.
    """
    b = np.asarray(base_C_i, dtype=float)[:, i_energy]
    r = np.asarray(reform_C_i, dtype=float)[:, i_energy]
    return 100.0 * (r - b) / b


def energy_budget_share_by_group(c_i_path, p_i_path, p_path, i_energy: int, t: int = 0):
    """Energy's share of consumption spending by lifetime-income group j, at period ``t``.

    The incidence read-out that only OG-Core can give. ``c_i_path`` is the
    disaggregated consumption array (T, S, J, I); ``p_i_path`` is (T, I) good prices;
    ``p_path`` is (T,) composite price. Returns a length-J array of energy spending
    shares (averaged over ages S). Confirm the exact TPI key for disaggregated
    consumption (``c_i`` vs similar) in OG-Core ``variables.md`` before wiring.
    """
    c = np.asarray(c_i_path, dtype=float)[t]      # (S, J, I)
    p_i = np.asarray(p_i_path, dtype=float)[t]    # (I,)
    spend = c * p_i[None, None, :]                # (S, J, I)
    energy_spend = spend[:, :, i_energy]          # (S, J)
    total_spend = spend.sum(axis=2)               # (S, J)
    share = energy_spend / total_spend            # (S, J)
    return share.mean(axis=0)                     # (J,)
