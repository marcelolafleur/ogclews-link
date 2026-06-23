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


def _energy_share(ctx) -> float:
    """Electricity's value-share of the OG energy good (io_matrix[energy_good, energy_industry])."""
    c, p = ctx.country, ctx.og_reform
    return float(np.asarray(p.io_matrix)[c.concordance.energy_good_index,
                                          c.concordance.energy_industry_index])


def _activity(ctx, driver="Y_m"):
    c = ctx.country
    idx = (c.concordance.energy_industry_index if driver == "Y_m" else c.concordance.energy_good_index)
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


def clean_incidence(ctx, solve):
    """Energy price with revenue recycled + energy a necessity (c_min>0): the textbook regressive
    incidence. NB energy_cmin must be below every group's baseline energy consumption."""
    channels.energy_price(ctx, price_ratio=1.20, recycle=True, energy_cmin=0.005)
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
    channels.capital_intensity(ctx, gamma_scale=cal["ratio"])
    solve(ctx)


def energy_capex(ctx, solve):
    """The capex-heavy generation buildout financed by an investment tax credit: lowers the energy
    industry's cost of capital, drawing private capital INTO energy (the capital-DEMAND lever)."""
    channels.energy_capex(ctx, inv_tax_credit=0.20)
    solve(ctx)


def carbon(ctx, solve):
    """Carbon price as a shared lever: OG consumption-side tax (recycled) + CLEWS EmissionsPenalty."""
    channels.carbon_tax(ctx, carbon_price=50.0, recycle=True)
    channels.emit_carbon_penalty(ctx, carbon_price=50.0)
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
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), driver="Y_m")


# --- composed -------------------------------------------------------------------

def forward(ctx, solve):
    """An energy-price reform that also emits CLEWS inputs: OG rate -> DiscountRate, OG activity ->
    demand scaling (the producer side of loop closure)."""
    channels.energy_price(ctx, price_ratio=1.20)
    solve(ctx)
    channels.emit_discount_rate(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), driver="Y_m")


def coupled(ctx, solve):
    """The full coupled soft-link: energy price from the CLEWS cost-of-electricity index (recycled) +
    public investment + carbon on the CLEWS side + GBD health, then OG rate/activity emitted back."""
    c, p = ctx.country, ctx.og_reform
    pr = signals.energy_price_ratio("cost_index", base_dir=c.scenario.base_dir,
                                    reform_dir=c.scenario.reform_dir, share=_energy_share(ctx),
                                    og_start_year=c.scenario.og_start_year, n=np.asarray(p.tau_c).shape[0])
    channels.energy_price(ctx, price_ratio=pr, recycle=True)
    channels.investment(ctx, _public_capex(ctx))
    channels.emit_carbon_penalty(ctx, carbon_price=50.0)    # carbon priced on the CLEWS side only here
    channels.health(ctx)
    solve(ctx)
    channels.emit_discount_rate(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), driver="Y_m")


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
    channels.carbon_tax(ctx, carbon_price=50.0, carbon_intensity=0.002)
    channels.emit_carbon_penalty(ctx, carbon_price=50.0)
    solve(ctx)


def _across_health(ctx, solve):
    channels.energy_price(ctx, price_ratio=1.20)
    channels.investment(ctx, _public_capex(ctx, scale=0.3, smooth_years=5))
    channels.carbon_tax(ctx, carbon_price=50.0, carbon_intensity=0.002)
    channels.emit_carbon_penalty(ctx, carbon_price=50.0)
    channels.health(ctx)
    solve(ctx)


ACROSS_STEPS = [
    ("energy price", _across_energy),
    ("+ investment", _across_investment),
    ("+ carbon", _across_carbon),
    ("+ health", _across_health),
]


# --- registry of runnable experiments (names for the CLI / battery dispatch) -----

_EXPERIMENTS = [energy_price, clean_incidence, investment, capital_intensity, energy_capex,
                carbon, health, discount_rate, demand, forward, coupled]


def names() -> list[str]:
    return [fn.__name__ for fn in _EXPERIMENTS]


def get(name):
    for fn in _EXPERIMENTS:
        if fn.__name__ == name:
            return fn
    raise KeyError(f"no experiment {name!r}; available: {names()}")
