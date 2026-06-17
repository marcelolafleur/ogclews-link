"""Actual OG-PHL (M=4) model run of a PRIVATE-capex incentive: an energy-industry investment tax
credit (route-B-on-the-firm-tax-side). Validates the generic `set_investment_incentive` lever end to
end: a permanent ITC on the energy industry lowers its cost of capital -> firms invest more -> the
energy industry's private capital K_m rises (and GDP responds). Reuses the standalone M=4 build; SS-only;
isolated /tmp output, read-only on ogcore/ogphl. Guarded for dask spawn.

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link-energy \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/run_energy_itc.py
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

from ogclews_link.energy_calibration import M4_PROD_DICT
from ogclews_link.policy_levers import (industry_registry, resolve_industry,
                                        set_investment_incentive)

sys.path.insert(0, "/Users/mlafleur/Projects/CLEWS-OG/OG_simulations")
import get_pop_data  # noqa: E402

OUT = "/tmp/og_m4_energy_itc"
ITC = 0.20            # 20% investment tax credit on the energy industry (permanent)


def build_baseline(out):
    os.makedirs(out, exist_ok=True)
    p = Specifications(baseline=True, num_workers=1, baseline_dir=out, output_base=out)
    with importlib.resources.open_text("ogphl", "ogphl_default_parameters.json") as f:
        p.update_specifications(json.load(f))
    io_df = io.get_io_matrix(prod_dict=M4_PROD_DICT)
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
    p, cols = build_baseline(os.path.join(OUT, "baseline"))
    print(f"industries={cols}; inv_tax_credit shape={np.asarray(p.inv_tax_credit).shape}")
    client = Client(processes=False, dashboard_address=None)
    try:
        base = solve_ss(p, client)
        Yb, Kb = float(base["Y"]), float(base["K"]); Kmb = np.atleast_1d(base["K_m"]); Db = float(base["D"])
        pr = copy.deepcopy(p); pr.baseline = False
        pr.baseline_dir = os.path.join(OUT, "baseline"); pr.output_base = os.path.join(OUT, "reform")
        os.makedirs(pr.output_base, exist_ok=True)
        reg = industry_registry(pr, names=list(M4_PROD_DICT), resource_index={"energy": 1})
        m_energy = resolve_industry("energy", reg)         # name -> index via the model-derived registry
        prov = set_investment_incentive(pr, m_energy, inv_tax_credit=ITC, phase_years=None)
        print(f"applied: {prov}")
        ref = solve_ss(pr, client)
        Yr, Kr = float(ref["Y"]), float(ref["K"]); Kmr = np.atleast_1d(ref["K_m"]); Dr = float(ref["D"])
        print(f"\n{ITC:.0%} energy ITC -> SS effects:")
        print(f"  GDP (Y):           {100*(Yr-Yb)/Yb:+.4f}%")
        print(f"  aggregate K:       {100*(Kr-Kb)/Kb:+.4f}%")
        print("  industry capital K_m:")
        for i, c in enumerate(cols):
            print(f"    {c:32s} {100*(Kmr[i]-Kmb[i])/Kmb[i]:+.4f}%")
        print(f"  govt debt D:       {100*(Dr-Db)/abs(Db):+.4f}%  (the ITC's fiscal cost)")
        em = cols.index("Electricity")
        print(f"\nLEVER CHECK: energy-industry private capital {'ROSE' if Kmr[em] > Kmb[em] else 'did NOT rise'} "
              f"({100*(Kmr[em]-Kmb[em])/Kmb[em]:+.3f}%) under the ITC.")
    except Exception as e:  # noqa: BLE001
        print(f"SOLVE FAILED {type(e).__name__}: {str(e)[:160]}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
