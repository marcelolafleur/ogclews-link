"""Loader + validator for the declarative scenario catalog (scenario_catalog.json).

The catalog (see docs/design/scenario-catalog.md) describes every lever a scenario builder can offer --
the channels (channels.py), the generic policy levers (policy_levers.py), the named templates, and the
guardrails -- so a UI renders forms and lints scenarios from ONE source. A "scenario" here is what the
builder assembles and what framework.Experiment stores: a list of ``(lever_id, options)`` where lever_id
is a channel id OR a generic-lever id.

Stdlib-only (json) so the validator imports without numpy/ogcore. ``signature_defaults()`` lazily imports
the channel code and is used only by the sync test that proves the catalog's defaults still match the
apply()/function signatures (the anti-drift check; defaults are duplicated here for the UI's benefit).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "scenario_catalog.json")

# Catalog type string -> the python types a value may take.
_TYPES = {
    "int": (int,), "float": (int, float), "bool": (bool,), "str": (str,),
    "list": (list, tuple), "industry_ref": (int, str),
}


@dataclass
class Issue:
    severity: str   # block | warn | info
    code: str       # machine code: a guardrail id, or unknown_lever/unknown_option/type/range/choice
    where: str      # "lever.option" or the lever id(s) the guardrail spans
    message: str

    def __str__(self):
        return f"[{self.severity}] {self.where}: {self.message}"


# --- loading --------------------------------------------------------------------

def load_catalog(path=None) -> dict:
    with open(path or _CATALOG_PATH) as fh:
        return json.load(fh)


def lever_spec(catalog, lever_id):
    """The spec for a channel OR a generic lever (the builder treats both as addable levers)."""
    return catalog.get("channels", {}).get(lever_id) or catalog.get("levers", {}).get(lever_id)


def option_defaults(catalog, lever_id) -> dict:
    spec = lever_spec(catalog, lever_id) or {}
    return {k: o.get("default") for k, o in spec.get("options", {}).items()}


def _normalize(scenario):
    """Accept [(id, opts)], [{id: opts}], or an object with a .channels attr -> [(id, opts)]."""
    items = getattr(scenario, "channels", scenario)
    out = []
    for item in items:
        if isinstance(item, dict):              # {id: opts}  (the catalog template form)
            (cid, opts), = item.items()
        else:                                    # (id, opts)  (the Experiment form)
            cid, opts = item
        out.append((cid, dict(opts or {})))
    return out


# --- value-level validation -----------------------------------------------------

def _check_value(cid, key, value, opt):
    typ = opt.get("type")
    pytypes = _TYPES.get(typ)
    # bool is a subclass of int -- reject it for numeric options and vice-versa.
    if typ in ("int", "float"):
        if isinstance(value, bool) or (pytypes and not isinstance(value, pytypes)):
            return [Issue("block", "type", f"{cid}.{key}", f"expected {typ}, got {type(value).__name__}")]
    elif pytypes and not isinstance(value, pytypes):
        return [Issue("block", "type", f"{cid}.{key}", f"expected {typ}, got {type(value).__name__}")]

    issues = []
    validators = opt.get("validators", {})
    if "choice" in validators:
        choices = validators["choice"]["choices"]
        supplied = value if isinstance(value, (list, tuple)) else [value]
        bad = [x for x in supplied if x not in choices]
        if bad:
            issues.append(Issue("block", "choice", f"{cid}.{key}", f"{bad} not in {choices}"))
    if "range" in validators and isinstance(value, (int, float)) and not isinstance(value, bool):
        r = validators["range"]
        sev = "warn" if r.get("level") == "warn" else "block"   # ParamTools default level is a hard error
        if "min" in r and value < r["min"]:
            issues.append(Issue(sev, "range", f"{cid}.{key}", f"{value} below min {r['min']}"))
        if "max" in r and value > r["max"]:
            issues.append(Issue(sev, "range", f"{cid}.{key}", f"{value} above max {r['max']}"))
    return issues


def validate_options(catalog, cid, options):
    spec = lever_spec(catalog, cid)
    if spec is None:
        return [Issue("block", "unknown_lever", cid, f"'{cid}' is not a channel or lever in the catalog")]
    known = spec.get("options", {})
    issues = []
    for key, value in options.items():
        if key not in known:
            issues.append(Issue("block", "unknown_option", f"{cid}.{key}", f"unknown option '{key}' for {cid}"))
            continue
        if value is None:                        # null == unset / use the default
            continue
        issues += _check_value(cid, key, value, known[key])
    return issues


# --- cross-lever guardrails (the validator's predicates; messages live in the catalog) ----------

def _eff(catalog, scen, cid, opt):
    """Effective value of a flag: the scenario's override, else the catalog default."""
    if cid in scen and scen[cid].get(opt) is not None:
        return scen[cid][opt]
    return option_defaults(catalog, cid).get(opt)


def _g_no_double_count(cat, s, model):
    # Only a real overlap when carbon actually wedges the OG energy tau_c (apply_to_og); a CLEWS-only
    # carbon price never touches the OG good, so it can co-exist with an energy-price shock.
    return "energy_price" in s and "carbon" in s and bool(_eff(cat, s, "carbon", "apply_to_og"))

def _g_operating_vs_capital(cat, s, model):
    return "energy_price" in s and "investment" in s

def _g_recycle_or_tax(cat, s, model):
    taxy = ("energy_price" in s and not _eff(cat, s, "energy_price", "recycle")) or \
           ("carbon" in s and _eff(cat, s, "carbon", "apply_to_og") and not _eff(cat, s, "carbon", "recycle"))
    return bool(taxy) and "route_revenue" not in s

def _g_separability(cat, s, model):
    if "set_investment_incentive" not in s:
        return False
    if model is None:
        return None                              # cannot verify without the model's industry registry
    industry = s["set_investment_incentive"].get("industry")
    if model.get("single_industry"):
        return True
    if isinstance(industry, str) and industry not in set(model.get("targetable_resources", [])):
        return True
    return False

def _g_magnitude(cat, s, model):
    return any(c in s for c in ("investment", "carbon", "health"))

def _g_post_solve(cat, s, model):
    return any(c in s for c in ("discount_rate", "demand"))

# Every guardrail id in the catalog MUST have an entry here; check_guardrails raises otherwise, so the
# data and the code can't silently drift apart.
_PREDICATES = {
    "no_double_count": _g_no_double_count,
    "operating_vs_capital": _g_operating_vs_capital,
    "recycle_or_tax": _g_recycle_or_tax,
    "separability": _g_separability,
    "magnitude_calibration": _g_magnitude,
    "post_solve_order": _g_post_solve,
}


def check_guardrails(catalog, scenario, model=None):
    scen = {cid: opts for cid, opts in _normalize(scenario)}
    issues = []
    for g in catalog.get("guardrails", []):
        gid = g["id"]
        if gid not in _PREDICATES:
            raise ValueError(f"catalog guardrail '{gid}' has no predicate in scenario_catalog._PREDICATES "
                             "-- the catalog and the validator are out of sync")
        verdict = _PREDICATES[gid](catalog, scen, model)
        where = ",".join(g.get("applies_to", []))
        message = g["message"].strip()
        if verdict is True:
            issues.append(Issue(g.get("severity", "warn"), gid, where, message))
        elif verdict is None:                    # applicable but needs context we weren't given
            issues.append(Issue("info", gid, where, "not checked (needs model context): " + message))
    return issues


def validate_scenario(catalog, scenario, model=None) -> dict:
    """Validate a scenario [(lever_id, options), ...]. Returns {errors, warnings, infos, ok}."""
    issues = []
    for cid, opts in _normalize(scenario):
        issues += validate_options(catalog, cid, opts)
    issues += check_guardrails(catalog, scenario, model)
    bucket_of = {"block": "errors", "warn": "warnings", "info": "infos"}
    out = {"errors": [], "warnings": [], "infos": []}
    for i in issues:
        out[bucket_of[i.severity]].append(i)
    out["ok"] = not out["errors"]
    return out


# --- anti-drift sync check (used by the test; lazily imports the channel code) -------------------

def signature_defaults(lever_id) -> dict:
    """Defaults declared in the channel's apply() / the lever function's signature (params WITH a
    default; the required positionals like ctx / industry_index / pct_gdp_path are excluded)."""
    import inspect

    from ogclews_link import channels, policy_levers  # noqa: F401  (channels self-register on import)
    from ogclews_link.framework import all_channels, get
    if lever_id in all_channels():
        sig = inspect.signature(get(lever_id).apply)
    else:
        sig = inspect.signature(getattr(policy_levers, lever_id))
    return {name: p.default for name, p in sig.parameters.items()
            if p.default is not inspect.Parameter.empty}
