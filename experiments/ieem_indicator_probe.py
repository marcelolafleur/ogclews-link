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
from dataclasses import dataclass
from pathlib import Path

from ogclews_link.env_accounts import (
    DEMO_LAND_MAP,
    PHL_V12_LAND_MAP,
    LandClosureError,
    LandMap,
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
    "Grassland": 0.70,
    "Barren": 0.40,
    "Other": 0.50,
    "Unallocated": 0.50,
}

SOCIAL_COST_CO2 = 30.0  # US$/tCO2, the value used in IDB-WP-01193 eq. 2


@dataclass(frozen=True)
class CaseProfile:
    """What differs between cases: land naming, emission species, land commodity."""

    land_map: LandMap
    species: str
    land_fuel: str


# Keyed by a substring of the case directory name. Both entries are verified against
# a real solve; a case matching neither is refused rather than read with a guess.
PROFILES = {
    # The demo exports CH4, CO2, N2O and their CO2EQ aggregate; pricing the aggregate
    # at the SCC is the eq.2 reading. Summing all four would double-count (bug §3.2).
    "CLEWs Demo": CaseProfile(DEMO_LAND_MAP, "CO2EQ", "LND"),
    # PHL exports CO2e and PM2_5 -- summing them would price particulates at the SCC.
    "Philippines_v12": CaseProfile(PHL_V12_LAND_MAP, "CO2e", "PHL_LND"),
}


def profile_for(case: Path) -> CaseProfile:
    for key, prof in PROFILES.items():
        if key in case.name:
            return prof
    raise SystemExit(
        f"no land map / species profile for case {case.name!r}; known: "
        f"{sorted(PROFILES)}. Add one -- reading land with the wrong map is how "
        "you get a silently empty answer."
    )

SHADOW_PRICE_FILES = [
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
     ("land is an ordinary commodity, so its balance shadow price is already exported in "
      "EBb4 -- read with commodity_shadow_price(fuel='LND', drop_zero=False)")),
    ("GNSAV, DeprCapStock", "NOT A CLEWS QUANTITY",
     "national-accounts aggregates; OG-Core produces these"),
]


def available_shadow_price_files(run: Path) -> list[str]:
    return [n for n in SHADOW_PRICE_FILES if (run / "csv" / f"{n}.csv").exists()]


def main(argv: list[str]) -> int:
    case = Path(argv[1]) if len(argv) > 1 else DEFAULT_CASE
    if not (case / "res").is_dir():
        print(f"no solved runs under {case}/res")
        return 1
    prof = profile_for(case)

    runs = sorted(p for p in (case / "res").iterdir() if (p / "csv").is_dir())
    print(f"case: {case.name}   scenarios: {[r.name for r in runs]}")
    print(f"land resource: {prof.land_map.resource_tech}   "
          f"land commodity: {prof.land_fuel}   species: {prof.species}\n")

    summary: dict[str, dict] = {}
    for run in runs:
        try:
            cover, resource = land_use_by_year(run, prof.land_map)
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
        emi = emissions_damage(run, SOCIAL_COST_CO2, species=prof.species)

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
            print(f"    EmiVal @ ${SOCIAL_COST_CO2:.0f}/t {prof.species}: "
                  f"{ey[0]}={emi[ey[0]]:,.1f} -> {ey[-1]}={emi[ey[-1]]:,.1f}")

        exported = available_shadow_price_files(run)
        print(f"    shadow prices exported: {exported}")

        # eq.3 end-to-end: the land balance shadow price as the unit rent (drop_zero MUST
        # be off -- a zero land shadow price is true abundance, not a missing year), and
        # forest net decline as the depletion flow. Units are the case's own
        # (currency per area unit x area), so this is a mechanism check.
        rents = commodity_shadow_price(
            run / "csv", fuel=prof.land_fuel, drop_zero=False
        ).to_dict()
        priced = {y: v for y, v in rents.items() if abs(v) > 1e-9}
        flow = depletion_flow({y: cover[y].get("Forest", 0.0) for y in years})
        depletion = natural_capital_depletion(flow, rents)
        biggest = max((abs(v) for v in rents.values()), default=0.0)
        print(f"    {prof.land_fuel} balance shadow price: {len(rents)} years read, "
              f"nonzero in {sorted(priced) or 'none'}, |max|={biggest:.3e}")
        print(f"    forest depletion flow: {sum(flow.values()):,.4f} over "
              f"{len(flow)} yr")
        print(f"    eq.3 natural-capital depletion (forest, PV @4%): "
              f"{depletion:,.4f}")
        # A rent at or below CBC's shadow-price reporting resolution is not a price. On PHL
        # this is the MINLNDTOT placeholder's token variable cost (1e-4), not scarcity.
        if 0 < biggest <= 1e-3:
            print(f"{'':4}[!] every nonzero rent is <= 1e-3, CBC's shadow price resolution: "
                  "this is the token cost of an unbounded land resource, not a "
                  "scarcity rent. The depletion figure above is not economically "
                  "meaningful (see plan stage 4).")
        elif biggest == 0.0:
            print(f"{'':4}[!] land rent identically zero -- land never priced.")

        summary[run.name] = {
            "years": [first, last],
            "bii": [b0, b1],
            "cover_first": cover[first],
            "cover_last": cover[last],
            "shadow_prices_exported": exported,
            "land_fuel": prof.land_fuel,
            "land_dual_nonzero_years": {y: priced[y] for y in sorted(priced)},
            "land_dual_max_abs": biggest,
            "land_rent_is_token_cost": 0 < biggest <= 1e-3,
            "forest_depletion_flow_total": sum(flow.values()),
            "eq3_forest_depletion_pv": depletion,
        }

    print("\n=== eq.2 / eq.3 term availability in a solved MUIOGO case ===")
    for name, status, note in TERM_STATUS:
        print(f"  [{status:>21}]  {name}")
        print(f"{'':26}{note}")

    # One file per case -- a shared name would let a PHL run silently overwrite the
    # demo's committed result, and the two are not comparable line for line.
    slug = "".join(c if c.isalnum() else "_" for c in case.name).strip("_").lower()
    out = Path(__file__).with_name(f"ieem_indicator_probe_{slug}.json")
    out.write_text(json.dumps({"case": case.name, "runs": summary}, indent=2) + "\n")
    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
