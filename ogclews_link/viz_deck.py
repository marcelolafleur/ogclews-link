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
    """A full-figure text page for figure-coord text. The draw callback writes via fig.text only
    (no axis is used), so we add none -- that lets savefig.bbox='tight' crop the canvas to the
    text block instead of leaving a large empty band of unused page. Returns the saved path in a
    one-element list (the builder contract)."""
    os.makedirs(out_dir, exist_ok=True)
    fig = plt.figure(figsize=figsize)
    draw(fig, None)
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
            subtitle="The model setup behind the figures -- the policies layered in, the income"
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
            line(f"Households are split into {len(groups)} groups by how much they earn over"
                 " their lifetime, poorest to richest; brackets are slices of the population,"
                 " with the richest 1% in their own group:")
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
        # Credit only -- the full caveat is already spelled out in the Assumptions section above.
        fig.text(x, y, style.source_line(), fontsize=8.5, color=style.MUTE,
                 ha="left", va="top", wrap=True)

    return _text_page(out_dir, name, draw=draw)


# --- (2) results-by-step summary table -------------------------------------------

def _marginal(cur, prev):
    """Marginal contribution of a step: the column-wise change from the previous step's cumulative
    values (the first step's previous is baseline = 0). None where either side is absent."""
    return [None if c is None or p is None else c - p for c, p in zip(cur, prev)]


def summary_table(layered, out_dir, *, note=None, name="summary_table"):
    """The across-steps results as a table-as-figure: columns Y%, C%, K%, L%, energy demand %,
    cons-tax revenue % (same field selection as figures.across_steps_table's CSV). The stored
    step values are CUMULATIVE (each step layered on the last), so each printed row is the step's
    MARGINAL contribution (this step's cumulative minus the previous step's) and a final Total row
    restates the full-reform cumulative -- the marginals sum to it. Values are the average over the
    first 10 transition years (the run's macro_pct_diff window), not a steady-state level.
    Numeric cells use a single neutral ink; the +/- sign carries direction, color carries no
    good/bad meaning (so falling energy demand, the policy goal, never reads as "bad")."""
    solved = _solved(layered)
    if not solved:
        return []
    os.makedirs(out_dir, exist_ok=True)

    col_labels = ["step", "Output %", "Consumption %", "Capital %", "Labor %",
                  "Energy demand %", "Consumption-tax revenue %"]

    def _cumvals(r):
        macro = r.get("macro", {}) or {}
        fiscal = r.get("fiscal", {}) or {}
        return [macro.get("Y"), macro.get("C"), macro.get("K"), macro.get("L"),
                r.get("energy_demand_pct"), fiscal.get("cons_tax_revenue_pct")]

    cum = [_cumvals(r) for r in solved]
    rows, prev = [], [0.0] * len(col_labels[1:])
    for r, cv in zip(solved, cum):
        rows.append([str(r.get("step", ""))] + [_fmt_pct(v) for v in _marginal(cv, prev)])
        prev = cv
    # Total = the full-reform cumulative (the last step's stored values; equals the marginal sum).
    total_idx = len(rows) + 1  # +1 for the header row
    rows.append(["All policies (total)"] + [_fmt_pct(v) for v in cum[-1]])

    fig, ax = plt.subplots(figsize=(10.0, 1.4 + 0.62 * (len(rows) + 1)))
    fig.subplots_adjust(top=0.74, bottom=0.10, left=0.045, right=0.965)
    ax.set_axis_off()

    ncols = len(col_labels)
    # bbox=[0,0,1,1] makes the table fill its axes, so it sits directly under the subtitle with no
    # tall empty band from vertical centering. Column widths still size to content below.
    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc="right", bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    # Size each column to its widest cell so the spelled-out headers (e.g. "Consumption-tax
    # revenue %") get the room they need instead of colliding with the neighbour.
    table.auto_set_column_width(col=list(range(ncols)))
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
        # Numeric body cells carry no good/bad color encoding -- the +/- sign in the text
        # already shows direction. A single neutral ink keeps falling energy demand (the
        # policy goal) from reading as "bad".
        cell.set_text_props(color=style.INK)
        if rr == total_idx:  # the Total row: bold, set off by a rule above
            cell.set_text_props(color=style.INK, fontweight="bold")
            cell.visible_edges = "T"
            cell.set_linewidth(1.0)
            cell.set_edgecolor("#333333")

    # subtle banding for row legibility (data-ink stays low: faint, behind text); skip the Total row
    for rr in range(1, len(rows) + 1):
        if rr % 2 == 0 and rr != total_idx:
            for cc in range(ncols):
                table[(rr, cc)].set_facecolor("#FAFAFA")

    style.title_block(
        fig, title="What each policy step contributes",
        subtitle="Average % change vs baseline over the first 10 years  ·  each row is that policy's "
                 "own (marginal) contribution; the last line is all policies combined",
        source=style.source_line(note), kicker="summary table", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- (3) cover page --------------------------------------------------------------

def cover_page(layered, country, fig_titles, out_dir, *, note=None, name="cover"):
    """The deck's title page: country name + scenario headline (country.name only -- no result
    word), and a contents list of the section/figure titles passed in via `fig_titles` (a list of
    strings). States no result. If `fig_titles` is empty, just renders the cover."""
    cname = getattr(country, "name", None) or "country"
    titles = [str(t) for t in (fig_titles or []) if str(t).strip()]
    titles = ["Welfare (who wins and loses)" if t == "Welfare (CEV)" else t
              for t in titles]

    def draw(fig, ax):
        style.title_block(
            fig,
            title=f"{cname}: coupled OG-Core x CLEWS scenario",
            subtitle="An economy-wide model of households over their whole life, coupled to an"
                     " energy, land and water system.",
            kicker="scenario deck", top=0.965)

        x, y = 0.045, 0.80

        def para(text, *, bold=False, color=style.SUB, size=10.5, gap=0.012):
            nonlocal y
            for chunk in textwrap.wrap(text, 96) or [""]:
                fig.text(x, y, chunk, fontsize=size, color=color,
                         fontweight="bold" if bold else "normal", ha="left", va="top")
                y -= 0.031
            y -= gap

        # Plain-language statement of the scenario, with the health channel spelled out.
        para("The scenario", bold=True, size=11.5, color=style.INK)
        para("Four policies are layered onto the economy, one at a time: a higher energy price, "
             "clean-energy investment, a carbon tax, and a health channel.")
        para("The health channel: cleaner air means fewer pollution deaths and less illness, so "
             "people live and work longer -- and this run adds that to the economy.")
        y -= 0.020

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

        # Source rides just below the contents (not pinned to the page bottom) so the tight-crop
        # fits the cover to its content instead of leaving a tall empty band beneath it.
        fig.text(x, y - 0.03, style.source_line(note), fontsize=8, color=style.MUTE,
                 ha="left", va="top", wrap=True)

    return _text_page(out_dir, name, draw=draw)
