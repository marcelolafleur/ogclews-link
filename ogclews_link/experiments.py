"""Named experiments: each is a plain function ``exp(ctx, solve)`` that calls channels in order and
calls ``solve(ctx)`` at the point the reform is solved. Pre-solve channels (clews->og, policy) run
before solve(ctx); og->clews ``emit_`` channels run after. Run one with:
    python -m ogclews_link run <name>     (see `python -m ogclews_link list`).
The data SOURCE for each channel (a controlled number, the CLEWS cost index, the dual, GBD) is visible
right here in the call -- not encoded in the name.
"""
from __future__ import annotations

import numpy as np

from . import channels, signals


def _energy_share(ctx):
    """Electricity's value-share of the OG energy good (io_matrix[energy_good, energy_industry]).
    None if the country can't isolate electricity (a required port is unresolved) -- the dependent
    energy_price channel will then skip, so the None is never consumed."""
    p = ctx.og_reform
    con = ctx.concordance
    if con is None or con.energy_good_index is None or con.energy_industry_index is None:
        return None
    return float(np.asarray(p.io_matrix)[con.energy_good_index, con.energy_industry_index])


def _electricity_intensity(ctx):
    """The M-vector phi_j (electricity's input-cost share per industry) for the Option-A' cost-push,
    read LINK-SIDE from the country package's SAM + PROD_DICT (no package import). None if the registry,
    SAM, or PROD_DICT is unavailable, or the vector does not align to the model's M -> the cost_push
    channel then skips. Best-effort: any failure degrades to None rather than breaking the run."""
    try:
        from . import aggregation, discovery, registry
        src = registry.package_source_dir(registry.lookup(ctx.country, require_env=False))
        sam = discovery._read_sam(src)
        prod, _cons = discovery.read_package_dicts(src)
        if sam is None or not prod:
            return None
        phi = aggregation.input_intensity(sam, prod)
        return phi if phi.shape == (int(ctx.og_reform.M),) else None
    except Exception:  # noqa: BLE001 -- a missing/odd SAM or registry must not break the run
        return None


def _activity(ctx, driver="Y_m"):
    con = ctx.concordance
    idx = None if con is None else (
        con.energy_industry_index if driver == "Y_m" else con.energy_good_index)
    if idx is None:                      # electricity not isolable -> emit_energy_demand will skip
        return None
    return signals.activity_ratio(ctx.base_tpi, ctx.reform_tpi, driver=driver, og_index=idx)


def _public_capex(ctx, *, scale=1.0, smooth_years=1):
    c, p = ctx.country, ctx.og_reform
    return signals.public_capex_pct_gdp(c.scenario.base_dir, c.scenario.reform_dir, c,
                                        og_start_year=c.scenario.og_start_year, T=p.T,
                                        scale=scale, smooth_years=smooth_years)


# --- single-channel experiments -------------------------------------------------

def energy_price(ctx, solve):
    """Controlled +20% energy price; the demand-response mechanism (no recycling, c_min=0)."""
    channels.energy_price(ctx, price_ratio=1.20)
    solve(ctx)


# --- the three energy-price TRANSMISSIONS, same controlled +20% stimulus (for the comparison) -----
# tau_c wedge = ``energy_price`` above (consumption-tax wedge); the two below route the SAME +20%
# electricity-price change through PRODUCTION instead. See experiments/run_energy_price_comparison.py.

def energy_price_tfp(ctx, solve):
    """Option A: a controlled +20% electricity price via the electricity industry's TFP (Z), so OG-Core
    produces the price endogenously and propagates it through its own Leontief io_matrix + GE feedback."""
    channels.energy_price_tfp(ctx, price_ratio=1.20)
    solve(ctx)


def energy_cost_push(ctx, solve):
    """Option A': a controlled +20% electricity price as an inter-industry cost-push -- a per-industry
    TFP haircut weighted by electricity's input-cost share phi_j (from the SAM). Reduced-form proxy."""
    channels.energy_cost_push(ctx, price_ratio=1.20, electricity_intensity=_electricity_intensity(ctx))
    solve(ctx)


def clean_incidence(ctx, solve):
    """Energy price with revenue recycled + energy a necessity (c_min>0): the textbook regressive
    incidence. NB energy_cmin must be below every group's baseline energy consumption."""
    channels.energy_price(ctx, price_ratio=1.20, recycle_revenue_to_transfers=True,
                          energy_subsistence_floor=0.005)
    solve(ctx)


def investment(ctx, solve):
    """PUBLIC-infrastructure (grid/T&D) capex -> alpha_I -> K_g. PHL/PEP has ~0 grid-capex delta, so
    this contributes ~nothing here (the transition is generation-side)."""
    channels.investment(ctx, _public_capex(ctx))
    solve(ctx)


def capital_intensity(ctx, solve):
    """A factor-SHARE / energy-PRICE lever: a permanent rise in the energy industry's capital exponent
    gamma, calibrated from the CLEWS reform/base power-fleet capital-cost-share ratio (first decade)."""
    c = ctx.country
    win = (c.scenario.og_start_year, c.scenario.og_start_year + 9)
    cal = signals.capital_intensity_ratio(c.scenario.base_dir, c.scenario.reform_dir, c, window=win)
    channels.capital_intensity(ctx, energy_capital_share_multiplier=cal["ratio"])
    solve(ctx)


def energy_capex(ctx, solve):
    """The capex-heavy generation buildout financed by an investment tax credit: lowers the energy
    industry's cost of capital, drawing private capital INTO energy (the capital-DEMAND lever)."""
    channels.energy_capex(ctx, investment_tax_credit_rate=0.20)
    solve(ctx)


def carbon(ctx, solve):
    """Carbon price as a shared lever: OG consumption-side tax (recycled) + CLEWS EmissionsPenalty."""
    channels.carbon_tax(ctx, carbon_price_usd_per_tco2=50.0, recycle_revenue_to_transfers=True)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    solve(ctx)


def health(ctx, solve):
    """CLEWS PM2.5 emissions change -> calibrated per-country dose-response (M; PHL ~0.08, not 1:1)
    -> OG mortality/morbidity."""
    channels.health(ctx)
    solve(ctx)


# --- forward (og->clews) plumbing, in isolation ---------------------------------

def discount_rate(ctx, solve):
    """Forward (OG->CLEWS) in isolation: OG interest rate -> CLEWS DiscountRate. Tests the emit
    plumbing on the (unmodified-reform) solve; the reform delta is exercised in 'forward'/'coupled'."""
    solve(ctx)
    channels.emit_discount_rate(ctx)


def demand(ctx, solve):
    """Forward (OG->CLEWS) in isolation: OG industry output Y_m -> CLEWS demand scaling. Tests the emit
    plumbing/format; the reform delta is exercised in 'forward'/'coupled'."""
    solve(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), og_activity="sector_output")


# --- composed -------------------------------------------------------------------

def forward(ctx, solve):
    """An energy-price reform that also emits CLEWS inputs: OG rate -> DiscountRate, OG activity ->
    demand scaling (the producer side of loop closure)."""
    channels.energy_price(ctx, price_ratio=1.20)
    solve(ctx)
    channels.emit_discount_rate(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), og_activity="sector_output")


def coupled(ctx, solve):
    """The full coupled soft-link: energy price from CLEWS (the cost-of-electricity index if the curated
    workbook is present, else the OSeMOSYS commodity-balance dual on raw MUIOGO output -- 'auto') +
    public investment + carbon on the CLEWS side + GBD health, then OG rate/activity emitted back."""
    c, p = ctx.country, ctx.og_reform
    pr = signals.energy_price_ratio("auto", base_dir=c.scenario.base_dir,
                                    reform_dir=c.scenario.reform_dir, share=_energy_share(ctx),
                                    og_start_year=c.scenario.og_start_year, n=np.asarray(p.tau_c).shape[0],
                                    fuel=c.electricity_fuel)
    channels.energy_price(ctx, price_ratio=pr, recycle_revenue_to_transfers=True)
    channels.investment(ctx, _public_capex(ctx))
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)    # carbon priced on the CLEWS side only here
    channels.health(ctx)
    solve(ctx)
    channels.emit_discount_rate(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), og_activity="sector_output")


# --- cumulative "across steps": each step adds one channel on top of the last ----
# Steps 2-4 use ILLUSTRATIVE magnitudes (investment scaled, small carbon intensity) -- the point is the
# composition, not calibrated policy numbers.

def _across_energy(ctx, solve):
    channels.energy_price(ctx, price_ratio=1.20)
    solve(ctx)


def _across_investment(ctx, solve):
    channels.energy_price(ctx, price_ratio=1.20)
    channels.investment(ctx, _public_capex(ctx, scale=0.3, smooth_years=5))
    solve(ctx)


def _across_carbon(ctx, solve):
    channels.energy_price(ctx, price_ratio=1.20)
    channels.investment(ctx, _public_capex(ctx, scale=0.3, smooth_years=5))
    channels.carbon_tax(ctx, carbon_price_usd_per_tco2=50.0, carbon_per_energy_unit=0.002)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    solve(ctx)


def _across_health(ctx, solve):
    channels.energy_price(ctx, price_ratio=1.20)
    channels.investment(ctx, _public_capex(ctx, scale=0.3, smooth_years=5))
    channels.carbon_tax(ctx, carbon_price_usd_per_tco2=50.0, carbon_per_energy_unit=0.002)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    channels.health(ctx)
    solve(ctx)


ACROSS_STEPS = [
    ("energy price", _across_energy),
    ("+ investment", _across_investment),
    ("+ carbon", _across_carbon),
    ("+ health", _across_health),
]


# --- registry of runnable experiments (names for the CLI / battery dispatch) -----

_EXPERIMENTS = [energy_price, energy_price_tfp, energy_cost_push, clean_incidence, investment,
                capital_intensity, energy_capex, carbon, health, discount_rate, demand, forward, coupled]


def names() -> list[str]:
    return [fn.__name__ for fn in _EXPERIMENTS]


def get(name):
    for fn in _EXPERIMENTS:
        if fn.__name__ == name:
            return fn
    raise KeyError(f"no experiment {name!r}; available: {names()}")
