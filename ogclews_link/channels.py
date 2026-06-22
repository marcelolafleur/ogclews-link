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

from . import health_profile, policy_levers, signals
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
    label = "CLEWS public-infrastructure (grid/T&D) capex -> public investment (alpha_I -> K_g)"
    direction = CLEWS_TO_OG
    theory_status = "structural_core"

    def apply(self, ctx, target="alpha_I", scale=1.0, persist=False, smooth_years=1):
        c = ctx.country
        p = ctx.og_reform
        # PUBLIC-INFRASTRUCTURE ONLY. alpha_I -> K_g is OG-Core's GOVERNMENT public-capital lever -- it
        # lifts every industry's productivity (via gamma_g), so only genuinely public infra (grid / T&D,
        # per country.is_public) belongs here. PRIVATE generation capex is NOT public investment: its
        # macro effect is the energy COST-PUSH (energy_price dual / I-O-calibrated Z), and a capex
        # SUBSIDY policy is policy_levers.set_investment_incentive (tau_b / ITC / delta_tau).
        inc = signals.power_capex_increment(c.scenario.base_dir, c.scenario.reform_dir, c, public_only=True)
        # CLEWS money is model-MUSD; units.deflator is the (uncalibrated, =1.0) CLEWS-money<->GDP-basis
        # bridge, made explicit so %-of-GDP is not a silent parity assumption. smooth_years dampens lumpy
        # year-to-year capex.
        pct_gdp = scale * inc * float(getattr(c.units, "deflator", 1.0)) / c.gdp_musd
        if smooth_years > 1:
            pct_gdp = pct_gdp.rolling(smooth_years, center=True, min_periods=1).mean()
        # transition capex is a FINITE flow: real during the CLEWS horizon, zero after (and in SS).
        path = _align_finite(pct_gdp, c.scenario.og_start_year, p.T)
        if not np.any(np.abs(path) > 1e-12):
            print("[guardrail] investment: no PUBLIC-infrastructure (grid/T&D) capex delta in this "
                  "scenario -- the public-investment channel contributes ~0. Private generation capex is "
                  "NOT routed here; its effect belongs to the energy cost-push channel.")
        full = np.zeros(np.asarray(p.alpha_I).shape[0])
        full[:p.T] = path
        if persist:                       # rare: permanent infrastructure -> carry the last value into SS
            full = _fit(path, full.shape[0])
        if np.max(path) > float(np.asarray(p.alpha_I)[0]):
            print(f"[guardrail] investment: peak alpha_I increment {np.max(path):.3f} > baseline "
                  f"alpha_I {float(np.asarray(p.alpha_I)[0]):.3f} -- large public-investment shock; "
                  f"check units.deflator and smooth_years.")
        if target == "alpha_I":
            p.alpha_I = np.asarray(p.alpha_I, dtype=float) + full
        else:
            # alpha_bs_I is read by OG-Core's get_I_g ONLY when baseline_spending=True (default False),
            # so this branch is a silent no-op under the default closure -- warn rather than fail quietly.
            if not bool(getattr(p, "baseline_spending", False)):
                print(f"[guardrail] investment target={target!r} writes alpha_bs_I, which OG-Core ignores "
                      f"unless baseline_spending=True (currently False) -- this shock will have NO effect.")
            p.alpha_bs_I = np.asarray(p.alpha_bs_I, dtype=float) * (1.0 + full)
        return {"target": target, "scope": "public_infrastructure", "persist": persist,
                "smooth_years": smooth_years, "cumulative_pct_gdp": float(path.sum()),
                "peak_pct_gdp": float(np.max(path))}

    def validate(self, ctx, active):
        return ["investment routes ONLY public-infrastructure (grid/T&D) capex to alpha_I -> K_g "
                "(economy-wide public capital, productive via gamma_g). Private generation capex is NOT "
                "here -- its macro effect is the energy cost-push, and a capex subsidy is "
                "set_investment_incentive. CLEWS-money vs GDP uses units.deflator (=1.0, uncalibrated) -- "
                "calibrate before any headline %-of-GDP."]


# --- #2b energy generation-mix capital intensity -> energy industry capital share (gamma) -------

class CapitalIntensityChannel(Channel):
    id = "capital_intensity"
    label = "CLEWS generation-mix capital intensity -> energy industry's capital share (gamma)"
    direction = CLEWS_TO_OG
    theory_status = "structural_core"

    def apply(self, ctx, window=None, gamma_scale=None, gamma_target=None, labor_share_floor=0.05):
        # ENERGY factor-share / production-technology lever: raise the energy industry's capital
        # exponent gamma[m] (a permanent, time-invariant structural shift; labor's share is the residual
        # 1-gamma-gamma_g, which falls). VERIFIED (PHL M=4 SS) -- this is NOT a crowding-out / "pull
        # capital into energy" lever: because gamma is a Cobb-Douglas exponent and the energy good is
        # small + demand-inelastic, raising it makes energy CHEAPER (output price ~-24%, output ~flat),
        # so energy CAPITAL FALLS (~-14%) with r flat (K_m = gamma_m*p_m*Y_m/rho). Its real effects are
        # the energy PRICE and the capital/labor income split. The capex-heavy-generation capital-draw-in
        # / crowding-out story belongs to the ITC lever (set_investment_incentive, which lowers the cost
        # of capital rho -- gamma is absent from it); gamma and the ITC give OPPOSITE signs on energy K.
        c = ctx.country
        p = ctx.og_reform
        m = c.concordance.energy_industry_index
        if gamma_target is None and gamma_scale is None:
            # calibrate the multiplicative shift from CLEWS: reform/base ratio of the power fleet's
            # capital cost share, over the first-decade window (ties to the scenario's OG start year).
            win = window or (c.scenario.og_start_year, c.scenario.og_start_year + 9)
            cal = signals.capital_intensity_ratio(c.scenario.base_dir, c.scenario.reform_dir, c, window=win)
            gamma_scale = cal["ratio"]
            calibration = cal
        else:
            calibration = {"source": "explicit override (gamma_target/gamma_scale)"}
        prov = policy_levers.set_capital_intensity(
            p, m, gamma_target=gamma_target, gamma_scale=gamma_scale, labor_share_floor=labor_share_floor)
        if abs(prov["gamma_new"] - prov["gamma_old"]) < 1e-6:
            print("[guardrail] capital_intensity: calibrated gamma shift ~0 -- the reform generation "
                  "mix is no more capital-intensive than baseline over this window, so the channel is "
                  "inert. (Private generation capex's macro effect then rides the energy cost-push.)")
        prov["calibration"] = calibration
        return prov

    def validate(self, ctx, active):
        msgs = ["capital_intensity raises the ENERGY industry's capital exponent gamma[m] -- a factor-"
                "SHARE / production-technology lever (labor's share is the residual 1-gamma-gamma_g, so "
                "this lowers it). VERIFIED it is NOT a crowding-out lever: raising gamma makes the small, "
                "inelastic energy good CHEAPER (energy price ~-24%, output ~flat), so energy CAPITAL "
                "FALLS (~-14%) with r flat -- the real effects are the energy price and the capital/labor "
                "income split. The capex-heavy-generation capital-draw-in story belongs to the ITC "
                "(set_investment_incentive, lowers the cost of capital). gamma, Z (TFP/cost-push) and the "
                "ITC are NOT 'three views of the same capex' -- they act on different objects (exponent "
                "vs TFP vs cost-of-capital) and gamma vs ITC give OPPOSITE signs on energy K; still don't "
                "stack them for the same buildout."]
        if "investment" in active:
            msgs.append("capital_intensity (private generation capital share, gamma) and investment "
                        "(PUBLIC grid/T&D capex -> K_g) are COMPLEMENTARY, not double-counting: "
                        "different capital, different OG lever.")
        return msgs


# --- #2c energy capex incentive (ITC): cost-of-capital subsidy -> energy capital DEMAND ----------

class CapitalDemandChannel(Channel):
    id = "energy_capex"
    label = "Energy capex incentive (ITC) -> energy capital demand"
    direction = POLICY
    theory_status = "structural_core"

    def apply(self, ctx, inv_tax_credit=0.20, delta_tau=None, tau_b_mult=None, phase_years=None):
        # The capital-DEMAND counterpart to capital_intensity (gamma). The capex-heavy generation
        # buildout financed by an investment tax credit: it lowers the energy industry's COST OF CAPITAL
        # (inv_tax_credit enters firm.get_cost_of_capital directly; gamma does NOT), so capital is drawn
        # INTO energy. VERIFIED (PHL M=4 SS): energy K +5.0% via the cost-of-capital wedge, paid through
        # the public budget (govt debt ~+0.001%). NB at PHL's small electricity scale this draws capital
        # IN but does NOT crowd others OUT (r flat, the other industries' K edge UP) -- describe it as
        # "capital reallocates into energy", not economy-wide crowding-out. gamma and the ITC give
        # OPPOSITE signs on energy K; do not stack them for the same buildout.
        c = ctx.country
        p = ctx.og_reform
        m = c.concordance.energy_industry_index
        prov = policy_levers.set_investment_incentive(
            p, m, inv_tax_credit=inv_tax_credit, delta_tau=delta_tau,
            tau_b_mult=tau_b_mult, phase_years=phase_years)
        prov["lever"] = "investment_tax_credit (cost-of-capital subsidy)"
        return prov

    def validate(self, ctx, active):
        msgs = ["energy_capex is the CAPITAL-DEMAND lever for the capex-heavy generation buildout: an ITC "
                "lowers the energy industry's cost of capital (inv_tax_credit enters firm.get_cost_of_"
                "capital), drawing capital INTO energy (verified +5% energy K, funded by the budget). It is "
                "the COUNTERPART to capital_intensity (gamma, a factor-share/price lever): they act on "
                "different objects (cost-of-capital vs the production exponent) and give OPPOSITE signs on "
                "energy K. At PHL's small electricity scale it does NOT crowd other industries out (r ~flat) "
                "-- it is capital REALLOCATION into energy, not economy-wide crowding-out."]
        if "capital_intensity" in active:
            msgs.append("energy_capex (ITC, cost-of-capital) and capital_intensity (gamma, factor share) "
                        "are TWO DIFFERENT mechanisms for the same buildout -- pick the one matching the "
                        "question (capital demand vs price/income-split); do NOT apply both.")
        return msgs


# --- #3 carbon price -> fiscal revenue (OG) + EmissionsPenalty (CLEWS) -----------

class CarbonChannel(Channel):
    id = "carbon"
    label = "Carbon price -> OG fiscal revenue + CLEWS EmissionsPenalty"
    direction = POLICY
    theory_status = "structural_core"

    def apply(self, ctx, carbon_price=50.0, carbon_intensity=0.002, apply_to_og=True,
              apply_to_clews=True, recycle=False, allow_illustrative=False):
        c = ctx.country
        i_e = c.concordance.energy_good_index
        p = ctx.og_reform
        cp = _fit(carbon_price, p.T)              # carbon price path (USD/tCO2)
        prov = {"carbon_price_mean": float(cp.mean()), "applied_to": []}
        if apply_to_og:
            # Consumption-side carbon tax on the energy good. UNITS (ad-valorem tau_c add-on =
            # carbon-cost-per-unit-good / price-per-unit-good): carbon_price is USD/tCO2 -> convert to
            # the OG numeraire via units.deflator (numeraire per USD); carbon_intensity is tCO2 per unit
            # of the OG energy good; base_pi is the good's price in the numeraire. So the ratio is
            # dimensionless ONLY once cp is in the numeraire. units.deflator is the (still-uncalibrated)
            # USD<->numeraire bridge -- at the default 1.0, USD is treated 1:1 as numeraire, so the
            # MAGNITUDE is illustrative until it is calibrated. OG has no energy in PRODUCTION, so this
            # prices only HOUSEHOLD energy (~1.4% of consumption); industrial carbon is unpriced here.
            base_pi = (np.asarray(ctx.base_tpi["p_i"])[:p.T, i_e] if ctx.base_tpi is not None
                       else np.ones(p.T))
            cp_num = cp * float(getattr(c.units, "deflator", 1.0))     # USD/tCO2 -> numeraire/tCO2
            dtau = cp_num * carbon_intensity / np.maximum(base_pi, 1e-9)
            if float(dtau.mean()) > 1.0 and not allow_illustrative:
                raise ValueError(
                    f"carbon: implied mean tau_c add-on {dtau.mean():.2f} (>100%) on the energy good -- "
                    "the USD->numeraire deflator (units.deflator) and/or carbon_intensity (tCO2 per unit "
                    "of the OG energy good) are uncalibrated, so this is not a real ad-valorem rate. "
                    "Calibrate them, or pass allow_illustrative=True to proceed with an explicitly "
                    "illustrative magnitude (do NOT report it as a policy result).")
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
              dose_response=None):
        c = ctx.country
        p = ctx.og_reform
        # The GBD burden is PM2.5-attributable, so scale the dose-response by the PM2.5 emission
        # reform/base ratio (c.health_emission), NOT CO2e -- a decarbonization reform moves CO2e and
        # PM2.5 by different ratios (e.g. CCS cuts CO2e but not PM2.5; coal->gas cuts PM2.5 sharply).
        species = getattr(c, "health_emission", None)
        er = signals.emissions_ratio(c.scenario.base_dir, c.scenario.reform_dir, c, species=species)
        demis = float(np.nanmean(er.values[:10])) - 1.0   # <0 == reform is cleaner (less PM2.5)
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
        # Dose-response multiplier M = energy mass share x CRF elasticity (data/pm25_health.json): maps a
        # POWER-sector PM2.5 emissions change to an AMBIENT-PM2.5 deaths/morbidity change. Power is only
        # ~10% of ambient PM2.5 and the CRF is concave, so M << 1 (PHL ~0.08); without it the channel
        # overstates the health effect ~12x. None -> M=1.0 (naive 1:1) with a loud guardrail.
        M = dose_response if dose_response is not None else getattr(c, "pm25_dose_response", None)
        if M is None:
            M = 1.0
            print(f"[guardrail] health: no calibrated emissions->deaths dose-response (M) for "
                  f"{gloc}; using M=1.0 (naive 1:1, overstates the effect). Add a row to "
                  "ogclews_link/data/pm25_health.json (see docs/design/emissions-to-health-dose-response.md).")
        M = float(M)
        prov = {"emissions_change": demis, "emissions_species": species or c.co2_emission,
                "dose_response_M": M, "affects": list(affects), "gbd_source": bool(gbd)}
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
                excess_deaths = float(total_pollution_deaths) * M * demis    # total x dose-response x emissions
                target_src = ("GBD total x M x emissions change" if gbd else "explicit total x M x emissions change")
            else:
                excess_deaths = _PLACEHOLDER_PM25_DEATHS * M * demis         # demis<0 -> lives saved
                target_src = "PLACEHOLDER total x M x emissions change (see DATA.md)"
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
            benefit = -morbidity_response * M * demis     # cleaner (demis<0) -> higher productivity; M scales
                                                          # the power-sector emissions change to the ambient effect
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
                "placeholder is an illustrative elderly-skewed shape only. The emissions->deaths "
                "dose-response M = energy mass share x CRF elasticity (data/pm25_health.json; PHL ~0.08, "
                "from McDuffie 2021) -- power is ~10% of ambient PM2.5 and the CRF is concave, so M<<1; "
                "M=1.0 with a guardrail if a country lacks a row. The morbidity productivity elasticity "
                "reuses M as a proxy. Pollution deaths skew elderly, so expect a weaker mortality->GDP "
                "channel than the working-age HIV case."]


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


def register_all():
    for cls in (EnergyPriceChannel, InvestmentChannel, CapitalIntensityChannel, CapitalDemandChannel,
                CarbonChannel, DiscountRateChannel, HealthChannel, DemandChannel):
        try:
            register(cls())
        except ValueError:
            pass  # idempotent


register_all()
