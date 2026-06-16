"""Transform-level tests: exercise every channel's math on array fixtures (no ogcore, no
solve) and the real CLEWS readers against actual files. Run with the OG-PHL venv:

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python tests/test_channels.py
"""
from __future__ import annotations

import os
import types

import numpy as np

from ogclews_link import channels, report, signals  # noqa: F401 (registers channels)
from ogclews_link.country import PHL
from ogclews_link.framework import ExperimentContext, all_channels, get

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
        alpha_I=np.full(TS, 0.02), alpha_T=np.full(TS, 0.05), alpha_bs_I=np.ones(TS),
        c_min=np.zeros(I), e=np.ones((T, S, J)), chi_n=np.ones((TS, S)), io_matrix=io)


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
    ids = set(all_channels())
    assert ids == {"energy_price", "investment", "carbon", "discount_rate", "health", "demand"}, ids


def test_energy_price_controlled():
    ctx = _ctx()
    prov = get("energy_price").apply(ctx, shock=0.20)
    tau = np.asarray(ctx.og_reform.tau_c)[0, I_E]
    assert abs((1 + tau) - 1.20 * 1.12) < 1e-9, (tau, prov)  # (1+tau_new) = ratio*(1+tau_base)


def test_energy_price_recycle_bumps_transfers():
    ctx = _ctx()
    a0 = np.asarray(ctx.og_reform.alpha_T).copy()
    prov = get("energy_price").apply(ctx, shock=0.20, recycle=True)
    assert prov["recycled_pct_gdp"] is not None and prov["recycled_pct_gdp"] > 0
    assert np.asarray(ctx.og_reform.alpha_T)[0] > a0[0]


def test_energy_price_cmin():
    ctx = _ctx()
    get("energy_price").apply(ctx, shock=0.10, energy_cmin=0.005)
    assert np.asarray(ctx.og_reform.c_min)[I_E] == 0.005


def test_ss_tail_persistence():
    # permanent policy (carbon tax, recycled transfers) must reach the SS tail T:T+S;
    # temporary transition capex (investment) must taper to baseline there.
    ctx = _ctx()
    get("carbon").apply(ctx, carbon_price=50.0, carbon_intensity=0.01, recycle=False)
    assert np.asarray(ctx.og_reform.tau_c)[-1, I_E] > 0.12, "carbon tau_c must persist into SS tail"
    ctx2 = _ctx()
    get("energy_price").apply(ctx2, shock=0.20, recycle=True)
    assert np.asarray(ctx2.og_reform.alpha_T)[-1] > 0.05, "recycled alpha_T must persist into SS tail"
    ctx3 = _ctx()
    a0 = np.asarray(ctx3.og_reform.alpha_I).copy()
    get("investment").apply(ctx3, public_only=False, persist=False)
    assert np.asarray(ctx3.og_reform.alpha_I)[-1] == a0[-1], "temporary investment must taper in SS tail"


def test_empty_signal_no_crash():
    import pandas as pd

    from ogclews_link.channels import _align_to_start, _fit
    assert _fit(np.array([]), 5).shape == (5,)                 # empty -> zeros, no IndexError
    s = pd.Series([1.0, 1.1], index=[2020, 2021])
    assert _align_to_start(s, 2026, 8).shape == (8,)           # start_year past the series -> zeros


def test_carbon_both_sides():
    ctx = _ctx()
    prov = get("carbon").apply(ctx, carbon_price=50.0, carbon_intensity=0.5, recycle=True)
    assert np.asarray(ctx.og_reform.tau_c)[0, I_E] > 0.12          # OG carbon tax raised energy tau_c
    assert "EmissionsPenalty" in ctx.clews_inputs                  # CLEWS side written
    assert set(prov["applied_to"]) == {"og_tau_c", "clews_emissions_penalty"}


def test_discount_rate_postsolve():
    ctx = _ctx()
    assert get("discount_rate").post_solve is True
    prov = get("discount_rate").apply(ctx, rate_key="r_p")
    assert ctx.clews_inputs["DiscountRate"]["rate"] == 0.05
    assert prov["clews_discount_rate"] == 0.05


def test_demand_postsolve():
    ctx = _ctx(with_reform=True)
    prov = get("demand").apply(ctx, driver="Y_m", elasticity=1.0)
    assert abs(prov["mean_ratio"] - 1.05) < 1e-9                   # +5% activity -> +5% demand
    assert "Demand" in ctx.clews_inputs


def test_guardrails_present():
    ctx = _ctx()
    assert get("carbon").validate(ctx, ["carbon"])                # one-price discipline message
    assert get("energy_price").validate(ctx, ["energy_price", "carbon"])  # double-count warning


def test_investment_reads_clews():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    a0 = np.asarray(ctx.og_reform.alpha_I).copy()
    prov = get("investment").apply(ctx, target="alpha_I", public_only=False)
    assert "cumulative_pct_gdp" in prov
    assert not np.allclose(np.asarray(ctx.og_reform.alpha_I), a0)  # alpha_I path moved


def test_health_reads_clews():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    e0 = np.asarray(ctx.og_reform.e).copy()
    prov = get("health").apply(ctx, affects=("mortality", "e"))
    assert "emissions_change" in prov
    shock = ctx.extras.get("health_shock")                        # disease_pop spec for the runtime
    assert shock is not None and "kappa" in shock and len(shock["profile"]) == 100
    assert not np.allclose(np.asarray(ctx.og_reform.e), e0)       # morbidity productivity path moved


def test_health_profile_shape():
    from ogclews_link import health_profile
    h = health_profile.placeholder_profile()
    assert h.shape == (100,) and abs(h.max() - 1.0) < 1e-9        # peak-1 relative shape
    assert h[80] > h[30]                                          # elderly-skewed (pollution mortality)


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
    orig = signals.commodity_shadow_price_ratio
    signals.commodity_shadow_price_ratio = lambda b, r, **k: pd.Series([1.20, 1.20], index=[sy, sy + 1])
    try:
        prov = get("energy_price").apply(ctx, price_source="dual")
    finally:
        signals.commodity_shadow_price_ratio = orig
    assert prov["source"] == "dual_shadow_price"
    share = float(np.asarray(ctx.og_reform.io_matrix)[I_E, M_E])      # electricity's share of the energy good
    tau = np.asarray(ctx.og_reform.tau_c)[0, I_E]
    # electricity dual ratio is diluted by `share` into the broader energy good, then folded into (1+tau)
    assert abs((1 + tau) - (1 + share * 0.20) * 1.12) < 1e-9, (tau, prov)


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
