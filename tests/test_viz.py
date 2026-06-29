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


def _fake_cache(root, tag, concordance=None):
    """A minimal selectable baseline cache: _discover_baseline_cache only isfile-checks these."""
    cache = os.path.join(root, "_og_baseline_cache", tag)
    os.makedirs(os.path.join(cache, "SS"))
    open(os.path.join(cache, "model_params.pkl"), "wb").write(b"x")
    open(os.path.join(cache, "SS", "SS_vars.pkl"), "wb").write(b"x")
    if concordance is not None:
        import json
        with open(os.path.join(cache, "baseline_meta.json"), "w") as f:
            json.dump({"concordance": concordance}, f)
    return cache


def test_discover_baseline_cache_walks_up():
    """The cache lives at the run root; the experiment dir may be nested below it (any country/model)."""
    from ogclews_link.viz import build
    root = tempfile.mkdtemp()
    cache = _fake_cache(root, "og-x-1.0-calib")
    coupled = os.path.join(root, "coupled"); os.makedirs(coupled)        # cache one level up
    assert build._discover_baseline_cache(coupled, {}) == cache
    deep = os.path.join(root, "exp", "exp"); os.makedirs(deep)            # cache two levels up
    assert build._discover_baseline_cache(deep, {}) == cache
    assert build._discover_baseline_cache(tempfile.mkdtemp(), {}) is None  # none present -> None


def test_discover_baseline_cache_matches_concordance():
    """With several caches, prefer the one whose baseline_meta concordance matches the run manifest."""
    from ogclews_link.viz import build
    root = tempfile.mkdtemp()
    want = {"energy_industry_index": 2, "energy_good_index": 1, "unavailable": {}}
    _fake_cache(root, "og-x-1.0-other", concordance={"energy_good_index": 9})
    match = _fake_cache(root, "og-x-1.0-match", concordance=want)
    coupled = os.path.join(root, "coupled"); os.makedirs(coupled)
    assert build._discover_baseline_cache(coupled, {"concordance": want}) == match


def test_coupled_run_missing_inputs_raise():
    """The bridge fails loud (no silent empty deck) when the reform or baseline is absent."""
    from ogclews_link.viz import build
    from ogclews_link.country import PHL
    try:
        build.build_deck_from_coupled_run(tempfile.mkdtemp(), PHL)  # empty: no reform/, no cache
        raise AssertionError("expected SystemExit for a run with no reform/")
    except SystemExit:
        pass


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("ok", _name)
    print("all viz smoke tests passed")
