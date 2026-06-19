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

STEP_COLORS = style.CATEGORICAL
# Distinct dash patterns per step so that policy steps whose curves nearly coincide (e.g. the
# price and investment steps) stay individually visible where they overlap, instead of one line
# hiding under the next.
STEP_LS = ["-", (0, (5, 2)), (0, (1, 1.4)), (0, (4, 2, 1, 2))]


def _lam_weighted_avg(dev, lam):
    """λ-weighted average of ``dev`` (S, J) across income groups, per age. Renormalizes the
    weights over the FINITE entries at each age, so groups masked to NaN (e.g. an undefined
    %-change) drop out of the average instead of silently biasing it toward 0 (mirrors
    cev_by_age's w = lam[ok]/lam[ok].sum() pattern, vectorized over ages)."""
    dev = np.asarray(dev, float)
    lam = np.asarray(lam, float).ravel()
    ok = np.isfinite(dev)                                     # (S, J)
    w = np.where(ok, lam[None, :], 0.0)                       # zero out missing groups' weight
    wsum = w.sum(axis=1)                                      # (S,)
    num = np.nansum(np.where(ok, dev, 0.0) * w, axis=1)       # (S,)
    return np.where(wsum > 0, num / np.where(wsum == 0, np.nan, wsum), np.nan)


def _lifecycle_band(ax, ages, dev, lam, base_params, *, band_label="income-group range",
                    line_label="population avg", color=None, right_pad=0.16, min_halfrange=None):
    """Shared lifecycle band builder for consumption_by_age and asset_by_age: a λ-weighted
    average line over the income-group fill_between(lo, hi) band, sign-colored (unless ``color``
    is forced), with the retirement marker and an end-of-line label. ``min_halfrange`` floors the
    y-axis half-range (e.g. 1.0%) so a near-null effect frames as small instead of being magnified
    into a dramatic wiggle. Returns (avg, color)."""
    avg = _lam_weighted_avg(dev, lam)
    lo, hi = np.nanmin(dev, axis=1), np.nanmax(dev, axis=1)
    c = color if color is not None else (style.LOSS if np.nanmean(avg) < 0 else style.GAIN)
    style.zero_line(ax)
    ax.fill_between(ages, lo, hi, color=c, alpha=0.10, zorder=1, label=band_label)
    ax.plot(ages, avg, color=c, lw=2.4, zorder=3)
    if min_halfrange is not None:                        # frame a near-null effect honestly (not magnified)
        ylo, yhi = ax.get_ylim()
        mid = 0.5 * (ylo + yhi)
        if 0.5 * (yhi - ylo) < min_halfrange:
            ax.set_ylim(mid - min_halfrange, mid + min_halfrange)
    style.label_ends(ax, [(ages[-1], avg[-1], line_label, c)])
    style.mark_retirement(ax, base_params, label_top=True)
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * right_pad)
    return avg, c


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
        ls = STEP_LS[i % len(STEP_LS)]
        ax.plot(range(J), ev, marker="o", color=c, lw=2.0, ls=ls, zorder=2,
                markeredgecolor="white", markeredgewidth=0.8)
        ends.append((J - 1, ev[-1], r["step"], c))
    # Floor the collision gap: scaling off the smallest end alone collapses toward 0 when the
    # lowest line ends near 0, so fall back to a fraction of the spread of all ends.
    end_ys = [e[1] for e in ends]
    min_gap = max(0.05 * abs(min(end_ys)), 0.03 * (np.ptp(end_ys) or 1.0))
    style.label_ends(ax, ends, min_gap=min_gap)
    ax.set_xticks(range(J))
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.set_xlim(-0.2, J - 1 + 0.5)
    ax.set_ylabel("energy-good demand change (%)")
    style.title_block(
        fig, title="Change in energy use, by income group",
        subtitle="Energy-good demand change by income group, poorest to richest  ·  one line per scenario",
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
    dev = style.pct_dev(cr, cb)                                                  # (S, J)
    ages = E + np.arange(cb.shape[0])
    keep = ages <= int(max_age)
    ages, dev = ages[keep], dev[keep]

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    avg, _ = _lifecycle_band(ax, ages, dev, lam, base_params, color=style.LOSS, right_pad=0.16)
    ax.set_xlabel("age")
    ax.set_ylabel("consumption change vs baseline (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Household spending change, by age",
        subtitle=f"Long-run change in spending over the life cycle, averaged across income groups "
                 f"(mean {np.nanmean(avg):+.2f}%)  ·  shaded band = range across income groups",
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
    dev = style.pct_dev(br, bb)                                                   # (S, J)
    ages = E + np.arange(bb.shape[0])
    keep = ages <= int(max_age)
    ages, dev = ages[keep], dev[keep]

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    avg, _ = _lifecycle_band(ax, ages, dev, lam, base_params, right_pad=0.08, min_halfrange=1.0)
    ax.set_xlabel("age")
    ax.set_ylabel("asset change vs baseline (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Household savings change, by age",
        subtitle=f"Long-run change in savings over the life cycle, averaged across income groups "
                 f"(mean {np.nanmean(avg):+.2f}%)  ·  shaded band = range across income groups",
        source=style.source_line(note), kicker="distribution: savings by age", top=0.965)
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
             ("bq", "income from inheritances")]
    lam = np.asarray(base_params.lambdas, float).ravel()
    E = int(np.atleast_1d(base_params.E).flat[0])
    series, ages = [], None
    for i, (key, lab) in enumerate(comps):
        if key not in base_tpi or key not in reform_tpi:
            continue
        arr_b, arr_r = np.asarray(base_tpi[key], float), np.asarray(reform_tpi[key], float)
        nyr = min(10, arr_b.shape[0])                    # first-decade average (period 0 is pre-phase-in)
        b0, r0 = arr_b[:nyr].mean(axis=0), arr_r[:nyr].mean(axis=0)               # (S, J)
        if b0.shape != r0.shape or b0.ndim != 2:
            continue
        a = E + np.arange(b0.shape[0])
        keep = a <= int(max_age)
        # Mask NEAR-zero baselines, not just exact zeros: e.g. labor income ~0 after retirement
        # makes the %-change ratio explode into a spurious terminal spike. Treat |base| below a
        # small fraction of the component's own peak as undefined (NaN) so it never sets the scale.
        tiny = 1e-3 * (np.nanmax(np.abs(b0)) or 1.0)
        # NaN the near-zero baselines first (not just exact zeros), then take the standard
        # %-deviation: style.pct_dev already maps an exact-zero base to NaN, so masking the
        # tiny entries to NaN here carries that same "undefined ratio" treatment through.
        b0m = np.where(np.abs(b0) < tiny, np.nan, b0)
        dev = style.pct_dev(r0, b0m)                                             # (S, J)
        dev = dev[keep]
        avg = _lam_weighted_avg(dev, lam)
        ages = a[keep] if ages is None else ages
        series.append((lab, avg, style.CATEGORICAL[i % len(style.CATEGORICAL)]))
    if not series:
        return []

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.4, 5.1))
    fig.subplots_adjust(top=0.76, bottom=0.18, left=0.095, right=0.84)
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
    style.mark_retirement(ax, base_params, label_top=True)
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.18)
    ax.set_xlabel("age")
    ax.set_ylabel("change in income vs baseline (%)")
    fig.text(0.045, 0.05,
             "Note: inheritances are split equally across households in this run, so the line is flat by design;\n"
             "it dips because fewer deaths leave fewer estates to pass on.",
             fontsize=8.5, color=style.SUB, ha="left", va="bottom")
    style.title_block(
        fig, title="Change in income, by source and age",
        subtitle="Labor income, capital income, and income from inheritances  ·  first-decade average, "
                 "across income groups",
        source=style.source_line(note),
        kicker="distribution: income sources", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
