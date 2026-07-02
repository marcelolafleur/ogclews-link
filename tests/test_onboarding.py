"""Share-readiness surface: declarative country onboarding, the loud config-trap guardrails, the
health-channel skip path, the MUIOGO export preflight, and the write-back region/commodity threading.
All numpy/pandas-only (no ogcore) -- runs in the link env."""
import json
import os
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from ogclews_link import channels, clews_io, muiogo_run, signals
from ogclews_link.country import (PHL, config_from_dict, country_registry, resolve_country)


# --- fixtures -------------------------------------------------------------------

ENTRY = {"name": "Testland", "un_code": "999", "og_repo": "og-tst", "gdp_musd": 100000.0,
         "og_start_year": 2026, "power_prefix": "TST_POW", "electricity_fuel": "TST_HOU_ELE",
         "clews_region": "REGA", "co2_emission": "CO2EQ",
         "units": {"base_year": 2021, "deflator": 2.0}, "scenario": {"years": [2020, 2050]}}


def _write_capex(d, rows):
    """A long-format CapitalInvestment CSV: r,t,y,v."""
    path = os.path.join(d, "CapitalInvestment.csv")
    pd.DataFrame(rows, columns=["r", "t", "y", "v"]).to_csv(path, index=False)
    return path


def _write_ebb4(d, fuels=("TST_HOU_ELE",), regions=("RE1",), years=range(2026, 2031), value=5.0):
    rows = [{"r": r, "f": f, "y": y, "EnergyBalanceEachYear4": value, "DiscountRate": 0.0}
            for r in regions for f in fuels for y in years]
    path = os.path.join(d, "EBb4_EnergyBalanceEachYear4_ICR.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _write_emissions(d, species=(("CO2", 10.0), ("CO2EQ", 100.0)), years=range(2026, 2031)):
    rows = [{"r": "RE1", "t": "TST_POW_X", "e": e, "m": 1, "y": y, "v": v}
            for e, v in species for y in years]
    path = os.path.join(d, "AnnualTechnologyEmissionByMode.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


# --- declarative country config ---------------------------------------------------

def test_phl_resolves_by_every_key():
    for sel in ("phl", "Philippines", "608", "og-phl"):
        assert resolve_country(sel) is PHL


def test_json_country_loads_and_resolves(tmp_path):
    f = tmp_path / "countries.json"
    f.write_text(json.dumps({"countries": [ENTRY]}))
    cc = resolve_country("og-tst", config_file=str(f))
    assert cc.name == "Testland" and cc.power_prefix == "TST_POW"
    assert cc.clews_region == "REGA" and cc.co2_emission == "CO2EQ"
    assert cc.units.base_year == 2021 and cc.units.deflator == 2.0
    assert cc.scenario.og_start_year == 2026 and cc.scenario.years[-1] == 2050
    # and by name / code too
    assert resolve_country("testland", config_file=str(f)).og_repo == "og-tst"
    assert resolve_country("999", config_file=str(f)).og_repo == "og-tst"


def test_bare_list_countries_file(tmp_path):
    f = tmp_path / "countries.json"
    f.write_text(json.dumps([ENTRY]))
    assert resolve_country("og-tst", config_file=str(f)).name == "Testland"


def test_required_keys_enforced():
    with pytest.raises(ValueError, match="power_prefix"):
        config_from_dict({k: v for k, v in ENTRY.items() if k != "power_prefix"})


def test_unknown_key_rejected():
    with pytest.raises(ValueError, match="power_prefx"):
        config_from_dict({**ENTRY, "power_prefx": "TYPO"})


def test_explicit_missing_countries_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        country_registry(config_file=str(tmp_path / "nope.json"))


def test_unknown_selector_lists_available():
    with pytest.raises(SystemExit, match="available"):
        resolve_country("atlantis")


def test_unset_power_prefix_fails_loud():
    cc = config_from_dict(ENTRY)
    object.__setattr__(cc, "power_prefix", None)
    with pytest.raises(ValueError, match="power_prefix"):
        cc.is_power("TST_POW_PP_SOL")


def test_example_countries_file_is_valid():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "ogclews_countries.example.json")) as f:
        data = json.load(f)
    cc = config_from_dict(data["countries"][0])
    assert cc.power_prefix and cc.og_repo and cc.scenario.og_start_year


# --- guardrail: power_prefix zero-match -------------------------------------------

def test_capex_wrong_prefix_raises_naming_codes(tmp_path):
    base, reform = tmp_path / "b", tmp_path / "r"
    for d in (base, reform):
        d.mkdir()
        _write_capex(str(d), [("RE1", "OTHER_POW_PP", 2026, 1.0)])
    cc = config_from_dict(ENTRY)
    with pytest.raises(ValueError) as e:
        signals.power_capex_increment(str(base), str(reform), cc)
    assert "TST_POW" in str(e.value) and "OTHER_POW_PP" in str(e.value)


def test_capex_public_only_no_markers_warns_and_zeroes(tmp_path, capsys):
    base, reform = tmp_path / "b", tmp_path / "r"
    for d, v in ((base, 1.0), (reform, 3.0)):
        d.mkdir()
        _write_capex(str(d), [("RE1", "TST_POW_PP_SOL", 2026, v)])   # power, but no _TD tech
    cc = config_from_dict(ENTRY)
    inc = signals.power_capex_increment(str(base), str(reform), cc, public_only=True)
    assert float(inc.sum()) == 0.0
    assert "public marker" in capsys.readouterr().out


def test_capex_matching_prefix_gives_delta(tmp_path):
    base, reform = tmp_path / "b", tmp_path / "r"
    for d, v in ((base, 1.0), (reform, 3.0)):
        d.mkdir()
        _write_capex(str(d), [("RE1", "TST_POW_PP_SOL", 2026, v)])
    cc = config_from_dict(ENTRY)
    inc = signals.power_capex_increment(str(base), str(reform), cc)
    assert float(inc.loc[2026]) == pytest.approx(2.0)


# --- guardrail: exact emission species --------------------------------------------

def test_emissions_exact_species_no_substring_sum(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    _write_emissions(str(d))
    cc = config_from_dict({**ENTRY, "co2_emission": "CO2"})
    s = signals.emissions_by_year(str(d), cc)
    assert float(s.loc[2026]) == pytest.approx(10.0)     # CO2 only -- NOT 110 (CO2 + CO2EQ)


def test_emissions_missing_species_raises_listing_present(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    _write_emissions(str(d))
    cc = config_from_dict(ENTRY)                          # co2_emission = CO2EQ (present)
    with pytest.raises(ValueError) as e:
        signals.emissions_by_year(str(d), cc, species="PM2_5")
    assert "PM2_5" in str(e.value) and "CO2EQ" in str(e.value)


# --- guardrail: electricity dual fuel/region --------------------------------------

def test_dual_generic_elc_multimatch_raises(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    _write_ebb4(str(d), fuels=("ELC001", "ELC002"))
    with pytest.raises(ValueError, match="electricity_fuel"):
        signals.commodity_shadow_price(str(d))
    # a single ELC commodity still resolves via the generic fallback
    d2 = tmp_path / "s2"; d2.mkdir()
    _write_ebb4(str(d2), fuels=("ELC001",))
    assert not signals.commodity_shadow_price(str(d2)).empty


def test_dual_multi_region_warns_but_works(tmp_path, capsys):
    d = tmp_path / "s"; d.mkdir()
    _write_ebb4(str(d), fuels=("TST_HOU_ELE",), regions=("RE1", "RE2"))
    s = signals.commodity_shadow_price(str(d), fuel="TST_HOU_ELE")
    assert not s.empty
    assert "AVERAGED across regions" in capsys.readouterr().out


# --- price-source provenance -------------------------------------------------------

def test_energy_price_ratio_records_resolved_source(tmp_path):
    base, reform = tmp_path / "b", tmp_path / "r"
    for d in (base, reform):
        d.mkdir()
        _write_ebb4(str(d), fuels=("TST_HOU_ELE",))
    resolved = {}
    out = signals.energy_price_ratio("auto", base_dir=str(base), reform_dir=str(reform), share=1.0,
                                     og_start_year=2026, n=5, fuel="TST_HOU_ELE", resolved=resolved)
    assert resolved["requested"] == "auto" and resolved["kind"] == "dual"
    assert np.allclose(out, 1.0)                          # identical base/reform duals -> flat ratio


# --- health channel skip path ------------------------------------------------------

def _fake_ctx(country, tmp_path):
    country.scenario.base_dir = str(tmp_path / "b")
    country.scenario.reform_dir = str(tmp_path / "r")
    os.makedirs(country.scenario.base_dir, exist_ok=True)
    os.makedirs(country.scenario.reform_dir, exist_ok=True)
    ctx = SimpleNamespace(country=country, og_reform=None, extras={}, provenance=[],
                          clews_inputs={}, reform_tpi=None)
    ctx.log = lambda channel, **kv: (ctx.provenance.append({"channel": channel, **kv})
                                     or {"channel": channel, **kv})
    return ctx


def test_health_skips_when_no_emissions_export(tmp_path, capsys):
    ctx = _fake_ctx(config_from_dict(ENTRY), tmp_path)    # empty scenario dirs
    rec = channels.health(ctx)
    assert rec["skipped"] and "unavailable" in rec["reason"]
    assert "[skip] health" in capsys.readouterr().out


def test_health_skips_when_species_absent(tmp_path):
    ctx = _fake_ctx(config_from_dict(ENTRY), tmp_path)    # health_emission default PM2_5
    _write_emissions(ctx.country.scenario.base_dir)       # exports CO2/CO2EQ only
    _write_emissions(ctx.country.scenario.reform_dir)
    rec = channels.health(ctx)
    assert rec["skipped"] and "PM2_5" in rec["reason"]


# --- MUIOGO export preflight --------------------------------------------------------

def test_preflight_reports_missing_stems(tmp_path, capsys):
    d = tmp_path / "s"; d.mkdir()
    _write_ebb4(str(d))
    found = muiogo_run.preflight(str(d), label="base")
    out = capsys.readouterr().out
    assert found["EBb4_EnergyBalanceEachYear4_ICR"] is True
    assert found["CapitalInvestment"] is False
    assert "CapitalInvestment" in out and "missing" in out


# --- write-back region / commodity threading ---------------------------------------

def test_emit_carbon_penalty_uses_country_region(tmp_path):
    ctx = _fake_ctx(config_from_dict(ENTRY), tmp_path)
    ctx.og_reform = SimpleNamespace(T=5)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    assert ctx.clews_inputs["EmissionsPenalty"]["region"] == "REGA"
    assert ctx.clews_inputs["EmissionsPenalty"]["emission"] == "CO2EQ"


def test_write_demand_addresses_spec_region_and_fuel(tmp_path):
    spec = {"og_activity": "sector_output", "og_index": 2, "clews_fuel": "TST_HOU_ELE",
            "region": "REGA", "start_year": 2026, "ratio_by_period": [1.0, 1.01]}
    path = clews_io.write_demand(spec, str(tmp_path))
    df = pd.read_csv(path)
    assert set(df["REGION"]) == {"REGA"} and set(df["CLEWS_FUEL"]) == {"TST_HOU_ELE"}
