"""Distributional-richness figures -- the incidence beyond the headline averages:
  * energy_demand_by_group -- the energy-demand response by lifetime-income group, one line per
    channel step (revives the old energy_by_income properly): the cut deepens as carbon is added,
    and the poorest cut energy use the most.
  * consumption_by_age     -- the SS consumption deviation across the lifecycle (λ-weighted, with
    the income-group range), showing WHEN in life the cost lands (young and old bear a little more).

Editorial house theme; import-safe (Agg). Builders take the already-loaded layered list / SS dicts.
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

_SRC = "Source: OG-PHL (OG-Core) x CLEWS coupled model · author's calculations"
STEP_COLORS = style.CATEGORICAL


# --- energy-demand response by income group (across steps) -----------------------

def energy_demand_by_group(layered, out_dir, *, note=None, name="energy_by_income"):
    """Energy-good demand %-change by lifetime-income group, one line per channel step. The cut
    deepens as the carbon price is layered in; the poorest groups cut energy use the most."""
    solved = [r for r in layered if "macro" in r and "energy_by_J" in r]
    if not solved:
        return []
    J = len(solved[0]["energy_by_J"])
    lab = _labels(J)
    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.085, right=0.80)
    style.clean(ax)
    ends = []
    for i, r in enumerate(solved):
        ev = np.asarray(r["energy_by_J"], float)
        c = STEP_COLORS[i % len(STEP_COLORS)]
        ax.plot(range(J), ev, marker="o", color=c, lw=2.0, zorder=2)
        ends.append((J - 1, ev[-1], r["step"], c))
    style.label_ends(ax, ends, min_gap=0.05 * abs(min(e[1] for e in ends)))
    ax.set_xticks(range(J))
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.set_xlim(-0.2, J - 1 + 0.5)
    ax.set_ylabel("energy-good demand change (%)")
    style.title_block(
        fig, title="Carbon pricing deepens the energy-demand cut",
        subtitle="Energy-good demand change by income group, poorest to richest  ·  one line per channel step",
        source=f"{_SRC}.  {note}" if note else _SRC, kicker="distribution: energy demand", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- consumption deviation across the lifecycle ----------------------------------

def consumption_by_age(base_ss, reform_ss, base_params, out_dir, *, note=None, max_age=90,
                       name="consumption_by_age"):
    """SS composite-consumption %-change by age: the λ-weighted lifecycle path with the income-
    group range as a band. Fairly even (~0.3%) through working life, a little deeper for the old.
    Capped at ``max_age`` -- the final model ages are a terminal-period boundary (assets fully
    drawn down), not a lifecycle feature."""
    cb, cr = np.asarray(base_ss["c"], float), np.asarray(reform_ss["c"], float)  # (S, J)
    if cb.shape != cr.shape:
        return []
    E = int(base_params.E)
    lam = np.asarray(base_params.lambdas, float).ravel()
    dev = 100.0 * (cr - cb) / np.where(cb == 0, np.nan, cb)                      # (S, J)
    ages = E + np.arange(cb.shape[0])
    keep = ages <= int(max_age)
    ages, dev = ages[keep], dev[keep]
    avg = np.nansum(dev * lam[None, :], axis=1)
    lo, hi = np.nanmin(dev, axis=1), np.nanmax(dev, axis=1)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    style.zero_line(ax)
    ax.fill_between(ages, lo, hi, color=style.LOSS, alpha=0.10, zorder=1, label="income-group range")
    ax.plot(ages, avg, color=style.LOSS, lw=2.4, zorder=3)
    style.label_ends(ax, [(ages[-1], avg[-1], "population avg", style.LOSS)])
    ax.axvline(65, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=2)
    ax.annotate("retirement", (65, ax.get_ylim()[1]), xytext=(5, -4), textcoords="offset points",
                fontsize=8.5, color=style.SUB, va="top")
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.16)
    ax.set_xlabel("age")
    ax.set_ylabel("consumption change vs baseline (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Consumption falls ~0.3% across the lifecycle, a bit more for the old",
        subtitle="Steady-state composite-consumption change by age, λ-weighted  ·  band = income-group range",
        source=f"{_SRC}.  {note}" if note else _SRC, kicker="distribution: by age", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
