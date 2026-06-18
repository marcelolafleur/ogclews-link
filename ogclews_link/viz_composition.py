"""Composition figures -- WHERE in the basket and the production structure the coupled run lands,
beyond the single-number macro averages:
  * consumption_by_good        -- the SS %-deviation of each composite consumption good, bars from
    zero, the energy good marked (route A: the good households buy and react to).
  * sectoral_reallocation      -- the SS %-deviation of output, capital, and labor by industry, a
    three-series dot plot, the energy industry marked (route B: the industry whose price carries
    the energy cost).
  * consumption_by_good_by_group -- the near-term consumption-quantity %-change by good for a few
    income groups (poorest / middle / richest), showing whether the basket re-mix is even across
    the income distribution.

The energy ports are read from the contract concordance (1-based) and converted to 0-based; goods
and sectors are labeled by index only ("good 1..I" / "sector 1..M") -- no hardcoded names, so the
figures are portable across country models. Editorial house theme; import-safe (Agg). Builders take
the already-loaded SS / TPI dicts + model_params and return a list of saved paths.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

from . import style  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402

from .figures import _labels  # noqa: E402


# --- energy-port resolution (read-only from the contract concordance) ------------
# The concordance pins the energy good (route A) and energy industry (route B). The builders
# accept a `concordance` keyword (the driver passes country.concordance) so the energy ports are
# resolved from the country actually being plotted; the package PHL_CONCORDANCE is kept only as a
# portable fallback. If neither yields a valid in-range index the builder simply omits the energy
# marker rather than guessing one.
#
# NOTE on basing: the rest of the codebase (og_wedge.energy_demand_response, report.incidence,
# channels) uses concordance.energy_good_index / energy_industry_index DIRECTLY as a 0-based
# numpy index (e.g. base_C_i[:, i_energy], tau_c[:, i_energy]). So the stored value IS the
# 0-based array position -- we use it as-is and do NOT subtract 1, to stay consistent with how
# the model wedges and reports already interpret it (e.g. energy_good_index=1 -> the 2nd good).

def _energy_index(attr, n, concordance=None):
    """Resolve an energy port (`attr` in {energy_good_index, energy_industry_index}) to a 0-based
    array index in range [0, n). The concordance value is already a 0-based position (see module
    note).

    Resolution order, both degrading gracefully:
      1. the `concordance` passed by the caller (the driver passes country.concordance), then
      2. the package PHL_CONCORDANCE, kept only as a portable fallback.
    Returns None when neither yields a valid in-range index, so callers can degrade to no marker
    rather than guessing one."""
    candidates = []
    if concordance is not None:
        candidates.append(concordance)
    try:
        from .contract import PHL_CONCORDANCE as _con  # read-only fallback import
        candidates.append(_con)
    except Exception:  # noqa: BLE001 -- absent/garbled package concordance must not break plotting
        pass
    for con in candidates:
        try:
            idx0 = int(getattr(con, attr))
        except Exception:  # noqa: BLE001 -- a garbled/partial concordance falls through
            continue
        if 0 <= idx0 < n:
            return idx0
    return None


def _good_labels(I, energy0=None):
    """1-based "good k" labels; the energy good (0-based `energy0`) gets a trailing asterisk."""
    return [f"good {k + 1}" + (" *" if energy0 is not None and k == energy0 else "") for k in range(I)]


def _sector_labels(M, energy0=None):
    """1-based "sector k" labels; the energy industry (0-based `energy0`) gets a trailing asterisk."""
    return [f"sector {k + 1}" + (" *" if energy0 is not None and k == energy0 else "") for k in range(M)]


# --- SS consumption change by composite good -------------------------------------

def consumption_by_good(base_ss, reform_ss, base_params, out_dir, *, note=None,
                        concordance=None, name="consumption_by_good"):
    """Steady-state %-change of each composite consumption good (C_i reform vs base), bars from
    zero, sign-colored, the computed % stamped on every bar. The energy good (concordance route A)
    is marked with an asterisk so the basket re-mix reads against its energy port -- by index, so
    it is portable across country models. `concordance` (the driver passes country.concordance)
    pins the energy port; PHL_CONCORDANCE is only a fallback."""
    cb_raw, cr_raw = base_ss.get("C_i"), reform_ss.get("C_i")
    cb = np.asarray(cb_raw, float).ravel() if cb_raw is not None else None
    cr = np.asarray(cr_raw, float).ravel() if cr_raw is not None else None
    if cb is None or cr is None or cb.shape != cr.shape or cb.size == 0:
        return []
    I = cb.size
    dev = style.pct_dev(cr, cb)
    energy0 = _energy_index("energy_good_index", I, concordance)
    lab = _good_labels(I, energy0)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.10, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    ax.bar(range(I), dev, width=0.66, color=style.signed(dev), zorder=2)
    for k, v in enumerate(dev):
        if not np.isfinite(v):
            continue
        ax.annotate(f"{v:+.2f}%", (k, v), xytext=(0, -11 if v < 0 else 6),
                    textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                    fontsize=9, fontweight="bold", color=style.LOSS if v < 0 else style.GAIN)
    ax.set_xticks(range(I))
    ax.set_xticklabels(lab)
    ax.margins(y=0.20)
    ax.set_ylabel("consumption change vs baseline (%)")
    fin = dev[np.isfinite(dev)]
    parts = []
    if fin.size:
        parts.append(f"range {np.min(fin):+.2f}% to {np.max(fin):+.2f}%")
    if energy0 is not None:
        parts.append(f"* marks the energy good (good {energy0 + 1})")
    sub = "  ·  ".join(parts)
    style.title_block(
        fig, title="Steady-state consumption change by good",
        subtitle=sub, source=style.source_line(note),
        kicker="composition: by good", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- SS output / capital / labor reallocation by industry ------------------------

def sectoral_reallocation(base_ss, reform_ss, base_params, out_dir, *, note=None,
                          concordance=None, name="sectoral_reallocation"):
    """Steady-state %-change by industry of output (Y_m), capital (K_m), and labor (L_m) -- a
    three-series dot plot, one cluster per sector, the computed values labeled. The energy industry
    (concordance route B) is marked with an asterisk. Dots (position/length encodings) keep the
    three series legible on one honest, zero-anchored scale. `concordance` (the driver passes
    country.concordance) pins the energy port; PHL_CONCORDANCE is only a fallback."""
    series = []
    for key, lbl, col in (("Y_m", "output", style.CATEGORICAL[0]),
                          ("K_m", "capital", style.CATEGORICAL[2]),
                          ("L_m", "labor", style.CATEGORICAL[3])):
        b, r = base_ss.get(key), reform_ss.get(key)
        if b is None or r is None:
            continue
        b = np.asarray(b, float).ravel()
        r = np.asarray(r, float).ravel()
        if b.shape != r.shape or b.size == 0:
            continue
        series.append((lbl, col, style.pct_dev(r, b)))
    if not series:
        return []
    M = series[0][2].size
    if any(s[2].size != M for s in series):
        return []
    energy0 = _energy_index("energy_industry_index", M, concordance)
    lab = _sector_labels(M, energy0)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    fig.subplots_adjust(top=0.74, bottom=0.12, left=0.16, right=0.86)
    style.clean(ax, left=False, grid="x")          # horizontal dot plot: vertical (x) gridlines
    style.zero_line(ax, axis="x")
    n = len(series)
    spread = 0.26                                  # vertical offset of the three markers per sector
    offs = np.linspace(-spread, spread, n) if n > 1 else np.array([0.0])
    markers = ["o", "s", "D", "^", "v"]
    all_vals = np.concatenate([s[2][np.isfinite(s[2])] for s in series]) if series else np.array([])
    span = (np.max(all_vals) - np.min(all_vals)) if all_vals.size else 1.0
    for si, (lbl, col, vals) in enumerate(series):
        ys = np.arange(M) + offs[si]
        ax.scatter(vals, ys, s=64, color=col, marker=markers[si % len(markers)], zorder=3,
                   label=lbl, edgecolor="white", linewidth=0.6)
        for k, v in enumerate(vals):
            if not np.isfinite(v):
                continue
            ax.annotate(f"{v:+.2f}%", (v, ys[k]),
                        xytext=(6 if v >= 0 else -6, 0), textcoords="offset points",
                        ha="left" if v >= 0 else "right", va="center",
                        fontsize=7.5, color=col)
    ax.set_yticks(range(M))
    ax.set_yticklabels(lab)
    ax.invert_yaxis()                              # sector 1 at top, reading order
    ax.set_ylim(M - 0.5, -0.5)
    if all_vals.size:
        lo, hi = np.min(all_vals), np.max(all_vals)
        ax.set_xlim(lo - 0.16 * (span or 1.0), hi + 0.20 * (span or 1.0))
    ax.set_xlabel("change vs baseline (%)")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    sub = (f"* marks the energy industry (sector {energy0 + 1})" if energy0 is not None
           else "Output, capital, and labor markers, one cluster per sector")
    style.title_block(
        fig, title="Steady-state output, capital, and labor by sector, change vs baseline",
        subtitle=sub, source=style.source_line(note),
        kicker="composition: by sector", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- near-term consumption change by good across income groups -------------------

def consumption_by_good_by_group(base_tpi, reform_tpi, base_params, out_dir, *, note=None,
                                 concordance=None, name="consumption_by_good_by_group"):
    """Near-term (t=0) consumption-quantity %-change by good for a few lifetime-income groups
    (poorest / middle / richest), as small multiples -- one panel per group, a bar per good. The
    quantity is c_i (T,I,S,J) at t=0 aggregated over ages -> (I,J), so the bars compare WHAT each
    group buys more/less of. The energy good (concordance route A) is marked with an asterisk."""
    cib = base_tpi.get("c_i")
    cir = reform_tpi.get("c_i")
    if cib is None or cir is None:
        return []
    cib = np.asarray(cib, float)
    cir = np.asarray(cir, float)
    if cib.shape != cir.shape or cib.ndim != 4 or cib.shape[0] == 0:
        return []
    # t=0, aggregate over ages (axis=S) -> (I, J) consumption-quantity per good per group
    b0 = cib[0].sum(axis=1)
    r0 = cir[0].sum(axis=1)
    I, J = b0.shape
    dev = style.pct_dev(r0, b0)                      # (I, J)

    # poorest / middle / richest -- distinct indices, degrade if J is tiny
    picks = sorted(set([0, J // 2, J - 1]))
    if not picks:
        return []
    lam = None
    try:
        lam = np.asarray(base_params.lambdas, float).ravel()
        if lam.size != J:
            lam = None
    except Exception:  # noqa: BLE001
        lam = None
    glab = _labels(J, lam)
    energy0 = _energy_index("energy_good_index", I, concordance)
    xlab = _good_labels(I, energy0)

    finite = dev[:, picks][np.isfinite(dev[:, picks])]
    vmax = np.max(np.abs(finite)) if finite.size else 1.0
    ylim = vmax * 1.30 or 1.0

    os.makedirs(out_dir, exist_ok=True)
    n = len(picks)
    fig, axes = plt.subplots(1, n, figsize=(3.1 * n + 1.4, 5.0), sharey=True)
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(top=0.74, bottom=0.20, left=0.085, right=0.97, wspace=0.18)
    for ai, j in enumerate(picks):
        ax = axes[ai]
        vals = dev[:, j]
        style.clean(ax, left=(ai == 0))
        style.zero_line(ax)
        ax.bar(range(I), vals, width=0.70, color=style.signed(vals), zorder=2)
        for k, v in enumerate(vals):
            if not np.isfinite(v):
                continue
            ax.annotate(f"{v:+.1f}%", (k, v), xytext=(0, -9 if v < 0 else 5),
                        textcoords="offset points", ha="center",
                        va="top" if v < 0 else "bottom", fontsize=7.0,
                        color=style.LOSS if v < 0 else style.GAIN)
        ax.set_xticks(range(I))
        ax.set_xticklabels(xlab, rotation=30, ha="right", fontsize=8)
        ax.set_ylim(-ylim, ylim)
        ax.set_title(glab[j] if j < len(glab) else f"group {j + 1}")
        if ai == 0:
            ax.set_ylabel("consumption change vs baseline (%)")
    sub = "Near-term (year 0) consumption-quantity change by good, poorest / mid (J//2) / richest group"
    if energy0 is not None:
        sub += f"  ·  * marks the energy good (good {energy0 + 1})"
    style.title_block(
        fig, title="Consumption change by good and income group",
        subtitle=sub, source=style.source_line(note),
        kicker="composition: good x group", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
