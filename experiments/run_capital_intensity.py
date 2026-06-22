"""Actual OG-PHL (M=4) model run of the gamma_energy capital-intensity lever -- a factor-SHARE /
production-technology shock on the energy industry. Solves baseline vs a reform that raises the energy
industry's capital exponent gamma[m] (calibrated from the CLEWS reform/base power-fleet capital-cost-
share ratio) and reports the mechanism.

VERIFIED RESULT (correct GE, not a bug): raising gamma does NOT pull capital into energy. Because gamma
is a Cobb-Douglas exponent (epsilon=1) and the energy good is small + demand-inelastic, the energy
output price COLLAPSES (~-24%), real output stays ~flat (+0.8%), and via K_m = gamma_m*p_m*Y_m/rho the
energy CAPITAL stock FALLS (~-14%) with r flat. So this lever's real effects are the energy PRICE and
the capital/labor income split -- NOT crowding-out. The capex-heavy-generation capital-draw-in /
crowding-out story belongs to the ITC lever (experiments/run_energy_itc.py: energy K +5%, via a lower
cost of capital). Reuses the standalone M=4 build; SS-only; isolated /tmp output, read-only on
ogcore/ogphl/CLEWS. Guarded for dask spawn.

    PYTHONPATH=/Users/mlafleur/Projects/ogclews-link \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/run_capital_intensity.py
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

from ogclews_link.country import PHL
from ogclews_link.energy_calibration import M4_PROD_DICT
from ogclews_link.policy_levers import set_capital_intensity
from ogclews_link.signals import capital_intensity_ratio

sys.path.insert(0, "/Users/mlafleur/Projects/CLEWS-OG/OG_simulations")
import get_pop_data  # noqa: E402

OUT = "/tmp/og_m4_capital_intensity"
WINDOW = (2026, 2035)          # first-decade calibration window (ties to og_start_year)


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


def _r(d):
    for k in ("r", "rss", "r_p"):
        if k in d:
            return float(np.atleast_1d(d[k]).ravel()[0])
    return float("nan")


def main():
    cal = capital_intensity_ratio(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL, window=WINDOW)
    scale = cal["ratio"]
    p, cols = build_baseline(os.path.join(OUT, "baseline"))
    m_e = PHL.concordance.energy_industry_index
    assert cols[m_e] == "Electricity", (m_e, cols)
    g0 = float(np.asarray(p.gamma)[m_e])
    print(f"industries={cols}")
    print(f"CLEWS calibration: power-fleet capital cost share base={cal['base_share']:.4f} "
          f"reform={cal['reform_share']:.4f} ratio={scale:.4f} (window {WINDOW})")
    print(f"energy gamma: {g0:.4f} -> {g0 * scale:.4f}  (labor share {1-g0-0.05:.4f} -> {1-g0*scale-0.05:.4f})")

    client = Client(processes=False, dashboard_address=None)
    try:
        base = solve_ss(p, client)
        Yb, Kb, rb = float(base["Y"]), float(base["K"]), _r(base)
        Kmb, Ymb, pmb = np.atleast_1d(base["K_m"]), np.atleast_1d(base["Y_m"]), np.atleast_1d(base["p_m"])
        pr = copy.deepcopy(p); pr.baseline = False
        pr.baseline_dir = os.path.join(OUT, "baseline"); pr.output_base = os.path.join(OUT, "reform")
        os.makedirs(pr.output_base, exist_ok=True)
        prov = set_capital_intensity(pr, m_e, gamma_scale=scale)
        print(f"\napplied: {prov}")
        ref = solve_ss(pr, client)
        Yr, Kr, rr = float(ref["Y"]), float(ref["K"]), _r(ref)
        Kmr, Ymr, pmr = np.atleast_1d(ref["K_m"]), np.atleast_1d(ref["Y_m"]), np.atleast_1d(ref["p_m"])
        print(f"\ngamma_energy {g0:.3f}->{g0*scale:.3f} -> SS effects:")
        print(f"  cost of capital r: {rb:.5f} -> {rr:.5f}  ({1e4*(rr-rb):+.1f} bps)")
        print(f"  GDP (Y):           {100*(Yr-Yb)/Yb:+.4f}%")
        print(f"  aggregate K:       {100*(Kr-Kb)/Kb:+.4f}%")
        print(f"  {'industry':32s} {'K_m %':>10s} {'Y_m %':>10s} {'p_m %':>10s}")
        for i, c in enumerate(cols):
            print(f"  {c:32s} {100*(Kmr[i]-Kmb[i])/Kmb[i]:+9.3f}% {100*(Ymr[i]-Ymb[i])/Ymb[i]:+9.3f}% "
                  f"{100*(pmr[i]-pmb[i])/pmb[i]:+9.3f}%")
        # MECHANISM CHECK (NOT a crowding-out check -- gamma is a factor-share/PRICE lever). The firm
        # identity K = gamma*p*Y/rho means a higher capital share against a COLLAPSING energy price and
        # ~flat output yields LESS energy capital. Confirm the identity closes and r stays flat.
        em = cols.index("Electricity")
        gK, gp, gY = Kmr[em] / Kmb[em], pmr[em] / pmb[em], Ymr[em] / Ymb[em]
        print(f"\nMECHANISM (Electricity): K {100*(gK-1):+.2f}%  =  gamma x{scale:.3f} * price {100*(gp-1):+.2f}%"
              f" * output {100*(gY-1):+.2f}%")
        print(f"  identity K = gamma*p*Y/rho:  gamma*p*Y = {scale*gp*gY:.4f}  vs observed K ratio {gK:.4f}"
              f"  (implied rho ratio {scale*gp*gY/gK:.4f}; ~1 => cost of capital flat)")
        print(f"  -> factor-share/PRICE lever: energy price {'FELL' if gp < 0.98 else 'did NOT fall'}, "
              f"r {'flat' if abs(rr-rb) < 1e-4 else 'moved'}, energy K {'fell' if gK < 1 else 'rose'}. "
              f"NOT crowding-out (that is the ITC lever's signature -- see run_energy_itc.py).")
    except Exception as e:  # noqa: BLE001
        print(f"SOLVE FAILED {type(e).__name__}: {str(e)[:160]}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
