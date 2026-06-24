"""Experiment 01 -- does OG-Core energy demand fall when CLEWS says energy is costlier?

The first test of the de novo thesis: the energy-price -> household demand-response
channel is testable on the *shipped* model with no core change, because households
already respond to the effective energy price (EqHH_ciDem2).

Pipeline:
  1. build the OG-PHL baseline (M=4, I=5) -- mirrors CLEWS-OG/OG_simulations/
     PEP_simulation.py, but WITHOUT its hand-set Z / alpha_G;
  2. derive an electricity-price ratio (PEP / Base) from the CLEWS cost-of-electricity
     export, scaled into an "Energy and water" consumption-good price ratio by
     electricity's share of that good (io_matrix);
  3. apply it as a tau_c wedge on the energy good (route A);
  4. solve baseline and reform;
  5. read the aggregate demand response AND its incidence across income groups J.

Modes (argv[1]): "dry" (default) builds params + signal + wedge and prints, NO solve;
"full" runs the two OLG solves. Run with the OG-PHL venv python.
"""
from __future__ import annotations

import contextlib
import os
import sys

import numpy as np

from ogclews_link import og_wedge, signals
from ogclews_link._calibration import CONS_DICT as _CONS_DICT, PROD_DICT as _PROD_DICT
from ogclews_link.contract import Concordance, ScenarioPair

# This legacy demo BUILDS the link's old M=4 coupling calibration inline (electricity isolated at
# column 1). Its energy ports are discovered from THAT build's own dicts -- the engine no longer keeps a
# vendored country concordance (it is discovered per run in the OG env; see contract.Concordance).
_M4_CON = Concordance.from_dicts(_PROD_DICT, _CONS_DICT)


@contextlib.contextmanager
def _client(num_workers):
    """A dask client for OG-Core's J-loop.

    ogcore TPI calls ``client.scatter(p)`` unconditionally, so ``client=None`` crashes
    the time-path solve. Instead:
      * num_workers > 1 -> multi-process LocalCluster (fastest when stable, but the
        cross-process replication of the scattered Specifications can be flaky);
      * num_workers <= 1 -> single-process THREADED client (``processes=False``):
        scatter stays in-process so it can't be "lost during replication", and the
        numba/numpy inner loop releases the GIL so threads still parallelize the J-loop.
    ``dashboard_address=None`` disables the 8787 dashboard, removing the port-conflict
    vector. Context-managed so a throwing solve can never orphan the cluster.
    """
    from distributed import Client

    if num_workers and num_workers > 1:
        client = Client(n_workers=num_workers, threads_per_worker=1, dashboard_address=None)
    else:
        client = Client(processes=False, dashboard_address=None)
    try:
        yield client
    finally:
        client.close()

CLEWS = "/Users/mlafleur/Projects/CLEWS-OG/CLEWS_simulations"
CLEWS_OG_SIM = "/Users/mlafleur/Projects/CLEWS-OG/OG_simulations"  # calibration_values, get_pop_data
UN_PHL = "608"
REPO_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exp01_out")

# Controlled energy-services price shock for the MECHANISM test. The data-driven
# good-price ratio is only ~+/-1.5% (electricity is ~11% of the bundled "Energy and
# water" good and PEP electricity is ~as cheap as Base), so a clean sustained shock is
# what isolates "do households react to an energy price". Reported alongside the data.
SHOCK = 0.20  # +20% sustained energy-good price

PHL = ScenarioPair(
    name="PEP_vs_Base",
    base_dir=os.path.join(CLEWS, "v6-Base"),
    reform_dir=os.path.join(CLEWS, "v6-PEP"),
    years=tuple(range(2020, 2054)),
    og_start_year=2020,
)
COST_BASE = os.path.join(PHL.base_dir, "260108_Cost of electricity generation_PHL_Base.xlsx")
COST_PEP = os.path.join(PHL.reform_dir, "260108_Cost of electricity generation_PHL_PEP.xlsx")


def build_signal():
    ratio = signals.cost_of_electricity_ratio(COST_BASE, COST_PEP)
    print("CLEWS electricity cost ratio (PEP / Base), by year:")
    print(ratio.round(4).to_string())
    print(f"  range: {ratio.min():.4f} .. {ratio.max():.4f}  (1.0 = no change)")
    return ratio


def _build_ogphl_baseline(base_dir, num_workers):
    """OG-PHL M=4 / I=5 baseline Specifications -- mirrors PEP_simulation.py setup,
    minus its hand-set Z and alpha_G (this experiment supplies the energy signal)."""
    import importlib.resources
    import json

    from ogcore.parameters import Specifications

    sys.path.insert(0, CLEWS_OG_SIM)
    from ogphl import input_output as io

    import get_pop_data
    from calibration_values import PROD_DICT

    p = Specifications(baseline=True, num_workers=num_workers,
                       baseline_dir=base_dir, output_base=base_dir)
    with importlib.resources.open_text("ogphl", "ogphl_default_parameters.json") as f:
        p.update_specifications(json.load(f))

    p.M, p.I = 4, 5
    alpha_c = io.get_alpha_c()
    io_df = io.get_io_matrix(prod_dict=PROD_DICT)
    p.update_specifications({
        "gamma_g": [p.gamma_g] * p.M,
        "epsilon": [p.epsilon] * p.M,
        "gamma": [p.gamma] * p.M,
        "cit_rate": [[p.cit_rate[0][0]]],
        # 1 x I so the energy consumption good has its own tau_c column to wedge
        "tau_c": [[float(p.tau_c[0][0])] * p.I],
        # c_min must be length I for the multi-good demand (get_ci) in ogcore 0.16.1;
        # default is 0.0 (no Stone-Geary subsistence -> clean unit-elastic demand)
        "c_min": [0.0] * p.I,
        "alpha_c": np.array(list(alpha_c.values())),
        "io_matrix": io_df.values,
        # magic initial guesses from PEP_simulation ("work on the first try")
        "initial_guess_r_SS": 0.050 * 1.2,
        "initial_guess_TR_SS": 0.2,
        "initial_guess_factor_SS": 144617.0,
    })
    pop = get_pop_data.baseline_pop(p, un_country_code=UN_PHL, download=False)[0]
    p.update_specifications(pop)
    return p, io_df


def _good_price_ratio(elec_ratio, io_df, m_elec, i_energy):
    """Scale the electricity-industry cost ratio into an 'Energy and water' good price
    ratio by electricity's share of that good: good_ratio = 1 + share*(elec_ratio - 1)."""
    share = float(io_df.values[i_energy, m_elec])
    return 1.0 + share * (np.asarray(elec_ratio, dtype=float) - 1.0), share


def run_dry():
    ratio = build_signal()
    print("\n[dry] building OG-PHL baseline params (no solve)...")
    p, io_df = _build_ogphl_baseline(os.path.join(REPO_OUT, "baseline"), num_workers=1)
    print(f"  S={p.S}  T={p.T}  M={p.M}  I={p.I}  start_year={p.start_year}")
    print(f"  tau_c shape={np.array(p.tau_c).shape}  Z shape={np.array(p.Z).shape}")

    m_e, i_e = _M4_CON.energy_industry_index, _M4_CON.energy_good_index
    good_ratio, share = _good_price_ratio(ratio.values, io_df, m_e, i_e)
    print(f"  electricity share of 'Energy and water' good (io_matrix[{i_e},{m_e}]) = {share:.3f}")
    print(f"  -> energy-good price ratio range: {good_ratio.min():.4f} .. {good_ratio.max():.4f}")

    import copy
    p2 = copy.deepcopy(p)
    tau_before = np.array(p2.tau_c)[:5, i_e].copy()
    p2, diag = og_wedge.set_energy_consumption_wedge(p2, i_e, good_ratio, recycle=False)
    tau_after = np.array(p2.tau_c)[:5, i_e]
    print(f"  tau_c[energy] first 5 periods  before={np.round(tau_before,4)}")
    print(f"  tau_c[energy] first 5 periods   after={np.round(tau_after,4)}")
    print("\n[dry] wiring OK. Re-run with 'full' to solve baseline + reform.")


def run_full():
    import copy
    import multiprocessing

    from ogcore.execute import runner
    from ogcore.utils import safe_read_pickle

    ratio = build_signal()
    # workers from argv[2]; <= 1 means single-process threaded client (stable scatter)
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else min(multiprocessing.cpu_count(), 6)
    mode = f"{nw} processes" if nw > 1 else "threaded (1 process)"
    base_dir = os.path.join(REPO_OUT, "baseline")
    reform_dir = os.path.join(REPO_OUT, "reform")

    print(f"\n[full] building + solving OG-PHL baseline ({mode})...")
    p, io_df = _build_ogphl_baseline(base_dir, num_workers=nw)
    m_e, i_e = _M4_CON.energy_industry_index, _M4_CON.energy_good_index

    # context: what the actual CLEWS data implies for the bundled energy good
    data_ratio, share = _good_price_ratio(ratio.values, io_df, m_e, i_e)
    print(f"[full] data-driven energy-good price ratio = {data_ratio.min():.4f}..{data_ratio.max():.4f} "
          f"(elec share of good={share:.3f}) -> negligible; using controlled +{SHOCK:.0%} shock for the test")

    with _client(nw) as client:
        runner(p, time_path=True, client=client)

    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir
    p2, diag = og_wedge.set_energy_consumption_wedge(p2, i_e, 1.0 + SHOCK, recycle=False)
    print(f"[full] reform: energy-good tau_c {np.array(p.tau_c)[0, i_e]:.3f} -> {diag['tau_c_new'][0]:.3f}; solving...")
    with _client(nw) as client:
        runner(p2, time_path=True, client=client)

    base = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
    reform = safe_read_pickle(os.path.join(reform_dir, "TPI", "TPI_vars.pkl"))

    print("\n" + "=" * 64)
    print(f"RESULT: energy-good demand response to a +{SHOCK:.0%} energy price")
    print("=" * 64)
    dC = og_wedge.energy_demand_response(base["C_i"], reform["C_i"], i_e)
    print("aggregate energy-good consumption, % change by period (first 15):")
    print(np.round(dC[:15], 3))
    print(f"  mean over first 10 periods: {np.nanmean(dC[:10]):.3f}%   (expect < 0: demand falls)")

    # incidence (the OG-unique payoff): differential response across income groups J.
    # ogcore TPI c_i is (T, I, S, J); c (composite) is (T, S, J).
    try:
        eJ = og_wedge.energy_demand_response_by_group(base["c_i"], reform["c_i"], i_e)
        print(f"\nincidence -- energy consumption %chg by income group J (j0 low .. j{len(eJ)-1} high):")
        print(np.round(eJ, 2))
        cb, cr = np.asarray(base["c"]), np.asarray(reform["c"])
        wJ = 100.0 * (cr[:10].mean(axis=(0, 1)) - cb[:10].mean(axis=(0, 1))) / cb[:10].mean(axis=(0, 1))
        print("welfare -- composite consumption %chg by income group J (CAVEAT: tax NOT recycled):")
        print(np.round(wJ, 2))
        shJ = og_wedge.energy_budget_share_by_group(base["c_i"], base["p_i"], p.tau_c, i_e)
        print("baseline energy budget share by J (uniform => homothetic at c_min=0):", np.round(shJ, 4))
    except Exception as e:  # noqa: BLE001 -- diagnostics must not mask the main result
        print(f"\n[incidence read skipped: {type(e).__name__}: {e}]")

    # fiscal artifact: the tau_c wedge mechanically raises consumption-tax revenue
    try:
        rev_b, rev_r = np.asarray(base["cons_tax_revenue"]), np.asarray(reform["cons_tax_revenue"])
        print(f"\nfiscal artifact -- cons_tax_revenue mean %chg (first 10): "
              f"{100*np.nanmean((rev_r[:10]-rev_b[:10])/rev_b[:10]):.2f}%  (real revenue to government; recycle for a pure price signal)")
    except Exception:  # noqa: BLE001, S110
        pass
    print(f"\nresource_constraint_error max |.|: base={np.max(np.abs(base['resource_constraint_error'])):.2e} "
          f"reform={np.max(np.abs(reform['resource_constraint_error'])):.2e}  (near 0 = solved cleanly)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    {"dry": run_dry, "full": run_full}.get(mode, run_dry)()
