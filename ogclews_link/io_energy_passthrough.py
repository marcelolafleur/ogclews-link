"""Input-output energy cost pass-through (Leontief price model) from the PHL SAM.

OG-Core has no energy in production (Phase 2 / energy-as-input is out of scope), so it cannot natively
pass an energy-price shock through inter-industry linkages. But the SAM's use table can — offline. This
computes, for a CLEWS energy-price change, the cost impact on each industry: DIRECT (own energy use) +
INDIRECT (energy embodied in purchased intermediates). That total cost-push per industry is what a
route-B per-industry Z haircut should be calibrated to, so the existing TFP lever carries the
pass-through the production function can't. Read-only on the SAM.

Method (Leontief price model): A[i,j] = (commodity i used by activity j) / (activity j gross output),
with commodity ``c<x>`` mapped to activity ``a<x>``. Direct energy cost coefficient e_j = energy-
commodity use by activity j / gross output. Total embodied energy intensity  eps = e @ (I - A)^{-1}.
For an energy price rise g (fraction), cost-push_j ~= eps_j * g (total) vs e_j * g (direct only); the
ratio eps_j/e_j is the indirect amplification. Aggregate to M industries (gross-output weighted).
A route-B calibration then sets dZ_m/Z_m = -cost_push_m.
"""
from __future__ import annotations

import numpy as np

from .energy_calibration import ELECTRICITY_COMMODITY, ENERGY_AND_FUELS, M4_PROD_DICT


def _activity_commodity_maps(sam):
    acts = [c for c in sam.columns if isinstance(c, str) and c.startswith("a")]
    # keep activities that have a matching commodity row c<name> (diagonal make assumption)
    pairs = [(a, "c" + a[1:]) for a in acts if ("c" + a[1:]) in sam.index]
    return [a for a, _ in pairs], [c for _, c in pairs]


def leontief_energy_intensity(energy_commodity, sam=None):
    """Return (acts, e_direct, eps_total): activity codes, direct energy cost coefficients, and total
    (direct+indirect) embodied energy cost intensity per unit output, from the SAM."""
    if sam is None:
        from ogphl.input_output import read_SAM
        sam = read_SAM()
    acts, comms = _activity_commodity_maps(sam)
    X = sam.loc[comms, acts].astype(float).values          # use table: commodity rows x activity cols
    gross = sam[acts].astype(float).values.sum(axis=0)     # activity gross output (column totals)
    gross_safe = np.where(gross > 0, gross, np.nan)
    A = X / gross_safe                                     # technical coefficients (commodity~activity)
    A = np.nan_to_num(A, nan=0.0)
    erows = [c for c in energy_commodity if c in sam.index]
    e_direct = (sam.loc[erows, acts].astype(float).values.sum(axis=0) / gross_safe)
    e_direct = np.nan_to_num(e_direct, nan=0.0)
    n = len(acts)
    L = np.linalg.inv(np.eye(n) - A)                       # Leontief inverse
    sr = np.max(np.abs(np.linalg.eigvals(A)))              # spectral radius sanity check (<1)
    eps_total = e_direct @ L                               # total embodied energy intensity by activity
    return acts, e_direct, eps_total, float(sr)


def cost_push_by_industry(g, energy_commodity=None, prod_dict=None, sam=None):
    """Per-M-industry cost-push from an energy price rise of fraction ``g``: gross-output-weighted
    direct and total (Leontief) cost increases, plus the route-B Z haircut dZ/Z = -total."""
    energy_commodity = energy_commodity or ELECTRICITY_COMMODITY
    prod_dict = prod_dict or M4_PROD_DICT
    if sam is None:
        from ogphl.input_output import read_SAM
        sam = read_SAM()
    acts, e_direct, eps_total, sr = leontief_energy_intensity(energy_commodity, sam)
    gross = {a: float(sam[a].astype(float).sum()) for a in acts}
    idx = {a: i for i, a in enumerate(acts)}
    out = {"_spectral_radius_A": sr}
    for ind, codes in prod_dict.items():
        codes = [a for a in dict.fromkeys(codes) if a in idx]
        w = np.array([gross[a] for a in codes])
        if w.sum() <= 0:
            continue
        direct = float(np.average([e_direct[idx[a]] for a in codes], weights=w)) * g
        total = float(np.average([eps_total[idx[a]] for a in codes], weights=w)) * g
        out[ind] = {"direct_pct": direct * 100, "total_pct": total * 100,
                    "indirect_amplification": (total / direct) if direct > 0 else float("nan"),
                    "Z_haircut": -total}
    return out


if __name__ == "__main__":
    for label, carrier in (("ELECTRICITY (celec)", ELECTRICITY_COMMODITY),
                           ("ENERGY+FUELS (celec+cmine+cwatr)", ENERGY_AND_FUELS)):
        g = 0.20
        res = cost_push_by_industry(g, energy_commodity=carrier)
        print(f"\n+{g:.0%} {label} price shock -> cost-push by M=4 industry "
              f"(spectral radius A={res.pop('_spectral_radius_A'):.3f}):")
        print(f"  {'industry':32s} {'direct':>8s} {'total':>8s} {'amplif':>7s} {'Z haircut':>10s}")
        for ind, r in res.items():
            print(f"  {ind:32s} {r['direct_pct']:7.3f}% {r['total_pct']:7.3f}% "
                  f"{r['indirect_amplification']:6.2f}x {r['Z_haircut']:+9.4f}")
