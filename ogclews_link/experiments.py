"""Named, reproducible experiments -- one per next-step channel, plus composed ones.
Run with:  python -m ogclews_link run <name>  (see `python -m ogclews_link list`).
"""
from __future__ import annotations

from .framework import Experiment

EXPERIMENTS = {
    # #1 mechanism: does household energy demand fall to an energy price?
    "energy_price": Experiment(
        "energy_price", [("energy_price", {"shock": 0.20})],
        "Controlled +20% energy price; the demand-response mechanism (no recycling, c_min=0)."),

    # #1b the clean, interpretable distributional result
    "clean_incidence": Experiment(
        "clean_incidence",
        [("energy_price", {"shock": 0.20, "recycle": True, "energy_cmin": 0.005})],
        "Energy price with revenue recycled (removes the tax artifact) AND energy c_min>0 "
        "(necessity -> differential exposure): the textbook regressive incidence. "
        "NB: energy_cmin must be calibrated below every group's baseline energy consumption."),

    # #2 transition investment -> public capital -> crowding-out, debt
    "investment": Experiment(
        "investment", [("investment", {"target": "alpha_I", "public_only": False})],
        "CLEWS power capex increment -> OG public investment (alpha_I); crowding-out + debt cost."),

    # #3 carbon price -> OG fiscal revenue + CLEWS EmissionsPenalty (one price, both sides)
    "carbon": Experiment(
        "carbon", [("carbon", {"carbon_price": 50.0, "recycle": True})],
        "Carbon price as a shared policy lever: OG consumption-side tax (recycled) + CLEWS penalty."),

    # #4 + #6 forward direction: OG results -> CLEWS inputs (discount rate, demand)
    "forward": Experiment(
        "forward",
        [("energy_price", {"shock": 0.20}), ("discount_rate", {}), ("demand", {"driver": "Y_m"})],
        "An energy-price reform that also emits CLEWS inputs: OG rate -> DiscountRate, "
        "OG activity -> demand scaling (the producer side of loop closure)."),

    # #5 emissions -> health -> demographics
    "health": Experiment(
        "health", [("health", {})],
        "CLEWS emissions change -> illustrative dose-response -> OG mortality/productivity."),

    # composed: a full single-pass soft link
    "full": Experiment(
        "full",
        [("energy_price", {"shock": 0.20, "recycle": True}),
         ("investment", {"target": "alpha_I"}),
         ("carbon", {"carbon_price": 50.0, "apply_to_og": False}),  # carbon on CLEWS side only here
         ("health", {}),
         ("discount_rate", {}),
         ("demand", {"driver": "Y_m"})],
        "All channels in one pass: CLEWS->OG (price, investment, health) + OG->CLEWS "
        "(discount rate, demand) + carbon to CLEWS. The full disciplined soft-link step."),
}


# Cumulative "across steps" sequence: each step adds one channel on top of the last, so the
# layered view shows what each channel contributes. Steps 2-4 use ILLUSTRATIVE magnitudes
# (investment scaled, small carbon intensity) pending the currency/deflator bridge -- the point
# is the composition, not calibrated policy numbers.
_EP = ("energy_price", {"shock": 0.20})
_INV = ("investment", {"target": "alpha_I", "public_only": False, "scale": 0.25})
_CARB = ("carbon", {"carbon_price": 50.0, "carbon_intensity": 0.002, "apply_to_og": True, "recycle": False})
_HEALTH = ("health", {})

ACROSS_STEPS = [
    ("energy price", [_EP]),
    ("+ investment", [_EP, _INV]),
    ("+ carbon", [_EP, _INV, _CARB]),
    ("+ health", [_EP, _INV, _CARB, _HEALTH]),
]


def get(name: str) -> Experiment:
    return EXPERIMENTS[name]


def names() -> list[str]:
    return list(EXPERIMENTS)
