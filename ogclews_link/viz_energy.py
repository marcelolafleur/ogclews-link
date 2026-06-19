"""Energy-channel figures -- the CLEWS->OG energy signals as the run actually sourced and
applied them. These are the honest-disclosure panels: what the live CLEWS run says about the
energy transition (price ratio, power-sector capex, emissions) set beside what the coupled run
actually fed OG-Core.

  * clews_signal_vs_applied -- THE FLAGSHIP. The real CLEWS energy-price cost ratio (reform/base)
    over calendar years, with the flat proxy wedge the run applied overlaid. The honest reveal
    that the headline run used an illustrative constant shock, not the data path.
  * capex_by_technology      -- cumulative reform-minus-base power-sector capital investment by
    technology, diverging horizontal bars.
  * channel_inputs_over_time -- small multiples of the time-varying CLEWS->OG signals (price
    ratio, power-capex increment, emissions gap), each on the shared calendar x-axis.

Editorial house theme (see style.py). Import-safe (matplotlib Agg). Builders take the
already-loaded country/params/TPI; the CLEWS readers (signals/clews_signal) read the live
scenario dirs at country.scenario.base_dir / reform_dir. Each builder is guarded -- it returns
[] (skips the panel) on any read failure, so a run without CLEWS dirs degrades cleanly.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

from . import signals, style  # noqa: E402
# Read the cost-of-electricity workbook through the channel's own finder so the figure
# reads exactly what the channel read (single source of truth for the glob/lock-file skip).
from .channels import _cost_xlsx  # noqa: E402,F401

style.apply()
import matplotlib.pyplot as plt  # noqa: E402


# --- helpers --------------------------------------------------------------------

def _energy_good_index(country) -> int:
    """The OG consumption good households buy as energy -- read from the concordance, never
    hardcoded. The good is labeled by its 1-based index, energy highlighted by that index."""
    return int(country.concordance.energy_good_index)


def _applied_energy_wedge(base_params, reform_params, i_e: int):
    """Recover the energy-price wedge the run actually applied to the OG energy good as the
    multiplicative reform/base ad-valorem ratio (1 + tau_reform) / (1 + tau_base) - 1, per
    period. The wedge is a reform/base price multiplier, directly comparable to the CLEWS cost
    ratio. Returns (wedge_path, is_flat) or (None, None) if tau_c is absent/misshaped."""
    try:
        tb = np.asarray(base_params.tau_c, dtype=float)
        tr = np.asarray(reform_params.tau_c, dtype=float)
    except Exception:  # noqa: BLE001
        return None, None
    if (tb.ndim != 2 or tr.ndim != 2 or i_e < 0
            or i_e >= tb.shape[1] or i_e >= tr.shape[1]):
        return None, None
    n = min(tb.shape[0], tr.shape[0])
    be, rf = tb[:n, i_e], tr[:n, i_e]
    wedge = (1.0 + rf) / np.where((1.0 + be) == 0, np.nan, (1.0 + be)) - 1.0
    # "flat" within numerical noise -> report it as the single constant the run applied
    finite = wedge[np.isfinite(wedge)]
    is_flat = bool(finite.size and (finite.max() - finite.min()) < 1e-4)
    return wedge, is_flat


def _gdp_musd(country):
    return float(getattr(country, "gdp_musd", np.nan))


# --- (1) flagship: real CLEWS price signal vs the applied wedge -------------------

def clews_signal_vs_applied(country, base_params, reform_params, out_dir, *, note=None,
                            name="clews_signal_vs_applied"):
    """The real CLEWS energy-price cost ratio (reform/base electricity cost) over calendar years,
    with the flat proxy wedge the coupled run actually applied to the OG energy good overlaid.

    The CLEWS ratio comes from the curated 'Cost of electricity generation' workbook each scenario
    ships (signals.cost_of_electricity_ratio reading country.scenario dirs). The applied wedge is
    recovered from the run's tau_c on the energy good. Both are reform/base multipliers, so they
    share the y-axis (1.0 == parity). The headline run used an illustrative CONSTANT shock rather
    than the data path -- stated as fact in the caption; the gap reads off the two plotted lines
    and the computed numbers, never as a judgment. Returns [] if the CLEWS workbook is unreadable.
    """
    try:
        ratio = signals.cost_of_electricity_ratio(
            _cost_xlsx(country.scenario.base_dir), _cost_xlsx(country.scenario.reform_dir))
    except Exception:  # noqa: BLE001 -- no CLEWS dirs / workbook -> skip cleanly
        return []
    ratio = ratio.dropna()
    if ratio.empty:
        return []
    years = np.asarray(ratio.index, dtype=int)
    rv = np.asarray(ratio.values, dtype=float)

    i_e = _energy_good_index(country)
    wedge, is_flat = _applied_energy_wedge(base_params, reform_params, i_e)
    applied_mult = (1.0 + float(np.nanmean(wedge))) if wedge is not None else None

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    fig.subplots_adjust(top=0.74, bottom=0.13, left=0.085, right=0.82)
    style.clean(ax, left=True)
    style.zero_line(ax, value=1.0)  # parity reference: reform == base

    # the real CLEWS signal -- the data path
    ax.plot(years, rv, color=style.CATEGORICAL[0], lw=2.4, zorder=3)
    ends = [(years[-1], rv[-1], "CLEWS cost ratio", style.CATEGORICAL[0])]

    rng = float(np.nanmax(rv) - np.nanmin(rv)) or 1.0

    # the flat applied wedge -- grey the proxy, color the signal
    if applied_mult is not None:
        ax.axhline(applied_mult, color=style.MUTE, lw=2.0, ls=(0, (5, 3)), zorder=2)
        # lift the end-label clear of its own dashed axhline so the line does not strike through it
        ends.append((years[-1], applied_mult + 0.03 * rng, "applied wedge", style.MUTE))

    style.label_ends(ax, ends, min_gap=0.08 * rng)
    ax.set_xlim(years[0], years[-1] + (years[-1] - years[0]) * 0.14)
    ax.set_ylabel("reform / base energy-price ratio")

    # subtitle carries only COMPUTED numbers; direction/magnitude are derived, never asserted
    sub = (f"Energy-system price ratio (reform vs baseline) ranges {rv.min():.2f} to {rv.max():.2f} "
           f"(average {rv.mean():.2f}), {years[0]}–{years[-1]}")
    if applied_mult is not None:
        kind = "a constant" if is_flat else "a near-constant"
        sub += f"  ·  this run instead assumed {kind} energy price of {applied_mult:.2f}"
    cap = "The assumed shock is the run's energy-good price multiplier; the headline run used an " \
          "illustrative flat price shock, not the year-by-year energy-system path"
    style.title_block(
        fig, title="Energy-price signal: what the energy model produced vs what this run assumed",
        subtitle=sub,
        source=style.source_line(note, extra=cap),
        kicker=f"energy price · good {i_e + 1}", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- (2) power-sector capex increment by technology ------------------------------

def capex_by_technology(country, out_dir, *, note=None, name="capex_by_technology"):
    """Cumulative reform-minus-base power-sector CapitalInvestment by technology -- the
    investment the transition reallocates across the generation fleet. Diverging horizontal bars
    from zero, sorted by value, each labeled with its computed model-MUSD. Power technologies are
    selected via country.is_power; magnitudes are model-MUSD with no deflator. Returns [] if the
    CapitalInvestment exports are unreadable, or skips technologies with a zero increment."""
    try:
        # signals exposes no public CLEWS-export finder; reuse its private _find (same locator
        # the channels use) rather than re-implement the glob here.
        mb = signals.read_clews_matrix(signals._find(country.scenario.base_dir, "CapitalInvestment"))
        mr = signals.read_clews_matrix(signals._find(country.scenario.reform_dir, "CapitalInvestment"))
    except Exception:  # noqa: BLE001
        return []

    def _cum(m):
        keep = [t for t in m.index if country.is_power(t)]
        return m.loc[keep].sum(axis=1) if keep else m.sum(axis=1).iloc[:0]

    cb, cr = _cum(mb), _cum(mr)
    techs = sorted(set(cb.index) | set(cr.index))
    diff = {t: float(cr.get(t, 0.0)) - float(cb.get(t, 0.0)) for t in techs}
    diff = {t: v for t, v in diff.items() if abs(v) > 1e-9}  # drop unchanged technologies
    if not diff:
        return []
    items = sorted(diff.items(), key=lambda kv: kv[1])  # ascending -> negatives at bottom
    labels = [t for t, _ in items]
    vals = np.asarray([v for _, v in items], dtype=float)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.8, max(3.4, 0.5 * len(vals) + 2.2)))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.36, right=0.92)
    style.clean(ax, left=False, grid="x")
    style.zero_line(ax, axis="x")
    ypos = np.arange(len(vals))
    ax.barh(ypos, vals, color=style.signed(vals), zorder=2, height=0.72)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=9)
    span = float(np.nanmax(np.abs(vals))) or 1.0
    for y, v in zip(ypos, vals):
        off = 0.012 * span * (1 if v >= 0 else -1)
        ax.annotate(f"{v:+,.0f}", (v + off, y), va="center",
                    ha="left" if v >= 0 else "right", fontsize=9,
                    color=style.GAIN if v >= 0 else style.LOSS)
    # x-limits from the actual data extremes (not symmetric ±max|val|, which leaves a dead
    # half-axis when the increments lean one way) plus a margin for the end labels; always
    # include zero so the diverging bars read against the zero reference.
    lo = float(min(vals.min(), 0.0))
    hi = float(max(vals.max(), 0.0))
    margin = 0.28 * span
    ax.set_xlim(lo - margin, hi + margin)
    ax.set_xlabel("cumulative reform − base capital investment (model MUSD)")
    style.title_block(
        fig, title="Change in power-sector investment, by technology",
        subtitle=f"Cumulative change (reform vs baseline) across {len(vals)} power technologies  ·  "
                 f"net {vals.sum():+,.0f} MUSD",
        source=style.source_line(
            note, extra="Model MUSD, no inflation adjustment applied (energy-model monetary units)"),
        kicker="investment · power sector", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- (3) the time-varying CLEWS->OG signals as small multiples -------------------

def channel_inputs_over_time(country, base_tpi, out_dir, *, note=None, name="channel_inputs"):
    """Small multiples (shared calendar x-axis) of the time-varying CLEWS->OG signals that can be
    sourced from the live scenario: the energy-price cost ratio, the power-capex increment (as %
    of GDP), and the emissions gap (reform/base). Each panel is a neutral description; where a
    channel collapses a path to a scalar before feeding OG, that fact is annotated as a computed
    number. Panels that cannot be read are skipped; returns [] if none can be built."""
    gdp = _gdp_musd(country)
    panels = []  # (title, years, values, baseline_value, color, annotate-fn)

    # energy-price cost ratio (reform / base); parity reference at 1.0
    try:
        r = signals.cost_of_electricity_ratio(
            _cost_xlsx(country.scenario.base_dir), _cost_xlsx(country.scenario.reform_dir)).dropna()
        if not r.empty:
            yrs = np.asarray(r.index, dtype=int)
            v = np.asarray(r.values, dtype=float)
            panels.append(("Energy price, reform vs baseline", yrs, v, 1.0,
                           style.CATEGORICAL[0],
                           f"range {v.min():.2f}–{v.max():.2f}"))
    except Exception:  # noqa: BLE001
        pass

    # power-capex increment as % of GDP (reform - base); zero reference
    try:
        inc = signals.power_capex_increment(
            country.scenario.base_dir, country.scenario.reform_dir, country, public_only=False)
        if not inc.empty and np.isfinite(gdp) and gdp > 0:
            yrs = np.asarray(inc.index, dtype=int)
            v = 100.0 * np.asarray(inc.values, dtype=float) / gdp
            panels.append(("Change in power-sector investment, % of GDP", yrs, v, 0.0,
                           style.CATEGORICAL[3],
                           f"sum over {yrs[0]}–{yrs[-1]}: {v.sum():+.2f}% of GDP"))
    except Exception:  # noqa: BLE001
        pass

    # emissions gap (reform / base); parity reference at 1.0
    try:
        er = signals.emissions_ratio(
            country.scenario.base_dir, country.scenario.reform_dir, country).dropna()
        if not er.empty:
            yrs = np.asarray(er.index, dtype=int)
            v = np.asarray(er.values, dtype=float)
            panels.append(("Emissions, reform vs baseline", yrs, v, 1.0,
                           style.CATEGORICAL[2],
                           f"average {v.mean():.2f}"))
    except Exception:  # noqa: BLE001
        pass

    if not panels:
        return []

    os.makedirs(out_dir, exist_ok=True)
    # shared calendar x-axis across the panels
    xlo = min(int(p[1][0]) for p in panels)
    xhi = max(int(p[1][-1]) for p in panels)
    fig, axes = plt.subplots(len(panels), 1, sharex=True,
                             figsize=(8.4, 2.0 * len(panels) + 1.6))
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(top=0.82, bottom=0.10, left=0.10, right=0.93, hspace=0.42)
    for ax, (ttl, yrs, v, base_val, color, ann) in zip(axes, panels):
        style.clean(ax, left=True)
        style.zero_line(ax, value=base_val)
        ax.plot(yrs, v, color=color, lw=2.2, zorder=3)
        if base_val == 0.0:  # a flow: shade from the zero reference
            ax.fill_between(yrs, base_val, v, color=color, alpha=0.10, zorder=1)
        ax.set_title(ttl)
        ax.set_xlim(xlo, xhi)
        # place the annotation where the series is NOT: if the line ends in the upper half of
        # its range, drop the label to the bottom; if it ends low, lift it to the top. Keeps it
        # clear of a series that plunges or climbs at the right edge.
        vmin, vmax = float(np.nanmin(v)), float(np.nanmax(v))
        vspan = (vmax - vmin) or 1.0
        ends_high = (float(v[-1]) - vmin) / vspan >= 0.5
        ay, ava = (0.06, "bottom") if ends_high else (0.94, "top")
        ax.annotate(ann, (0.985, ay), xycoords="axes fraction", ha="right", va=ava,
                    fontsize=8.5, color=style.SUB)
    axes[-1].set_xlabel("year")
    style.title_block(
        fig, title="Energy-system signals fed into the economy, over time",
        subtitle="The energy-system signals over calendar years, before each policy step enters the economic model",
        source=style.source_line(
            note, extra="A policy step may reduce a year-by-year path to a single number "
            "(e.g. a flat price shock or a 10-year average) before it enters the economic model"),
        kicker="clews → og signals", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
