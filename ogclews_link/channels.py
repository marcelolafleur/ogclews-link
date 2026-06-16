"""The integration channels. Each is a small, economically-grounded transform with the
exact OG-Core parameter / CLEWS variable it touches stated in its docstring, plus
guardrails in validate(). All transforms operate on a duck-typed Specifications (numpy
attributes), so they are unit-testable without ogcore.

Verified OG-Core mechanics (ogcore 0.16.x, fiscal.py / household.py / tax.py): G=alpha_G*Y,
TR=alpha_T*Y, I_g=alpha_I*Y -> K_g law of motion -> CES production; the consumption-tax
wedge (1+tau_c_i)p_i enters the demand FOC (get_ci), the budget (get_cons), the composite
price (get_ptilde), and books cons_tax_revenue (tax.cons_tax_liab). rho (T+S,S), e (T,S,J),
chi_n (T+S,S), alpha_* (T+S,), tau_c (T+S,I).

Tail convention: parameters are length (T+S); indices T:T+S are the STEADY STATE that
anchors TPI's terminal condition. A PERMANENT policy (a standing carbon/energy price and
its recycling) must fill the SS tail; a TEMPORARY transition (front-loaded capex) must
taper to baseline in the SS (write [:T] only). Each channel states which it is.
"""
from __future__ import annotations

import glob
import os

import numpy as np

from . import health_profile, signals
from .framework import CLEWS_TO_OG, OG_TO_CLEWS, POLICY, Channel, register


# --- helpers --------------------------------------------------------------------

def _fit(value, n: int) -> np.ndarray:
    """Broadcast/forward-fill to length n; an empty input yields zeros (no crash)."""
    arr = np.atleast_1d(np.asarray(value, dtype=float))
    if arr.size == 0:
        return np.zeros(n)
    if arr.shape[0] == 1:
        return np.full(n, arr[0])
    if arr.shape[0] >= n:
        return arr[:n]
    out = np.empty(n)
    out[: arr.shape[0]] = arr
    out[arr.shape[0]:] = arr[-1]
    return out


def _align_to_start(series, start_year: int, n: int) -> np.ndarray:
    """Align a PERMANENT signal (a standing price level): real values during the data
    horizon, then the last value carried forward (it persists). Period 0 == start_year."""
    hi = int(series.index.max())
    if start_year > hi:               # signal ends before OG starts -> nothing to align
        return np.zeros(n)
    s = series.reindex(range(start_year, hi + 1)).ffill().bfill()
    return _fit(s.values, n)


def _align_finite(series, start_year: int, n: int) -> np.ndarray:
    """Align a FINITE flow (e.g. transition capex): real values during the data horizon,
    then ZERO -- the flow ends, it is not carried forward. Critical for investment, where
    forward-filling would turn a temporary build into a permanent shock that breaks TPI."""
    hi = int(series.index.max())
    if start_year > hi:
        return np.zeros(n)
    vals = series.reindex(range(start_year, hi + 1)).fillna(0.0).values
    out = np.zeros(n)
    out[: min(len(vals), n)] = vals[:n]
    return out


def _cost_xlsx(scenario_dir: str) -> str:
    hits = [h for h in glob.glob(os.path.join(scenario_dir, "*Cost of electricity*.xlsx"))
            if not os.path.basename(h).startswith("~$")]
    return sorted(hits)[0]


def recycle_via_transfers(ctx, i_good: int, dtau_path) -> float | None:
    """Return the energy-tax revenue to households as a lump-sum transfer (TR=alpha_T*Y),
    so the government collects the tau_c revenue and rebates it -- approximately
    revenue-neutral, isolating the price/substitution effect from the fiscal effect.

    FIRST-ORDER: revenue is estimated on BASELINE quantities (dtau * p_i * C_i); the wedge
    shrinks its own base, so this slightly OVERSTATES the reform revenue (error O(shock)).
    EXACT neutrality needs a post-solve read of reform cons_tax_revenue and a re-solve
    (a one-step iteration) -- not done here. Fills the SS tail to match a PERMANENT wedge.
    """
    b = ctx.base_tpi
    if b is None:
        return None
    p = ctx.og_reform
    T = p.T
    Ci = np.asarray(b["C_i"])[:T, i_good]
    pi = np.asarray(b["p_i"])[:T, i_good]
    Y = np.asarray(b["Y"])[:T]
    bump = (_fit(dtau_path, T) * pi * Ci) / np.maximum(Y, 1e-12)   # extra revenue, share of GDP
    aT = np.asarray(p.alpha_T, dtype=float)
    p.alpha_T = aT + _fit(bump, aT.shape[0])                       # carry into the SS tail
    return float(np.mean(bump[:10]))


# --- #1 energy price -> household demand (+ incidence) --------------------------

class EnergyPriceChannel(Channel):
    id = "energy_price"
    label = "Energy price -> household demand + incidence"
    direction = CLEWS_TO_OG
    theory_status = "structural_core"

    def apply(self, ctx, shock=0.20, use_clews_data=False, energy_cmin=0.0, recycle=False,
              price_source="controlled", fuel=None):
        c = ctx.country
        i_e, m_e = c.concordance.energy_good_index, c.concordance.energy_industry_index
        p = ctx.og_reform
        n = np.asarray(p.tau_c).shape[0]
        # price_source takes priority over the legacy use_clews_data flag.
        if price_source == "dual":
            # RIGOROUS source: reform/base ratio of the OSeMOSYS commodity-balance DUAL (the
            # marginal electricity price), from a MUIOGO CBC export. fuel=None matches ELC* codes.
            # Point c.scenario at the run dirs holding the EBb4 CSV (see muiogo_run).
            ratio = signals.commodity_shadow_price_ratio(
                c.scenario.base_dir, c.scenario.reform_dir, fuel=fuel)
            if ratio.dropna().empty:
                raise ValueError(
                    "energy_price price_source='dual': commodity-balance dual ratio is empty / "
                    "all-NaN -- no overlapping base/reform years, or a zero baseline shadow price "
                    "for the matched fuel. Check the EBb4 export, the fuel code, and the run years.")
            # electricity is only `share` of the OG energy good's value, so dilute the electricity
            # dual ratio into the energy good exactly as the cost-index branch does (else overstated).
            share = float(np.asarray(p.io_matrix)[i_e, m_e])
            good_ratio = _align_to_start(1.0 + share * (ratio - 1.0), c.scenario.og_start_year, n)
            src = "dual_shadow_price"
        elif use_clews_data or price_source == "clews_cost_index":
            ratio = signals.cost_of_electricity_ratio(
                _cost_xlsx(c.scenario.base_dir), _cost_xlsx(c.scenario.reform_dir))
            share = float(np.asarray(p.io_matrix)[i_e, m_e])  # electricity's value-share of the energy good
            good_ratio = _align_to_start(1.0 + share * (ratio - 1.0), c.scenario.og_start_year, n)
            src = "clews_cost_index"
        else:
            good_ratio = 1.0 + shock
            src = f"controlled_{shock:+.0%}"
        tau = np.array(p.tau_c, dtype=float)
        before = tau[:, i_e].copy()
        tau[:, i_e] = _fit(good_ratio, tau.shape[0]) * (1.0 + tau[:, i_e]) - 1.0  # permanent: full tail
        p.tau_c = tau
        dtau = tau[:, i_e] - before
        if energy_cmin > 0:
            if ctx.base_tpi is not None:  # guard: c_min above a poor household's energy use breaks the solve
                base_min = float(np.asarray(ctx.base_tpi["c_i"])[:, i_e].min())
                if energy_cmin > 0.5 * base_min:
                    print(f"[guardrail] energy_cmin={energy_cmin} exceeds 50% of the minimum baseline "
                          f"per-household energy consumption ({base_min:.4f}); risks negative consumption "
                          f"/ a broken solve. Calibrate it lower.")
            cm = np.array(p.c_min, dtype=float)
            cm[i_e] = energy_cmin                  # energy as a NECESSITY -> differential exposure incidence
            p.c_min = cm
        recycled = recycle_via_transfers(ctx, i_e, dtau[:p.T]) if recycle else None
        return {"source": src, "tau_c_energy_0": float(tau[0, i_e]), "dtau_mean": float(dtau[:10].mean()),
                "energy_cmin": energy_cmin, "recycled_pct_gdp": recycled}

    def validate(self, ctx, active):
        w = []
        if "carbon" in active:
            w.append("energy_price + carbon both wedge the energy good's tau_c -- a resource cost and "
                     "a tax are different objects; ensure the increase is not counted twice.")
        return w


# --- #2 CLEWS investment -> public capital -> crowding-out/debt ------------------

class InvestmentChannel(Channel):
    id = "investment"
    label = "CLEWS energy capex -> public investment (crowding-out, debt)"
    direction = CLEWS_TO_OG
    theory_status = "structural_core"

    def apply(self, ctx, target="alpha_I", public_only=True, scale=1.0, persist=False, smooth_years=1):
        c = ctx.country
        p = ctx.og_reform
        inc = signals.power_capex_increment(c.scenario.base_dir, c.scenario.reform_dir, c, public_only)
        # CLEWS monetary units are model-MUSD; dividing by real GDP assumes ~parity (no deflator
        # bridge yet). public_only routes only public-infra (T&D) techs to K_g; private generation
        # capex is NOT public investment. smooth_years dampens lumpy year-to-year capex spikes.
        pct_gdp = scale * inc / c.gdp_musd
        if smooth_years > 1:
            pct_gdp = pct_gdp.rolling(smooth_years, center=True, min_periods=1).mean()
        # transition capex is a FINITE flow: real during the CLEWS horizon, zero after (and in SS).
        path = _align_finite(pct_gdp, c.scenario.og_start_year, p.T)
        full = np.zeros(np.asarray(p.alpha_I).shape[0])
        full[:p.T] = path
        if persist:                       # rare: permanent infrastructure -> carry the last value into SS
            full = _fit(path, full.shape[0])
        if np.max(path) > float(np.asarray(p.alpha_I)[0]):
            print(f"[guardrail] investment: peak alpha_I increment {np.max(path):.3f} > baseline "
                  f"alpha_I {float(np.asarray(p.alpha_I)[0]):.3f} -- large public-investment shock; "
                  f"check units, public_only, and smooth_years.")
        if target == "alpha_I":
            p.alpha_I = np.asarray(p.alpha_I, dtype=float) + full
        else:
            p.alpha_bs_I = np.asarray(p.alpha_bs_I, dtype=float) * (1.0 + full)
        return {"target": target, "public_only": public_only, "persist": persist,
                "smooth_years": smooth_years, "cumulative_pct_gdp": float(path.sum()),
                "peak_pct_gdp": float(np.max(path))}

    def validate(self, ctx, active):
        w = ["investment->alpha_I treats capex as PUBLIC infrastructure (K_g); verify the "
             "public/private tagging (public_only=True keeps only T&D). CLEWS-MUSD vs real GDP "
             "assumes unit parity -- add a deflator before headline use."]
        if "energy_price" in active:
            w.append("investment + energy_price: do not route the same transition burden through both a "
                     "price/productivity drag and public investment (price = operating cost; investment "
                     "= capital account).")
        return w


# --- #3 carbon price -> fiscal revenue (OG) + EmissionsPenalty (CLEWS) -----------

class CarbonChannel(Channel):
    id = "carbon"
    label = "Carbon price -> OG fiscal revenue + CLEWS EmissionsPenalty"
    direction = POLICY
    theory_status = "structural_core"

    def apply(self, ctx, carbon_price=50.0, carbon_intensity=0.5, apply_to_og=True,
              apply_to_clews=True, recycle=False):
        c = ctx.country
        i_e = c.concordance.energy_good_index
        p = ctx.og_reform
        cp = _fit(carbon_price, p.T)              # USD/tCO2 path
        prov = {"carbon_price_mean": float(cp.mean()), "applied_to": []}
        if apply_to_og:
            # consumption-side carbon tax on the energy good. UNITS: carbon_intensity must be tCO2
            # per unit of the OG energy good, and carbon_price in the OG numeraire (NOT raw USD) for
            # the ad-valorem ratio to be dimensionless -- no deflator is applied yet, so treat the
            # magnitude as illustrative. OG has no energy in PRODUCTION, so this prices only
            # HOUSEHOLD energy (~1.4% of consumption); industrial carbon is unpriced on the OG side.
            base_pi = (np.asarray(ctx.base_tpi["p_i"])[:p.T, i_e] if ctx.base_tpi is not None
                       else np.ones(p.T))
            dtau = cp * carbon_intensity / np.maximum(base_pi, 1e-9)
            if float(dtau.mean()) > 1.0:
                print(f"[guardrail] carbon: mean implied tau_c add-on {dtau.mean():.2f} (>100%) -- "
                      f"carbon_intensity/price units are almost certainly off (need tCO2 per unit good "
                      f"and price in OG numeraire). Treat as illustrative.")
            tau = np.array(p.tau_c, dtype=float)
            tau[:, i_e] = tau[:, i_e] + _fit(dtau, tau.shape[0])   # permanent policy: full tail
            p.tau_c = tau
            prov["applied_to"].append("og_tau_c")
            prov["og_base_note"] = "OG taxes household energy only (~1.4% of consumption); industrial carbon unpriced"
            if recycle:
                prov["recycled_pct_gdp"] = recycle_via_transfers(ctx, i_e, dtau)
        if apply_to_clews:
            ctx.clews_inputs["EmissionsPenalty"] = {
                "region": "RE1", "emission": c.co2_emission,
                "start_year": c.scenario.og_start_year, "value_by_period": cp.tolist()}
            prov["applied_to"].append("clews_emissions_penalty")
        return prov

    def validate(self, ctx, active):
        return ["carbon price must appear ONCE: set it as policy (here) feeding both sides; do not also "
                "infer a carbon price from a CLEWS shadow price into OG. OG side captures only the "
                "household carbon base -- not the economy-wide footprint CLEWS prices."]


# --- #4 OG interest rate -> CLEWS discount rate (harmonization) ------------------

class DiscountRateChannel(Channel):
    id = "discount_rate"
    label = "OG equilibrium rate -> CLEWS DiscountRate"
    direction = OG_TO_CLEWS
    theory_status = "structural_core"
    post_solve = True

    def apply(self, ctx, rate_key="r_p", scalar=True, region="RE1"):
        r = signals.og_interest_rate(ctx.base_tpi, rate_key)  # OG real per-period (market) rate
        rate = float(np.mean(r[:10])) if scalar else r.tolist()
        ctx.clews_inputs["DiscountRate"] = {"region": region, "rate": rate, "key": rate_key,
                                            "convention": "real; OG market cost of capital; period~annual if S=80"}
        return {"rate_key": rate_key, "clews_discount_rate": rate if scalar else "path"}

    def validate(self, ctx, active):
        return ["discount harmonization uses OG's market portfolio return r_p (not a separate social "
                "rate); confirm real-vs-nominal and that one OG period == one calendar year "
                "(S == ending_age-starting_age)."]


# --- #5 CLEWS emissions -> health -> demographics (external dose-response) -------

class HealthChannel(Channel):
    id = "health"
    label = "CLEWS emissions -> health -> mortality/productivity"
    direction = CLEWS_TO_OG
    theory_status = "reduced_form"  # external, illustrative dose-response

    def apply(self, ctx, mortality_response=0.05, morbidity_response=0.01,
              affects=("mortality", "e"), profile_path=None, phase_years=5, prod_J=7):
        c = ctx.country
        p = ctx.og_reform
        er = signals.emissions_ratio(c.scenario.base_dir, c.scenario.reform_dir, c)
        demis = float(np.nanmean(er.values[:10])) - 1.0   # <0 == reform is cleaner
        prov = {"emissions_change": demis, "affects": list(affects)}
        if "mortality" in affects:
            # disease_pop method: stash an age-profile mortality shock for the runtime to apply
            # (rho += kappa*g_t*h(s) -> recompute population). h(s) from GBD data, else placeholder.
            profile = (health_profile.load_profile(profile_path) if profile_path
                       else health_profile.placeholder_profile())
            kappa = mortality_response * demis            # PLACEHOLDER dose-response; cleaner -> kappa<0 -> fewer deaths
            ctx.extras["health_shock"] = {"kappa": kappa, "profile": profile, "phase_years": phase_years}
            prov["mortality_kappa"] = kappa
            prov["profile_source"] = "GBD data" if profile_path else "PLACEHOLDER (no GBD profile; see DATA.md)"
        if "e" in affects:                                # morbidity via effective labor e (T,S,J)
            benefit = -morbidity_response * demis         # PLACEHOLDER; cleaner -> higher productivity
            e = np.array(p.e, dtype=float)
            ramp = np.linspace(0.0, benefit, phase_years)
            for t, b in enumerate(ramp):
                e[t, :, :prod_J] *= (1.0 + b)
            e[phase_years:, :, :prod_J] *= (1.0 + benefit)
            p.e = e
            prov["morbidity_benefit"] = benefit
        return prov

    def validate(self, ctx, active):
        return ["health uses the disease_pop AGE-PROFILE mortality method (CostOfDisease): "
                "rho += kappa*g_t*h(s), phased in, then the population is recomputed via get_pop_objs. "
                "The age profile h(s) MUST come from GBD ambient-PM2.5 deaths-by-age (DATA.md) -- the "
                "placeholder is an illustrative elderly-skewed shape only. The dose-response "
                "(emissions->kappa) and the morbidity productivity response are PLACEHOLDERS pending "
                "data. Pollution deaths skew elderly, so expect a weaker mortality->GDP channel than "
                "the working-age HIV case."]


# --- #6 OG activity -> CLEWS demand (the forward driver) ------------------------

class DemandChannel(Channel):
    id = "demand"
    label = "OG activity/consumption -> CLEWS energy-service demand"
    direction = OG_TO_CLEWS
    theory_status = "structural_core"
    post_solve = True

    def apply(self, ctx, driver="Y_m", elasticity=1.0, og_index=None, clews_fuel=None):
        c = ctx.country
        idx = og_index if og_index is not None else c.concordance.energy_industry_index
        get = signals.og_sector_output if driver == "Y_m" else signals.og_consumption_good
        yb, yr = get(ctx.base_tpi, idx), get(ctx.reform_tpi, idx)
        T = min(len(yb), len(yr))
        ratio = (yr[:T] / np.maximum(yb[:T], 1e-12)) ** elasticity
        mr = float(ratio[:10].mean())
        ctx.clews_inputs["Demand"] = {
            "driver": driver, "og_index": idx, "clews_fuel": clews_fuel,
            "start_year": c.scenario.og_start_year, "ratio_by_period": ratio.tolist()}
        prov = {"driver": driver, "elasticity": elasticity, "mean_ratio": mr}
        if abs(mr - 1.0) < 1e-3:
            prov["note"] = ("ratio ~= 1: the forward demand channel is INERT in a single CLEWS->OG pass; "
                            "it becomes a real driver only inside the iterated loop.")
        return prov

    def validate(self, ctx, active):
        return ["demand ratio-scales base CLEWS demand by reform/base activity; needs the "
                "OG-industry/good -> CLEWS-fuel concordance and an annual->timeslice decision."]


def register_all():
    for cls in (EnergyPriceChannel, InvestmentChannel, CarbonChannel,
                DiscountRateChannel, HealthChannel, DemandChannel):
        try:
            register(cls())
        except ValueError:
            pass  # idempotent


register_all()
