"""Transform tests for env_accounts. No solve; fixtures are written to tmp_path."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ogclews_link.env_accounts import (
    DEMO_LAND_MAP,
    LandClosureError,
    LandMap,
    composite_index,
    emissions_damage,
    land_use_by_year,
    natural_capital_depletion,
)

ACTIVITY_HEADER = ["r", "t", "m", "y", "TotalAnnualTechnologyActivityByMode"]


def _write(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _activity(tmp_path: Path, rows: list[list]) -> Path:
    run = tmp_path / "REF"
    _write(run / "csv" / "TotalAnnualTechnologyActivityByMode.csv",
           ACTIVITY_HEADER, rows)
    return run


# Real 2020 values from the shipped CLEWs Demo REF solve; these sum to 299.9965.
DEMO_2020 = [
    ["RE1", "RSCLND", "1", "2020", "299.9965"],
    ["RE1", "LNDMAIRNF", "1", "2020", "4.085"],
    ["RE1", "LNDRICRNF", "1", "2020", "1.4205"],
    ["RE1", "LNDMAIIRR", "1", "2020", "0.339"],
    ["RE1", "LNDRICIRR", "1", "2020", "0.531"],
    ["RE1", "LNDFOR", "1", "2020", "253.6"],
    ["RE1", "LNDBLT", "1", "2020", "15.0"],
    ["RE1", "LNDWAT", "1", "2020", "25.021"],
]


def test_land_use_reads_activity_and_closes(tmp_path):
    run = _activity(tmp_path, DEMO_2020)
    cover, resource = land_use_by_year(run)

    assert set(cover) == {2020}
    assert cover[2020]["Forest"] == pytest.approx(253.6)
    assert cover[2020]["Built-up"] == pytest.approx(15.0)
    # four crop technologies collapse into one class
    assert cover[2020]["Cropland"] == pytest.approx(6.3755)
    assert resource[2020] == pytest.approx(299.9965)
    assert sum(cover[2020].values()) == pytest.approx(resource[2020], abs=1e-3)


def test_accepts_csv_subdir_directly(tmp_path):
    run = _activity(tmp_path, DEMO_2020)
    cover, _ = land_use_by_year(run / "csv")
    assert cover[2020]["Forest"] == pytest.approx(253.6)


def test_closure_failure_when_a_land_class_is_missing(tmp_path):
    """The guard that catches the real bug: drop forest, closure must fail."""
    run = _activity(tmp_path, DEMO_2020)
    partial = LandMap(
        resource_tech="RSCLND",
        classes={k: v for k, v in DEMO_LAND_MAP.classes.items() if k != "LNDFOR"},
    )
    with pytest.raises(LandClosureError, match="do not close"):
        land_use_by_year(run, partial)


def test_closure_can_be_disabled(tmp_path):
    run = _activity(tmp_path, DEMO_2020)
    partial = LandMap(
        resource_tech="RSCLND",
        classes={k: v for k, v in DEMO_LAND_MAP.classes.items() if k != "LNDFOR"},
    )
    cover, _ = land_use_by_year(run, partial, check_closure=False)
    assert "Forest" not in cover[2020]


def test_missing_resource_row_is_a_closure_failure(tmp_path):
    run = _activity(tmp_path, [r for r in DEMO_2020 if r[1] != "RSCLND"])
    with pytest.raises(LandClosureError, match="no 'RSCLND' row"):
        land_use_by_year(run)


def test_blank_activity_values_are_skipped(tmp_path):
    run = _activity(tmp_path, DEMO_2020 + [["RE1", "LNDFOR", "1", "2021", ""]])
    cover, _ = land_use_by_year(run, check_closure=False)
    assert 2021 not in cover


def test_missing_file_returns_empty(tmp_path):
    cover, resource = land_use_by_year(tmp_path / "nope")
    assert cover == {} and resource == {}


def test_composite_index_is_area_weighted():
    cover = {"Forest": 253.6, "Cropland": 6.3755, "Built-up": 15.0,
             "Water bodies": 25.021}
    coef = {"Forest": 0.95, "Cropland": 0.55, "Built-up": 0.35,
            "Water bodies": 0.90}
    got = composite_index(cover, coef)
    expected = sum(cover[k] * coef[k] for k in cover) / sum(cover.values())
    assert got == pytest.approx(expected)
    # bounded by the coefficients present
    assert min(coef.values()) <= got <= max(coef.values())


def test_composite_index_uniform_coefficients_returns_that_value():
    cover = {"Forest": 10.0, "Cropland": 90.0}
    assert composite_index(cover, {"Forest": 0.6, "Cropland": 0.6}) == pytest.approx(0.6)


def test_composite_index_missing_coefficient_raises():
    with pytest.raises(KeyError, match="Cropland"):
        composite_index({"Forest": 1.0, "Cropland": 1.0}, {"Forest": 0.95})


def test_composite_index_no_area_returns_none():
    assert composite_index({}, {}) is None
    assert composite_index({"Forest": 0.0}, {"Forest": 0.95}) is None


def test_emissions_damage_scales_and_aggregates(tmp_path):
    run = tmp_path / "REF"
    _write(
        run / "csv" / "AnnualTechnologyEmission.csv",
        ["r", "t", "e", "y", "AnnualTechnologyEmission"],
        [
            ["RE1", "PWRCOA", "CO2", "2020", "100.0"],
            ["RE1", "PWRGAS", "CO2", "2020", "50.0"],
            ["RE1", "PWRCOA", "CO2", "2021", "80.0"],
            ["RE1", "PWROIL", "CO2", "2021", ""],
        ],
    )
    got = emissions_damage(run, 30.0)
    assert got == {2020: pytest.approx(4500.0), 2021: pytest.approx(2400.0)}


def test_natural_capital_depletion_discounts_from_base_year():
    q = {2020: 10.0, 2021: 10.0}
    rents = {2020: 2.0, 2021: 2.0}
    got = natural_capital_depletion(q, rents, discount=0.04)
    assert got == pytest.approx(20.0 + 20.0 / 1.04)


def test_natural_capital_depletion_uses_only_shared_years():
    got = natural_capital_depletion({2020: 10.0, 2021: 5.0}, {2020: 2.0})
    assert got == pytest.approx(20.0)


def test_natural_capital_depletion_without_rents_is_zero():
    """The current state of play: quantities exist, unit rents do not."""
    assert natural_capital_depletion({2020: 10.0}, {}) == 0.0
