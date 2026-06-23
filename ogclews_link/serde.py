"""Serialization across the link <-> OG-runner environment boundary. numpy-only (NO ogcore, NO the
country package), so it imports cleanly in BOTH the lightweight link env and the OG model's env.

Boundary discipline (see the cross-env design): the link writes JSON (parameter overrides + the health
shock); the OG runner writes .npz (baseline params + solutions) read back with allow_pickle=False. No
pickle and no ogcore object ever crosses the boundary, so the link and OG env may run different numpy
versions safely. ``baseline_p.pkl`` (the full Specifications) is written and re-read ONLY inside the OG
env -- never by the link.
"""
from __future__ import annotations

import json
import types

import numpy as np

# Scalar ints + read-only arrays the channels/levers consult; the runner exports these from the solved
# baseline Specifications, the link loads them into the duck-typed og_reform.
BASELINE_INT_KEYS = ("T", "S", "E", "M", "I")
BASELINE_ARRAY_KEYS = ("tau_c", "c_min", "alpha_T", "alpha_I", "alpha_bs_I", "gamma", "gamma_g",
                       "epsilon", "e", "inv_tax_credit", "delta_tau", "tau_b", "Z", "io_matrix")

# The params a channel may MUTATE (everything the link diffs back as overrides). Subset of the arrays
# above; the read-only ones (gamma_g, epsilon, Z) are shape/guard inputs, never written by a channel.
MUTABLE_PARAM_KEYS = ("tau_c", "c_min", "alpha_T", "alpha_I", "alpha_bs_I", "gamma",
                      "inv_tax_credit", "delta_tau", "tau_b", "e")

# The solution variables read downstream -- the consumed subset of an OG SS/TPI dict. The first row is
# read by channels + report + golden (the battery's correctness gate); the second is read only by the viz
# lifecycle/savings plots (carried so a deck can be built straight off the cross-env solution npz).
SOLUTION_KEYS = ("C_i", "c_i", "c", "p_i", "Y_m", "Y", "C", "K", "L", "r", "r_p", "r_gov", "w",
                 "cons_tax_revenue", "resource_constraint_error",
                 "n", "b_s", "factor")


class OGParams(types.SimpleNamespace):
    """Duck-typed stand-in for an OG-Core ``Specifications``: a bag of the exported baseline arrays +
    ints that the channels mutate by plain attribute get/set. No ogcore needed to construct it. The
    ``update_specifications`` stub exists only for API symmetry -- no channel calls it (a contract test
    guards that), the real one runs in the OG runner."""

    def update_specifications(self, d: dict):
        for k, v in d.items():
            setattr(self, k, v)
        return self


# --- OG runner side (in the OG env): extract from / build a real Specifications -------------------

def save_params_npz(path, p) -> None:
    """Export the duck-type's needed params from a solved baseline ``Specifications`` p (runner-side)."""
    out = {k: np.asarray(getattr(p, k)) for k in BASELINE_INT_KEYS}
    out.update({k: np.asarray(getattr(p, k), dtype=float) for k in BASELINE_ARRAY_KEYS})
    np.savez(path, **out)


def save_solution_npz(path, solution: dict) -> None:
    """Flatten the consumed-subset of an OG solution dict to a numeric-only .npz (runner-side). Asserts
    every value is a numeric ndarray -- a ragged/object array would force allow_pickle and reintroduce
    the cross-env numpy-skew risk, so fail loudly instead."""
    out = {}
    for k in SOLUTION_KEYS:
        if k not in solution:
            continue
        arr = np.asarray(solution[k])
        if arr.dtype == object:
            raise TypeError(f"save_solution_npz: '{k}' is object-dtype (ragged?); refusing to pickle "
                            "across the env boundary -- the runner must hand back numeric arrays only.")
        out[k] = arr
    np.savez(path, **out)


# --- link side (numpy-only): load exports, diff, write the override/health specs ------------------

def load_baseline_bundle(params_path, solution_path):
    """Load the runner's baseline export into (OGParams template, base_tpi dict, baseline_arrays dict).
    The template is what _fresh_reform deepcopies for the channels to mutate; baseline_arrays is the
    pristine reference the override diff compares against."""
    with np.load(params_path, allow_pickle=False) as z:
        ints = {k: int(z[k]) for k in BASELINE_INT_KEYS if k in z.files}
        arrays = {k: z[k] for k in BASELINE_ARRAY_KEYS if k in z.files}
    og = OGParams(**ints, **{k: v.copy() for k, v in arrays.items()})
    base_tpi = load_solution(solution_path)
    return og, base_tpi, arrays


def load_solution(path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def diff_against_baseline(og_reform, baseline_arrays: dict) -> dict:
    """SPARSE override diff: only the mutable params a channel actually changed vs the exported baseline,
    as {attr: nested list} (JSON-ready). dtype is lost over JSON -- the runner casts back to float64."""
    diff = {}
    for k in MUTABLE_PARAM_KEYS:
        base = baseline_arrays.get(k)
        cur = getattr(og_reform, k, None)
        if cur is None:
            continue
        cur = np.asarray(cur, dtype=float)
        if base is None or not np.array_equal(cur, np.asarray(base, dtype=float)):
            diff[k] = cur.tolist()
    return diff


def write_overrides_json(diff: dict, path) -> None:
    with open(path, "w") as f:
        json.dump(diff, f)


def read_overrides_json(path) -> dict:
    """Runner-side: load overrides, casting the lists back to float64 arrays for update_specifications."""
    with open(path) as f:
        raw = json.load(f)
    return {k: np.asarray(v, dtype=float) for k, v in raw.items()}


def write_health_json(health_shock: dict, path) -> None:
    """The ctx.extras['health_shock'] dict: {excess_deaths, profile, phase_years, rc_ss}; profile->list."""
    out = dict(health_shock)
    if "profile" in out:
        out["profile"] = np.asarray(out["profile"], dtype=float).tolist()
    with open(path, "w") as f:
        json.dump(out, f)


def read_health_json(path) -> dict:
    with open(path) as f:
        out = json.load(f)
    if "profile" in out:
        out["profile"] = np.asarray(out["profile"], dtype=float)
    return out
