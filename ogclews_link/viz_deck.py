"""Deck chrome -- the text and table pages that frame the figure set as a readable deck,
built from the same style.py house theme as the charts:

  * methods_card  -- a full-figure text card: the channel/step sequence, the income-group
    definition, and the run's illustrative-assumptions caveats. Describes the setup only;
    asserts no finding.
  * summary_table -- the across-steps results as a table-as-figure: one row per solved step,
    macro Y/C/K/L %, energy-demand %, and consumption-tax-revenue %, sign-colored per cell.
    Exactly the columns figures.across_steps_table writes to CSV -- no new computation.
  * cover_page    -- the title page: country name + scenario, and a contents list of the
    section/figure titles in the deck. States no result.

These are PAGES, not plots: no data axes, no judgment words. Any number shown is read straight
from the passed-in records (the macro/fiscal/energy fields), never recomputed or characterized.
Editorial house theme; import-safe (Agg). Builders take the already-loaded layered list / country
config + out_dir + keyword-only note=None, name=...; they RETURN the list of saved paths.
"""
from __future__ import annotations

import os
import textwrap

import matplotlib

matplotlib.use("Agg")

from . import style  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402


# --- small shared helpers --------------------------------------------------------

def _solved(layered):
    """The records that carry a solved macro block, in run order (degrade to [] if none)."""
    return [r for r in (layered or []) if isinstance(r, dict) and "macro" in r]


def _fmt_pct(v):
    """Signed percent with a fixed 2 decimals; '--' when the field is absent. Normalizes
    -0.0 to 0.0 so a rounded-to-zero value never prints a spurious minus sign."""
    if v is None:
        return "--"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "--"
    if f == 0.0:
        f = 0.0
    return f"{f:+.2f}"


def _text_page(out_dir, name, *, draw, figsize=(8.4, 10.9)):
    """A full-figure text page: a single axis with all chrome removed, ready for figure-coord
    text. Returns the saved path in a one-element list (the builder contract)."""
    os.makedirs(out_dir, exist_ok=True)
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    draw(fig, ax)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- (1) methods & caveats card --------------------------------------------------

def methods_card(layered, country, out_dir, *, note=None, name="methods_card"):
    """A full-figure text card describing HOW to read the deck: the channel/step sequence (from
    the layered step names), the lifetime-income-group definition (style.income_labels), and the
    run's illustrative-assumptions caveats (the `note` string). Asserts no finding -- it states
    the setup and the assumptions only. Pure text reflow; no axes."""
    solved = _solved(layered)
    steps = [str(r.get("step", "")) for r in solved if r.get("step")]
    J = len(solved[0]["consumption_by_J"]) if solved and "consumption_by_J" in solved[0] else 0
    groups = style.income_labels(J) if J else []
    cname = getattr(country, "name", None)

    def draw(fig, ax):
        style.title_block(
            fig,
            title="How to read this deck",
            subtitle="The model setup behind the figures -- the channels layered in, the income"
                     " groups, and the assumptions.",
            kicker="methods & caveats", top=0.965)

        x, y, dy = 0.045, 0.80, 0.030
        sub_x = 0.065

        def heading(text):
            nonlocal y
            fig.text(x, y, text, fontsize=11.5, fontweight="bold", color=style.INK,
                     ha="left", va="top")
            y -= 0.034

        def line(text, color=style.SUB, size=10.0, wrap=92, indent=sub_x):
            nonlocal y
            for chunk in textwrap.wrap(text, wrap) or [""]:
                fig.text(indent, y, chunk, fontsize=size, color=color, ha="left", va="top")
                y -= dy
            y -= 0.004

        def gap():
            nonlocal y
            y -= 0.018

        # channel / step sequence
        heading("Channel steps")
        if steps:
            line("Each step layers one more linkage onto the one before; figures read left to"
                 " right in this order:")
            for i, s in enumerate(steps, 1):
                line(f"{i}.  {s}", color=style.INK, indent=sub_x + 0.012)
        else:
            line("(no solved steps found in this run)")
        gap()

        # income-group definition
        heading("Income groups")
        if groups:
            line(f"Households are split into {len(groups)} lifetime-income groups, ordered"
                 " poorest to richest. Bracket labels are population-share percentiles:")
            # Wrap the bracket labels on the same width budget as the other body lines, so a
            # non-default J (more groups) or wider labels stay on-page instead of running off.
            line("  ".join(groups), color=style.INK, indent=sub_x + 0.012)
        else:
            line("(income-group partition not available in this run)")
        gap()

        # assumptions / caveats
        heading("Assumptions & caveats")
        if note:
            line(str(note), color=style.SUB)
        else:
            line("Results are illustrative.", color=style.SUB)

        # Footer rides just below where the body text actually ended (not pinned to the page
        # bottom), so a short card doesn't leave a large empty band above the credit line.
        y -= 0.012
        if cname:
            fig.text(x, y, f"Scenario country: {cname}.", fontsize=9.5,
                     color=style.MUTE, ha="left", va="top")
            y -= 0.026
        fig.text(x, y, style.source_line(note), fontsize=8, color=style.MUTE,
                 ha="left", va="top")

    return _text_page(out_dir, name, draw=draw)


# --- (2) results-by-step summary table -------------------------------------------

def summary_table(layered, out_dir, *, note=None, name="summary_table"):
    """The across-steps results as a table-as-figure: one row per solved step; columns Y%, C%,
    K%, L%, energy demand %, cons-tax revenue %. These are exactly the columns
    figures.across_steps_table writes to CSV -- the same field selection, no new computation. Each
    numeric cell is text-colored by its sign (style.signed convention: gains blue, losses red)."""
    solved = _solved(layered)
    if not solved:
        return []
    os.makedirs(out_dir, exist_ok=True)

    col_labels = ["step", "Y %", "C %", "K %", "L %", "energy demand %", "cons-tax revenue %"]
    rows, cell_vals = [], []
    for r in solved:
        macro = r.get("macro", {}) or {}
        fiscal = r.get("fiscal", {}) or {}
        vals = [macro.get("Y"), macro.get("C"), macro.get("K"), macro.get("L"),
                r.get("energy_demand_pct"), fiscal.get("cons_tax_revenue_pct")]
        rows.append([str(r.get("step", ""))] + [_fmt_pct(v) for v in vals])
        cell_vals.append(vals)

    fig, ax = plt.subplots(figsize=(9.6, 1.0 + 0.52 * (len(rows) + 1)))
    fig.subplots_adjust(top=0.74, bottom=0.10, left=0.045, right=0.965)
    ax.set_axis_off()

    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc="right", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.55)

    ncols = len(col_labels)
    for (rr, cc), cell in table.get_celld().items():
        cell.set_edgecolor(style.GRID)
        cell.set_linewidth(0.7)
        if cc == 0:
            cell.set_text_props(ha="left")
            cell.PAD = 0.04
        if rr == 0:  # header row
            cell.set_text_props(color=style.INK, fontweight="bold")
            cell.set_facecolor("white")
            cell.visible_edges = "B"  # underline only
            cell.set_linewidth(1.0)
            cell.set_edgecolor("#333333")
            continue
        cell.visible_edges = "B"
        # sign-color the numeric body cells (cc>=1) by their underlying value
        if cc >= 1:
            v = cell_vals[rr - 1][cc - 1]
            if v is not None:
                try:
                    f = float(v)
                except (TypeError, ValueError):
                    f = 0.0
                color = style.LOSS if f < 0 else (style.GAIN if f > 0 else style.SUB)
                cell.set_text_props(color=color)
        else:
            cell.set_text_props(color=style.INK)

    # subtle banding for row legibility (data-ink stays low: faint, behind text)
    for rr in range(1, len(rows) + 1):
        if rr % 2 == 0:
            for cc in range(ncols):
                table[(rr, cc)].set_facecolor("#FAFAFA")

    style.title_block(
        fig, title="Results by channel step",
        subtitle="One row per solved step  ·  change vs baseline (%)  ·  blue positive, red negative",
        source=style.source_line(note), kicker="summary table", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- (3) cover page --------------------------------------------------------------

def cover_page(layered, country, fig_titles, out_dir, *, note=None, name="cover"):
    """The deck's title page: country name + scenario headline (country.name only -- no result
    word), and a contents list of the section/figure titles passed in via `fig_titles` (a list of
    strings). States no result. If `fig_titles` is empty, just renders the cover."""
    cname = getattr(country, "name", None) or "country"
    titles = [str(t) for t in (fig_titles or []) if str(t).strip()]

    def draw(fig, ax):
        style.title_block(
            fig,
            title=f"{cname}: coupled OG-Core x CLEWS scenario",
            subtitle="An OLG macro model (OG-Core) coupled to an energy-land-water system (CLEWS),"
                     " shown channel by channel.",
            kicker="scenario deck", top=0.965)

        x, y = 0.045, 0.78
        if titles:
            fig.text(x, y, "Contents", fontsize=11.5, fontweight="bold", color=style.INK,
                     ha="left", va="top")
            y -= 0.040
            for i, t in enumerate(titles, 1):
                wrapped = textwrap.wrap(t, 84) or [""]
                fig.text(0.065, y, f"{i:>2}.", fontsize=10.0, color=style.MUTE,
                         ha="left", va="top")
                for k, chunk in enumerate(wrapped):
                    fig.text(0.105, y, chunk, fontsize=10.5,
                             color=style.INK if k == 0 else style.SUB, ha="left", va="top")
                    y -= 0.030
                y -= 0.006

        fig.text(x, 0.020, style.source_line(note), fontsize=8, color=style.MUTE,
                 ha="left", va="bottom")

    return _text_page(out_dir, name, draw=draw)
