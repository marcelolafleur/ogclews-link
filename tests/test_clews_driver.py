"""Transform-level tests for the CLEWS re-run seam (clews_driver): case copy, code->opaque-id
translation, demand patching, and interpreter resolution -- NO MUIOGO env, NO solve (the empirical
round-trip lives in experiments/seam_roundtrip.py and runs deliberately against the real case).
Run with the standalone link venv: ``uv run pytest tests/test_clews_driver.py``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ogclews_link import clews_driver


def _fixture_case(root: Path, name: str = "TinyCase") -> Path:
    """A minimal MUIOGO-shaped case: genData registries + RYC.json SAD rows for two commodities in
    two scenarios (mirrors the real layout read from Philippines_v9)."""
    case = root / name
    (case / "view").mkdir(parents=True)
    (case / "res" / "Base" / "csv").mkdir(parents=True)
    gd = {
        "osy-casename": name,
        "osy-comm": [{"CommId": "COM_aaa", "Comm": "PHL_HOU_ELE", "Desc": "hh elec", "UnitId": "PJ"},
                     {"CommId": "COM_bbb", "Comm": "PHL_AGR_ELE", "Desc": "agri elec", "UnitId": "PJ"}],
        "osy-tech": [{"TechId": "TEC_t1", "Tech": "PHL_POW_PP", "Desc": "pp"}],
        "osy-emis": [{"EmisId": "EMI_0", "Emis": "CO2e", "Desc": "co2"}],
        "osy-scenarios": [{"ScenarioId": "SC_0", "Scenario": "BASE", "Active": True},
                          {"ScenarioId": "SC_x", "Scenario": "ALT", "Active": True}],
    }
    (case / "genData.json").write_text(json.dumps(gd))
    ryc = {"SAD": {"SC_0": [{"CommId": "COM_aaa", "2020": 10.0, "2021": 20.0},
                            {"CommId": "COM_bbb", "2020": 5.0, "2021": 5.0}],
                   "SC_x": [{"CommId": "COM_aaa", "2020": 1.0, "2021": 1.0}]},
           "AAD": {"SC_0": [{"CommId": "COM_bbb", "2020": 7.0, "2021": 7.0}]}}
    (case / "RYC.json").write_text(json.dumps(ryc))
    (case / "view" / "resData.json").write_text(json.dumps(
        {"osy-cases": [{"Case": "Base", "CaseId": "CS_1", "Scenarios": [
            {"ScenarioId": "SC_0", "Active": True}]}]}))
    return case


def test_copy_case_stamps_name_and_preserves_source(tmp_path):
    _fixture_case(tmp_path)
    dst = clews_driver.copy_case(str(tmp_path), "TinyCase", "TinyCase__patch")
    gd = json.loads((Path(dst) / "genData.json").read_text())
    assert gd["osy-casename"] == "TinyCase__patch"                  # copy addressed by its own name
    src_gd = json.loads((tmp_path / "TinyCase" / "genData.json").read_text())
    assert src_gd["osy-casename"] == "TinyCase"                     # source untouched
    assert (Path(dst) / "view" / "resData.json").is_file()          # caserun records carried
    with pytest.raises(FileExistsError):
        clews_driver.copy_case(str(tmp_path), "TinyCase", "TinyCase__patch")
    clews_driver.copy_case(str(tmp_path), "TinyCase", "TinyCase__patch", overwrite=True)


def test_registry_translation_and_loud_miss(tmp_path):
    case = _fixture_case(tmp_path)
    reg = clews_driver.case_registry(str(case))
    assert reg["comm"]["PHL_HOU_ELE"] == "COM_aaa"
    assert reg["emis"]["CO2e"] == "EMI_0"
    with pytest.raises(KeyError) as e:
        clews_driver._lookup(reg, "comm", "NOPE")
    assert "PHL_AGR_ELE" in str(e.value)                            # the miss lists what exists


def test_scale_annual_demand_scalar(tmp_path):
    case = _fixture_case(tmp_path)
    prov = clews_driver.scale_annual_demand(str(case), "PHL_HOU_ELE", 1.10)
    ryc = json.loads((case / "RYC.json").read_text())
    row = ryc["SAD"]["SC_0"][0]
    assert row["2020"] == pytest.approx(11.0) and row["2021"] == pytest.approx(22.0)
    assert ryc["SAD"]["SC_0"][1]["2020"] == 5.0                     # other commodity untouched
    assert ryc["SAD"]["SC_x"][0]["2020"] == 1.0                     # other scenario untouched
    assert prov["rows"] == 1 and prov["mean_factor"] == pytest.approx(1.10)


def test_scale_annual_demand_per_year_map(tmp_path):
    case = _fixture_case(tmp_path)
    clews_driver.scale_annual_demand(str(case), "PHL_HOU_ELE", {"2021": 2.0})
    row = json.loads((case / "RYC.json").read_text())["SAD"]["SC_0"][0]
    assert row["2020"] == 10.0 and row["2021"] == 40.0             # only the mapped year scaled


def test_scale_annual_demand_loud_failures(tmp_path):
    case = _fixture_case(tmp_path)
    with pytest.raises(KeyError):
        clews_driver.scale_annual_demand(str(case), "PHL_HOU_ELE", 1.1, scenario="SC_missing")
    with pytest.raises(KeyError):
        clews_driver.scale_annual_demand(str(case), "CO2e", 1.1)   # an emission is not a commodity
    with pytest.raises(KeyError):                                   # commodity exists, no rows in AAD
        clews_driver.scale_annual_demand(str(case), "PHL_HOU_ELE", 1.1, param="AAD")


def test_scale_annual_demand_rejects_all_zero_rows(tmp_path):
    # Scaling a zero demand row is a silent downstream no-op (the empirical round-trip caught this
    # live: PHL_HOU_ELE carries 0 while PHL_HOU_ELEF carries the load) -- must fail loudly and name
    # the commodities that DO carry demand.
    case = _fixture_case(tmp_path)
    ryc = json.loads((case / "RYC.json").read_text())
    ryc["SAD"]["SC_0"].append({"CommId": "COM_zero", "2020": 0, "2021": 0})
    (case / "RYC.json").write_text(json.dumps(ryc))
    gd = json.loads((case / "genData.json").read_text())
    gd["osy-comm"].append({"CommId": "COM_zero", "Comm": "PHL_ZERO", "Desc": "", "UnitId": "PJ"})
    (case / "genData.json").write_text(json.dumps(gd))
    with pytest.raises(ValueError) as e:
        clews_driver.scale_annual_demand(str(case), "PHL_ZERO", 1.1)
    assert "ALL ZERO" in str(e.value) and "PHL_HOU_ELE" in str(e.value)  # names the live carriers
    # and the file was NOT rewritten (no partial mutation on failure)
    assert json.loads((case / "RYC.json").read_text())["SAD"]["SC_0"][0]["2020"] == 10.0


def test_muiogo_python_resolution(tmp_path, monkeypatch):
    fake = tmp_path / "python"
    fake.write_text("")
    monkeypatch.setenv("OGCLEWS_MUIOGO_PYTHON", str(fake))
    assert clews_driver.muiogo_python() == str(fake)
    assert clews_driver.muiogo_python(override=str(fake)) == str(fake)
    monkeypatch.setenv("OGCLEWS_MUIOGO_PYTHON", str(tmp_path / "gone"))
    if not (Path.home() / ".venvs" / "muiogo" / "bin" / "python").is_file():
        with pytest.raises(FileNotFoundError):
            clews_driver.muiogo_python()


def test_api_dir_guard(tmp_path):
    with pytest.raises(FileNotFoundError):
        clews_driver._api_dir(str(tmp_path))                        # not a MUIOGO checkout
