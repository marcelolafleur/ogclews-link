"""Regenerate every figure for an existing across-steps run from the pickles already on disk
-- no model solve. Use to iterate on figure STYLE without re-running OG-Core.

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/regen_figures.py
"""
from __future__ import annotations

import json
import os

from ogcore.utils import safe_read_pickle

from ogclews_link import channels, figures, report_html  # noqa: F401 (channels registers)
from ogclews_link.country import PHL

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/across_steps"
NOTE = ("Illustrative: +20% energy-price wedge (a cost-index proxy, not the CLEWS dual); "
        "investment/carbon magnitudes uncalibrated; carbon revenue not recycled.")


def _tpi(label):
    p = os.path.join(OUT, label, "TPI", "TPI_vars.pkl")
    return safe_read_pickle(p) if os.path.isfile(p) else None


def main():
    ie = PHL.concordance.energy_good_index
    layered = json.load(open(os.path.join(OUT, "layered_results.json")))
    fig_dir = os.path.join(OUT, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    figures.across_steps_waterfall(layered, fig_dir, note=NOTE)
    figures.macro_honest(layered, fig_dir, note=NOTE)
    figures.energy_physical(PHL, fig_dir)
    figures.across_steps_table(layered, os.path.join(fig_dir, "across_steps_summary.csv"))
    report_html.write_html_report(layered, os.path.join(OUT, "report.html"))

    base_tpi = _tpi("baseline")
    try:
        factor = float(safe_read_pickle(os.path.join(OUT, "baseline", "SS", "SS_vars.pkl"))["factor"])
    except Exception:  # noqa: BLE001
        factor = None

    made = []
    for r in layered:
        label = r.get("step")
        if "macro" not in r or label == "baseline":
            continue
        reform_tpi = _tpi(label)
        if base_tpi is None or reform_tpi is None:
            print(f"  (skip incidence for {label!r}: pickle missing)")
            continue
        sdir = os.path.join(OUT, label, "figures")
        figures.incidence_hero(base_tpi, reform_tpi, ie, sdir,
                               title=f"{PHL.name}: {label}", note=NOTE, factor=factor)
        made.append(label)
    print(f"Regenerated figures in {fig_dir}/ + incidence for: {made}")


if __name__ == "__main__":
    main()
