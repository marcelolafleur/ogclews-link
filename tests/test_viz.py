"""Smoke tests for the viz subpackage: import-safety, theme install, and that a couple of figures
plus the index portal render to disk from synthetic data (no model solve). Run with:

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python tests/test_viz.py
"""
from __future__ import annotations

import os
import tempfile


def test_imports():
    from ogclews_link.viz import build, plots, report, style, tables  # noqa: F401
    from ogclews_link.viz import build_figures
    assert callable(build_figures)


def test_style_idempotent():
    from ogclews_link.viz import style
    style.apply()
    style.apply()  # idempotent
    import matplotlib.pyplot as plt
    assert plt.rcParams["figure.facecolor"] == "white"


def _layered():
    """A minimal layered-results stand-in: two solved steps with the fields the deck reads."""
    j = [-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3]
    def step(name, y):
        return {"step": name, "macro": {"Y": y, "C": -y, "K": y / 2, "L": y / 3},
                "consumption_by_J": j, "energy_by_J": j, "energy_demand_pct": -10.0 * y,
                "fiscal": {"cons_tax_revenue_pct": 2.0 * y}}
    return [step("energy price", 0.02), step("+ thing", 0.05)]


def test_waterfall_renders():
    from ogclews_link.viz import plots
    saved = plots.across_steps_waterfall(_layered(), tempfile.mkdtemp())
    assert saved and all(os.path.isfile(p) for p in saved)


def test_summary_table_renders():
    from ogclews_link.viz import tables
    saved = tables.summary_table(_layered(), tempfile.mkdtemp())
    assert saved and os.path.isfile(saved[0])


def test_index_renders():
    from ogclews_link.viz import report
    d = tempfile.mkdtemp()
    figs = os.path.join(d, "figures")
    os.makedirs(figs)
    open(os.path.join(figs, "summary_table.png"), "wb").write(b"\x89PNG\r\n")  # a figure to link
    out = report.write_index(figs, os.path.join(d, "index.html"),
                             [("Headline", ["summary_table"])])
    assert os.path.isfile(out) and "summary_table.png" in open(out).read()


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("ok", _name)
    print("all viz smoke tests passed")
