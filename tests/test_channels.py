"""Transform-level tests: exercise every channel's math on array fixtures (no ogcore, no
solve) and the real CLEWS readers against actual files. Run with the OG-PHL venv:

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python tests/test_channels.py
"""
from __future__ import annotations

import os
import types

import numpy as np

from ogclews_link import channels, report, signals  # noqa: F401
from ogclews_link.country import PHL
from ogclews_link.framework import ExperimentContext, preflight

T, S, J, M, I = 20, 8, 7, 4, 5
TS = T + S
I_E, M_E = PHL.concordance.energy_good_index, PHL.concordance.energy_industry_index
HAVE_CLEWS = os.path.isdir(PHL.scenario.base_dir) and os.path.isdir(PHL.scenario.reform_dir)
_MUIOGO_RUN = "/Users/mlafleur/Projects/MUIOGO/WebAPP/DataStorage/CLEWs Demo/res/REF"
_GBD_HIV_CSV = ("/Users/mlafleur/Projects/CostOfDisease/source/JDE/hiv-data/"
                "IHME-GBD_2023_DATA-ddf37f70-1/IHME-GBD_2023_DATA-ddf37f70-1.csv")


def _params():
    io = np.full((I, M), 0.25)
    io[I_E, M_E] = 0.107
    return types.SimpleNamespace(
        T=T, J=J, M=M, I=I, baseline=False,
        tau_c=np.full((TS, I), 0.12), Z=np.ones((TS, M)),
        gamma=np.full(M, 0.53785), gamma_g=np.full(M, 0.05),   # per-industry, time-invariant (1-D, M)
        alpha_I=np.full(TS, 0.02), alpha_T=np.full(TS, 0.05), alpha_bs_I=np.ones(TS),
        c_min=np.zeros(I), e=np.ones((T, S, J)), chi_n=np.ones((TS, S)), io_matrix=io,
        inv_tax_credit=np.zeros((TS, M)), delta_tau=np.zeros((TS, M)), tau_b=np.full((TS, M), 0.25))


def _tpi(scale=1.0):
    return {"C_i": np.full((T, I), 10.0) * scale, "p_i": np.full((T, I), 1.0),
            "Y": np.full(T, 100.0), "Y_m": np.full((T, M), 25.0) * scale,
            "c_i": np.ones((T, I, S, J)) * scale, "c": np.ones((T, S, J)) * scale,
            "r_p": np.full(T, 0.05), "cons_tax_revenue": np.full(T, 1.0),  # (T,) like real OG
            "resource_constraint_error": np.full(T, 1e-6)}


def _ctx(with_reform=False):
    ctx = ExperimentContext(country=PHL, og_reform=_params(), base_tpi=_tpi(1.0))
    if with_reform:
        ctx.reform_tpi = _tpi(1.05)  # +5% activity
    return ctx


# --- tests ----------------------------------------------------------------------

def test_registry():
    for name in ["energy_price", "investment", "capital_intensity", "energy_capex", "carbon_tax",
                 "emit_carbon_penalty", "emit_discount_rate", "health", "emit_energy_demand"]:
        assert callable(getattr(channels, name)), name


def test_energy_capex_itc():
    # the ITC (capital-demand) channel applies an investment tax credit to the ENERGY industry only
    ctx = _ctx()
    channels.energy_capex(ctx, inv_tax_credit=0.20)
    itc = ctx.og_reform.inv_tax_credit
    assert itc[0, M_E] == 0.20
    assert all(itc[0, m] == 0.0 for m in range(M) if m != M_E)


def test_energy_price_controlled():
    ctx = _ctx()
    prov = channels.energy_price(ctx, price_ratio=1.20)
    tau = np.asarray(ctx.og_reform.tau_c)[0, I_E]
    assert abs((1 + tau) - 1.20 * 1.12) < 1e-9, (tau, prov)  # (1+tau_new) = ratio*(1+tau_base)


def test_energy_price_recycle_bumps_transfers():
    ctx = _ctx()
    a0 = np.asarray(ctx.og_reform.alpha_T).copy()
    prov = channels.energy_price(ctx, price_ratio=1.20, recycle=True)
    assert prov["recycled_pct_gdp"] is not None and prov["recycled_pct_gdp"] > 0
    assert np.asarray(ctx.og_reform.alpha_T)[0] > a0[0]


def test_energy_price_cmin():
    ctx = _ctx()
    channels.energy_price(ctx, price_ratio=1.10, energy_cmin=0.005)
    assert np.asarray(ctx.og_reform.c_min)[I_E] == 0.005


def test_ss_tail_persistence(monkeypatch):
    # permanent policy (carbon tax, recycled transfers) must reach the SS tail T:T+S;
    # temporary transition capex (investment) must taper to baseline there.
    ctx = _ctx()
    channels.carbon_tax(ctx, carbon_price=50.0, carbon_intensity=0.01, recycle=False)
    assert np.asarray(ctx.og_reform.tau_c)[-1, I_E] > 0.12, "carbon tau_c must persist into SS tail"
    ctx2 = _ctx()
    channels.energy_price(ctx2, price_ratio=1.20, recycle=True)
    assert np.asarray(ctx2.og_reform.alpha_T)[-1] > 0.05, "recycled alpha_T must persist into SS tail"
    # investment is public-infra-only and PHL/PEP has ~0 grid capex, so inject a synthetic non-zero
    # public-infra increment to actually exercise the finite-flow taper.
    import pandas as pd
    from ogclews_link import signals as _sig
    yrs = list(range(2026, 2054))
    monkeypatch.setattr(_sig, "power_capex_increment", lambda *a, **k: pd.Series([5000.0] * len(yrs), index=yrs))
    ctx3 = _ctx()
    a0 = np.asarray(ctx3.og_reform.alpha_I).copy()
    capex = _sig.public_capex_pct_gdp(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL,
                                      og_start_year=PHL.scenario.og_start_year, T=ctx3.og_reform.T)
    channels.investment(ctx3, capex, persist=False)
    assert np.asarray(ctx3.og_reform.alpha_I)[-1] == a0[-1], "temporary investment must taper in SS tail"
    assert not np.allclose(np.asarray(ctx3.og_reform.alpha_I)[:5], a0[:5]), "transition years must move"


def test_empty_signal_no_crash():
    import pandas as pd

    from ogclews_link.signals import _align_to_start, _fit
    assert _fit(np.array([]), 5).shape == (5,)                 # empty -> zeros, no IndexError
    s = pd.Series([1.0, 1.1], index=[2020, 2021])
    assert _align_to_start(s, 2026, 8).shape == (8,)           # start_year past the series -> zeros


def test_carbon_both_sides():
    ctx = _ctx()
    # units-sane illustrative intensity (50 USD/tCO2 * 0.005 = 25% add-on, < the 100% hard-block)
    channels.carbon_tax(ctx, carbon_price=50.0, carbon_intensity=0.005, recycle=True)
    channels.emit_carbon_penalty(ctx, carbon_price=50.0)
    assert np.asarray(ctx.og_reform.tau_c)[0, I_E] > 0.12          # OG carbon tax raised energy tau_c
    assert "EmissionsPenalty" in ctx.clews_inputs                  # CLEWS side written


def test_carbon_blocks_absurd_tax():
    import pytest
    # carbon_intensity=0.5 with the uncalibrated deflator implies a ~2500% tau_c -> must hard-raise,
    # not silently apply a meaningless tax.
    with pytest.raises(ValueError):
        channels.carbon_tax(_ctx(), carbon_price=50.0, carbon_intensity=0.5)
    # ...but an explicit illustrative override is allowed:
    ctx = _ctx()
    channels.carbon_tax(ctx, carbon_price=50.0, carbon_intensity=0.5, allow_illustrative=True)
    assert np.asarray(ctx.og_reform.tau_c)[0, I_E] > 0.12


def test_discount_rate_postsolve():
    ctx = _ctx(with_reform=True)  # the emit_ channel forwards the REFORM equilibrium rate
    prov = channels.emit_discount_rate(ctx, rate_key="r_p")
    assert ctx.clews_inputs["DiscountRate"]["rate"] == 0.05
    assert prov["clews_discount_rate"] == 0.05


def test_demand_postsolve():
    ctx = _ctx(with_reform=True)
    ar = signals.activity_ratio(ctx.base_tpi, ctx.reform_tpi, driver="Y_m", og_index=M_E)
    prov = channels.emit_energy_demand(ctx, ar, driver="Y_m")
    assert abs(prov["mean_ratio"] - 1.05) < 1e-9                   # +5% activity -> +5% demand
    assert "Demand" in ctx.clews_inputs


def test_guardrails_present():
    assert preflight(["carbon_tax", "emit_carbon_penalty"])       # one-price discipline message
    assert preflight(["energy_price", "carbon_tax"])              # double-count warning


def test_investment_public_infra_only():
    # public-infra-only: PHL/PEP has NO grid (T&D) capex delta, so the public-investment channel
    # correctly contributes ~nothing (private generation capex's effect rides the energy channel).
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    a0 = np.asarray(ctx.og_reform.alpha_I).copy()
    capex = signals.public_capex_pct_gdp(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL,
                                         og_start_year=PHL.scenario.og_start_year, T=ctx.og_reform.T)
    prov = channels.investment(ctx, capex, target="alpha_I")
    assert "cumulative_pct_gdp" in prov
    assert abs(prov["cumulative_pct_gdp"]) < 1e-9                  # no public-infra capex delta
    assert np.allclose(np.asarray(ctx.og_reform.alpha_I), a0)      # alpha_I unchanged (honest ~0)


# --- #2b capital intensity (gamma_energy) lever + calibration + channel ---------

def test_capital_intensity_lever_scale():
    from ogclews_link import policy_levers
    p = _params()
    prov = policy_levers.set_capital_intensity(p, M_E, gamma_scale=1.122)
    assert abs(np.asarray(p.gamma)[M_E] - 0.53785 * 1.122) < 1e-9     # energy gamma scaled
    for m in range(M):                                               # every OTHER industry untouched
        if m != M_E:
            assert abs(np.asarray(p.gamma)[m] - 0.53785) < 1e-12
    # labor share is the residual 1 - gamma - gamma_g (no separate parameter)
    assert abs(prov["labor_share_new"] - (1 - 0.53785 * 1.122 - 0.05)) < 1e-9
    assert prov["mode"] == "scale" and prov["gamma_old"] == 0.53785


def test_capital_intensity_lever_target_and_identity():
    from ogclews_link import policy_levers
    p = _params()
    prov = policy_levers.set_capital_intensity(p, M_E, gamma_target=0.60)
    assert abs(np.asarray(p.gamma)[M_E] - 0.60) < 1e-12
    # gamma + gamma_g + labor == 1 by construction
    assert abs(prov["gamma_new"] + prov["gamma_g"] + prov["labor_share_new"] - 1.0) < 1e-12


def test_capital_intensity_lever_blocks_infeasible():
    import pytest
    from ogclews_link import policy_levers
    # gamma 0.99 + gamma_g 0.05 -> labor share -0.04 < floor: a <=0 labor exponent OG-Core won't catch
    with pytest.raises(ValueError):
        policy_levers.set_capital_intensity(_params(), M_E, gamma_target=0.99)
    with pytest.raises(ValueError):                                  # scale big enough to break the floor
        policy_levers.set_capital_intensity(_params(), M_E, gamma_scale=1.8)
    with pytest.raises(ValueError):                                  # gamma > 1
        policy_levers.set_capital_intensity(_params(), M_E, gamma_target=1.2)


def test_capital_intensity_lever_requires_exactly_one():
    import pytest
    from ogclews_link import policy_levers
    with pytest.raises(ValueError):                                  # neither
        policy_levers.set_capital_intensity(_params(), M_E)
    with pytest.raises(ValueError):                                  # both
        policy_levers.set_capital_intensity(_params(), M_E, gamma_target=0.6, gamma_scale=1.1)


def test_capital_intensity_channel_explicit():
    ctx = _ctx()
    g0 = float(np.asarray(ctx.og_reform.gamma)[M_E])
    prov = channels.capital_intensity(ctx, gamma_scale=1.122)       # caller-sourced scale
    assert float(np.asarray(ctx.og_reform.gamma)[M_E]) > g0
    assert prov["gamma_new"] > prov["gamma_old"]


def test_capital_intensity_validate():
    # single-channel framing now lives in the docstring; cross-channel cautions in preflight()
    assert "factor-SHARE" in (channels.capital_intensity.__doc__ or "")
    msgs2 = preflight(["capital_intensity", "investment"])
    assert any("COMPLEMENTARY" in m for m in msgs2)                  # vs the public-investment channel


def test_capital_cost_share_reader():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    sb = signals.capital_cost_share(PHL.scenario.base_dir, PHL, window=(2026, 2035))
    sr = signals.capital_cost_share(PHL.scenario.reform_dir, PHL, window=(2026, 2035))
    assert 0.0 < sb < 1.0 and 0.0 < sr < 1.0
    cal = signals.capital_intensity_ratio(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL)
    assert cal["ratio"] > 1.0                                        # PEP mix more capital-intensive near-term
    assert abs(cal["ratio"] - sr / sb) < 1e-9


def test_capital_intensity_channel_calibrates_from_clews():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    g0 = float(np.asarray(ctx.og_reform.gamma)[M_E])
    cal = signals.capital_intensity_ratio(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL,
                                          window=(PHL.scenario.og_start_year, PHL.scenario.og_start_year + 9))
    prov = channels.capital_intensity(ctx, gamma_scale=cal["ratio"])  # caller sources from CLEWS
    assert cal["ratio"] > 1.0
    assert float(np.asarray(ctx.og_reform.gamma)[M_E]) > g0 and prov["labor_share_new"] > 0


def test_health_reads_clews():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    e0 = np.asarray(ctx.og_reform.e).copy()
    prov = channels.health(ctx, affects=("mortality", "e"))
    assert "emissions_change" in prov
    shock = ctx.extras.get("health_shock")                        # disease_pop spec for the runtime
    assert shock is not None and "excess_deaths" in shock and len(shock["profile"]) == 100
    assert shock["rc_ss"] == PHL.rc_ss                            # scoped SS tolerance routed to the reform
    assert shock["excess_deaths"] < 0                             # PHL reform is cleaner -> lives saved (negative)
    assert not np.allclose(np.asarray(ctx.og_reform.e), e0)       # morbidity productivity path moved


def test_health_dose_response_multiplier():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    # M = energy mass share x CRF elasticity scales the power-emissions change to the ambient effect.
    p1 = channels.health(_ctx(), affects=("mortality",), total_pollution_deaths=43951.0, dose_response=1.0)
    pm = channels.health(_ctx(), affects=("mortality",), total_pollution_deaths=43951.0, dose_response=0.082)
    assert pm["dose_response_M"] == 0.082
    assert abs(pm["mortality_excess_deaths"] / p1["mortality_excess_deaths"] - 0.082) < 1e-9  # linear in M
    # default (no arg) uses the calibrated PHL value from the data file, not the naive 1:1
    dflt = channels.health(_ctx(), affects=("mortality",), total_pollution_deaths=43951.0)
    assert dflt["dose_response_M"] == PHL.pm25_dose_response and PHL.pm25_dose_response < 0.2


def test_health_profile_shape():
    from ogclews_link import health_profile
    h = health_profile.placeholder_profile()
    assert h.shape == (100,) and abs(h.max() - 1.0) < 1e-9        # peak-1 relative shape
    assert h[80] > h[30]                                          # elderly-skewed (pollution mortality)


def test_disease_pop_bidirectional_calibration():
    # Bidirectional brentq: a positive target -> positive shock_scale (add deaths); a negative
    # target -> negative shock_scale (save lives). No OG solve -- pure construction vs the vendored
    # (CostOfDisease) total_deaths. Uses the in-repo _demog, so it actually exercises the dependency
    # (no external-path skip).
    from ogclews_link import _demog, health_pop, health_profile

    nage, ny = 100, 5
    s = np.arange(nage)
    mort = np.tile(0.001 + 0.004 * (s / 99.0) ** 3, (ny, 1))      # rises with age, in (0,1)
    fert = np.zeros((ny, nage)); fert[:, 15:45] = 0.05
    imm = np.zeros((ny, nage))
    infmort = np.full(ny, 0.02)
    pop = (1e6 * np.exp(-s / 50.0))[None, :]                       # (1, nage)
    h = health_profile.placeholder_profile(nage)
    base = _demog.total_deaths(pop, fert, mort, infmort, imm, num_years=ny)[ny - 1].sum()

    for target in (+5000.0, -5000.0):
        scale, path = health_pop.calibrate_shock_scale(
            target, pop, fert, mort, infmort, imm, h, ny, _demog.total_deaths)
        realized = _demog.total_deaths(pop, fert, path, infmort, imm, num_years=ny)[ny - 1].sum() - base
        assert (scale > 0) == (target > 0), (target, scale)        # scale sign tracks target sign
        assert abs(realized - target) < 1.0, (target, realized)    # brentq hit the signed target
        assert path.min() >= 0.0 and path.max() <= 1.0             # clip floor + ceiling respected


def test_disease_pop_nonmonotone_bracketing():
    # REGRESSION: realized year-ny excess deaths are NOT monotone in shock_scale (survivorship
    # feedback + the 0.0 clip), so the max achievable excess is at a FINITE interior scale. The old
    # doubling-walk assumed monotonicity and could (a) falsely reject a feasible target whose only
    # bracket endpoint sits past the turning point, or (b) land on a non-minimal root. The outward
    # scan must return the SMALLEST-|scale| root and report the true achievable extremum on
    # infeasibility. Driven by a controlled non-monotone total_deaths so the curve shape is exact.
    from ogclews_link import health_pop

    nage, ny = 8, 3
    mort = np.full((ny, nage), 0.10)
    fert = np.zeros((ny, nage)); imm = np.zeros((ny, nage)); infmort = np.zeros(ny)
    pop = np.full((1, nage), 1.0)
    h = np.ones(nage)                                             # so mean(final-row shock) == 0.1 + scale

    def nonmono(pop, fert, m, infmort, imm, num_years):
        # year-(ny-1) deaths = a parabola in the mean shocked rate x, peaking at x=0.2: excess rises
        # to an interior max at scale=+0.1 then FALLS -- exactly the shape the doubling-walk mishandles.
        x = float(m[-1].mean())
        val = -((x - 0.2) ** 2) * 1e6 + 4e4
        d = np.zeros((num_years, m.shape[1])); d[-1, 0] = val
        return d

    base = nonmono(pop, fert, mort, infmort, imm, ny)[ny - 1].sum()  # x=0.1 -> val 3e4
    # +5000 is reachable on BOTH the rising (scale~0.029) and falling (scale~0.171) branch; the
    # solver must return the smaller-|scale| (rising) root, and must NOT falsely reject it.
    scale, path = health_pop.calibrate_shock_scale(5000.0, pop, fert, mort, infmort, imm, h, ny, nonmono)
    realized = nonmono(pop, fert, path, infmort, imm, ny)[ny - 1].sum() - base
    assert 0.0 < scale < 0.1 and abs(realized - 5000.0) < 1.0, (scale, realized)

    # a target beyond the interior maximum (~1e4 excess) is infeasible -> raise with the achievable max.
    try:
        health_pop.calibrate_shock_scale(5e4, pop, fert, mort, infmort, imm, h, ny, nonmono)
        raise AssertionError("expected RuntimeError for a target past the interior maximum")
    except RuntimeError as e:
        assert "exceeds the achievable" in str(e)


def test_morbidity_age_profile():
    # The morbidity (effective-labor) effect must accept an AGE distribution, mirroring mortality's
    # h(s): a non-uniform shape concentrates the productivity gain by age; the default is uniform.
    from ogclews_link import health_profile
    E, S = 20, 80
    # default in the channel is uniform (np.ones(S) inline -> "all active ages equal"); a non-uniform
    # shape concentrates the gain by age:
    wap = health_profile.working_age_profile(E, S)
    assert wap.shape == (S,) and abs(wap.max() - 1.0) < 1e-9         # peak-1 shape over active periods
    assert wap[:5].mean() < wap[20:40].mean()                       # prime-age weighted above the oldest
    # a full-age-grid (E+S) input maps to the active tail [E:]; arbitrary length interpolates to S
    full = np.linspace(0.0, 1.0, E + S)
    assert health_profile.morbidity_shape_to_S(full, S, E).shape == (S,)
    assert health_profile.morbidity_shape_to_S(np.ones(37), S, E).shape == (S,)


def test_vendored_demog_selfcontained():
    # Portability: the demographic helpers + PHL calibration are vendored in-repo (no absolute-path
    # loads of CostOfDisease / CLEWS-OG). They import and run on numpy alone.
    from ogclews_link import _calibration, _demog
    assert "Electricity" in _calibration.PROD_DICT and _calibration.PROD_DICT["Electricity"] == ["aelec"]
    ny, nage = 5, 100
    mort = np.full((ny, nage), 0.01)
    fert = np.zeros((ny, nage)); fert[:, 20:40] = 0.05
    imm = np.zeros((ny, nage)); infmort = np.full(ny, 0.02)
    pop = np.full((1, nage), 1000.0)
    d = _demog.total_deaths(pop, fert, mort, infmort, imm, num_years=ny)
    assert d.shape == (ny, nage) and np.all(d >= 0)
    assert _demog.extrapolate_demographics(mort[:2], ny).shape == (ny, nage)


def test_gbd_profile_and_total_from_real_export():
    # Validate the GBD readers against a REAL IHME export (HIV/South-Africa stands in for the PHL
    # ambient-PM2.5 pull -- identical format) so the pipeline is proven before the real CSV lands.
    from ogclews_link import health_profile
    if not os.path.isfile(_GBD_HIV_CSV):
        print("  (skip: GBD export absent)"); return
    h = health_profile.build_profile_from_gbd(
        _GBD_HIV_CSV, location_name="South Africa", year=2023,
        key_col="cause_name", key_value="HIV/AIDS")           # PHL PM2.5 -> rei_name/Ambient... instead
    assert h.shape == (100,) and abs(h.max() - 1.0) < 1e-9       # peak-1 age shape from real GBD rates
    tot = health_profile.total_deaths_from_gbd(
        _GBD_HIV_CSV, location_name="South Africa", year=2023,
        key_col="cause_name", key_value="HIV/AIDS")
    assert tot > 0                                               # total deaths (excess_deaths target)


def test_gbd_morbidity_readers_from_real_export():
    # Validate the morbidity YLD readers against the real PHL ambient-PM2.5 GBD export (if present).
    from ogclews_link import health_profile
    csv = PHL.gbd_burden_csv
    if not csv or not os.path.isfile(csv):
        print("  (skip: GBD burden export absent)"); return
    g = health_profile.build_morbidity_profile_from_gbd(csv, "Philippines", 2023)
    assert g.shape == (100,) and abs(g.max() - 1.0) < 1e-9       # peak-1 working-age YLD shape
    assert g[20] < 0.05 and g[25] < g[60] < g[90]               # ~0 young, RISES with age (vs elderly deaths)
    rate = health_profile.morbidity_yld_rate_from_gbd(csv, "Philippines", 2023)
    yld = health_profile.total_yld_from_gbd(csv, "Philippines", 2023)
    assert rate > 0 and yld > 0                                  # magnitude (peak rate) + provenance total


def test_clews_capex_reader():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    inc = signals.power_capex_increment(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL)
    assert len(inc) > 10 and np.isfinite(inc.values).all()
    cap = signals.read_clews_matrix(signals._find(PHL.scenario.reform_dir, "CapitalInvestment"))
    assert any(PHL.is_power(t) for t in cap.index)                 # power techs parsed


def test_report_transforms():
    b, r = _tpi(1.0), _tpi(1.0)
    r["C_i"] = r["C_i"] * 0.83                                     # ~ -17% energy demand
    dr = report.demand_response(b, r, I_E)
    assert abs(dr[0] - (-17.0)) < 0.5
    inc = report.incidence(b, r, I_E)
    assert inc["energy_by_J"].shape == (J,)


def test_commodity_shadow_price_dual():
    # MUIOGO exports the annual energy commodity-balance dual discounted to start-year PV
    # (raw * (1+DR)^(y-start+0.5)); the reader recovers the raw marginal and forms a ratio.
    import tempfile

    csv = ("r,f,y,EBb4_EnergyBalanceEachYear4_ICR,DiscountRate\n"
           "RE1,ELC,2020,1.520032676622447,0.05\n"   # = 1.4833681 * 1.05^0.5
           "RE1,ELC,2021,2.10,0.05\n"
           "RE1,GAS,2020,3.0,0.05\n")
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(csv); path = f.name
    try:
        s = signals.commodity_shadow_price(path, fuel="ELC")              # undiscount by default
        assert abs(s.loc[2020] - 1.520032676622447 / (1.05 ** 0.5)) < 1e-6
        raw = signals.commodity_shadow_price(path, fuel="ELC", undiscount=False)
        assert abs(raw.loc[2020] - 1.520032676622447) < 1e-9
        default = signals.commodity_shadow_price(path)                    # default = ELC* prefix
        assert 2020 in default.index and 2021 in default.index
        ratio = signals.commodity_shadow_price_ratio(path, path, fuel="GAS")
        assert abs(ratio.loc[2020] - 1.0) < 1e-9                          # self-ratio is 1
    finally:
        os.remove(path)


def test_energy_price_dual_source():
    # price_source="dual" drives the energy wedge from the commodity-balance dual RATIO (not
    # the controlled shock). Stub the reader so the branch + alignment are exercised with no
    # CLEWS files and no OG solve.
    import pandas as pd

    ctx = _ctx()
    sy = PHL.scenario.og_start_year
    share = float(np.asarray(ctx.og_reform.io_matrix)[I_E, M_E])      # electricity's share of the energy good
    n = np.asarray(ctx.og_reform.tau_c).shape[0]
    orig = signals.commodity_shadow_price_ratio
    signals.commodity_shadow_price_ratio = lambda b, r, **k: pd.Series([1.20, 1.20], index=[sy, sy + 1])
    try:
        # sourcing (dispatch + dilution + align) now lives in signals.energy_price_ratio; the channel
        # just applies the ready good-level ratio.
        ratio = signals.energy_price_ratio("dual", base_dir=PHL.scenario.base_dir,
                                           reform_dir=PHL.scenario.reform_dir, share=share,
                                           og_start_year=sy, n=n)
        channels.energy_price(ctx, price_ratio=ratio)
    finally:
        signals.commodity_shadow_price_ratio = orig
    tau = np.asarray(ctx.og_reform.tau_c)[0, I_E]
    # electricity dual ratio is diluted by `share` into the broader energy good, then folded into (1+tau)
    assert abs((1 + tau) - (1 + share * 0.20) * 1.12) < 1e-9, tau


def test_muiogo_run_reader():
    from ogclews_link import muiogo_run

    if not os.path.isdir(_MUIOGO_RUN):
        print("  (skip: MUIOGO sample run absent)"); return
    csv_dir = muiogo_run.find_run_csv_dir(_MUIOGO_RUN)
    assert os.path.basename(csv_dir) == "csv"
    fuels = muiogo_run.electricity_fuels(csv_dir)
    assert fuels and all(f.upper().startswith("ELC") for f in fuels)   # ELC001/ELC002
    assert muiogo_run.verify_run(csv_dir)[muiogo_run._EBB4] is True
    s = signals.commodity_shadow_price(csv_dir, fuel=fuels[0])         # reader consumes the run dir
    assert len(s) > 0 and np.isfinite(s.values).all()


def test_run_manifest():
    import json
    import tempfile

    from ogclews_link import experiments
    from ogclews_link.manifest import write_run_manifest

    ctx = _ctx()
    ctx.log("energy_price", source="controlled_+20%", dtau_mean=0.224)
    exp = experiments.get("energy_price")
    with tempfile.TemporaryDirectory() as d:
        path = write_run_manifest(d, exp, PHL, ctx, clews_run="/some/muiogo/run")
        m = json.load(open(path))
    assert m["experiment"]["name"] == "energy_price"
    assert m["country"] == "Philippines"
    assert m["scenario"]["name"] == "PEP_vs_Base"
    assert m["clews_run"] == "/some/muiogo/run"
    assert m["channels"][0]["id"] == "energy_price" and len(m["provenance"]) == 1


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
