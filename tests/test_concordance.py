"""Concordance discovery wiring: the energy ports are derived from the calibration's
aggregation dicts (via ogclews_link.aggregation) instead of hand-set literals -- and stay
consistent with whatever aggregation the model is actually built with.
"""
import pytest

from ogclews_link.contract import Concordance, PHL_CONCORDANCE
from ogclews_link.energy_calibration import M4_PROD_DICT

# CONS_DICT-shaped aggregation: electricity good ("Energy and water") at index 1
CONS = {"Food": ["cfood"], "Energy and water": ["cmine", "celec", "cwatr"],
        "Non-durables": ["ctext"], "Services": ["cosrv"]}
# real-style 7-sector PROD_DICT: electricity folded into "Utilities" at index 2
PROD7 = {"Agriculture": ["amaiz"], "Mining": ["amine"], "Utilities": ["aelec", "awatr"],
         "Construction": ["acons"], "Trade": ["atrad"], "Services": ["aosrv"], "Mfg": ["afood"]}


def test_from_dicts_bespoke_m4_matches_old_literal():
    # the M=4 build aggregation -> electricity industry at 1 == the old hand-set Concordance(1, 1)
    c = Concordance.from_dicts(M4_PROD_DICT, CONS)
    assert (c.energy_industry_index, c.energy_good_index) == (1, 1)


def test_from_dicts_real_7sector_finds_utilities_at_2():
    c = Concordance.from_dicts(PROD7, CONS)
    assert (c.energy_industry_index, c.energy_good_index) == (2, 1)   # discovered, not declared


def test_phl_concordance_is_discovered_and_unchanged():
    # the shipped PHL default is now derived (from the M=4 build dict), still (1, 1) -> no behavior change
    assert (PHL_CONCORDANCE.energy_industry_index, PHL_CONCORDANCE.energy_good_index) == (1, 1)


def test_from_dicts_carrier_not_found_raises():
    with pytest.raises(ValueError, match="not found"):
        Concordance.from_dicts({"A": ["axxx"]}, CONS)


def test_from_dicts_split_carrier_raises():
    split = {"A": ["aelec"], "B": ["aelcg"]}   # electricity in two production groups -> ambiguous index
    with pytest.raises(ValueError, match="split across"):
        Concordance.from_dicts(split, CONS)


def test_from_dicts_custom_carrier_water():
    c = Concordance.from_dicts(PROD7, CONS, carrier="water")
    assert c.energy_industry_index == 2          # water also lives in "Utilities"
    assert c.energy_good_index == 1              # cwatr is in "Energy and water"


def test_from_package_ogphl_uses_real_calibration():
    pytest.importorskip("ogphl")
    c = Concordance.from_package("ogphl")        # real 7-sector PROD_DICT -> "Utilities" at 2
    assert (c.energy_industry_index, c.energy_good_index) == (2, 1)


def test_cost_push_reports_discovered_energy_index():
    pytest.importorskip("ogphl")
    from ogclews_link.io_energy_passthrough import cost_push_by_industry
    out = cost_push_by_industry(0.20)            # default M4 build dict -> electricity column 1
    assert out["_energy_industry_index"] == 1
