"""Named, reproducible experiments -- DERIVED from the single-source scenario catalog
(ogclews_link/scenario_catalog.json, via scenario_catalog.py). Edit the templates THERE, not here.
Run with:  python -m ogclews_link run <name>   (see `python -m ogclews_link list`).
"""
from __future__ import annotations

from . import scenario_catalog as _sc
from .framework import Experiment

_CATALOG = _sc.load_catalog()


def _channels(items):
    """Catalog form [{id: opts}, ...] -> framework form [(id, opts), ...]."""
    out = []
    for item in items:
        (cid, opts), = item.items()
        out.append((cid, dict(opts or {})))
    return out


# Single-run templates -> the named EXPERIMENTS dict (the layered one becomes ACROSS_STEPS below).
EXPERIMENTS = {
    name: Experiment(name, _channels(tpl["channels"]), tpl.get("question", ""))
    for name, tpl in _CATALOG["templates"].items()
    if tpl.get("run_mode") != "layered"
}

# The cumulative "across steps" layered template -> [(label, [(id, opts), ...]), ...]: each step adds
# one channel on top of the last, so the layered view shows what each channel contributes.
ACROSS_STEPS = [(layer["label"], _channels(layer["channels"]))
                for layer in _CATALOG["templates"]["across_steps"]["layers"]]


def get(name: str) -> Experiment:
    return EXPERIMENTS[name]


def names() -> list[str]:
    return list(EXPERIMENTS)
