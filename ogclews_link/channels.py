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
    new_aT = aT + _fit(bump, aT.shape[0])                          # carry into the SS tail
    if np.any(new_aT < 0):
        # A cheaper-energy reform (dtau<0) shrinks the recycle and, unfloored, would drive alpha_T
        # NEGATIVE -- a lump-sum TAX on households (TR=alpha_T*Y), bypassing OG-Core's alpha_T>=0
        # validator since we set the attribute directly. Floor at 0 to keep it a transfer. NOTE: a
        # sign-flipping recycle means transfers are the wrong closure instrument for this reform --
        # the floor protects the solve, but the scenario should route the rebate elsewhere.
        print("[guardrail] recycle_via_transfers: bump would push alpha_T < 0 (a lump-sum tax on "
              "households); floored at 0. A negative recycle implies the closure instrument should change.")
        new_aT = np.maximum(new_aT, 0.0)
    p.alpha_T = new_aT
    return float(np.mean((new_aT - aT)[:10]))   # realized recycle (post-floor), share of GDP


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
            # alpha_bs_I is read by OG-Core's get_I_g ONLY when baseline_spending=True (default False),
            # so this branch is a silent no-op under the default closure -- warn rather than fail quietly.
            if not bool(getattr(p, "baseline_spending", False)):
                print(f"[guardrail] investment target={target!r} writes alpha_bs_I, which OG-Core ignores "
                      f"unless baseline_spending=True (currently False) -- this shock will have NO effect.")
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
        if ctx.reform_tpi is None:
            raise ValueError("DiscountRateChannel is post_solve and needs ctx.reform_tpi (the reform "
                             "equilibrium rate); it was None -- run it after the reform solve.")
        r = signals.og_interest_rate(ctx.reform_tpi, rate_key)  # REFORM OG real per-period (market) rate
        rate = float(np.mean(r[:10])) if scalar else r.tolist()
        ctx.clews_inputs["DiscountRate"] = {"region": region, "rate": rate, "key": rate_key,
                                            "convention": "real; OG market cost of capital; period~annual if S=80"}
        return {"rate_key": rate_key, "clews_discount_rate": rate if scalar else "path"}

    def validate(self, ctx, active):
        return ["discount harmonization uses OG's market portfolio return r_p (not a separate social "
                "rate); confirm real-vs-nominal and that one OG period == one calendar year "
                "(S == ending_age-starting_age)."]


# --- #5 CLEWS emissions -> health -> demographics (external dose-response) -------

# PLACEHOLDER: total annual ambient-PM2.5-attributable deaths for PHL -- the real value comes from
# GBD (health_profile.total_deaths_from_gbd on the IHME export; see DATA.md). Order-of-magnitude
# stand-in so the channel runs; do NOT report calibrated numbers off it.
_PLACEHOLDER_PM25_DEATHS = 64_000.0


class HealthChannel(Channel):
    id = "health"
    label = "CLEWS emissions -> health -> mortality/productivity"
    direction = CLEWS_TO_OG
    theory_status = "reduced_form"  # external, illustrative dose-response

    def apply(self, ctx, excess_deaths=None, total_pollution_deaths=None, morbidity_response=0.01,
              affects=("mortality", "e"), profile_path=None, morbidity_profile=None,
              phase_years=5, prod_J=7, gbd_csv=None, gbd_location=None, gbd_year=None,
              pollutant=None):
        c = ctx.country
        p = ctx.og_reform
        # pollutant selects the CLEWS emission species used as the dose proxy: None -> CO2e (default,
        # back-compatible), or "PM2_5" -- the actual health-relevant pollutant, tracked in the same
        # files and moving DIFFERENTLY (PEP cuts PM2.5 ~15-20% via transport vs CO2e ~38% via power).
        er = signals.emissions_ratio(c.scenario.base_dir, c.scenario.reform_dir, c, species=pollutant)
        demis = float(np.nanmean(er.values[:10])) - 1.0   # <0 == reform is cleaner
        if not np.isfinite(demis):
            raise ValueError(f"health: emissions_ratio gave a non-finite change ({demis}); "
                             "check the CLEWS emissions files.")
        # GBD sourcing: one multi-cause ambient-PM2.5 burden export drives BOTH the mortality h(s) +
        # total (All-causes Deaths) and the morbidity g(s) + YLD-rate magnitude (working-age chronic
        # causes). Present -> retires the placeholders; explicit args still override. Multi-cause file
        # -> key on cause_name="All causes" for the deaths total (else rei-keyed rows double-count).
        gbd = gbd_csv or getattr(c, "gbd_burden_csv", None)
        gloc = gbd_location or getattr(c, "name", None)
        gyr = int(gbd_year or getattr(c, "gbd_year", 2023))
        prov = {"emissions_change": demis, "affects": list(affects), "gbd_source": bool(gbd),
                "pollutant": pollutant or c.co2_emission}
        if "mortality" in affects:
            # disease_pop method: stash a SIGNED excess-deaths target + age shape; the runtime's
            # health_pop.disease_pop solves rho += shock_scale*g_t*h(s) (clipped) to hit it, then
            # recomputes the population. Cleaner reform (demis<0) -> deaths AVOIDED -> NEGATIVE target.
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
                excess_deaths = float(total_pollution_deaths) * demis    # total x emissions fraction
                target_src = ("GBD total x emissions change" if gbd else "explicit total x emissions change")
            else:
                excess_deaths = _PLACEHOLDER_PM25_DEATHS * demis         # demis<0 -> lives saved
                target_src = "PLACEHOLDER total x emissions change (see DATA.md)"
                print(f"[guardrail] health: using PLACEHOLDER total PM2.5 deaths "
                      f"({_PLACEHOLDER_PM25_DEATHS:,.0f}); supply a GBD export before reporting calibrated numbers.")
            ctx.extras["health_shock"] = {"excess_deaths": float(excess_deaths), "profile": profile,
                                          "phase_years": phase_years, "rc_ss": c.rc_ss}
            prov["mortality_excess_deaths"] = float(excess_deaths)
            prov["target_source"] = target_src
            prov["profile_source"] = psrc
        if "e" in affects:                                # morbidity via effective labor e (T, S, J)
            if gbd and morbidity_profile is None:
                # working-age YLD age shape g(s) + peak per-person YLD rate (the magnitude), so the
                # per-age productivity haircut = the GBD YLD-rate fraction by age x the emissions change.
                morbidity_profile = health_profile.build_morbidity_profile_from_gbd(gbd, gloc, gyr)
                morbidity_response = health_profile.morbidity_yld_rate_from_gbd(gbd, gloc, gyr)
                msrc = "GBD YLD-by-age (working-age causes)"
            else:
                msrc = ("custom age shape" if morbidity_profile is not None else "uniform (all active ages)")
            benefit = -morbidity_response * demis         # cleaner (demis<0) -> higher productivity
            e = np.array(p.e, dtype=float)
            S = e.shape[1]
            # Age distribution of the morbidity gain, mirroring the mortality channel's h(s): a peak-1
            # relative shape over the S active periods; the magnitude is carried by `benefit`. Default
            # (no GBD, no profile) = UNIFORM (every active age gains equally).
            g = (health_profile.morbidity_shape_to_S(morbidity_profile, S, getattr(p, "E", 0))
                 if morbidity_profile is not None else np.ones(S))
            gcol = g[:, None]                             # (S, 1): broadcast across the prod_J cols
            ramp = np.linspace(0.0, benefit, phase_years)
            for t, b in enumerate(ramp):
                e[t, :, :prod_J] *= (1.0 + b * gcol)
            e[phase_years:, :, :prod_J] *= (1.0 + benefit * gcol)
            p.e = e
            prov["morbidity_benefit"] = benefit
            prov["morbidity_response"] = float(morbidity_response)
            prov["morbidity_profile_source"] = msrc
        return prov

    def validate(self, ctx, active):
        return ["health uses the disease_pop AGE-PROFILE mortality method (CostOfDisease): "
                "rho += shock_scale*g_t*h(s) (shock_scale solved to a signed excess-deaths target; "
                "negative = lives saved), phased in, then the population is recomputed via get_pop_objs. "
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
        # default index must match the slice space: og_sector_output slices Y_m (industry m index),
        # og_consumption_good slices C_i (good i index). PHL masks this (both indices == 1).
        default_idx = (c.concordance.energy_industry_index if driver == "Y_m"
                       else c.concordance.energy_good_index)
        idx = og_index if og_index is not None else default_idx
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


# ================================================================================
# EXPLORATORY CHANNELS (channel-exploration lane). Prototypes from
# NEW-CHANNELS-FEASIBILITY.md: financing (remittances/diaspora bonds), crop/food,
# climate, water, household cooking, LDC graduation. Each is a verified transform with
# guardrails; magnitudes are ILLUSTRATIVE pending calibration (flagged in validate()).
# ================================================================================


# --- #7 diaspora remittances -> household income + labor supply -----------------

class RemittancesChannel(Channel):
    """OG-Core models remittances natively: aggregate RM = alpha_RM * Y, distributed to households
    by eta_RM (an untaxed lump-sum in the budget). PHL baseline already runs alpha_RM ~= 0.072 (7.2%
    of GDP), so this channel VARIES that level (a remittance boom/bust, or the consumption-support arm
    of the remittances-vs-diaspora-bonds contrast). The labor-supply response is the pure income
    effect (higher non-labor income -> less labor); no chi_n edit. OG-Core SUBTRACTS aggregate RM in
    the resource constraint while adding it to budgets, so this is a redistribution + labor-supply
    device, NOT a free national windfall -- read welfare as incidence across eta_RM, not added GDP."""
    id = "remittances"
    label = "Diaspora remittances -> household income / labor supply (alpha_RM, eta_RM)"
    direction = POLICY
    theory_status = "structural_core"

    def apply(self, ctx, alpha_rm=None, alpha_rm_mult=None, shock_pct_gdp=None, g_rm=None,
              concentrate_low_income=False, persist=True):
        p = ctx.og_reform
        base1 = float(getattr(p, "alpha_RM_1", 0.0))
        baseT = float(getattr(p, "alpha_RM_T", base1))
        if alpha_rm is not None:                       # absolute remittances/GDP target
            new1 = newT = float(alpha_rm)
        elif alpha_rm_mult is not None:                # scale the baseline level
            new1, newT = base1 * float(alpha_rm_mult), baseT * float(alpha_rm_mult)
        elif shock_pct_gdp is not None:                # additive %-GDP shock
            new1, newT = base1 + float(shock_pct_gdp), baseT + float(shock_pct_gdp)
        else:
            new1, newT = base1, baseT
        p.alpha_RM_1 = max(new1, 0.0)
        p.alpha_RM_T = max(newT, 0.0) if persist else baseT   # persist=False -> a transitory shock
        if g_rm is not None:
            p.g_RM = list(np.atleast_1d(np.asarray(g_rm, dtype=float)))
        moved = None
        if concentrate_low_income and hasattr(p, "eta_RM"):
            # tilt incidence toward the lowest lifetime-income type (last axis j=0), renormalizing to
            # the array's ORIGINAL total so aggregate RM is unchanged -- only WHO receives it shifts.
            eta = np.array(p.eta_RM, dtype=float)
            tot = eta.sum()
            w = np.ones(eta.shape[-1]); w[0] = 2.0      # double the lowest-income weight (illustrative)
            eta = eta * w
            eta = eta * (tot / eta.sum()) if eta.sum() else eta
            p.eta_RM = eta
            moved = True
        return {"alpha_RM_1": float(p.alpha_RM_1), "alpha_RM_T": float(p.alpha_RM_T),
                "baseline_alpha_RM": base1, "d_pct_gdp": float(p.alpha_RM_1 - base1),
                "persist": persist, "eta_tilted_low_income": moved}

    def validate(self, ctx, active):
        w = ["remittances enter as an untaxed lump-sum (alpha_RM*Y distributed by eta_RM); the "
             "labor-supply effect is the income effect, NOT a chi_n change. OG-Core SUBTRACTS RM in "
             "the resource constraint (redistribution + labor supply, not a national windfall) -- read "
             "welfare as eta_RM incidence. PHL baseline alpha_RM ~= 0.072; set levels relative to that."]
        if "diaspora_bonds" in active:
            w.append("remittances + diaspora_bonds is the intended CONTRAST (household consumption "
                     "support vs diaspora-financed public investment): run them as separate arms, not summed.")
        return w


# --- #8 diaspora bonds -> foreign-financed public investment --------------------

class DiasporaBondChannel(Channel):
    """The financing-side counterpart to remittances: instead of flowing to households, diaspora
    savings are captured into a sovereign bond that funds PUBLIC INVESTMENT (alpha_I -> K_g) -- the
    natural home for the CLEWS transition capex the `investment` channel reads. Reduced-form over
    OG-Core's open-economy machinery (it has no distinct 'tranche' object): proceeds bump alpha_I, an
    optional 'patriotic discount' lowers world_int_rate_annual, and the foreign share of new debt
    (zeta_D) rises. The burden is future debt service at the world rate; the benefit is crowded-in
    public capital at a discounted cost of funds."""
    id = "diaspora_bonds"
    label = "Diaspora bonds -> foreign-financed public investment (alpha_I, world rate, zeta_D)"
    direction = POLICY
    theory_status = "research"

    def apply(self, ctx, issuance_pct_gdp=0.01, years=10, discount_bps=0.0,
              fund="public_investment", foreign_share=None):
        from .policy_levers import route_revenue
        p = ctx.og_reform
        n = np.asarray(p.alpha_I).shape[0]
        path = np.zeros(n)
        path[: min(int(years), n)] = float(issuance_pct_gdp)     # FINITE issuance window (taper in SS)
        routed = route_revenue(p, path, to=fund, fill_ss_tail=False)
        prov = {"issuance_pct_gdp": float(issuance_pct_gdp), "years": int(years),
                "funded": routed.get("param"), "cumulative_pct_gdp": float(path.sum())}
        if discount_bps:                                          # patriotic discount: below-market rate
            wr0 = np.atleast_1d(np.asarray(getattr(p, "world_int_rate_annual", [0.04]), dtype=float))
            p.world_int_rate_annual = list(np.maximum(wr0 - float(discount_bps) / 1e4, 0.0))
            prov["world_rate"] = float(np.mean(p.world_int_rate_annual))
            prov["discount_bps"] = float(discount_bps)
        if foreign_share is not None and hasattr(p, "zeta_D"):    # more new debt absorbed abroad
            zd = np.array(p.zeta_D, dtype=float)
            zd[...] = float(foreign_share)
            p.zeta_D = zd
            prov["zeta_D"] = float(foreign_share)
        return prov

    def validate(self, ctx, active):
        w = ["diaspora_bonds is a REDUCED-FORM of an external bond: OG-Core has no separate diaspora "
             "tranche, so proceeds bump alpha_I and the discount is a world-rate cut. The PHL has issued "
             "retail $-bonds (~US$1.6bn, 2021) but NO true patriotic-discount diaspora bond -- treat "
             "discount_bps as a SENSITIVITY axis, not an observed parameter."]
        if "investment" in active:
            w.append("diaspora_bonds + investment both write alpha_I: use diaspora_bonds as the FINANCING "
                     "of the investment channel's transition capex, not an independent second bump.")
        return w


# --- #9 crop / food price -> household demand + regressive incidence -------------

class FoodPriceChannel(Channel):
    """A crop/food-price shock on the FOOD consumption good (i=food, alpha_c~=0.357 in PHL -- ~25x the
    consumption weight of energy, so high welfare leverage and, with a subsistence floor, strongly
    regressive). Two routes (run as ALTERNATIVES, then compare): a consumption-price wedge tau_c[food]
    (clones the energy_price plumbing) or an agricultural-TFP hit Z[NatRes] (the GTAP-standard
    land-augmenting shock, letting the price emerge endogenously). EXTERNALLY DRIVEN: the live CLEWS
    has no crop signal (PHL_LND_CRP=0), so `yield_loss` comes from IRRI (~10%/degC) / IFPRI-IMPACT."""
    id = "food_price"
    label = "Crop yield loss -> food price + regressive incidence (tau_c[Food] / Z[NatRes])"
    direction = CLEWS_TO_OG
    theory_status = "reduced_form"   # external climate-crop driven; no CLEWS crop signal yet

    def apply(self, ctx, yield_loss=0.10, pass_through=0.7, route="tau_c", food_cmin=0.0):
        c = ctx.country
        p = ctx.og_reform
        i_f = int(getattr(c.concordance, "food_good_index", 0))
        m_a = int(getattr(c.concordance, "agri_industry_index", 0))
        yl = float(yield_loss)
        # a fractional crop yield LOSS -> a consumer food-price rise via supply elasticity / import
        # pass-through (PHL is a large rice importer, so pass_through is high).
        price_rise = float(pass_through) * yl / max(1.0 - yl, 1e-6)
        prov = {"yield_loss": yl, "pass_through": float(pass_through), "route": route,
                "implied_price_rise": price_rise}
        if route in ("tau_c", "both"):
            tau = np.array(p.tau_c, dtype=float)
            tau[:, i_f] = (1.0 + price_rise) * (1.0 + tau[:, i_f]) - 1.0     # permanent: full SS tail
            p.tau_c = tau
            prov["tau_c_food_0"] = float(tau[0, i_f])
        if route in ("Z", "both"):
            Z = np.array(p.Z, dtype=float)
            Z[:, m_a] = Z[:, m_a] * (1.0 - yl)                              # ag-TFP hit (endogenous price)
            p.Z = Z
            prov["Z_natres_mult"] = float(1.0 - yl)
        if food_cmin > 0:
            cm = np.array(p.c_min, dtype=float)
            cm[i_f] = float(food_cmin)            # food as a NECESSITY -> regressive incidence (Stone-Geary)
            p.c_min = cm
            prov["food_cmin"] = float(food_cmin)
        return prov

    def validate(self, ctx, active):
        return ["food_price is EXTERNALLY driven: the live CLEWS emits no crop signal (PHL_LND_CRP=0; "
                "only agricultural ENERGY demand), so yield_loss must come from IRRI/IFPRI climate-crop "
                "data, not CLEWS. Food is ~35.7% of consumption -> high welfare leverage; set food_cmin>0 "
                "for the regressive incidence. tau_c (price wedge) and Z (ag-TFP) are ALTERNATIVE "
                "representations -- route='both' double-counts the same shock; pick one and compare."]


# --- #10 climate (temperature) -> labor productivity + crop TFP -----------------

class ClimateDamageChannel(Channel):
    """Temperature damage to effective labor e (heat stress, ILO 'Working on a Warmer Planet') and to
    agricultural TFP Z[NatRes] (crop heat sensitivity). EXTERNAL-DATA channel: CLEWS treats climate as
    exogenous and applies the SAME physical climate to base and reform, so there is NO base-vs-reform
    climate signal -- this is an ABSOLUTE level shock and is honest ONLY if applied to the BASELINE too
    (else it reads as 'PEP causes climate damage', which is false). Use the temp path consistent with
    the PEP emissions scenario."""
    id = "climate_damage"
    label = "Temperature -> labor productivity (e) + crop TFP (Z[NatRes])"
    direction = POLICY
    theory_status = "research"

    def apply(self, ctx, temp_rise=2.0, labor_loss_per_deg=0.015, ag_loss_per_deg=0.08,
              affects=("e", "Z"), exposed_J=None, phase_years=10):
        c = ctx.country
        p = ctx.og_reform
        dT = float(temp_rise)
        prov = {"temp_rise": dT, "affects": list(affects)}
        if "e" in affects:
            e = np.array(p.e, dtype=float)
            T, S, J = e.shape
            haircut = float(labor_loss_per_deg) * dT            # fractional labor-productivity loss
            cols = list(range(J)) if exposed_J is None else [j for j in exposed_J if 0 <= j < J]
            ramp = np.linspace(0.0, haircut, max(int(phase_years), 1))
            for t in range(T):
                h = ramp[t] if t < len(ramp) else haircut
                for j in cols:
                    e[t, :, j] *= (1.0 - h)
            p.e = e
            prov["labor_haircut"] = haircut
            prov["exposed_J"] = cols
        if "Z" in affects:
            m_a = int(getattr(c.concordance, "agri_industry_index", 0))
            Z = np.array(p.Z, dtype=float)
            Z[:, m_a] = Z[:, m_a] * (1.0 - float(ag_loss_per_deg) * dT)
            p.Z = Z
            prov["ag_Z_mult"] = float(1.0 - float(ag_loss_per_deg) * dT)
        return prov

    def validate(self, ctx, active):
        w = ["climate_damage is an ABSOLUTE level shock with NO CLEWS base-vs-reform signal (climate is "
             "exogenous, identical across scenarios). It is honest ONLY if also applied to the baseline "
             "(the Runner solves the baseline WITHOUT channels, so a reform-only application would read "
             "as PEP-attributable climate damage -- it is NOT). Frame as 'both futures are poorer'."]
        if "health" in active:
            w.append("climate_damage + health: heat MORTALITY would route through the same disease_pop "
                     "machinery -- reconcile cause-of-death accounting or double-count. This channel does "
                     "labor (e) + crop (Z) only; do not also add an aggregate-GDP elasticity (it embeds both).")
        return w


# --- #11 water stress -> energy/ag cost-push (the strongest live CLEWS signal) ---

class WaterStressChannel(Channel):
    """The transition's WATER FOOTPRINT as a cost-push. Power-sector water demand is the LARGEST
    reform-differential non-energy CLEWS signal in the live PEP run (PHL_DEM_PWR water ~5x surface /
    ~12x groundwater by 2050). A rising water requirement raises the cost of provision in the
    water-using industry -> a small TFP haircut Z[m] (default electricity), or routes a water-
    infrastructure investment to alpha_I. Magnitudes ILLUSTRATIVE (no water-shadow-price bridge yet)."""
    id = "water_stress"
    label = "CLEWS water demand -> cost-push (Z) or water-infra investment (alpha_I)"
    direction = CLEWS_TO_OG
    theory_status = "research"

    def apply(self, ctx, route="Z", elasticity=0.02, target_industry=None,
              prefixes=("PHL_DEM_PWR",), invest_scale=0.5):
        from .policy_levers import route_revenue
        c = ctx.country
        p = ctx.og_reform
        ratio = signals.water_demand_ratio(c.scenario.base_dir, c.scenario.reform_dir, prefixes)
        n = np.asarray(p.Z).shape[0]
        rpath = _align_to_start(ratio, c.scenario.og_start_year, n)
        excess = np.maximum(rpath - 1.0, 0.0)                 # fractional extra water the reform needs
        prov = {"route": route, "elasticity": float(elasticity),
                "mean_water_ratio": float(np.nanmean(ratio.values[:10])) if len(ratio) else 1.0,
                "peak_excess": float(np.max(excess))}
        if route == "Z":
            m = int(target_industry) if target_industry is not None else c.concordance.energy_industry_index
            haircut = float(elasticity) * excess              # cost-push -> TFP haircut on the water user
            Z = np.array(p.Z, dtype=float)
            Z[:, m] = Z[:, m] * (1.0 - haircut)
            p.Z = Z
            prov["industry"] = m
            prov["peak_Z_haircut"] = float(np.max(haircut))
        elif route == "alpha_I":                              # build water infrastructure to meet demand
            prov.update(route_revenue(p, float(invest_scale) * elasticity * excess,
                                      to="public_investment", fill_ss_tail=False))
        return prov

    def validate(self, ctx, active):
        return ["water_stress reads the LARGEST live non-energy CLEWS signal (power-sector water demand), "
                "but the OG entry is a design choice: a Z cost-push (no energy-in-production in OG yet) or "
                "alpha_I water infrastructure. The water->cost elasticity is ILLUSTRATIVE pending a "
                "water-shadow-price / cost bridge. Do not combine the Z route with energy_price on the "
                "same industry without separating the operating-cost vs water-scarcity components."]


# --- #12 household cooking air pollution (HAP) -> mortality/productivity ---------

class CookingHealthChannel(Channel):
    """Household air pollution from solid-fuel COOKING, via the same disease_pop machinery as the
    `health` channel but driven by the SOLID-FUEL cooking share (BIOM+COAL+OIL) and a BIMODAL HAP age
    profile (under-5 + elderly), distinct from ambient PM2.5 (elderly-skewed). A clean-cooking reform
    (solid fuel -> LPG/electric) lowers the share -> fewer HAP deaths. NB: in the LIVE PEP pair the
    signal is ~0 (biomass/coal cooking are identical base->reform; only electric cooking moves, and it
    FALLS) and the cooking block is stylized (~100% solid fuel; PHL is heavily LPG) -- so this needs a
    clean-cooking scenario + cooking-block recalibration to bite (see validate())."""
    id = "cooking_health"
    label = "Household cooking air pollution (HAP) -> mortality (disease_pop) / productivity"
    direction = CLEWS_TO_OG
    theory_status = "reduced_form"

    # PLACEHOLDER total PHL HAP deaths/yr (order 10^4, declining as LPG access rises); real value is a
    # GBD "Household air pollution from solid fuels" pull (rei ~87) -- see DATA.md. Do NOT report off it.
    _PLACEHOLDER_HAP_DEATHS = 25_000.0

    def apply(self, ctx, hap_deaths=None, solid_fuel_change=None, profile_path=None,
              phase_years=5, morbidity_response=0.0, prod_J=7):
        c = ctx.country
        p = ctx.og_reform
        ds = (float(solid_fuel_change) if solid_fuel_change is not None
              else signals.cooking_solid_fuel_change(c.scenario.base_dir, c.scenario.reform_dir))
        profile = (health_profile.load_profile(profile_path) if profile_path
                   else health_profile.hap_profile())
        total = float(hap_deaths) if hap_deaths is not None else self._PLACEHOLDER_HAP_DEATHS
        if hap_deaths is None:
            print(f"[guardrail] cooking_health: using PLACEHOLDER total HAP deaths "
                  f"({self._PLACEHOLDER_HAP_DEATHS:,.0f}); supply a GBD HAP pull before reporting numbers.")
        excess = total * ds                       # ds<0 (less solid fuel) -> lives saved (negative)
        ctx.extras["health_shock"] = {"excess_deaths": float(excess), "profile": profile,
                                      "phase_years": phase_years, "rc_ss": c.rc_ss}
        prov = {"solid_fuel_change": ds, "hap_excess_deaths": float(excess),
                "profile": "bimodal HAP (under-5 + elderly)" if profile_path is None else "file",
                "inert_signal": abs(ds) < 1e-9}
        if morbidity_response and "e" in dir(p):   # optional productivity co-benefit on e
            e = np.array(p.e, dtype=float)
            benefit = -float(morbidity_response) * ds
            e[:, :, :prod_J] *= (1.0 + benefit)
            p.e = e
            prov["morbidity_benefit"] = benefit
        return prov

    def validate(self, ctx, active):
        w = ["cooking_health reuses disease_pop but is driven by the SOLID-FUEL cooking share + a "
             "BIMODAL HAP age profile (under-5 LRI/neonatal + elderly cardiopulmonary). In the live PEP "
             "pair the signal is ~0 (biomass/coal cooking identical base->reform; cooking block is "
             "stylized ~100% solid fuel vs PHL's heavy LPG) -- it needs a CLEAN-COOKING scenario + "
             "cooking recalibration to produce a real effect. HAP is INDOOR personal exposure of "
             "solid-fuel users: do NOT double-count with the `health` channel's ambient PM2.5 deaths."]
        if "health" in active:
            w.append("cooking_health + health both write ctx.extras['health_shock'] -> the LATER one "
                     "wins (only one mortality recompute per solve). Run them in SEPARATE experiments, "
                     "or combine the targets into one disease_pop call.")
        return w


# --- #13 LDC graduation -> trade-preference loss / financing cost / ODA ----------

class LDCGraduationChannel(Channel):
    """UN LDC graduation: loss of trade preferences (EBA/GSP -> higher export tariffs), concessional
    finance ('dual graduation' -> higher borrowing cost), and LDC-targeted ODA. NOT APPLICABLE to the
    Philippines (a lower-middle-income country, never an LDC) -> a no-op here unless the country is
    flagged is_ldc or the caller acknowledges. Calibratable for an actual graduating LDC (Bangladesh /
    Nepal / Lao PDR, 24 Nov 2026). Levers: a trade wedge (tau_c, single-good proxy for the EU-garment-
    concentrated shock), world_int_rate up, alpha_G down (aid cut), phased over the smooth transition."""
    id = "ldc_graduation"
    label = "LDC graduation -> trade-preference loss, financing cost, ODA cut"
    direction = POLICY
    theory_status = "research"

    def apply(self, ctx, trade_wedge=0.05, financing_bps=100.0, aid_cut_pct_gdp=0.01,
              phase_years=5, acknowledge_non_ldc=False):
        from .policy_levers import route_revenue
        c = ctx.country
        p = ctx.og_reform
        if not (bool(getattr(c, "is_ldc", False)) or acknowledge_non_ldc):
            print(f"[guardrail] ldc_graduation: {getattr(c, 'name', 'country')} is NOT flagged as an LDC "
                  "(the Philippines never was) -- no-op. Set country.is_ldc=True or pass "
                  "acknowledge_non_ldc=True to model a hypothetical graduation.")
            return {"applied": False, "reason": "country not an LDC"}
        i_t = int(getattr(c.concordance, "food_good_index", 0))   # tradable proxy (single-good map)
        prov = {"applied": True, "trade_wedge": float(trade_wedge), "financing_bps": float(financing_bps),
                "aid_cut_pct_gdp": float(aid_cut_pct_gdp)}
        # (a) preference loss -> export-weighted tariff increase, as an ad-valorem consumption wedge
        if trade_wedge:
            tau = np.array(p.tau_c, dtype=float)
            tau[:, i_t] = (1.0 + float(trade_wedge)) * (1.0 + tau[:, i_t]) - 1.0
            p.tau_c = tau
        # (b) loss of concessional finance -> higher world interest rate
        if financing_bps:
            wr0 = np.atleast_1d(np.asarray(getattr(p, "world_int_rate_annual", [0.04]), dtype=float))
            p.world_int_rate_annual = list(wr0 + float(financing_bps) / 1e4)
            prov["world_rate"] = float(np.mean(p.world_int_rate_annual))
        # (c) ODA cut -> lower government consumption (alpha_G), phased over the smooth-transition window
        if aid_cut_pct_gdp:
            n = np.asarray(p.alpha_G).shape[0]
            cut = np.zeros(n)
            cut[: min(int(phase_years), n)] = -float(aid_cut_pct_gdp)
            cut[min(int(phase_years), n):] = -float(aid_cut_pct_gdp)   # permanent loss
            prov.update({"aid_route": route_revenue(p, cut, to="government_consumption")})
        return prov

    def validate(self, ctx, active):
        return ["ldc_graduation is NOT applicable to the Philippines (never an LDC) -- it no-ops unless "
                "is_ldc/acknowledge_non_ldc. For a real graduating LDC the levers are well-precedented "
                "(WTO-EIF 2022; GTAP), but a single-good OG compresses the EU-garment-concentrated trade "
                "shock into one wedge (lossy); calibrate the wedge to utilization-weighted preference "
                "margins, not gross tariff lines."]


def register_all():
    for cls in (EnergyPriceChannel, InvestmentChannel, CarbonChannel,
                DiscountRateChannel, HealthChannel, DemandChannel,
                RemittancesChannel, DiasporaBondChannel, FoodPriceChannel,
                ClimateDamageChannel, WaterStressChannel, CookingHealthChannel,
                LDCGraduationChannel):
        try:
            register(cls())
        except ValueError:
            pass  # idempotent


register_all()
