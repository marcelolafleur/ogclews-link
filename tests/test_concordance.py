"""Concordance discovery wiring: the energy ports are DERIVED from a calibration's aggregation dicts
(via ogclews_link.aggregation) instead of hand-set literals, with a PRODUCTION-side purity gate --
electricity must be ISOLATED as its own pure industry, else every energy port comes back unavailable
and the energy channels skip. The concordance is discovered per run in the OG env (from the country
package's PROD_DICT/CONS_DICT) and exported to the link; there is no link-vendored country concordance.
"""
import pytest

from ogclews_link.contract import Concordance
from ogclews_link.energy_calibration import M4_PROD_DICT

# CONS_DICT-shaped aggregation: electricity good ("Energy and water") at index 1
CONS = {"Food": ["cfood"], "Energy and water": ["cmine", "celec", "cwatr"],
        "Non-durables": ["ctext"], "Services": ["cosrv"]}
# real-style 7-sector PROD_DICT: electricity FUSED with water in "Utilities" at index 2 (NOT isolated)
PROD7 = {"Agriculture": ["amaiz"], "Mining": ["amine"], "Utilities": ["aelec", "awatr"],
         "Construction": ["acons"], "Trade": ["atrad"], "Services": ["aosrv"], "Mfg": ["afood"]}


def test_from_dicts_isolated_electricity_resolves():
    # the M=4 build isolates electricity as its OWN pure industry ("Electricity" = ["aelec"]) -> index 1
    c = Concordance.from_dicts(M4_PROD_DICT, CONS)
    assert (c.energy_industry_index, c.energy_good_index) == (1, 1)
    assert not c.unavailable


def test_from_dicts_fused_utilities_is_unavailable():
    # electricity FUSED with water in one production group -> NOT isolated -> the energy coupling can't
    # attach: BOTH ports None, the reason recorded, so every energy channel skips for this country.
    c = Concordance.from_dicts(PROD7, CONS)
    assert c.energy_industry_index is None and c.energy_good_index is None
    assert "not isolated" in c.unavailable["energy_industry_index"]


def test_from_dicts_carrier_not_found_marks_unavailable():
    # absent carrier -> both ports None with a recorded reason (NOT a raise, NOT a silent guess).
    c = Concordance.from_dicts({"A": ["axxx"]}, CONS)
    assert c.energy_industry_index is None and "not found" in c.unavailable["energy_industry_index"]
    assert c.energy_good_index is None


def test_from_dicts_split_carrier_marks_unavailable():
    split = {"A": ["aelec"], "B": ["aelcg"]}   # electricity in two production groups -> ambiguous index
    c = Concordance.from_dicts(split, CONS)
    assert c.energy_industry_index is None and "split across" in c.unavailable["energy_industry_index"]


def test_from_dicts_custom_carrier_water_isolated():
    # the carrier is generic: a build that isolates WATER as its own pure industry resolves on water
    prod = {"Power": ["aelcg"], "Water": ["awatr"], "Rest": ["aother"]}
    c = Concordance.from_dicts(prod, CONS, carrier="water")
    assert c.energy_industry_index == 1          # "Water" at index 1
    assert c.energy_good_index == 1              # cwatr in "Energy and water"


def test_from_dicts_disambiguates_cons_good_via_production_analogue():
    # ZAF-style: the carrier regex (^[ac]el) also matches electricity embodied in machinery (celcm, a
    # Durable) and distribution (celcd, a Service), so the carrier hits THREE consumption groups. The
    # household energy good must still resolve -- to the commodity analogue (celcg) of the resolved
    # production carrier (aelcg) -- rather than collapsing to None and skipping the demand-side channels.
    prod = {"Primary": ["aagri"], "Energy": ["aelcg"], "Tertiary": ["aserv"], "Secondary": ["amanu"]}
    cons = {"Food": ["cfood"], "Energy and extraction": ["celcg", "cmine"],
            "Non-durables": ["ctext"], "Durables": ["celcm", "cdura"], "Services": ["celcd", "cserv"]}
    c = Concordance.from_dicts(prod, cons)
    assert c.energy_industry_index == 1            # Energy isolated (aelcg)
    assert c.energy_good_index == 1                # "Energy and extraction" (celcg), NOT None
    assert not c.unavailable


def test_from_package_reflects_ogphl_real_dicts():
    pytest.importorskip("ogphl")
    # from_package must mirror the package's OWN real PROD_DICT/CONS_DICT. Assert it equals from_dicts on
    # those same dicts rather than hard-coding an index/share -- robust to ogphl evolving its aggregation
    # (it currently ISOLATES electricity as its own group; it used to fuse it with water). The purity-gate
    # behavior itself is covered by the controlled-fixture tests above.
    import ogphl
    assert Concordance.from_package("ogphl") == Concordance.from_dicts(ogphl.PROD_DICT, ogphl.CONS_DICT)


def test_channel_skips_when_port_unavailable():
    # if the country's aggregation can't isolate electricity, the energy channel SKIPS (records the
    # reason) and mutates nothing. The concordance now lives on the CONTEXT (per run), not the country.
    import numpy as np

    from ogclews_link import channels, serde
    from ogclews_link.country import PHL
    from ogclews_link.framework import ExperimentContext
    con = Concordance(energy_industry_index=1, energy_good_index=None,
                      unavailable={"energy_good_index": "carrier 'electricity' is split across ..."})
    og = serde.OGParams(T=20, S=0, I=5, tau_c=np.full((20, 5), 0.12))
    ctx = ExperimentContext(country=PHL, concordance=con, og_reform=og, base_tpi=None)
    before = og.tau_c.copy()
    rec = channels.energy_price(ctx, price_ratio=1.20)               # needs energy_good_index (None)
    assert rec.get("skipped") is True and "energy_good_index" in rec["reason"]
    assert np.array_equal(og.tau_c, before)                          # mutated nothing
    assert ctx.provenance[-1]["channel"] == "energy_price" and ctx.provenance[-1]["skipped"]


def test_channel_skips_when_no_concordance():
    # belt-and-suspenders: a run whose baseline exported NO concordance (ctx.concordance is None) also
    # skips every energy channel rather than crashing -- single-industry / older exports degrade cleanly.
    import numpy as np

    from ogclews_link import channels, serde
    from ogclews_link.country import PHL
    from ogclews_link.framework import ExperimentContext
    og = serde.OGParams(T=20, S=0, I=5, tau_c=np.full((20, 5), 0.12))
    ctx = ExperimentContext(country=PHL, concordance=None, og_reform=og, base_tpi=None)
    rec = channels.energy_price(ctx, price_ratio=1.20)
    assert rec.get("skipped") is True
    assert np.array_equal(og.tau_c, np.full((20, 5), 0.12))


def test_cost_push_reports_discovered_energy_index():
    pytest.importorskip("ogphl")
    from ogclews_link.io_energy_passthrough import cost_push_by_industry
    out = cost_push_by_industry(0.20)            # default M4 build dict (electricity isolated) -> column 1
    assert out["_energy_industry_index"] == 1
