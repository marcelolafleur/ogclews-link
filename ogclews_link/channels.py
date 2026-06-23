"""The integration channels: plain functions, one per economically-grounded transform. Each takes
the coupling context ``ctx`` first (the mutable analogue of OG-Core's ``p``), then explicit levers,
reads/mutates ``ctx``, and records its own provenance via ``ctx.log(name, ...)``. All transforms
operate on a duck-typed Specifications (numpy attributes), so they are unit-testable without ogcore.

A channel takes the ALREADY-SOURCED value it needs (e.g. a price ratio); WHERE that value comes from
-- a controlled number, the CLEWS cost index, or the OSeMOSYS dual -- is the caller's choice, via the
signals.* helpers. og->clews channels carry an ``emit_`` prefix and run AFTER the reform solve.

Verified OG-Core mechanics (ogcore 0.16.x): G=alpha_G*Y, TR=alpha_T*Y, I_g=alpha_I*Y -> K_g -> CES
production; the consumption-tax wedge (1+tau_c_i)p_i enters the demand FOC, the budget, the composite
price, and books cons_tax_revenue. rho (T+S,S), e (T,S,J), chi_n (T+S,S), alpha_* (T+S,), tau_c (T+S,I).
Tail convention: parameters are length (T+S); indices T:T+S are the STEADY STATE anchoring TPI's
terminal condition. A PERMANENT policy fills the SS tail; a TEMPORARY transition tapers to baseline.
"""
from __future__ import annotations

import numpy as np

from . import health_profile, policy_levers, signals
from .signals import _fit


def _recycle_via_transfers(ctx, i_good: int, dtau_path) -> float | None:
    """Return the energy-tax revenue to households as a lump-sum transfer (TR=alpha_T*Y), isolating
    the price/substitution effect from the fiscal effect. FIRST-ORDER: revenue is estimated on BASELINE
    quantities (dtau * p_i * C_i), slightly overstating reform revenue. Fills the SS tail (permanent
    wedge). A sign-flipping recycle is floored at alpha_T>=0 (a transfer, not a tax)."""
    b = ctx.base_tpi
    if b is None:
        return None
    p = ctx.og_reform
    T = p.T
    Ci = np.asarray(b["C_i"])[:T, i_good]
    pi = np.asarray(b["p_i"])[:T, i_good]
    Y = np.asarray(b["Y"])[:T]
    bump = (_fit(dtau_path, T) * pi * Ci) / np.maximum(Y, 1e-12)
    aT = np.asarray(p.alpha_T, dtype=float)
    new_aT = aT + _fit(bump, aT.shape[0])
    if np.any(new_aT < 0):
        print("[guardrail] _recycle_via_transfers: bump would push alpha_T < 0 (a lump-sum tax on "
              "households); floored at 0. A negative recycle implies the closure instrument should change.")
        new_aT = np.maximum(new_aT, 0.0)
    p.alpha_T = new_aT
    return float(np.mean((new_aT - aT)[:10]))


# --- #1 energy price -> household demand (+ incidence) · clews->og ---------------

def energy_price(ctx, price_ratio, *, energy_cmin=0.0, recycle=False):
    """Energy price -> household demand + incidence (clews->og). A higher energy price reaches
    households as a tau_c wedge on the energy good; demand falls, the cost of living rises, and with a
    subsistence floor the incidence is regressive -- OG has no energy in production, so this is the
    only door. ``price_ratio`` is the ALREADY-SOURCED reform/base price ratio of the energy good: a
    scalar (e.g. 1.20 for a controlled +20%, applied undiluted) or a per-period path from
    signals.energy_price_ratio(kind='cost_index'|'dual', ...) (which dilutes by electricity's share).

    Mutates tau_c[:, energy] always; c_min[energy] if energy_cmin>0; alpha_T if recycle.
    """
    c = ctx.country
    i_e = c.concordance.energy_good_index
    p = ctx.og_reform
    tau = np.array(p.tau_c, dtype=float)
    before = tau[:, i_e].copy()
    tau[:, i_e] = _fit(price_ratio, tau.shape[0]) * (1.0 + tau[:, i_e]) - 1.0   # permanent: full tail
    p.tau_c = tau
    dtau = tau[:, i_e] - before
    if energy_cmin > 0:
        if ctx.base_tpi is not None:
            base_min = float(np.asarray(ctx.base_tpi["c_i"])[:, i_e].min())
            if energy_cmin > 0.5 * base_min:
                print(f"[guardrail] energy_cmin={energy_cmin} exceeds 50% of the minimum baseline "
                      f"per-household energy consumption ({base_min:.4f}); risks negative consumption "
                      f"/ a broken solve. Calibrate it lower.")
        cm = np.array(p.c_min, dtype=float)
        cm[i_e] = energy_cmin
        p.c_min = cm
    recycled = _recycle_via_transfers(ctx, i_e, dtau[:p.T]) if recycle else None
    return ctx.log("energy_price", tau_c_energy_0=float(tau[0, i_e]),
                   dtau_mean=float(dtau[:10].mean()), energy_cmin=energy_cmin,
                   recycled_pct_gdp=recycled)


# --- #2 public-infrastructure capex -> public capital (alpha_I -> K_g) · clews->og ---

def investment(ctx, capex_pct_gdp, *, target="alpha_I", persist=False):
    """Public-infrastructure (grid/T&D) capex -> public investment (clews->og). ``capex_pct_gdp`` is the
    ALREADY-SOURCED finite %-of-GDP capex flow path (signals.public_capex_pct_gdp), zero after the CLEWS
    horizon. PUBLIC infra only: alpha_I -> K_g lifts every industry's productivity via gamma_g. Private
    generation capex is NOT here -- its macro effect is the energy cost-push, and a capex subsidy is
    energy_capex. Mutates alpha_I (or alpha_bs_I, a no-op unless baseline_spending=True)."""
    p = ctx.og_reform
    path = np.asarray(capex_pct_gdp, dtype=float)
    if not np.any(np.abs(path) > 1e-12):
        print("[guardrail] investment: no PUBLIC-infrastructure (grid/T&D) capex delta in this scenario "
              "-- the public-investment channel contributes ~0. Private generation capex is NOT routed "
              "here; its effect belongs to the energy cost-push channel.")
    full = np.zeros(np.asarray(p.alpha_I).shape[0])
    full[:p.T] = path[:p.T]
    if persist:
        full = _fit(path[:p.T], full.shape[0])
    if np.max(path) > float(np.asarray(p.alpha_I)[0]):
        print(f"[guardrail] investment: peak alpha_I increment {np.max(path):.3f} > baseline alpha_I "
              f"{float(np.asarray(p.alpha_I)[0]):.3f} -- large public-investment shock; check the capex "
              f"source's units.deflator and smoothing.")
    if target == "alpha_I":
        p.alpha_I = np.asarray(p.alpha_I, dtype=float) + full
    else:
        if not bool(getattr(p, "baseline_spending", False)):
            print(f"[guardrail] investment target={target!r} writes alpha_bs_I, which OG-Core ignores "
                  f"unless baseline_spending=True (currently False) -- this shock will have NO effect.")
        p.alpha_bs_I = np.asarray(p.alpha_bs_I, dtype=float) * (1.0 + full)
    return ctx.log("investment", target=target, scope="public_infrastructure", persist=persist,
                   cumulative_pct_gdp=float(path.sum()), peak_pct_gdp=float(np.max(path)))


# --- #2b generation-mix capital intensity -> energy industry capital share (gamma) · clews->og ---

def capital_intensity(ctx, gamma_scale=None, *, gamma_target=None, labor_share_floor=0.05):
    """Energy industry's capital share gamma[m] -- a factor-SHARE / production-technology lever
    (clews->og), a permanent time-invariant shift (labor's share is the residual 1-gamma-gamma_g, which
    falls). ``gamma_scale`` is the ALREADY-SOURCED multiplicative shift (caller passes
    signals.capital_intensity_ratio(...)['ratio']); or pass an absolute gamma_target. VERIFIED (PHL M=4)
    this is NOT crowding-out: with the small, demand-inelastic energy good, raising gamma makes
    electricity CHEAPER (price ~-24%, output ~flat) so energy CAPITAL FALLS (~-14%) with r flat. The
    capital-draw-in story is energy_capex (ITC); gamma and the ITC give OPPOSITE signs on energy K."""
    c = ctx.country
    p = ctx.og_reform
    m = c.concordance.energy_industry_index
    prov = policy_levers.set_capital_intensity(
        p, m, gamma_target=gamma_target, gamma_scale=gamma_scale, labor_share_floor=labor_share_floor)
    if abs(prov["gamma_new"] - prov["gamma_old"]) < 1e-6:
        print("[guardrail] capital_intensity: gamma shift ~0 -- the reform generation mix is no more "
              "capital-intensive than baseline, so the channel is inert.")
    return ctx.log("capital_intensity", **prov)


# --- #2c energy capex incentive (ITC): cost-of-capital subsidy -> energy capital DEMAND · policy ---

def energy_capex(ctx, *, inv_tax_credit=0.20, delta_tau=None, tau_b_mult=None, phase_years=None):
    """Energy capex incentive (ITC) -> energy capital demand (policy). The capital-DEMAND counterpart to
    capital_intensity: an ITC lowers the energy industry's COST OF CAPITAL (inv_tax_credit enters
    firm.get_cost_of_capital; gamma does not), drawing capital INTO energy. VERIFIED (PHL M=4): energy K
    +5.0%, funded via the public budget. At PHL's small electricity scale this is capital REALLOCATION
    into energy, not economy-wide crowding-out. delta_tau (accelerated depreciation) and tau_b_mult (CIT
    multiplier) are two further separable firm-tax instruments, off by default."""
    c = ctx.country
    p = ctx.og_reform
    m = c.concordance.energy_industry_index
    prov = policy_levers.set_investment_incentive(
        p, m, inv_tax_credit=inv_tax_credit, delta_tau=delta_tau,
        tau_b_mult=tau_b_mult, phase_years=phase_years)
    prov["lever"] = "investment_tax_credit (cost-of-capital subsidy)"
    return ctx.log("energy_capex", **prov)


# --- #3 carbon price · policy (split: OG tax + CLEWS penalty) --------------------

def carbon_tax(ctx, *, carbon_price=50.0, carbon_intensity=0.002, recycle=False,
               allow_illustrative=False):
    """Carbon price as an OG consumption-side tax on the household energy good (policy). UNITS: the
    ad-valorem tau_c add-on = carbon-cost-per-unit-good / price-per-unit-good. carbon_price is USD/tCO2
    -> numeraire via units.deflator; carbon_intensity is tCO2 per unit of the OG energy good; base_pi is
    the good's price. At the default deflator=1.0 the MAGNITUDE is illustrative until calibrated. OG has
    no energy in PRODUCTION, so this prices only HOUSEHOLD energy (~1.4% of consumption). The CLEWS-side
    EmissionsPenalty is emit_carbon_penalty -- set the price ONCE and feed both."""
    c = ctx.country
    i_e = c.concordance.energy_good_index
    p = ctx.og_reform
    cp = _fit(carbon_price, p.T)
    base_pi = (np.asarray(ctx.base_tpi["p_i"])[:p.T, i_e] if ctx.base_tpi is not None
               else np.ones(p.T))
    cp_num = cp * float(getattr(c.units, "deflator", 1.0))      # USD/tCO2 -> numeraire/tCO2
    dtau = cp_num * carbon_intensity / np.maximum(base_pi, 1e-9)
    if float(dtau.mean()) > 1.0 and not allow_illustrative:
        raise ValueError(
            f"carbon_tax: implied mean tau_c add-on {dtau.mean():.2f} (>100%) on the energy good -- the "
            "USD->numeraire deflator (units.deflator) and/or carbon_intensity (tCO2 per unit of the OG "
            "energy good) are uncalibrated, so this is not a real ad-valorem rate. Calibrate them, or "
            "pass allow_illustrative=True to proceed with an explicitly illustrative magnitude.")
    tau = np.array(p.tau_c, dtype=float)
    tau[:, i_e] = tau[:, i_e] + _fit(dtau, tau.shape[0])         # permanent policy: full tail
    p.tau_c = tau
    prov = {"carbon_price_mean": float(cp.mean()),
            "og_base_note": "OG taxes household energy only (~1.4% of consumption); industrial carbon unpriced"}
    if recycle:
        prov["recycled_pct_gdp"] = _recycle_via_transfers(ctx, i_e, dtau)
    return ctx.log("carbon_tax", **prov)


def emit_carbon_penalty(ctx, *, carbon_price=50.0):
    """Carbon price as a CLEWS EmissionsPenalty artifact (policy, og->clews-style emit). The
    energy-system side of the same carbon price that carbon_tax applies to OG -- set the price ONCE and
    feed both sides; do not also infer a carbon price from a CLEWS shadow price back into OG."""
    c = ctx.country
    p = ctx.og_reform
    cp = _fit(carbon_price, p.T)
    ctx.clews_inputs["EmissionsPenalty"] = {
        "region": "RE1", "emission": c.co2_emission,
        "start_year": c.scenario.og_start_year, "value_by_period": cp.tolist()}
    return ctx.log("emit_carbon_penalty", carbon_price_mean=float(cp.mean()))


# --- #4 OG equilibrium rate -> CLEWS DiscountRate · og->clews (post-solve) -------

def emit_discount_rate(ctx, *, rate_key="r_p", scalar=True, region="RE1"):
    """OG equilibrium rate -> CLEWS DiscountRate (og->clews; run AFTER the reform solve). Harmonizes the
    energy model's discount rate to OG's market cost of capital r_p (not a separate social rate)."""
    if ctx.reform_tpi is None:
        raise ValueError("emit_discount_rate is post-solve and needs ctx.reform_tpi (the reform "
                         "equilibrium rate); it was None -- call it after the reform solve.")
    r = signals.og_interest_rate(ctx.reform_tpi, rate_key)
    rate = float(np.mean(r[:10])) if scalar else r.tolist()
    ctx.clews_inputs["DiscountRate"] = {"region": region, "rate": rate, "key": rate_key,
                                        "convention": "real; OG market cost of capital; period~annual if S=80"}
    return ctx.log("emit_discount_rate", rate_key=rate_key,
                   clews_discount_rate=rate if scalar else "path")


# --- #5 CLEWS emissions -> health -> demographics · clews->og --------------------

def health(ctx, *, excess_deaths=None, total_pollution_deaths=None, morbidity_response=0.01,
           affects=("mortality", "e"), profile_path=None, morbidity_profile=None,
           phase_years=5, prod_J=7, dose_response=None):
    """CLEWS PM2.5 emissions change -> calibrated dose-response -> OG mortality/morbidity (clews->og).
    Scales by the PM2.5 (not CO2e) reform/base emission ratio and the per-country multiplier M = energy
    mass share x CRF elasticity (country.pm25_dose_response; PHL ~0.082; ``dose_response`` overrides).
    Mortality -> a signed excess-deaths target driving the disease_pop demographic re-solve (rho, age
    profile from GBD; negative = lives saved); morbidity -> the effective-labour path e (the main output
    gain). Totals come from the country's GBD export -- no fabricated number is used."""
    c = ctx.country
    p = ctx.og_reform
    species = getattr(c, "health_emission", None)
    er = signals.emissions_ratio(c.scenario.base_dir, c.scenario.reform_dir, c, species=species)
    demis = float(np.nanmean(er.values[:10])) - 1.0       # <0 == reform is cleaner
    if not np.isfinite(demis):
        raise ValueError(f"health: emissions_ratio gave a non-finite change ({demis}); "
                         "check the CLEWS emissions files.")
    M = signals.pm25_dose_response(c, override=dose_response)
    gbd = getattr(c, "gbd_burden_csv", None)
    gloc = getattr(c, "name", None)
    gyr = int(getattr(c, "gbd_year", 2023))
    prov = {"emissions_change": demis, "emissions_species": species or c.co2_emission,
            "dose_response_M": M, "affects": list(affects), "gbd_source": bool(gbd)}
    if "mortality" in affects:
        if gbd and profile_path is None:
            profile = health_profile.build_profile_from_gbd(
                gbd, gloc, gyr, key_col="cause_name", key_value="All causes")
            if excess_deaths is None and total_pollution_deaths is None:
                total_pollution_deaths = health_profile.total_deaths_from_gbd(
                    gbd, gloc, gyr, key_col="cause_name", key_value="All causes")
            psrc = "GBD ambient-PM2.5 deaths-by-age"
        elif profile_path:
            profile = health_profile.load_profile(profile_path); psrc = "file"
        else:
            profile = health_profile.placeholder_profile()
            psrc = "PLACEHOLDER (no GBD profile; see DATA.md)"
        if excess_deaths is not None:
            target_src = "explicit excess_deaths"
        elif total_pollution_deaths is not None:
            excess_deaths = float(total_pollution_deaths) * M * demis    # total x dose-response x emissions
            target_src = ("GBD total x M x emissions change" if gbd else "explicit total x M x emissions change")
        else:
            raise ValueError("health mortality: no excess_deaths, no total_pollution_deaths, and no GBD "
                             "export to source the ambient-PM2.5 deaths total -- supply a GBD file "
                             "(country.gbd_burden_csv) or an explicit total. No fabricated default is used.")
        ctx.extras["health_shock"] = {"excess_deaths": float(excess_deaths), "profile": profile,
                                      "phase_years": phase_years, "rc_ss": c.rc_ss}
        prov["mortality_excess_deaths"] = float(excess_deaths)
        prov["target_source"] = target_src
        prov["profile_source"] = psrc
    if "e" in affects:
        if gbd and morbidity_profile is None:
            morbidity_profile = health_profile.build_morbidity_profile_from_gbd(gbd, gloc, gyr)
            morbidity_response = health_profile.morbidity_yld_rate_from_gbd(gbd, gloc, gyr)
            msrc = "GBD YLD-by-age (working-age causes)"
        else:
            msrc = ("custom age shape" if morbidity_profile is not None else "uniform (all active ages)")
        benefit = -morbidity_response * M * demis          # cleaner (demis<0) -> higher productivity; M scales
        e = np.array(p.e, dtype=float)
        S = e.shape[1]
        g = (health_profile.morbidity_shape_to_S(morbidity_profile, S, getattr(p, "E", 0))
             if morbidity_profile is not None else np.ones(S))
        gcol = g[:, None]
        ramp = np.linspace(0.0, benefit, phase_years)
        for t, b in enumerate(ramp):
            e[t, :, :prod_J] *= (1.0 + b * gcol)
        e[phase_years:, :, :prod_J] *= (1.0 + benefit * gcol)
        p.e = e
        prov["morbidity_benefit"] = benefit
        prov["morbidity_response"] = float(morbidity_response)
        prov["morbidity_profile_source"] = msrc
    return ctx.log("health", **prov)


# --- #6 OG activity -> CLEWS energy-service demand · og->clews (post-solve) ------

def emit_energy_demand(ctx, activity_ratio, *, driver="Y_m", og_index=None, clews_fuel=None):
    """OG activity -> CLEWS energy-service demand (og->clews; run AFTER the reform solve). ``activity_ratio``
    is the ALREADY-SOURCED reform/base activity ratio path (signals.activity_ratio); this writes the
    Demand artifact scaling baseline CLEWS demand by it -- the producer side of loop closure."""
    c = ctx.country
    default_idx = (c.concordance.energy_industry_index if driver == "Y_m"
                   else c.concordance.energy_good_index)
    idx = og_index if og_index is not None else default_idx
    ratio = np.asarray(activity_ratio, dtype=float)
    mr = float(ratio[:10].mean())
    ctx.clews_inputs["Demand"] = {
        "driver": driver, "og_index": idx, "clews_fuel": clews_fuel,
        "start_year": c.scenario.og_start_year, "ratio_by_period": ratio.tolist()}
    prov = {"driver": driver, "mean_ratio": mr}
    if abs(mr - 1.0) < 1e-3:
        prov["note"] = ("ratio ~= 1: the forward demand channel is INERT in a single CLEWS->OG pass; "
                        "it becomes a real driver only inside the iterated loop.")
    return ctx.log("emit_energy_demand", **prov)
