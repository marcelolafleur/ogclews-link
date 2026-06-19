"""Scenario-catalog loader + validator tests (plain asserts; run like test_channels.py):

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link-scenario \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python tests/test_scenario_catalog.py

The validator tests are stdlib-only; test_catalog_defaults_match_signatures imports the channel code
(numpy/ogcore), so the whole file is run under the OG-PHL venv.
"""
from __future__ import annotations

from ogclews_link import scenario_catalog as sc

CAT = sc.load_catalog()


def _codes(issues):
    return {i.code for i in issues}


def _eqdefault(a, b):
    if isinstance(a, tuple):
        a = list(a)
    if isinstance(b, tuple):
        b = list(b)
    return a == b


# --- loading + anti-drift -------------------------------------------------------

def test_catalog_loads():
    assert set(CAT) >= {"channels", "levers", "templates", "guardrails"}
    assert set(CAT["channels"]) == {"energy_price", "investment", "carbon",
                                    "discount_rate", "health", "demand"}


def test_catalog_defaults_match_signatures():
    # The catalog duplicates defaults from the apply()/function signatures for the UI's benefit; this is
    # the test that keeps them from drifting. Checked both directions for channels (completeness + value).
    for cid, spec in CAT["channels"].items():
        sig = sc.signature_defaults(cid)
        opts = spec["options"]
        for name in sig:
            assert name in opts, f"{cid}.{name} is an apply() kwarg missing from the catalog"
        for name, opt in opts.items():
            assert name in sig, f"catalog option {cid}.{name} is not a real apply() kwarg"
            assert _eqdefault(opt.get("default"), sig[name]), (cid, name, opt.get("default"), sig[name])
    for lid, spec in CAT["levers"].items():
        sig = sc.signature_defaults(lid)
        for name, opt in spec["options"].items():
            if opt.get("default") is None and name not in sig:
                continue   # a required positional (industry, pct_gdp_path) -- no signature default
            assert name in sig, f"catalog lever option {lid}.{name} is not a real kwarg"
            assert _eqdefault(opt.get("default"), sig[name]), (lid, name, opt.get("default"), sig[name])


def test_every_guardrail_has_a_predicate():
    for g in CAT["guardrails"]:
        assert g["id"] in sc._PREDICATES, f"guardrail {g['id']} has no predicate"


def test_json_matches_yaml():
    # the loaded JSON must equal the authored YAML; regenerate the JSON whenever the YAML changes.
    try:
        import os

        import yaml
    except ImportError:
        print("  (skip: pyyaml absent)")
        return
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(root, "docs", "design", "scenario_catalog.yaml")
    if not os.path.isfile(src):
        print("  (skip: authored yaml absent)")
        return
    assert yaml.safe_load(open(src)) == CAT, "scenario_catalog.json is stale vs the authored yaml — regenerate it"


# --- value-level validation -----------------------------------------------------

def test_clean_scenario_passes():
    res = sc.validate_scenario(CAT, [("energy_price", {"shock": 0.20, "recycle": True, "energy_cmin": 0.005})])
    assert res["ok"], [str(i) for i in res["errors"]]


def test_unknown_lever_and_option_block():
    assert "unknown_lever" in _codes(sc.validate_scenario(CAT, [("nope", {})])["errors"])
    assert "unknown_option" in _codes(sc.validate_scenario(CAT, [("carbon", {"bogus": 1})])["errors"])


def test_choice_enforced():
    bad = sc.validate_scenario(CAT, [("energy_price", {"price_source": "magic"})])
    assert "choice" in _codes(bad["errors"])
    ok = sc.validate_scenario(CAT, [("energy_price", {"price_source": "dual"})])
    assert "choice" not in _codes(ok["errors"] + ok["warnings"])


def test_range_warn_vs_block():
    warn = sc.validate_scenario(CAT, [("carbon", {"carbon_price": 99999})])    # range level: warn
    assert "range" in _codes(warn["warnings"]) and warn["ok"]
    block = sc.validate_scenario(CAT, [("investment", {"smooth_years": 99})])  # no level -> hard block
    assert "range" in _codes(block["errors"]) and not block["ok"]


def test_type_checked():
    bad = sc.validate_scenario(CAT, [("carbon", {"carbon_price": "lots"})])
    assert "type" in _codes(bad["errors"])
    # a bool must not satisfy a numeric option
    assert "type" in _codes(sc.validate_scenario(CAT, [("carbon", {"carbon_price": True})])["errors"])


# --- guardrails -----------------------------------------------------------------

def test_double_count_warns():
    # energy_price + carbon-on-OG both wedge the energy tau_c -> warn (matches EnergyPriceChannel.validate);
    # a CLEWS-only carbon price (apply_to_og=False) does not, so no warning there.
    res = sc.validate_scenario(CAT, [("energy_price", {}), ("carbon", {})])
    assert "no_double_count" in _codes(res["warnings"]) and res["ok"]
    clews_only = sc.validate_scenario(CAT, [("energy_price", {}), ("carbon", {"apply_to_og": False})])
    assert "no_double_count" not in _codes(clews_only["warnings"])


def test_recycle_or_tax_warns():
    taxy = sc.validate_scenario(CAT, [("energy_price", {"shock": 0.2})])               # no recycle
    assert "recycle_or_tax" in _codes(taxy["warnings"])
    clean = sc.validate_scenario(CAT, [("energy_price", {"shock": 0.2, "recycle": True})])
    assert "recycle_or_tax" not in _codes(clean["warnings"])


def test_separability_needs_model_then_blocks():
    sii = [("set_investment_incentive", {"industry": "agriculture"})]
    assert "separability" in _codes(sc.validate_scenario(CAT, sii)["infos"])              # no model -> info
    model = {"single_industry": False, "targetable_resources": ["energy"]}
    assert "separability" in _codes(sc.validate_scenario(CAT, sii, model=model)["errors"])  # undeclared resource
    ok = sc.validate_scenario(CAT, [("set_investment_incentive", {"industry": "energy"})], model=model)
    assert "separability" not in _codes(ok["errors"])


def test_post_solve_warns():
    res = sc.validate_scenario(CAT, [("discount_rate", {}), ("demand", {})])
    assert "post_solve_order" in _codes(res["warnings"])


# --- templates round-trip through the validator ---------------------------------

def test_templates_validate():
    # Every shipped template should at least carry no hard errors (warnings/infos are fine -- e.g. the
    # carbon template is a tax+recycle, the forward template touches post-solve channels).
    for name, tpl in CAT["templates"].items():
        scenarios = ([layer["channels"] for layer in tpl["layers"]] if tpl.get("run_mode") == "layered"
                     else [tpl["channels"]])
        for scen in scenarios:
            res = sc.validate_scenario(CAT, scen)
            assert res["ok"], (name, [str(i) for i in res["errors"]])


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
