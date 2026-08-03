"""Which of IEEM's headline indicators can we already compute from a solved case?

Exploratory probe behind `docs/design/ieem-comparative-assessment.md`. The arithmetic
lives in `ogclews_link.env_accounts`; this script just points it at the shipped
`CLEWs Demo` case and prints what comes out.

IEEM (IDB) publishes a wealth figure and a biodiversity index we do not. Both are
defined in Banerjee et al. (2020), IDB-WP-01193:

  Composite BII -- area-weighted mean of a per-land-class coefficient (their sec. 2.4).
  Genuine saving -- eq. 2:
      GenuineSAV_t = GNSAV_t - DeprCapStock_t - DeplForStock_t - DeplMinStock_t - EmiVal_t
  with natural-capital depletion valued by eq. 3, unit rent endogenous, 4% discount.

Usage:
    uv run python experiments/ieem_indicator_probe.py [CASE_DIR]

Default CASE_DIR is the MUIOGO demo case. Reads only; never writes to the case.

The BII coefficients below are illustrative literature central tendencies, NOT
country-specific PREDICTS means. They prove the arithmetic path. They are not a result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ogclews_link.env_accounts import (
    DEMO_LAND_MAP,
    LandClosureError,
    composite_index,
    depletion_flow,
    emissions_damage,
    land_use_by_year,
    natural_capital_depletion,
)
from ogclews_link.signals import commodity_shadow_price

DEFAULT_CASE = Path(
    "/Users/marcelolafleur/Projects/MUIOGO/WebAPP/DataStorage/CLEWs Demo"
)

# Illustrative only -- see module docstring.
BII_COEF = {
    "Forest": 0.95,
    "Cropland": 0.55,
    "Built-up": 0.35,
    "Water bodies": 0.90,
}

SOCIAL_COST_CO2 = 30.0  # US$/tCO2, the value used in IDB-WP-01193 eq. 2

# The demo exports CH4, CO2, N2O and their CO2EQ aggregate; pricing the aggregate
# at the SCC is the eq.2 reading. Summing all four would double-count (bug §3.2).
EMISSION_SPECIES = "CO2EQ"

DUAL_NAMES = [
    "E8_AnnualEmissionsLimit",
    "EBb4_EnergyBalanceEachYear4_ICR",
    "UDC1_UserDefinedConstraintInequality",
    "UDC2_UserDefinedConstraintEquality",
]

TERM_STATUS = [
    ("land-cover state vector (LULC)", "PRESENT",
     "solved annual areas by class, closing exactly on the land resource"),
    ("composite BII", "COMPUTABLE NOW",
     "area-weighted mean over that vector; needs PREDICTS coefficients only"),
    ("EmiVal (CO2 damage)", "COMPUTABLE NOW",
     "AnnualTechnologyEmission x social cost of carbon"),
    ("qdepl (quantity depleted)", "PRESENT",
     "net decline of the cover-class stock (depletion_flow over solved areas)"),
    ("unitrent (eq.3 unit rent)", "PRESENT",
     ("land is an ordinary commodity, so its balance dual is already exported in "
      "EBb4 -- read with commodity_shadow_price(fuel='LND', drop_zero=False)")),
    ("GNSAV, DeprCapStock", "NOT A CLEWS QUANTITY",
     "national-accounts aggregates; OG-Core produces these"),
]


def available_duals(run: Path) -> list[str]:
    return [n for n in DUAL_NAMES if (run / "csv" / f"{n}.csv").exists()]


def main(argv: list[str]) -> int:
    case = Path(argv[1]) if len(argv) > 1 else DEFAULT_CASE
    if not (case / "res").is_dir():
        print(f"no solved runs under {case}/res")
        return 1

    runs = sorted(p for p in (case / "res").iterdir() if p.is_dir())
    print(f"case: {case.name}   scenarios: {[r.name for r in runs]}\n")

    summary: dict[str, dict] = {}
    for run in runs:
        try:
            cover, resource = land_use_by_year(run, DEMO_LAND_MAP)
        except LandClosureError as exc:
            print(f"--- {run.name}: CLOSURE FAILED -- {exc}\n")
            continue
        if not cover:
            print(f"--- {run.name}: no land output\n")
            continue

        years = sorted(cover)
        first, last = years[0], years[-1]
        b0 = composite_index(cover[first], BII_COEF)
        b1 = composite_index(cover[last], BII_COEF)
        emi = emissions_damage(run, SOCIAL_COST_CO2, species=EMISSION_SPECIES)

        print(f"--- {run.name} ({first}-{last})")
        for y in (first, last):
            areas = ", ".join(f"{k}={v:,.2f}" for k, v in sorted(cover[y].items()))
            total = sum(cover[y].values())
            print(f"    {y}: {areas}")
            print(f"{'':9}total={total:,.4f}  land resource={resource[y]:,.4f}  "
                  f"gap={total - resource[y]:+.2e}  [closure OK]")
        if b0 is not None and b1 is not None:
            print(f"    composite BII: {b0:.4f} -> {b1:.4f} "
                  f"({(b1 - b0) / b0 * 100:+.3f}%)   [illustrative coefficients]")
        if emi:
            ey = sorted(emi)
            print(f"    EmiVal @ ${SOCIAL_COST_CO2:.0f}/t {EMISSION_SPECIES}: "
                  f"{ey[0]}={emi[ey[0]]:,.1f} -> {ey[-1]}={emi[ey[-1]]:,.1f}")

        duals = available_duals(run)
        print(f"    duals exported: {duals}")

        # eq.3 end-to-end: the land balance dual as the unit rent (drop_zero MUST
        # be off -- a zero land dual is true abundance, not a missing year), and
        # forest net decline as the depletion flow. Units are the case's own
        # (currency per area unit x area), so this is a mechanism check.
        rents = commodity_shadow_price(
            run / "csv", fuel="LND", drop_zero=False
        ).to_dict()
        priced = {y: v for y, v in rents.items() if abs(v) > 1e-9}
        flow = depletion_flow({y: cover[y].get("Forest", 0.0) for y in years})
        depletion = natural_capital_depletion(flow, rents)
        print(f"    LND balance dual: {len(rents)} years read, "
              f"nonzero in {sorted(priced) or 'none'}")
        print(f"    eq.3 natural-capital depletion (forest, PV @4%): "
              f"{depletion:,.4f}")

        summary[run.name] = {
            "years": [first, last],
            "bii": [b0, b1],
            "cover_first": cover[first],
            "cover_last": cover[last],
            "duals": duals,
            "lnd_dual_nonzero_years": {y: priced[y] for y in sorted(priced)},
            "forest_depletion_flow_total": sum(flow.values()),
            "eq3_forest_depletion_pv": depletion,
        }

    print("\n=== eq.2 / eq.3 term availability in a solved MUIOGO case ===")
    for name, status, note in TERM_STATUS:
        print(f"  [{status:>21}]  {name}")
        print(f"{'':26}{note}")

    out = Path(__file__).with_name("ieem_indicator_probe_result.json")
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
