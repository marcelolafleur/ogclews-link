"""Figures + tables for a coupled run, rebuilt around best-practice economic dataviz and an
adversarial review of both what's insightful and how it looks. Analytical principles:
  * plot the DEVIATION itself on lines/dots (never truncated bars) -- honest about small effects;
  * DIVERGING color centered on zero for signed data (gains vs losses);
  * income groups labeled by PERCENTILE, ordered poorest->richest;
  * the distributional incidence is the hero (most models can't show who-pays), shown WITH its
    mechanism (energy budget share) and in DOLLARS, not just %;
  * the 'across steps' story as a WATERFALL of marginal channel contributions (not occluded lines);
  * macro panels on a FIXED axis with a 'negligible by construction' note;
  * the PHYSICAL energy side (emissions) shown -- a CLEWS linkage must show the energy system;
  * every figure carries its assumptions in a grey source line.
Visual language (see style.py): editorial theme -- Source Sans 3/Roboto type, colorblind-safe
diverging + Okabe-Ito categorical palettes, open frame (no top/right spines), faint y-grid, no
tick marks, a colored kicker rule + left-aligned bold claim + grey dek, direct line-end labels,
crisp 200-dpi embedded-font output. Import-safe (matplotlib Agg).
"""
from __future__ import annotations

import csv
import os

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

from . import style  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402

LOSS, GAIN = style.LOSS, style.GAIN
STEP_COLORS = style.CATEGORICAL

_SRC = style.SRC


def _labels(J, lambdas=None):
    return style.income_labels(J, lambdas)


# --- the hero: distributional incidence + mechanism + dollars --------------------

def incidence_hero(base_tpi, reform_tpi, i_energy, out_dir, *, title, note, factor=None,
                   name="incidence", kicker="distributional incidence"):
    """Three linked panels: (1) the incidence curve -- welfare % change by income group as a
    dot-and-line, diverging color by sign; (2) the MECHANISM -- welfare vs baseline energy
    budget share; (3) the DOLLAR effect per household (approximate, via the OG income factor)."""
    from . import report

    os.makedirs(out_dir, exist_ok=True)
    inc = report.incidence(base_tpi, reform_tpi, i_energy)
    w = np.asarray(inc["consumption_by_J"], dtype=float)
    J = len(w)
    lab = _labels(J)

    cib, pib = np.asarray(base_tpi["c_i"]), np.asarray(base_tpi["p_i"])  # (T,I,S,J),(T,I)
    spend = pib[0][:, None, None] * cib[0]                                # (I,S,J)
    share = (spend[i_energy] / spend.sum(axis=0)).mean(axis=0) * 100       # (J,) energy budget share %

    ncol = 3 if factor is not None else 2
    fig, axes = plt.subplots(1, ncol, figsize=(4.9 * ncol, 5.0),
                             gridspec_kw={"width_ratios": [1.12, 1.0, 1.12][:ncol]})
    fig.subplots_adjust(top=0.74, bottom=0.17, left=0.055, right=0.985, wspace=0.30)

    # (1) who bears it -- the incidence curve
    ax = axes[0]
    style.clean(ax)
    style.zero_line(ax)
    ax.plot(range(J), w, color="0.75", lw=1.2, zorder=1)
    ax.scatter(range(J), w, c=style.signed(w), s=110, zorder=3, edgecolor="white", linewidth=1.0)
    ax.set_xticks(range(J))
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.set_ylabel("consumption change (%)")
    ax.set_title("Who bears it")
    ax.margins(y=0.16)  # headroom so the extreme-value labels clear the axis/tick labels
    jmin, jmax = int(np.argmin(w)), int(np.argmax(w))
    for j, va in ((jmin, "top" if w[jmin] < 0 else "bottom"),
                  (jmax, "bottom" if w[jmax] >= 0 else "top")):
        ax.annotate(f"{w[j]:+.2f}%", (j, w[j]), xytext=(0, 11 if va == "bottom" else -11),
                    textcoords="offset points", ha="center", va=va, fontsize=9.5,
                    fontweight="bold", color=GAIN if w[j] >= 0 else LOSS)

    # (2) the mechanism -- welfare vs baseline energy budget share
    ax = axes[1]
    style.clean(ax, grid="y")
    style.zero_line(ax)
    ax.scatter(share, w, c=style.signed(w), s=90, edgecolor="white", linewidth=1.0, zorder=3)
    sp = float(share.mean())
    ax.set_xlim(0, max(2.2, float(share.max()) * 1.5))
    ax.set_xlabel("baseline energy budget share (%)")
    ax.set_ylabel("consumption change (%)")
    ax.set_title("Welfare vs baseline energy share")
    ax.annotate(
        f"energy is ~{sp:.1f}% of the baseline\nbudget, on average across groups",
        xy=(sp, float(np.median(w))), xytext=(0.045, 0.94), textcoords="axes fraction",
        fontsize=8.5, color=style.SUB, va="top", ha="left",
        arrowprops=dict(arrowstyle="->", color="#BBBBBB", lw=0.8))

    # (3) the dollar effect per household
    if factor is not None:
        cb, cr = np.asarray(base_tpi["c"]), np.asarray(reform_tpi["c"])   # (T,S,J)
        dC = (cr[:10].mean(axis=(0, 1)) - cb[:10].mean(axis=(0, 1))) * float(factor)
        ax = axes[2]
        style.clean(ax)
        style.zero_line(ax)
        ax.bar(range(J), dC, color=style.signed(dC), width=0.74, zorder=2)
        ax.set_xticks(range(J))
        ax.set_xticklabels(lab, rotation=30, ha="right")
        ax.set_ylabel("consumption change / household / year (approx.)")
        ax.set_title("How much per household")
        pad = 0.02 * (np.nanmax(np.abs(dC)) or 1.0)
        for j, v in enumerate(dC):
            ax.annotate(f"{v:+,.0f}", (j, v), xytext=(0, 4 if v >= 0 else -4),
                        textcoords="offset points", ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=8, color=style.INK)
        ax.margins(y=0.16)

    style.title_block(fig, title=title,
                      subtitle="Consumption change by income group, poorest to richest",
                      source=f"{_SRC}.  {note}", kicker=kicker, top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- across steps: waterfall of marginal channel contributions -------------------

def _waterfall(values, labels, title, subtitle, ylabel, out_path, note=None,
               kicker="channel decomposition", segments=None):
    """Bridge chart: each bar is the MARGINAL contribution of adding that channel, stacked on a
    running cumulative; diverging color by sign. A net marker closes the bridge. ``segments`` (optional)
    maps a bar index -> [(value, color, label), ...] that SUM to that bar's marginal, drawn as a
    stacked bar with a small legend -- e.g. the health bar split into mortality + morbidity parts."""
    segments = segments or {}
    marg = np.diff(np.concatenate([[0.0], values]))
    cum = np.concatenate([[0.0], np.cumsum(marg)])
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.11, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    seg_handles = {}
    for i, m in enumerate(marg):
        if i in segments:                              # stacked sub-parts that sum to this marginal
            base = cum[i]
            for val, color, lab in segments[i]:
                ax.bar(i, val, bottom=base, color=color, width=0.62, zorder=2,
                       edgecolor="white", linewidth=0.6)
                seg_handles.setdefault(lab, color)
                base += val
        else:
            ax.bar(i, m, bottom=cum[i], color=GAIN if m >= 0 else LOSS, width=0.62, zorder=2)
        if i < len(marg) - 1:
            ax.plot([i + 0.31, i + 1 - 0.31], [cum[i + 1], cum[i + 1]], color="0.6",
                    lw=0.8, zorder=1)
        ax.annotate(f"{m:+.3f}", (i, cum[i + 1]), textcoords="offset points",
                    xytext=(0, 5 if m >= 0 else -5), ha="center",
                    va="bottom" if m >= 0 else "top", fontsize=8.5, color=style.INK)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel(ylabel)
    ax.margins(x=0.06, y=0.13)  # footroom so the smallest marginal label clears the axis rule
    if seg_handles:
        from matplotlib.patches import Patch
        ax.legend([Patch(facecolor=c) for c in seg_handles.values()], list(seg_handles),
                  loc="upper left", frameon=False, fontsize=8.5)
    style.title_block(fig, title=title, subtitle=f"{subtitle}  ·  net {cum[-1]:+.3f}%",
                      source=f"{_SRC}.  {note}" if note else _SRC, kicker=kicker, top=0.965)
    return style.save(fig, out_path)


def across_steps_waterfall(layered, out_dir, note=None):
    solved = [r for r in layered if "macro" in r]
    if len(solved) < 2:
        return []
    labels = [r["step"] for r in solved]
    yvals = [r["macro"]["Y"] for r in solved]
    # Split the health bar into mortality + morbidity sub-parts, if the run recorded the split.
    # mortality marginal = mortality-only-cumulative GDP − the previous step's GDP; morbidity is the
    # remainder of the combined health marginal (a sequential, exact split that sums to the bar).
    segments = {}
    for i, r in enumerate(solved):
        split = r.get("health_split")
        if split is not None and i > 0:
            mort_marg = split["mortality"] - yvals[i - 1]
            morb_marg = (yvals[i] - yvals[i - 1]) - mort_marg
            segments[i] = [(mort_marg, style.CATEGORICAL[2], "mortality"),
                           (morb_marg, style.CATEGORICAL[3], "morbidity")]
    saved = [_waterfall(yvals, labels,
                        "What each channel adds to GDP",
                        "Marginal contribution to GDP as channels are layered in",
                        "GDP change (%)", os.path.join(out_dir, "waterfall_gdp.png"), note,
                        segments=segments)]
    saved.append(_waterfall([r["consumption_by_J"][0] for r in solved], labels,
                            "What each channel adds for the poorest group",
                            "Marginal welfare contribution for the 0-25% group",
                            "consumption change (%)",
                            os.path.join(out_dir, "waterfall_poorest.png"), note))
    return saved


def macro_honest(layered, out_dir, ylim=0.5, note=None):
    """Macro aggregates across steps on a FIXED axis, so near-zero effects read as near-zero;
    lines direct-labeled at their right ends (no legend box)."""
    solved = [r for r in layered if "macro" in r]
    if not solved:
        return []
    steps = [r["step"] for r in solved]
    n = len(steps)
    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.10, right=0.90)
    style.clean(ax, left=True)
    ends = []
    for v, c in zip(["Y", "C", "K", "L"], style.CATEGORICAL):
        ys = [r["macro"].get(v) for r in solved]
        ax.plot(range(n), ys, marker="o", color=c, zorder=2)
        ends.append((n - 1, ys[-1], v, c))
    style.zero_line(ax)
    style.label_ends(ax, ends)
    ax.set_ylim(-ylim, ylim)
    ax.set_xlim(-0.3, n - 1 + 0.5)
    ax.set_xticks(range(n))
    ax.set_xticklabels(steps, rotation=15, ha="right")
    ax.set_ylabel("change vs baseline (%)")
    finite = [(abs(y), y, v) for (_x, y, v, _c) in ends if y is not None]
    if finite:
        _, mval, mvar = max(finite)
        ax.annotate(f"largest move: {mval:+.2f}% ({mvar})",
                    (0.015, 0.04), xycoords="axes fraction", fontsize=8.5, color=style.SUB, va="bottom")
    style.title_block(fig, title="Macro aggregates vs baseline",
                      subtitle="Change vs baseline (%), fixed axis  ·  Y output, C consumption, K capital, L labor",
                      source=f"{_SRC}.  {note}" if note else _SRC, kicker="macro aggregates", top=0.965)
    return [style.save(fig, os.path.join(out_dir, "macro_honest.png"))]


# --- the physical energy side (a CLEWS linkage must show the energy system) -------

def energy_physical(country, out_dir):
    """CLEWS emissions, reform vs baseline (the transition's physical signal), lines
    direct-labeled and the avoided-emissions wedge called out."""
    from . import signals

    os.makedirs(out_dir, exist_ok=True)
    try:
        eb = signals.emissions_by_year(country.scenario.base_dir, country)
        er = signals.emissions_by_year(country.scenario.reform_dir, country)
    except Exception as e:  # noqa: BLE001
        print(f"[figures] energy_physical skipped: {type(e).__name__}: {e}")
        return []
    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.15, left=0.11, right=0.88)
    style.clean(ax)
    erb = eb.reindex(er.index)
    ax.plot(eb.index, eb.values, color=style.MUTE, zorder=2)
    ax.plot(er.index, er.values, color=style.GAIN, zorder=3)
    ax.fill_between(er.index, erb.values, er.values, color=style.GAIN, alpha=0.12, zorder=1)
    style.label_ends(ax, [(eb.index[-1], eb.values[-1], "baseline", style.MUTE),
                          (er.index[-1], er.values[-1], "reform", style.GAIN)])
    ax.set_xlim(right=float(er.index[-1]) + (float(er.index[-1]) - float(er.index[0])) * 0.13)
    ax.set_ylabel(f"emissions ({country.co2_emission})")
    avoided = float(np.nansum((erb.values - er.values)))
    if np.isfinite(avoided) and abs(avoided) > 0:
        ymid = float(er.index[len(er) // 2])
        yv = float(np.nanmean([erb.values[len(er) // 2], er.values[len(er) // 2]]))
        word = "avoided" if avoided > 0 else "additional"
        ax.annotate(f"cumulative {word}\n≈ {abs(avoided):,.0f} {country.co2_emission}",
                    (ymid, yv), xytext=(6, 18), textcoords="offset points",
                    fontsize=8.5, color=style.TEAL, fontweight="medium")
    rel = style.direction(avoided if np.isfinite(avoided) else 0.0,
                          up="below", down="above", flat="≈")
    style.title_block(fig, title=f"Reform emissions {rel} baseline",
                      subtitle="Energy-system emissions, baseline vs reform",
                      source=_SRC, kicker="energy system", top=0.965)
    return [style.save(fig, os.path.join(out_dir, "emissions_path.png"))]


# --- table -----------------------------------------------------------------------

def across_steps_table(layered, path):
    solved = [r for r in layered if "macro" in r]
    if not solved:
        return None
    J = len(solved[0]["consumption_by_J"])
    lab = _labels(J)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "energy_demand_pct", "Y_pct", "C_pct", "K_pct", "L_pct",
                    "govt_revenue_pct"] + [f"consumption_{x}" for x in lab])
        for r in solved:
            w.writerow([r["step"], r["energy_demand_pct"]] + [r["macro"].get(v) for v in ("Y", "C", "K", "L")]
                       + [r["fiscal"]["cons_tax_revenue_pct"]] + r["consumption_by_J"])
    return path


def og_default_outputs(base_dir, reform_dir, out_dir, start_year=None, plots=False):
    """OG-Core's own macro_table (always) + plot_all (only if plots=True -- most of its 31
    default plots are coincident-line noise for a coupled run, so off by default)."""
    from ogcore import output_tables as ot
    from ogcore.utils import safe_read_pickle

    os.makedirs(out_dir, exist_ok=True)
    try:
        bt = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
        bp = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
        rt = safe_read_pickle(os.path.join(reform_dir, "TPI", "TPI_vars.pkl"))
        rp = safe_read_pickle(os.path.join(reform_dir, "model_params.pkl"))
        ot.macro_table(bt, bp, reform_tpi=rt, reform_params=rp, var_list=["Y", "C", "K", "L", "r", "w"],
                       output_type="pct_diff", num_years=10, start_year=start_year or bp.start_year
                       ).to_csv(os.path.join(out_dir, "og_macro_table.csv"))
    except Exception as e:  # noqa: BLE001
        print(f"[figures] og macro_table skipped: {type(e).__name__}: {e}")
    if plots:
        from ogcore import output_plots as op
        try:
            op.plot_all(base_dir, reform_dir, os.path.join(out_dir, "og_plots"))
        except Exception as e:  # noqa: BLE001
            print(f"[figures] og plot_all skipped: {type(e).__name__}: {e}")
    return out_dir
