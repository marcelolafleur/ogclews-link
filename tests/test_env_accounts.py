"""Transform tests for env_accounts. No solve; fixtures are written to tmp_path."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ogclews_link.env_accounts import (
    DEMO_LAND_MAP,
    PHL_V12_LAND_MAP,
    LandClosureError,
    LandMap,
    composite_index,
    depletion_flow,
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


def test_empty_land_map_raises_not_returns_empty(tmp_path):
    """Plan §3 bug 1: an empty map must refuse, never read as 'no land here'."""
    run = _activity(tmp_path, DEMO_2020)
    empty = LandMap(resource_tech="MINLNDTOT", classes={})
    with pytest.raises(ValueError, match="maps no technology"):
        land_use_by_year(run, empty)
    # closure off is no escape hatch -- the refusal is before any reading
    with pytest.raises(ValueError, match="maps no technology"):
        land_use_by_year(run, empty, check_closure=False)


def test_map_matching_nothing_in_nonempty_file_raises(tmp_path):
    run = _activity(tmp_path, DEMO_2020)
    wrong_case = LandMap(resource_tech="MINLNDTOT", classes={"ENV_LAND": "Forest"})
    with pytest.raises(LandClosureError, match="matched nothing"):
        land_use_by_year(run, wrong_case)


def test_resource_only_match_is_a_closure_failure(tmp_path):
    """Classes that match nothing while the resource matches must not pass."""
    run = _activity(tmp_path, DEMO_2020)
    resource_only = LandMap(resource_tech="RSCLND", classes={"NOPE": "Forest"})
    with pytest.raises(LandClosureError, match="do not close"):
        land_use_by_year(run, resource_only)


# PHL-shaped fixture: the cover-class vector lives in one technology's modes.
MODAL_2020 = [
    ["RE1", "MINLNDTOT", "1", "2020", "300.0"],
    ["RE1", "ENV_LAND", "1", "2020", "250.0"],
    ["RE1", "ENV_LAND", "2", "2020", "30.0"],
    ["RE1", "ENV_LAND", "3", "2020", "20.0"],
]

MODAL_MAP = LandMap(
    resource_tech="MINLNDTOT",
    mode_classes={"ENV_LAND": {"1": "Forest", "2": "Cropland", "3": "Built-up"}},
)


def test_mode_classes_read_cover_from_modes(tmp_path):
    """Plan §3 bug 3: PHL carries the cover vector in ENV_LAND's modes."""
    run = _activity(tmp_path, MODAL_2020)
    cover, resource = land_use_by_year(run, MODAL_MAP)
    assert cover[2020] == {"Forest": 250.0, "Cropland": 30.0, "Built-up": 20.0}
    assert resource[2020] == pytest.approx(300.0)


# Real 2020 values from the solved Philippines_v12 Base_v12 run (CBC Optimal);
# modes 1-7 are cover classes, mode 8 is untagged land. These close on MINLNDTOT.
PHL_2020 = [
    ["RE1", "MINLNDTOT", "1", "2020", "295.8131"],
    ["RE1", "ENV_LAND", "1", "2020", "179.7818"],
    ["RE1", "ENV_LAND", "2", "2020", "0.0"],
    ["RE1", "ENV_LAND", "3", "2020", "0.0"],
    ["RE1", "ENV_LAND", "4", "2020", "0.0"],
    ["RE1", "ENV_LAND", "5", "2020", "0.7698"],
    ["RE1", "ENV_LAND", "6", "2020", "1.5984"],
    ["RE1", "ENV_LAND", "7", "2020", "113.6631"],
    ["RE1", "ENV_LAND", "8", "2020", "0.0"],
]


def test_phl_map_reads_real_solved_values_and_closes(tmp_path):
    """Stage 3: the shipped PHL map, against values from the real solve."""
    run = _activity(tmp_path, PHL_2020)
    cover, resource = land_use_by_year(run, PHL_V12_LAND_MAP)
    assert cover[2020]["Forest"] == pytest.approx(179.7818)
    assert cover[2020]["Cropland"] == pytest.approx(113.6631)
    assert cover[2020]["Unallocated"] == 0.0  # all land is tagged in Base_v12
    assert resource[2020] == pytest.approx(295.8131)
    assert sum(cover[2020].values()) == pytest.approx(295.8131, abs=1e-3)


def test_phl_map_covers_all_eight_modes():
    """A missing mode would silently drop area; closure would then fail on a solve."""
    assert set(PHL_V12_LAND_MAP.mode_classes["ENV_LAND"]) == {
        str(m) for m in range(1, 9)
    }
    assert not PHL_V12_LAND_MAP.is_empty


def test_phl_untagged_land_shows_as_unallocated(tmp_path):
    """If mode 8 ever goes positive it must appear as area, not break closure."""
    rows = [r[:] for r in PHL_2020]
    for r in rows:
        if r[1] == "ENV_LAND" and r[2] == "1":
            r[4] = "169.7818"          # move 10 out of Forest...
        elif r[1] == "ENV_LAND" and r[2] == "8":
            r[4] = "10.0"              # ...into untagged land
    cover, resource = land_use_by_year(_activity(tmp_path, rows), PHL_V12_LAND_MAP)
    assert cover[2020]["Unallocated"] == pytest.approx(10.0)
    assert sum(cover[2020].values()) == pytest.approx(resource[2020], abs=1e-3)


def test_unmapped_mode_is_dropped_and_closure_catches_it(tmp_path):
    run = _activity(tmp_path, MODAL_2020)
    partial = LandMap(
        resource_tech="MINLNDTOT",
        mode_classes={"ENV_LAND": {"1": "Forest", "2": "Cropland"}},  # mode 3 missing
    )
    with pytest.raises(LandClosureError, match="do not close"):
        land_use_by_year(run, partial)


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


def _emissions(tmp_path: Path, rows: list[list]) -> Path:
    run = tmp_path / "REF"
    _write(run / "csv" / "AnnualTechnologyEmission.csv",
           ["r", "t", "e", "y", "AnnualTechnologyEmission"], rows)
    return run


# Multi-species on purpose: the demo has CH4/CO2/CO2EQ/N2O, PHL has CO2e/PM2_5.
EMISSION_ROWS = [
    ["RE1", "PWRCOA", "CO2", "2020", "100.0"],
    ["RE1", "PWRGAS", "CO2", "2020", "50.0"],
    ["RE1", "PWRCOA", "PM2_5", "2020", "7.0"],
    ["RE1", "PWRCOA", "CO2", "2021", "80.0"],
    ["RE1", "PWRCOA", "PM2_5", "2021", "6.0"],
    ["RE1", "PWROIL", "CO2", "2021", ""],
]


def test_emissions_damage_prices_only_the_requested_species(tmp_path):
    """Plan §3 bug 2: PM2_5 must not be priced at the social cost of carbon."""
    run = _emissions(tmp_path, EMISSION_ROWS)
    got = emissions_damage(run, 30.0, species="CO2")
    assert got == {2020: pytest.approx(4500.0), 2021: pytest.approx(2400.0)}


def test_emissions_damage_accepts_several_species(tmp_path):
    run = _emissions(tmp_path, EMISSION_ROWS)
    got = emissions_damage(run, 30.0, species={"CO2", "PM2_5"})
    assert got == {2020: pytest.approx(4710.0), 2021: pytest.approx(2580.0)}


def test_emissions_damage_unknown_species_raises(tmp_path):
    run = _emissions(tmp_path, EMISSION_ROWS)
    with pytest.raises(ValueError, match="species present"):
        emissions_damage(run, 30.0, species="CO2e")  # PHL code against demo-style file


def test_emissions_damage_missing_file_returns_empty(tmp_path):
    assert emissions_damage(tmp_path / "nope", 30.0, species="CO2") == {}


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


def test_natural_capital_depletion_keeps_true_zero_rents():
    """A zero land rent is a real observation (abundance), contributing 0."""
    got = natural_capital_depletion({2020: 5.0, 2021: 5.0}, {2020: 0.0, 2021: 2.0})
    assert got == pytest.approx(10.0 / 1.04)


def test_depletion_flow_is_the_net_decline():
    """Plan §3 bug 4: eq. 3 wants the flow, not the standing stock."""
    stock = {2020: 253.6, 2021: 253.3, 2022: 253.0}
    got = depletion_flow(stock)
    assert got == {2021: pytest.approx(0.3), 2022: pytest.approx(0.3)}
    assert 2020 not in got  # no predecessor, no flow


def test_depletion_flow_growth_year_depletes_nothing():
    got = depletion_flow({2020: 100.0, 2021: 102.0, 2022: 101.0})
    assert got == {2021: 0.0, 2022: pytest.approx(1.0)}
