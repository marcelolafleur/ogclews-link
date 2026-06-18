"""One-page headline dashboard -- the coupled run on a single slide. Four compact panels carry the
whole arc, left to right, top to bottom:

  1. energy system   -- baseline vs reform emissions path (the physical CLEWS signal)
  2. macro dynamics  -- GDP & consumption deviation over the transition
  3. channels        -- what each layered channel adds to GDP (the decomposition)
  4. welfare         -- steady-state lifetime CEV by income group

Reuses the per-figure machinery (viz_welfare._Felicity, viz_transition._pct_path) rather than
re-deriving it, so the dashboard always matches its standalone figures. Import-safe (Agg).
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

from . import style, viz_transition, viz_welfare  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402

from .figures import _labels  # noqa: E402

_SRC = style.SRC


def _panel_emissions(ax, country):
    from . import signals
    eb = signals.emissions_by_year(country.scenario.base_dir, country)
    er = signals.emissions_by_year(country.scenario.reform_dir, country)
    erb = eb.reindex(er.index)
    ax.plot(eb.index, eb.values, color=style.MUTE, lw=2.0, zorder=2)
    ax.plot(er.index, er.values, color=style.GAIN, lw=2.2, zorder=3)
    ax.fill_between(er.index, erb.values, er.values, color=style.GAIN, alpha=0.12, zorder=1)
    style.label_ends(ax, [(eb.index[-1], eb.values[-1], "base", style.MUTE),
                          (er.index[-1], er.values[-1], "reform", style.GAIN)], min_gap=0.0)
    ax.set_xlim(right=float(er.index[-1]) + (float(er.index[-1]) - float(er.index[0])) * 0.18)
    ax.set_ylabel(f"emissions ({country.co2_emission})")
    ax.set_title("1 · Emissions: baseline vs reform")


def _panel_macro(ax, base_tpi, reform_tpi, start_year, n_years=80):
    n = min(n_years, len(np.asarray(base_tpi["Y"])))
    yrs = viz_transition._years(start_year, n)
    for v, lab, c in (("Y", "GDP", style.CATEGORICAL[0]), ("C", "consumption", style.CATEGORICAL[1])):
        d = viz_transition._pct_path(base_tpi, reform_tpi, v, n)
        ax.plot(yrs, d, color=c, lw=2.2, zorder=2)
        ax.annotate(lab, (yrs[-1], d[-1]), xytext=(5, 0), textcoords="offset points",
                    color=c, fontsize=9.5, fontweight="medium", va="center")
    style.zero_line(ax)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.18)
    ax.set_ylabel("change vs baseline (%)")
    ax.set_title("2 · Macro aggregates over the transition")


def _panel_waterfall(ax, layered):
    solved = [r for r in layered if "macro" in r]
    labels = [r["step"].replace("+ ", "") for r in solved]
    yvals = [r["macro"]["Y"] for r in solved]
    marg = np.diff(np.concatenate([[0.0], yvals]))
    cum = np.concatenate([[0.0], np.cumsum(marg)])
    for i, m in enumerate(marg):
        ax.bar(i, m, bottom=cum[i], color=style.GAIN if m >= 0 else style.LOSS, width=0.64, zorder=2)
        if i < len(marg) - 1:
            ax.plot([i + 0.32, i + 1 - 0.32], [cum[i + 1], cum[i + 1]], color="0.6", lw=0.8, zorder=1)
    style.zero_line(ax)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.margins(y=0.16)
    ax.set_ylabel("GDP change (%)")
    ax.set_title(f"3 · What each channel adds to GDP  ·  net {cum[-1]:+.3f}%")


def _panel_cev(ax, base_ss, reform_ss, base_params, reform_params):
    fe = viz_welfare._Felicity(base_params)
    cb, nb = np.asarray(base_ss["c"], float), np.asarray(base_ss["n"], float)
    cr, nr = np.asarray(reform_ss["c"], float), np.asarray(reform_ss["n"], float)
    chi = np.asarray(base_params.chi_n, float)[-1]
    rho_b, rho_r = np.asarray(base_params.rho, float)[-1], np.asarray(reform_params.rho, float)[-1]
    J = cb.shape[1]
    cev = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cr[:, j], nr[:, j]), chi, rho_b, rho_r, j)
                            for j in range(J)])
    ax.bar(range(J), cev, width=0.66, color=style.signed(cev), zorder=2)
    style.zero_line(ax)
    ax.set_xticks(range(J))
    ax.set_xticklabels(_labels(J), rotation=30, ha="right", fontsize=8)
    ax.margins(y=0.18)
    ax.set_ylabel("lifetime CEV (%)")
    ax.set_title("4 · Welfare by income group (CEV)")


def headline_dashboard(layered, base_tpi, reform_tpi, base_ss, reform_ss, base_params,
                       reform_params, country, out_dir, *, start_year, note=None,
                       name="headline_dashboard"):
    """The whole coupled run on one slide: emissions, macro dynamics, channel decomposition, welfare."""
    os.makedirs(out_dir, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 9.4))
    fig.subplots_adjust(top=0.82, bottom=0.085, left=0.075, right=0.965, hspace=0.42, wspace=0.22)
    for ax in axes.ravel():
        style.clean(ax, left=True)

    try:
        _panel_emissions(axes[0, 0], country)
    except Exception as e:  # noqa: BLE001 -- emissions needs the external CLEWS dir; degrade gracefully
        axes[0, 0].set_title("1 · Emissions: baseline vs reform")
        axes[0, 0].text(0.5, 0.5, f"(emissions unavailable:\n{type(e).__name__})", ha="center",
                        va="center", transform=axes[0, 0].transAxes, color=style.MUTE, fontsize=9)
    _panel_macro(axes[0, 1], base_tpi, reform_tpi, start_year)
    _panel_waterfall(axes[1, 0], layered)
    _panel_cev(axes[1, 1], base_ss, reform_ss, base_params, reform_params)

    style.title_block(
        fig, title=f"{country.name}: coupled OG-Core × CLEWS scenario",
        subtitle="Emissions · macro transition · channel decomposition · welfare (CEV)",
        source=f"{_SRC}.  {note}" if note else _SRC, kicker="headline dashboard", top=0.975)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
