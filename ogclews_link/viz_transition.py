"""Transition-path figures -- the TIME SERIES of the reform's deviation across the OG-Core
transition (in calendar years), not the 10-year-mean snapshot the waterfall/macro_honest use.
The dynamics are the story: the full path can differ sharply from its long-run (10-yr-mean)
level, so these builders show the whole trajectory rather than a single snapshot.

Editorial house theme (see style.py). Import-safe (matplotlib Agg). Builders take the already-
loaded baseline/reform TPI dicts + the calendar start year, so they run from pickles in seconds.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

from . import style  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402

MACRO_VARS = [("Y", "GDP", style.CATEGORICAL[0]), ("C", "consumption", style.CATEGORICAL[1]),
              ("K", "capital", style.CATEGORICAL[2]), ("L", "labor", style.CATEGORICAL[3])]


def _years(start_year, n):
    return np.arange(int(start_year), int(start_year) + int(n))


def _clamp_n(hz, base_tpi, reform_tpi, *vars_):
    """Plot horizon clamped to BOTH dicts' actual lengths for every variable plotted, so a
    shorter reform array can never make _pct_path slice mismatched lengths and crash."""
    lens = [len(np.asarray(d[v])) for v in vars_
            for d in (base_tpi, reform_tpi) if v in d]
    return min([int(hz)] + lens)


def _pct_path(base_tpi, reform_tpi, var, n):
    return style.pct_dev(np.asarray(reform_tpi[var], dtype=float)[:n],
                         np.asarray(base_tpi[var], dtype=float)[:n])


def _closure_window(params, start_year, default_n, *, tail=30):
    """Calendar year the OG-Core budget-closure rule begins (start_year + tG1) and a plot horizon
    that stops a modest tail past it -- long-run convergence (tG2) is centuries out and not worth
    plotting. Returns (closure_year or None, n_years)."""
    if params is None:
        return None, int(default_n)
    try:
        tG1 = int(np.atleast_1d(params.tG1).flat[0])
    except Exception:  # noqa: BLE001
        return None, int(default_n)
    return int(start_year) + tG1, min(int(default_n), tG1 + int(tail))


def _closure_line(ax, closure_year, yrs):
    """Dashed vertical marker where the budget-closure rule begins (only if within the span)."""
    if closure_year is None or not (yrs[0] <= closure_year <= yrs[-1]):
        return
    ax.axvline(closure_year, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=1.8)
    # White halo + high zorder so the label stays readable where a series peaks near the closure
    # year (the marker would otherwise sit right under it on several transition figures).
    ax.annotate("budget rule begins", (closure_year, ax.get_ylim()[1]), xytext=(4, -4),
                textcoords="offset points", fontsize=8, color=style.SUB, va="top", zorder=6,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))


# --- the hero: macro aggregates over the transition ------------------------------

def macro_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                     params=None, title="The economy over time, vs baseline (output, consumption, capital, labor)",
                     name="macro_transition"):
    """Y/C/K/L % deviation from baseline across the transition, calendar-year x-axis, lines
    direct-labeled at their right ends. The largest GDP deviation is marked -- the path can be
    several times the long-run (10-yr-mean) effect the snapshot figures report."""
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, *(v for v, _, _ in MACRO_VARS))
    yrs = _years(start_year, n)
    paths = {v: _pct_path(base_tpi, reform_tpi, v, n) for v, _, _ in MACRO_VARS}

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.085, right=0.86)
    style.clean(ax, left=True)
    ends = []
    for v, lab, c in MACRO_VARS:
        ax.plot(yrs, paths[v], color=c, lw=2.2, zorder=2)
        ends.append((yrs[-1], paths[v][-1], lab, c))
    style.zero_line(ax)
    # call out the largest GDP deviation (the dynamic the snapshot hides) -- by magnitude, so
    # the marker is honest whether the path runs above or below baseline
    y = paths["Y"]
    pk = int(np.nanargmax(np.abs(y)))
    ax.scatter([yrs[pk]], [y[pk]], s=46, color=style.CATEGORICAL[0], zorder=4,
               edgecolor="white", linewidth=1.0)
    ax.annotate(f"largest deviation {y[pk]:+.2f}% in {yrs[pk]}", (yrs[pk], y[pk]),
                xytext=(8, 12), textcoords="offset points", fontsize=9.5,
                fontweight="bold", color=style.CATEGORICAL[0])
    rng = float(np.nanmax([np.nanmax(np.abs(p)) for p in paths.values()]))
    # Nudge near-zero end-labels (e.g. capital/labor, which can both finish ~0) off the zero axis
    # and onto their own side, then de-collide with a generous gap so they don't stack and touch.
    off = 0.06 * rng
    ends = [(x, (off if y >= 0 else -off) if abs(y) < off else y, t, c) for (x, y, t, c) in ends]
    style.label_ends(ax, ends, min_gap=0.09 * rng)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.12)
    ax.set_ylabel("change vs baseline (%)")
    _y0, _y1 = ax.get_ylim()                          # top headroom so the closure label clears
    ax.set_ylim(_y0, _y1 + 0.14 * (_y1 - _y0))        # the GDP-peak marker
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title=title,
        subtitle=f"% change vs baseline, {yrs[0]}–{yrs[-1]}  ·  shows how the economy gets there over time",
        source=style.source_line(note), kicker="macro transition", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- fiscal ratios over the transition -------------------------------------------

def fiscal_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                      params=None, name="fiscal_transition"):
    """Debt/GDP and Revenue/GDP as LEVELS (baseline vs reform) across the transition -- the
    fiscal footprint of the reform. (Carbon/consumption-tax revenue is not recycled here, so
    the revenue line is a phantom-revenue diagnostic, flagged in the caption.)"""
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)

    panels = [("D", "Debt / GDP", "government debt"),
              ("total_tax_revenue", "Revenue / GDP", "total tax revenue")]
    panels = [p for p in panels if p[0] in base_tpi and p[0] in reform_tpi]
    if not panels:
        return []
    n = _clamp_n(hz, base_tpi, reform_tpi, "Y", *(p[0] for p in panels))
    yrs = _years(start_year, n)

    def ratio(tpi, num):
        return 100.0 * np.asarray(tpi[num], float)[:n] / np.asarray(tpi["Y"], float)[:n]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.9 * len(panels), 5.0))
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(top=0.74, bottom=0.13, left=0.075, right=0.93, wspace=0.26)
    for ax, (var, ttl, desc) in zip(axes, panels):
        style.clean(ax, left=True)
        rb, rr = ratio(base_tpi, var), ratio(reform_tpi, var)
        ax.plot(yrs, rb, color=style.MUTE, lw=2.0, zorder=2)
        ax.plot(yrs, rr, color=style.CATEGORICAL[0], lw=2.2, zorder=3)
        ax.fill_between(yrs, rb, rr, color=style.CATEGORICAL[0], alpha=0.10, zorder=1)
        style.label_ends(ax, [(yrs[-1], rb[-1], "baseline", style.MUTE),
                              (yrs[-1], rr[-1], "reform", style.CATEGORICAL[0])],
                         min_gap=0.05 * (float(np.nanmax(np.r_[rb, rr])) - float(np.nanmin(np.r_[rb, rr])) or 1))
        ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.16)
        ax.set_title(f"{ttl}  ·  {desc}")
        ax.set_ylabel("% of GDP")
        _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Government debt and revenue over time",
        subtitle="Debt and revenue as a share of GDP, baseline vs reform",
        source=style.source_line(note), kicker="fiscal paths", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def revenue_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                       params=None, name="revenue_transition"):
    """Consumption-tax revenue (the carbon tax flows through it) as a share of GDP, baseline AND
    reform LEVELS across the transition -- not just the change -- so the absolute paths and the gap
    between them both read. Closure-rule marker; capped to the closure window."""
    if not all("cons_tax_revenue" in t and "Y" in t for t in (base_tpi, reform_tpi)):
        return []
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, "cons_tax_revenue", "Y")
    yrs = _years(start_year, n)

    def _share(tpi):  # revenue as % of GDP (a level, comparable across base/reform)
        rev = np.asarray(tpi["cons_tax_revenue"], dtype=float)[:n]
        gdp = np.asarray(tpi["Y"], dtype=float)[:n]
        return 100.0 * rev / np.where(gdp == 0, np.nan, gdp)

    rb, rr = _share(base_tpi), _share(reform_tpi)
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.10, right=0.88)
    style.clean(ax, left=True)
    ax.plot(yrs, rb, color=style.MUTE, lw=2.2, zorder=2)
    ax.plot(yrs, rr, color=style.CATEGORICAL[2], lw=2.4, zorder=3)
    ax.fill_between(yrs, rb, rr, color=style.CATEGORICAL[2], alpha=0.10, zorder=1)
    rng = float(np.nanmax(np.concatenate([rb, rr])) - np.nanmin(np.concatenate([rb, rr]))) or 1.0
    style.label_ends(ax, [(yrs[-1], rb[-1], "baseline", style.MUTE),
                          (yrs[-1], rr[-1], "reform", style.CATEGORICAL[2])], min_gap=0.08 * rng)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.14)
    ax.set_ylabel("consumption-tax revenue (% of GDP)")
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Consumption-tax revenue over time (incl. carbon)",
        subtitle=f"Revenue as a share of GDP, baseline vs reform, {yrs[0]}-{yrs[-1]}",
        source=style.source_line(note), kicker="carbon revenue", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def rates_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                     params=None, name="rates_transition"):
    """Interest rate r and wage w as % deviation from baseline across the transition. Both are
    PRICES (r a rate, w a level), so % deviation is the comparable unit (not the ×100-of-a-wage-
    level artifact). The computed max |deviation| is shown in the subtitle."""
    have = [v for v in ("r", "w") if v in base_tpi and v in reform_tpi]
    if not have:
        return []
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, *have)
    yrs = _years(start_year, n)
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.10, right=0.88)
    style.clean(ax, left=True)
    style.zero_line(ax)
    labels = {"r": ("interest rate", style.CATEGORICAL[4]), "w": ("wage", style.CATEGORICAL[2])}
    ends, allv = [], []
    for v in ("r", "w"):
        if v not in have:
            continue
        d = _pct_path(base_tpi, reform_tpi, v, n)
        allv.append(d)
        lab, c = labels[v]
        ax.plot(yrs, d, color=c, lw=2.2, zorder=2)
        ends.append((yrs[-1], d[-1], lab, c))
    rng = float(np.nanmax([np.nanmax(np.abs(d)) for d in allv]))
    style.label_ends(ax, ends, min_gap=0.10 * rng)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.14)
    ax.set_ylabel("change vs baseline (%)")
    _y0, _y1 = ax.get_ylim()                          # top headroom so the peak isn't clipped and
    ax.set_ylim(_y0, _y1 + 0.16 * (_y1 - _y0))        # the closure label clears the peak
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Interest rates and wages over time",
        subtitle=f"Interest rate and wage, % change vs baseline  ·  largest change {rng:.2f}%",
        source=style.source_line(note), kicker="factor prices", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- public investment and public capital over the transition --------------------

# I_g/K_g are the public-investment flow and public-capital stock. The figure focuses on its
# title subject (public investment and public capital), so only these two series are plotted;
# the broader investment aggregates (I_d / I_total) carry a single-period domestic-investment
# outlier that would set the y-axis and compress these paths into an unreadable band, and they
# fall outside the title's scope. Each (var, label, color) -- labels are model-generic.
_PUBINV_VARS = [("I_g", "public investment", style.CATEGORICAL[0]),
                ("K_g", "public capital", style.CATEGORICAL[2])]


def public_investment(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                      params=None, name="public_investment"):
    """Public investment (I_g) and public capital (K_g) as % deviation from baseline across the
    transition. Calendar-year x-axis, lines direct-labeled at their right ends, closure-rule
    marker, capped plot horizon. Scoped to the title subject -- the broader investment aggregates
    are deliberately omitted (their single-period outlier would compress these paths). Magnitudes
    are uncalibrated -- keep that caveat in the caption note. Returns [] if I_g/K_g are absent."""
    if not all(v in base_tpi and v in reform_tpi for v in ("I_g", "K_g")):
        return []
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, *(v for v, _, _ in _PUBINV_VARS))
    yrs = _years(start_year, n)
    vars_here = [(v, lab, c) for v, lab, c in _PUBINV_VARS
                 if v in base_tpi and v in reform_tpi]

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.10, right=0.84)
    style.clean(ax, left=True)
    style.zero_line(ax)
    ends, allv = [], []
    for v, lab, c in vars_here:
        d = _pct_path(base_tpi, reform_tpi, v, n)
        allv.append(d)
        ax.plot(yrs, d, color=c, lw=2.2, zorder=2)
        ends.append((yrs[-1], d[-1], lab, c))
    rng = float(np.nanmax([np.nanmax(np.abs(d)) for d in allv]))
    # Two converging end-labels can also land on the zero line; a generous min_gap nudges them
    # apart vertically and a non-zero floor keeps the gap usable even when both ends sit near 0.
    style.label_ends(ax, ends, min_gap=max(0.16 * rng, 0.08))
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.14)
    ax.set_ylabel("change vs baseline (%)")
    _y0, _y1 = ax.get_ylim()                          # top headroom so the closure label clears
    ax.set_ylim(_y0, _y1 + 0.14 * (_y1 - _y0))        # the steep public-investment rise
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Public investment and public capital over time",
        subtitle=f"% change vs baseline, {yrs[0]}–{yrs[-1]}  ·  largest change {rng:.2f}%",
        source=style.source_line(note), kicker="public capital", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
