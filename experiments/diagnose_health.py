"""No-solve diagnostic for the health channel SS resource-constraint failure. Rebuilds the
baseline PARAMS (fast; NO OG solve -- the saved baseline solve is reused elsewhere), applies
the health shock three ways (mortality-only / morbidity-only / both), and inspects the
resulting demographic + ability arrays for the kind of breakage that makes the steady-state
resource constraint fail (omega not summing to 1, SS population not stationary, g_n_ss off).

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/diagnose_health.py
"""
from __future__ import annotations

import copy
import json

import numpy as np

from ogclews_link import channels
from ogclews_link.country import PHL
from ogclews_link.framework import ExperimentContext
from ogclews_link.runtime import Runtime

BASE = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/validate_health/health/baseline"


def inspect(p0, pr):
    out = {}
    for a in ("rho", "omega", "g_n", "imm_rates", "e"):
        b, x = np.asarray(getattr(p0, a), float), np.asarray(getattr(pr, a), float)
        out[a] = dict(
            changed=bool(not np.allclose(b, x)),
            finite=bool(np.isfinite(x).all()),
            shape=str(x.shape),
            maxabsdiff=(float(np.nanmax(np.abs(x - b))) if b.shape == x.shape else "SHAPE-MISMATCH"),
        )
    om = np.asarray(pr.omega, float)
    out["omega_rowsum_range"] = [round(float(om.sum(1).min()), 6), round(float(om.sum(1).max()), 6)]
    # SS population must be stationary: the last omega row should equal omega_SS
    out["omega_SS_stationarity_maxdiff"] = float(np.max(np.abs(om[-1] - np.asarray(pr.omega_SS, float))))
    out["g_n_ss_base_vs_reform"] = [round(float(p0.g_n_ss), 6), round(float(pr.g_n_ss), 6)]
    rb, rr = np.asarray(p0.rho, float), np.asarray(pr.rho, float)
    out["rho_elderly_mean_base_vs_reform"] = [round(float(rb[:, -16:].mean()), 6),
                                              round(float(rr[:, -16:].mean()), 6)]
    return out


def main():
    rt = Runtime(num_workers=1, show_progress=False)
    print("building baseline params (no solve)...")
    p0, _ = rt.build_baseline(PHL, BASE)
    for tag, aff in (("both", ("mortality", "e")), ("mortality", ("mortality",)), ("morbidity", ("e",))):
        pr = copy.deepcopy(p0)
        pr.baseline = False
        pr.__dict__.pop("_e_long_cache", None)
        ctx = ExperimentContext(country=PHL, og_reform=pr, base_tpi=None)
        prov = channels.health(ctx, affects=aff)
        if ctx.extras.get("health_shock") is not None:
            ctx.og_reform = rt.apply_health_shock(ctx.og_reform, ctx.extras["health_shock"])
        print(f"\n=== {tag}  affects={aff} ===")
        print("inputs:", {k: v for k, v in prov.items() if k != "profile"})
        print("sanity:", json.dumps(inspect(p0, ctx.og_reform)))


if __name__ == "__main__":
    main()
