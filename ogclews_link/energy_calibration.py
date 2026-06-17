"""Phase-1 route-C calibration: per-industry energy cost share ``theta_m`` from the PHL SAM.

Feeds the energy-as-CES-input extension (see ``docs/design/energy-as-production-input-spec.md``):
the firm's energy nest needs, for each industry m, the share of energy in that industry's costs.
``theta_m`` = energy-commodity intermediate purchases by the industry's activities, divided by those
activities' gross output (column total), aggregated to the M=4 CLEWS industries.

Read-only: it imports ``ogphl.input_output.read_SAM`` only to read the packaged SAM and computes from
it. It modifies NO shared package. It is the standalone prototype of an ``ogphl.input_output``
``get_energy_use_shares`` that can be upstreamed once the route-C PR lands.
"""
from __future__ import annotations

# M=4 CLEWS production aggregation (the vendored PROD_DICT): industry -> SAM activity codes.
# "Electricity" = ["aelec"] (electricity ONLY -> clean match to the per-fuel CLEWS dual); water and
# mining sit in "Natural Resources". This is the proven-runnable platform (see the design spec).
M4_PROD_DICT = {
    "Natural Resources": ["amaiz", "arice", "aocer", "aoils", "aroot", "avege", "asugr", "atoba",
                          "acoff", "afrui", "aocrp", "acatt", "apoul", "aoliv", "afore", "afish",
                          "amine", "awatr"],
    "Electricity": ["aelec"],
    "Construction, Trade, Services": ["acons", "atrad", "atran", "ahotl", "acomm", "afsrv", "areal",
                                      "absrv", "apadm", "aeduc", "aheal", "aosrv"],
    "Manufacturing": ["afood", "abeve", "atext", "awood", "achem", "anmet", "ametl", "amach", "aoman"],
}

# Energy carriers in the SAM. CRITICAL calibration point: electricity (celec) is a SMALL input share
# in PHL (~0.4-0.7% of most industries' costs); the economically material energy cost is FUELS
# (cmine = petroleum/extraction, which the SAM groups under "Energy and water"). So the carrier you
# price dominates the result: an electricity-only route-C channel is structurally correct but
# quantitatively small; a material energy-cost story needs the fuel carrier (priced by the matching
# CLEWS fuel dual). The minimal one-carrier version should price whichever carrier the shock is about.
ELECTRICITY_COMMODITY = ["celec"]
ENERGY_AND_FUELS = ["celec", "cmine", "cwatr"]   # electricity + fuels + water (the "Energy and water" set)


def get_energy_use_shares(prod_dict=None, energy_commodity=None, sam=None):
    """``theta_m``: energy intermediate cost share by industry, from the SAM (read-only).

    Returns ``{industry: share}``. ``share`` = (energy-commodity rows purchased by the industry's
    activity columns) / (those activity columns' gross output). Activity lists are de-duplicated so a
    repeated SAM code can't double-count (the packaged PROD_DICT lists ``acoff`` twice).
    """
    prod_dict = prod_dict or M4_PROD_DICT
    energy_commodity = energy_commodity or ELECTRICITY_COMMODITY
    if sam is None:
        from ogphl.input_output import read_SAM
        sam = read_SAM()
    erows = [c for c in energy_commodity if c in sam.index]
    if not erows:
        raise ValueError(f"energy commodity rows {energy_commodity} not found in SAM index")
    theta = {}
    for industry, acts in prod_dict.items():
        cols = list(dict.fromkeys(a for a in acts if a in sam.columns))  # dedup, preserve order
        if not cols:
            theta[industry] = 0.0
            continue
        energy_in = sam.loc[erows, cols].astype(float).values.sum()
        gross = sam[cols].astype(float).values.sum()
        theta[industry] = float(energy_in / gross) if gross > 0 else 0.0
    return theta


def fine_activity_shares(energy_commodity=None, sam=None, top=12):
    """Diagnostic: energy cost share by FINE SAM activity (shows the within-Manufacturing
    heterogeneity that the M=4 aggregation averages away). Returns a sorted list of (code, share)."""
    energy_commodity = energy_commodity or ELECTRICITY_COMMODITY
    if sam is None:
        from ogphl.input_output import read_SAM
        sam = read_SAM()
    erows = [c for c in energy_commodity if c in sam.index]
    acts = [c for c in sam.columns if isinstance(c, str) and c.startswith("a")]
    out = []
    for a in acts:
        gross = float(sam[a].astype(float).sum())
        if gross > 0:
            out.append((a, float(sam.loc[erows, a].astype(float).sum()) / gross))
    return sorted((x for x in out if x[1] > 0), key=lambda kv: -kv[1])[:top]


if __name__ == "__main__":
    for label, carrier in (("ELECTRICITY only (celec)", ELECTRICITY_COMMODITY),
                           ("ENERGY+FUELS (celec+cmine+cwatr)", ENERGY_AND_FUELS)):
        print(f"\ntheta_m by M=4 industry — {label}:")
        for ind, sh in get_energy_use_shares(energy_commodity=carrier).items():
            print(f"  {ind:32s} {sh * 100:6.2f} %")
    print("\nfine-activity ENERGY+FUELS shares (top — the within-Manufacturing heterogeneity M=4 averages):")
    for code, sh in fine_activity_shares(energy_commodity=ENERGY_AND_FUELS):
        print(f"  {code:8s} {sh * 100:6.2f} %")
