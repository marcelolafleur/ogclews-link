"""Experiment 01 -- does OG-Core energy demand fall when CLEWS says energy is costlier?

The first test of the de novo thesis: the energy-price -> household demand-response
channel is the richest interaction, and (per the feasibility read) it is testable on
the *shipped* model with no core change, because households already respond to the
effective energy price (EqHH_ciDem2).

This script:
  1. builds the OG-PHL baseline (M=4, I=5),
  2. derives an energy-price ratio from the CLEWS PEP-vs-Base cost-of-electricity export,
  3. applies it as a tau_c wedge on the energy consumption good (route A),
  4. solves baseline and reform,
  5. reads the aggregate demand response AND its incidence across income groups J.

Heavy OG solves are GUARDED behind RUN_SIM -- flip it on a machine with ogcore + ogphl
installed and the distributed/dask cluster available. Left off, the script still builds
the wedge and prints the price signal + tau_c path so the setup can be inspected cheaply.
"""
from __future__ import annotations

import os

from ogclews_link import clews_signal, og_wedge
from ogclews_link.contract import PHL_CONCORDANCE, ScenarioPair

RUN_SIM = False  # flip on where ogcore + ogphl + a dask cluster are available

CLEWS = "/Users/mlafleur/Projects/CLEWS-OG/CLEWS_simulations"
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
    """The CLEWS energy-price ratio (reform/base) -- first-pass average-cost proxy."""
    ratio = clews_signal.cost_of_electricity_ratio(COST_BASE, COST_PEP)
    print("CLEWS electricity cost ratio (PEP / Base):")
    print(ratio.to_string())
    return ratio


def main():
    ratio = build_signal()

    if not RUN_SIM:
        print(
            "\nRUN_SIM is off -- showing setup only. The wedge would set tau_c on the "
            f"energy good (i={PHL_CONCORDANCE.energy_good_index}) so the effective energy "
            "price tracks the ratio above. Flip RUN_SIM where ogcore+ogphl are installed."
        )
        return

    # --- heavy path: build OG-PHL, apply wedge, solve, read response -------------
    import copy

    from ogcore.execute import runner
    from ogcore.parameters import Specifications

    from ogclews_link.iterate import _read_tpi

    base_dir = os.path.abspath("./exp01_out/baseline")
    reform_dir = os.path.abspath("./exp01_out/reform")

    p = _build_ogphl_baseline(base_dir)          # see helper: mirrors PEP_simulation setup
    runner(p, time_path=True)
    base = _read_tpi(base_dir)

    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir
    # route A: households face the CLEWS energy price via tau_c on the energy good
    p2, diag = og_wedge.set_energy_consumption_wedge(
        p2, PHL_CONCORDANCE.energy_good_index, ratio.values, recycle=False
    )
    runner(p2, time_path=True)
    reform = _read_tpi(reform_dir)

    dC = og_wedge.energy_demand_response(
        base["tpi"]["C_i"], reform["tpi"]["C_i"], PHL_CONCORDANCE.energy_good_index
    )
    print("\nEnergy-good demand response (reform vs base, % by year):")
    print(dC[:15])
    print(
        "\nIncidence read-out (energy budget share by income group J) is available from "
        "the disaggregated consumption path -- see og_wedge.energy_budget_share_by_group; "
        "confirm the TPI key for disaggregated c_i in OG-Core variables.md."
    )


def _build_ogphl_baseline(base_dir):  # pragma: no cover
    """Construct the M=4/I=5 OG-PHL baseline Specifications.

    Mirror the setup in CLEWS-OG/OG_simulations/PEP_simulation.py (defaults JSON, M=4,
    I=5, io_matrix, alpha_c, population) but DROP its hand-set Z/alpha_G -- this
    experiment supplies the energy signal from data instead. Kept as a stub so the
    import-light path stays runnable without ogphl.
    """
    raise NotImplementedError(
        "Wire OG-PHL baseline here (see PEP_simulation.py), minus its hand-set Z/alpha_G."
    )


if __name__ == "__main__":
    main()
