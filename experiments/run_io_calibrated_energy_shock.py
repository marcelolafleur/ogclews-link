"""Actual OG-PHL (M=4) model run of an I-O-CALIBRATED energy resource-cost shock (route B done right).

Pipeline that works with what we have (no Phase-2 model extension):
  1. Leontief price model on the PHL SAM -> per-industry total (direct+indirect) cost-push from an
     energy-price shock g  (ogclews_link.io_energy_passthrough).
  2. Apply it as a per-industry TFP haircut Z[:,m] *= (1 - cost_push_m) -- so the existing supply-side
     lever carries the inter-industry pass-through, calibrated (not hand-set).
  3. Solve baseline vs reform SS and compare GDP + industry output.

Contrast with the consumption-tax (tau_c) route: a properly-calibrated supply-side cost shock should
LOWER GDP (a real resource cost), not raise it. SS-only (fast). Isolated: own /tmp output dir, read-only
on ogcore/ogphl/SAM, never touches the shared run dirs. Guarded for dask spawn.

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link-energy \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/run_io_calibrated_energy_shock.py
"""
import copy
import json
import os
import sys

import importlib.resources
import numpy as np
from distributed import Client
from ogcore.execute import runner
from ogcore.parameters import Specifications
from ogcore.utils import safe_read_pickle
from ogphl import input_output as io

from ogclews_link.energy_calibration import ENERGY_AND_FUELS, M4_PROD_DICT
from ogclews_link.io_energy_passthrough import cost_push_by_industry

sys.path.insert(0, "/Users/mlafleur/Projects/CLEWS-OG/OG_simulations")
import get_pop_data  # noqa: E402

OUT = "/tmp/og_m4_io_energy"
G = 0.20                       # +20% energy(+fuels) price shock (stand-in for a CLEWS dual ratio)


def build_baseline(out):
    os.makedirs(out, exist_ok=True)
    p = Specifications(baseline=True, num_workers=1, baseline_dir=out, output_base=out)
    with importlib.resources.open_text("ogphl", "ogphl_default_parameters.json") as f:
        p.update_specifications(json.load(f))
    io_df = io.get_io_matrix(prod_dict=M4_PROD_DICT)        # (I=5, M=4) SAM-calibrated
    alpha_c = io.get_alpha_c()
    p.M, p.I = io_df.shape[1], io_df.shape[0]
    p.update_specifications({
        "gamma_g": [p.gamma_g] * p.M, "epsilon": [p.epsilon] * p.M, "gamma": [p.gamma] * p.M,
        "cit_rate": [[p.cit_rate[0][0]]], "tau_c": [[float(p.tau_c[0][0])] * p.I],
        "c_min": [0.0] * p.I, "alpha_c": np.array(list(alpha_c.values())), "io_matrix": io_df.values,
        "initial_guess_r_SS": 0.06, "initial_guess_TR_SS": 0.2, "initial_guess_factor_SS": 144617.0,
    })
    pop = get_pop_data.baseline_pop(p, un_country_code="608", download=False)
    p.update_specifications(pop[0])
    return p, list(io_df.columns)


def solve_ss(p, client):
    runner(p, time_path=False, client=client)
    return safe_read_pickle(os.path.join(p.output_base, "SS", "SS_vars.pkl"))


def main():
    push = cost_push_by_industry(G, energy_commodity=ENERGY_AND_FUELS)
    push.pop("_spectral_radius_A", None)
    p, cols = build_baseline(os.path.join(OUT, "baseline"))
    haircut = np.array([1.0 + push[c]["Z_haircut"] for c in cols])   # (1 - cost_push_m) per industry
    print(f"industries={cols}")
    print(f"per-industry Z multiplier (1 - cost_push): {np.round(haircut, 4)}")

    client = Client(processes=False, dashboard_address=None)
    try:
        base = solve_ss(p, client)
        Yb = float(base["Yss"]); Ymb = np.atleast_1d(base["Y_vec_ss"])
        pr = copy.deepcopy(p); pr.baseline = False
        pr.baseline_dir = os.path.join(OUT, "baseline"); pr.output_base = os.path.join(OUT, "reform")
        os.makedirs(pr.output_base, exist_ok=True)
        pr.Z = np.asarray(p.Z, dtype=float) * haircut[None, :]       # permanent per-industry TFP haircut
        ref = solve_ss(pr, client)
        Yr = float(ref["Yss"]); Ymr = np.atleast_1d(ref["Y_vec_ss"])
        print(f"\nGDP (Yss): baseline={Yb:.5f}  reform={Yr:.5f}  change={100*(Yr-Yb)/Yb:+.4f}%")
        print("industry output Y_m change:")
        for i, c in enumerate(cols):
            print(f"  {c:32s} {100*(Ymr[i]-Ymb[i])/Ymb[i]:+.4f}%")
        print(f"\nSIGN CHECK: {'LOWERS GDP (correct for a resource cost)' if Yr < Yb else 'RAISES GDP (!)'}")
    except Exception as e:  # noqa: BLE001
        print(f"SOLVE FAILED {type(e).__name__}: {str(e)[:140]}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
