"""Transform-level tests for the generic policy levers (no ogcore, no solve). Run:
    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link-energy \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/test_policy_levers.py
"""
import types

import numpy as np

from ogclews_link.policy_levers import (INDUSTRY_CATALOG, resolve_industry,
                                        route_revenue, set_investment_incentive)

TpS, M = 320, 4


def _p():
    return types.SimpleNamespace(
        Z=np.ones((TpS, M)), inv_tax_credit=np.zeros((TpS, M)), delta_tau=np.full((TpS, M), 0.05),
        tau_b=np.full((TpS, M), 0.25), alpha_T=np.full(TpS, 0.09), alpha_I=np.full(TpS, 0.02),
        alpha_G=np.full(TpS, 0.05))


def test_investment_incentive_targets_one_industry_window():
    p = _p()
    prov = set_investment_incentive(p, "energy", inv_tax_credit=0.20, delta_tau=0.22,
                                    tau_b_mult=0.5, phase_years=10)
    assert prov["m"] == 1
    assert np.allclose(p.inv_tax_credit[:10, 1], 0.20) and np.allclose(p.inv_tax_credit[10:, 1], 0.0)
    assert np.allclose(p.inv_tax_credit[:, 0], 0.0)                  # other industries untouched
    assert np.allclose(p.delta_tau[:10, 1], 0.22) and np.allclose(p.delta_tau[10:, 1], 0.05)
    assert np.allclose(p.tau_b[:10, 1], 0.125) and np.allclose(p.tau_b[10:, 1], 0.25)
    print("PASS investment_incentive targets one industry over a window")


def test_generic_over_industry_index_or_name():
    p = _p()
    set_investment_incentive(p, 3, inv_tax_credit=0.10)             # by int index (manufacturing)
    assert np.allclose(p.inv_tax_credit[:, 3], 0.10)
    assert resolve_industry("manufacturing") == 3 and resolve_industry(2) == 2
    assert resolve_industry("agriculture") == 0                    # bundled in Natural Resources (warns)
    assert INDUSTRY_CATALOG["agriculture"]["separable_m4"] is False
    print("PASS generic over industry name/index; agriculture flagged non-separable")


def test_route_revenue_destinations():
    path = np.full(TpS, 0.005)                                     # 0.5% of GDP revenue stream
    p = _p(); r = route_revenue(p, path, to="public_investment")
    assert r["param"] == "alpha_I" and np.allclose(p.alpha_I[:5], 0.025)
    p = _p(); route_revenue(p, path, to="transfers"); assert np.allclose(p.alpha_T[:5], 0.095)
    p = _p(); route_revenue(p, path, to="government_consumption"); assert np.allclose(p.alpha_G[:5], 0.055)
    p = _p(); a0 = p.alpha_I.copy(); r = route_revenue(p, path, to="deficit")
    assert r["param"] is None and np.allclose(p.alpha_I, a0)        # deficit = no spending bump
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
