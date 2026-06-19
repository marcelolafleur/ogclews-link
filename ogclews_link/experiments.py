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

    # --- exploratory channels (channel-exploration lane; see NEW-CHANNELS-FEASIBILITY.md) ---

    # #7/#8 the financing contrast: same diaspora resource as household remittances vs a bond that
    # funds public investment. Run as two ARMS (not summed) and compare incidence/welfare.
    "remittances_boom": Experiment(
        "remittances_boom", [("remittances", {"shock_pct_gdp": 0.03, "concentrate_low_income": True})],
        "Remittances arm: +3pp-of-GDP remittance inflow to (low-income-tilted) households -- "
        "consumption support + income-effect labor-supply response (alpha_RM, eta_RM)."),
    "diaspora_bond_finance": Experiment(
        "diaspora_bond_finance",
        [("diaspora_bonds", {"issuance_pct_gdp": 0.02, "years": 10, "discount_bps": 100.0})],
        "Diaspora-bond arm: a 2%-GDP/yr issuance (100bps patriotic discount) funding public "
        "investment -- crowd-in vs future debt service (alpha_I, world rate)."),

    # #9 crop/food price -- the high-leverage regressive channel (food ~35.7% of consumption)
    "food_price": Experiment(
        "food_price",
        [("food_price", {"yield_loss": 0.10, "pass_through": 0.7, "route": "tau_c", "food_cmin": 0.02})],
        "A 10% climate crop-yield loss -> food-price wedge with a subsistence floor: regressive "
        "incidence on the food good (external IRRI/IFPRI driver; tau_c route)."),

    # #10 climate temperature damage (ABSOLUTE level shock -- see channel guardrail)
    "climate_damage": Experiment(
        "climate_damage", [("climate_damage", {"temp_rise": 2.0})],
        "+2 degC: heat-stress labor-productivity loss (e) + crop-TFP loss (Z[NatRes]). Absolute "
        "level shock -- honest only applied to baseline AND reform (not PEP-attributable)."),

    # #11 water stress -- the strongest live non-energy CLEWS signal (power-sector water +5-12x)
    "water_stress": Experiment(
        "water_stress", [("water_stress", {"route": "Z", "elasticity": 0.02})],
        "CLEWS power-sector water demand -> cost-push on the electricity industry's TFP "
        "(the transition's water footprint -- the largest non-energy reform signal)."),

    # #12 household cooking air pollution (HAP) -- inert in this scenario; needs a clean-cooking run
    "cooking_health": Experiment(
        "cooking_health", [("cooking_health", {})],
        "Household solid-fuel cooking -> HAP mortality via disease_pop (bimodal age profile). "
        "INERT in the live PEP pair (cooking unchanged) -- demonstrates the transform, flags the signal."),

    # #13 LDC graduation -- not applicable to PHL (no-op); shown for the framework's reach
    "ldc_graduation": Experiment(
        "ldc_graduation", [("ldc_graduation", {"acknowledge_non_ldc": True})],
        "Hypothetical LDC graduation (PHL is not an LDC): trade-preference loss + financing cost + "
        "ODA cut. acknowledge_non_ldc=True to run the illustrative transform."),

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
# finite (transition-only) + smoothed + gentle scale, so the cumulative steps converge
_INV = ("investment", {"target": "alpha_I", "public_only": False, "scale": 0.3, "smooth_years": 5})
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
