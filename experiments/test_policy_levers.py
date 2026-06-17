"""Transform-level tests for the generic policy levers (no ogcore, no solve). Run:
    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link-energy \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/test_policy_levers.py
"""
import types

import numpy as np

from ogclews_link.policy_levers import (industry_registry, resolve_industry,
                                        route_revenue, set_investment_incentive)

TpS = 320


def _p(M=4):
    return types.SimpleNamespace(
        M=M, Z=np.ones((TpS, M)), inv_tax_credit=np.zeros((TpS, M)), delta_tau=np.full((TpS, M), 0.05),
        tau_b=np.full((TpS, M), 0.25), alpha_T=np.full(TpS, 0.09), alpha_I=np.full(TpS, 0.02),
        alpha_G=np.full(TpS, 0.05))


def test_registry_derived_from_model_not_hardcoded():
    # multi-industry model: names from the country's PROD_DICT ordering, energy index DECLARED
    p = _p(M=4)
    reg = industry_registry(p, names=["Natural Resources", "Electricity", "Services", "Manufacturing"],
                            resource_index={"energy": 1})
    assert reg["n"] == 4 and not reg["single_industry"]
    assert resolve_industry("energy", reg) == 1            # declared resource
    assert resolve_industry("Manufacturing", reg) == 3     # by name
    assert resolve_industry(2, reg) == 2                   # by index
    # a model that declares NO names -> generic, index-only
    reg2 = industry_registry(_p(M=3))
    assert reg2["names"] == ["industry_0", "industry_1", "industry_2"]
    assert resolve_industry(2, reg2) == 2
    print("PASS registry derived per-model (names + declared resources), not hardcoded")


def test_single_industry_model_degrades_gracefully():
    reg = industry_registry(_p(M=1), names=["economy"])
    assert reg["single_industry"] and reg["targetable_resources"] == []
    assert resolve_industry(0, reg) == 0                   # the one aggregate industry is addressable
    try:
        resolve_industry("energy", reg)                    # no separate energy sector in M=1
        raise AssertionError("expected single-industry error")
    except ValueError as e:
        assert "single-industry" in str(e) and "consumption good" in str(e)
    print("PASS single-industry (M=1) model: resource targeting unavailable, clear message")


def test_unknown_resource_actionable_error():
    reg = industry_registry(_p(M=4), names=["a", "b", "c", "d"], resource_index={"energy": 1})
    try:
        resolve_industry("water", reg)                     # not declared
        raise AssertionError("expected unknown-resource error")
    except ValueError as e:
        assert "Declare it in the country config" in str(e)
    print("PASS undeclared resource -> actionable error (declare in country config)")


def test_investment_incentive_by_index_targets_window():
    p = _p(M=4)
    reg = industry_registry(p, names=["NR", "Electricity", "Svc", "Mfg"], resource_index={"energy": 1})
    m = resolve_industry("energy", reg)                    # name -> index via the model registry
    prov = set_investment_incentive(p, m, inv_tax_credit=0.20, delta_tau=0.22, tau_b_mult=0.5,
                                    phase_years=10)
    assert prov["m"] == 1
    assert np.allclose(p.inv_tax_credit[:10, 1], 0.20) and np.allclose(p.inv_tax_credit[10:, 1], 0.0)
    assert np.allclose(p.inv_tax_credit[:, 0], 0.0)        # other industries untouched
    assert np.allclose(p.tau_b[:10, 1], 0.125)
    try:
        set_investment_incentive(p, 9, inv_tax_credit=0.1)  # out-of-range index for M=4
        raise AssertionError("expected out-of-range error")
    except ValueError as e:
        assert "out of range" in str(e)
    print("PASS investment incentive by index targets one industry/window; index validated vs M")


def test_route_revenue_destinations():
    path = np.full(TpS, 0.005)
    p = _p(); r = route_revenue(p, path, to="public_investment")
    assert r["param"] == "alpha_I" and np.allclose(p.alpha_I[:5], 0.025)
    p = _p(); route_revenue(p, path, to="transfers"); assert np.allclose(p.alpha_T[:5], 0.095)
    p = _p(); route_revenue(p, path, to="government_consumption"); assert np.allclose(p.alpha_G[:5], 0.055)
    p = _p(); a0 = p.alpha_I.copy(); r = route_revenue(p, path, to="deficit")
    assert r["param"] is None and np.allclose(p.alpha_I, a0)
    print("PASS route_revenue: transfers / public_investment / government_consumption / deficit")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t(); passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}"); failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
