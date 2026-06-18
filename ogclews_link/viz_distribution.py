"""Distributional-richness figures -- the incidence beyond the headline averages:
  * energy_demand_by_group -- the energy-demand response by lifetime-income group, one line per
    channel step (revives the old energy_by_income properly).
  * consumption_by_age     -- the SS consumption deviation across the lifecycle (λ-weighted, with
    the income-group range), showing WHEN in life the deviation lands.

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

_SRC = style.SRC
STEP_COLORS = style.CATEGORICAL


# --- energy-demand response by income group (across steps) -----------------------

def energy_demand_by_group(layered, out_dir, *, note=None, name="energy_by_income"):
    """Energy-good demand %-change by lifetime-income group, one line per channel step."""
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
        fig, title="Energy-demand change by income group, across channel steps",
        subtitle="Energy-good demand change by income group, poorest to richest  ·  one line per channel step",
        source=style.source_line(note), kicker="distribution: energy demand", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- consumption deviation across the lifecycle ----------------------------------

def consumption_by_age(base_ss, reform_ss, base_params, out_dir, *, note=None, max_age=90,
                       name="consumption_by_age"):
    """SS composite-consumption %-change by age: the λ-weighted lifecycle path with the income-
    group range as a band, showing when in life the deviation lands.
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
    r_age = style.retire_age(base_params)
    if r_age is not None:
        ax.axvline(r_age, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=2)
        ax.annotate("retirement", (r_age, ax.get_ylim()[1]), xytext=(5, -4),
                    textcoords="offset points", fontsize=8.5, color=style.SUB, va="top")
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.16)
    ax.set_xlabel("age")
    ax.set_ylabel("consumption change vs baseline (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Consumption change by age",
        subtitle=f"Steady-state composite-consumption change by age, λ-weighted (mean {np.nanmean(avg):+.2f}%)"
                 "  ·  band = income-group range",
        source=style.source_line(note), kicker="distribution: by age", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- asset deviation across the lifecycle (stock-side companion) ------------------

def asset_by_age(base_ss, reform_ss, base_params, out_dir, *, note=None, max_age=85,
                 name="asset_by_age"):
    """SS household-asset %-change by age: the λ-weighted lifecycle path with the income-group
    range as a band -- the stock-side companion to consumption_by_age.
    Capped at ``max_age`` -- the final model ages are a terminal-period drawdown boundary (assets
    falling to ~0), not a lifecycle feature; the cap is tighter here than for consumption so the
    band/line do not plunge into that boundary at the right edge. Ages where baseline assets are
    ~0 are dropped from the %-change (the ratio is undefined there) rather than spiking."""
    if "b_s" not in base_ss or "b_s" not in reform_ss:
        return []
    bb, br = np.asarray(base_ss["b_s"], float), np.asarray(reform_ss["b_s"], float)  # (S, J)
    if bb.shape != br.shape or bb.ndim != 2:
        return []
    E = int(np.atleast_1d(base_params.E).flat[0])
    lam = np.asarray(base_params.lambdas, float).ravel()
    dev = 100.0 * (br - bb) / np.where(bb == 0, np.nan, bb)                       # (S, J)
    ages = E + np.arange(bb.shape[0])
    keep = ages <= int(max_age)
    ages, dev = ages[keep], dev[keep]
    avg = np.nansum(dev * lam[None, :], axis=1)
    lo, hi = np.nanmin(dev, axis=1), np.nanmax(dev, axis=1)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    style.zero_line(ax)
    band_c = style.LOSS if np.nanmean(avg) < 0 else style.GAIN
    ax.fill_between(ages, lo, hi, color=band_c, alpha=0.10, zorder=1, label="income-group range")
    ax.plot(ages, avg, color=band_c, lw=2.4, zorder=3)
    style.label_ends(ax, [(ages[-1], avg[-1], "population avg", band_c)])
    r_age = style.retire_age(base_params)
    if r_age is not None:
        ax.axvline(r_age, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=2)
        ax.annotate("retirement", (r_age, ax.get_ylim()[1]), xytext=(5, -4),
                    textcoords="offset points", fontsize=8.5, color=style.SUB, va="top")
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.08)
    ax.set_xlabel("age")
    ax.set_ylabel("asset change vs baseline (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Household assets by age, change vs baseline",
        subtitle=f"Steady-state household assets by age, λ-weighted (mean {np.nanmean(avg):+.2f}%)"
                 "  ·  band = income-group range",
        source=style.source_line(note), kicker="distribution: assets by age", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- income-component deviation across the lifecycle (near-term TPI snapshot) -----

def income_composition_by_age(base_tpi, reform_tpi, base_params, out_dir, *, note=None,
                              max_age=80, name="income_composition_by_age"):
    """Near-term (t=0) %-deviation of the three household-income components -- labor income,
    capital income and bequests -- by age, λ-weighted over income groups, one line each.
    A transition snapshot: these are TPI-only quantities (no SS analogue), read at the first
    transition period. Components absent from the run are skipped; returns [] if none present.
    Capped at ``max_age`` -- the final model ages are a terminal-period boundary (assets fully
    drawn down), not a lifecycle feature -- so those spikes do not set the scale."""
    comps = [("labor_income", "labor income"), ("capital_income", "capital income"),
             ("bq", "bequests")]
    lam = np.asarray(base_params.lambdas, float).ravel()
    E = int(np.atleast_1d(base_params.E).flat[0])
    series, ages = [], None
    for i, (key, lab) in enumerate(comps):
        if key not in base_tpi or key not in reform_tpi:
            continue
        b0 = np.asarray(base_tpi[key], float)[0]                                  # (S, J)
        r0 = np.asarray(reform_tpi[key], float)[0]
        if b0.shape != r0.shape or b0.ndim != 2:
            continue
        a = E + np.arange(b0.shape[0])
        keep = a <= int(max_age)
        # Mask NEAR-zero baselines, not just exact zeros: e.g. labor income ~0 after retirement
        # makes the %-change ratio explode into a spurious terminal spike. Treat |base| below a
        # small fraction of the component's own peak as undefined (NaN) so it never sets the scale.
        tiny = 1e-3 * (np.nanmax(np.abs(b0)) or 1.0)
        dev = 100.0 * (r0 - b0) / np.where(np.abs(b0) < tiny, np.nan, b0)         # (S, J)
        dev = dev[keep]
        avg = np.nansum(dev * lam[None, :], axis=1)
        ages = a[keep] if ages is None else ages
        series.append((lab, avg, style.CATEGORICAL[i % len(style.CATEGORICAL)]))
    if not series:
        return []

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.84)
    style.clean(ax, left=True)
    style.zero_line(ax)
    ends = []
    for lab, avg, c in series:
        ax.plot(ages, avg, color=c, lw=2.2, zorder=3)
        ends.append((ages[-1], avg[-1], lab, c))
    finite = np.concatenate([np.asarray(a, float)[np.isfinite(a)] for _, a, _ in series])
    span = np.ptp(finite) or 1.0
    gap = 0.07 * span
    # Keep end-labels off the zero reference line: nudge any anchor sitting within the
    # min-gap band of zero out to its own side, so the axhline never strikes through text.
    off = 0.5 * gap
    ends = [(x, (off if y >= 0 else -off) if abs(y) < off else y, t, c)
            for (x, y, t, c) in ends]
    style.label_ends(ax, ends, min_gap=gap)
    r_age = style.retire_age(base_params)
    if r_age is not None:
        ax.axvline(r_age, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=2)
        ax.annotate("retirement", (r_age, ax.get_ylim()[1]), xytext=(5, -4),
                    textcoords="offset points", fontsize=8.5, color=style.SUB, va="top")
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.18)
    ax.set_xlabel("age")
    ax.set_ylabel("income-component change vs baseline (%)")
    style.title_block(
        fig, title="Income components by age, change vs baseline",
        subtitle="First transition period (t=0), λ-weighted  ·  one line per income component",
        source=style.source_line(note if note else "Transition snapshot: TPI-only, first period."),
        kicker="distribution: income components", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
