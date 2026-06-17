"""Test + validate the HEALTH channel in isolation: build the OG-PHL baseline, apply ONLY the
health channel (the disease_pop age-profile mortality shock + the morbidity productivity effect),
solve, and report (a) convergence and (b) whether the mechanism actually fired in the right
direction -- demographics/mortality/productivity all move as the economics says. Explicit
PASS/FAIL so "validate" means something.

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/validate_health.py
"""
from __future__ import annotations

import json
import os

import numpy as np
from ogcore.utils import safe_read_pickle

from ogclews_link import channels, report  # noqa: F401 (registers channels)
from ogclews_link.country import PHL
from ogclews_link.experiments import EXPERIMENTS
from ogclews_link.runtime import Runtime

OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/validate_health"
TOL = 1e-3  # max acceptable resource-constraint error for "converged"


def _params(sub):
    return safe_read_pickle(os.path.join(OUT, "health", sub, "model_params.pkl"))


def _age_axis_mean(arr, lo, hi):
    """Mean of an array over age indices [lo:hi] on its LAST-but-J axis. rho is (...,S),
    e is (...,S,J); collapse everything except the age slice."""
    a = np.asarray(arr, dtype=float)
    if a.ndim == 1:           # (S,)
        return float(a[lo:hi].mean())
    if a.ndim == 2:           # (T+S, S)
        return float(a[:, lo:hi].mean())
    return float(a[:, lo:hi, :].mean())  # (T+S, S, J) -> e


def main():
    rt = Runtime(num_workers=7, show_progress=True)
    ctx = rt.runner_for(PHL).run(EXPERIMENTS["health"], PHL, out_root=OUT, max_passes=1)

    print("\n" + "=" * 72 + "\nHEALTH CHANNEL VALIDATION (standalone, +health only)\n" + "=" * 72)
    checks = []  # (name, ok, detail)

    solved = ctx.reform_tpi is not None
    if not solved:
        print("\n[convergence] REFORM DID NOT SOLVE:", ctx.extras.get("error", "unknown"))
        checks.append(("reform converged", False, ctx.extras.get("error", "unknown")))
        _dump(checks, None)
        return

    fc = report.fiscal_check(ctx.base_tpi, ctx.reform_tpi)
    rc_b, rc_r = fc.get("rc_error_base"), fc.get("rc_error_reform")
    rc_ok = (rc_r is None) or (rc_r < TOL)   # reform_tpi exists => solved; rc is a quality gate
    rc_detail = (f"base={rc_b:.2e} reform={rc_r:.2e}" if (rc_b is not None and rc_r is not None)
                 else "solved; resource_constraint_error not in TPI dict")
    checks.append(("reform converged", rc_ok, rc_detail))

    hp = next((r for r in ctx.provenance if r.get("channel") == "health"), {})
    demis = hp.get("emissions_change")
    excess = hp.get("mortality_excess_deaths")
    benefit = hp.get("morbidity_benefit")
    print(f"\n[inputs] emissions change demis={demis} (reform cleaner if <0)")
    print(f"         mortality excess_deaths target={excess} | morbidity benefit={benefit} | "
          f"profile={hp.get('profile_source')}")
    checks.append(("reform is cleaner (demis<0)", demis is not None and demis < 0, f"demis={demis}"))
    checks.append(("excess_deaths<0 (cleaner -> lives saved)", excess is not None and excess < 0,
                   f"excess_deaths={excess}"))
    checks.append(("morbidity benefit>0 (cleaner -> more productive)",
                   benefit is not None and benefit > 0, f"benefit={benefit}"))

    # --- did the mechanism actually fire? compare baseline vs reform model params ---
    bp, rp = _params("baseline"), _params("reform")
    S = int(bp.S)
    eld_lo, eld_hi = int(0.80 * S), S          # "elderly" = top 20% of ages
    wrk_lo, wrk_hi = int(0.05 * S), int(0.80 * S)

    rho_b, rho_r = np.asarray(bp.rho, float), np.asarray(rp.rho, float)
    rho_changed = not np.allclose(rho_b, rho_r)
    rho_eld_b, rho_eld_r = _age_axis_mean(rho_b, eld_lo, eld_hi), _age_axis_mean(rho_r, eld_lo, eld_hi)
    print(f"\n[mortality rho] changed={rho_changed} | elderly mean base={rho_eld_b:.5f} "
          f"reform={rho_eld_r:.5f} (reform should be LOWER)")
    checks.append(("mortality fell at elderly ages", rho_changed and rho_eld_r < rho_eld_b,
                   f"{rho_eld_r:.5f} < {rho_eld_b:.5f}"))

    e_b, e_r = np.asarray(bp.e, float), np.asarray(rp.e, float)
    e_changed = not np.allclose(e_b, e_r)
    e_wrk_b, e_wrk_r = _age_axis_mean(e_b, wrk_lo, wrk_hi), _age_axis_mean(e_r, wrk_lo, wrk_hi)
    print(f"[productivity e] changed={e_changed} | working-age mean base={e_wrk_b:.5f} "
          f"reform={e_wrk_r:.5f} (reform should be HIGHER)")
    checks.append(("productivity rose for working ages", e_changed and e_wrk_r > e_wrk_b,
                   f"{e_wrk_r:.5f} > {e_wrk_b:.5f}"))

    try:
        gn_b, gn_r = float(np.mean(bp.g_n)), float(np.mean(rp.g_n))
        print(f"[pop growth g_n] base mean={gn_b:+.5f} reform={gn_r:+.5f} (reform should be >= base)")
        checks.append(("population growth did not fall", gn_r >= gn_b - 1e-9, f"{gn_r:+.5f} vs {gn_b:+.5f}"))
    except Exception as e:  # noqa: BLE001
        print(f"[pop growth g_n] (skipped: {type(e).__name__}: {e})")

    # --- macro + distributional response ---
    macro = report.macro_pct_diff(ctx.base_tpi, ctx.reform_tpi)
    print("\n[macro %% vs baseline] " + ", ".join(f"{k}={np.nanmean(v):+.3f}" for k, v in macro.items()))
    ie = PHL.concordance.energy_good_index
    inc = report.incidence(ctx.base_tpi, ctx.reform_tpi, ie)
    print(f"[welfare %% by income group] {list(np.round(inc['welfare_by_J'], 3))}")

    _dump(checks, {"demis": demis, "excess_deaths": excess, "benefit": benefit,
                   "rc_error_reform": rc_r, "macro": {k: float(np.nanmean(v)) for k, v in macro.items()},
                   "welfare_by_J": [float(x) for x in inc["welfare_by_J"]]})


def _dump(checks, summary):
    print("\n" + "-" * 72)
    npass = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:42} {detail}")
    print("-" * 72)
    print(f"  {npass}/{len(checks)} checks passed")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "validation.json"), "w") as f:
        json.dump({"checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
                   "summary": summary}, f, indent=2, default=str)


if __name__ == "__main__":
    main()
