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
        "investment", [("investment", {"target": "alpha_I"})],
        "PUBLIC-infrastructure (grid/T&D) capex -> alpha_I -> K_g. NB: PHL/PEP has ~0 grid-capex delta "
        "(the transition is generation-side), so this contributes ~nothing here; private generation "
        "capex's macro effect lives in the energy channel, a capex subsidy in set_investment_incentive."),

    # #2b energy gamma (capital share) -> a factor-mix / energy-PRICE lever (NOT crowding-out)
    "capital_intensity": Experiment(
        "capital_intensity", [("capital_intensity", {})],
        "A factor-SHARE / energy-PRICE lever: a PERMANENT rise in the energy industry's capital exponent "
        "gamma (calibrated from the CLEWS reform/base power-fleet capital-cost-share ratio, first-decade "
        "window). VERIFIED (PHL M=4) this is NOT crowding-out: with eps=1 and a small, demand-inelastic "
        "energy good, raising gamma makes electricity CHEAPER (price ~-24%) so energy CAPITAL FALLS "
        "(~-14%) with r flat -- a lens on the energy price and the capital/labor income split. The "
        "capital-DEMAND ('energy needs capital') story is the energy_capex channel."),

    # #2c energy capex incentive (ITC) -> draws capital INTO energy (the capital-DEMAND lever)
    "energy_capex": Experiment(
        "energy_capex", [("energy_capex", {"inv_tax_credit": 0.20})],
        "The capex-heavy generation buildout financed by an investment tax credit: it lowers the energy "
        "industry's cost of capital, drawing private capital INTO energy (verified +5% energy K, paid via "
        "the public budget). The capital-DEMAND counterpart to capital_intensity (gamma); at PHL's small "
        "electricity scale it reallocates capital into energy without crowding other industries out."),

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

    # #4 OG interest rate -> CLEWS DiscountRate, IN ISOLATION (forward emit plumbing)
    "discount_rate": Experiment(
        "discount_rate", [("discount_rate", {})],
        "Forward (OG->CLEWS) in isolation: OG interest rate -> CLEWS DiscountRate input. Tests the "
        "emit plumbing/format on the baseline solve; the reform delta is exercised in 'forward'/'full'."),

    # #6 OG industry output -> CLEWS demand scaling, IN ISOLATION (forward emit plumbing)
    "demand": Experiment(
        "demand", [("demand", {"driver": "Y_m"})],
        "Forward (OG->CLEWS) in isolation: OG industry output Y_m -> CLEWS demand scaling. Tests the "
        "emit plumbing/format; the reform delta is exercised in 'forward'/'full'."),

    # #5 emissions -> health -> demographics
    "health": Experiment(
        "health", [("health", {})],
        "CLEWS PM2.5 emissions change -> calibrated per-country dose-response (M = energy mass share x "
        "CRF elasticity, data/pm25_health.json; PHL ~0.08, NOT 1:1) -> OG mortality/productivity."),

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

    # composed with REAL data: CLEWS cost-of-electricity index for the energy price + GBD health
    "full_real": Experiment(
        "full_real",
        [("energy_price", {"price_source": "clews_cost_index", "recycle": True}),
         ("investment", {"target": "alpha_I"}),
         ("carbon", {"carbon_price": 50.0, "apply_to_og": False}),
         ("health", {}),
         ("discount_rate", {}),
         ("demand", {"driver": "Y_m"})],
        "REAL-data full soft-link: energy price from the CLEWS cost-of-electricity index (PEP vs Base, "
        "~-3.8% -- cheaper power), health from the GBD ambient-PM2.5 export (PHL ~44k deaths, real age "
        "profile), plus investment/carbon/discount_rate/demand. The realistic coupled run -- vs 'full', "
        "which uses the +20% stand-in and placeholder health."),
}


# Cumulative "across steps" sequence: each step adds one channel on top of the last, so the
# layered view shows what each channel contributes. Steps 2-4 use ILLUSTRATIVE magnitudes
# (investment scaled, small carbon intensity) pending the currency/deflator bridge -- the point
# is the composition, not calibrated policy numbers.
_EP = ("energy_price", {"shock": 0.20})
# public-infrastructure (grid/T&D) only; ~0 for PHL/PEP (generation-side transition), so the
# "+ investment" step below contributes ~nothing -- the generation capex's effect is in the energy step.
_INV = ("investment", {"target": "alpha_I", "scale": 0.3, "smooth_years": 5})
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
