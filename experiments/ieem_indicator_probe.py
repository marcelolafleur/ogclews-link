"""Probe: can IEEM's headline indicators be computed from MUIOGO/CLEWS output as-is?

IEEM (IDB) reports two things our stack does not: a biodiversity index derived from
land cover, and a genuine-savings/wealth figure that nets natural-capital depletion off
national saving. Both are defined in Banerjee et al. (2020), IDB-WP-01193:

  Composite BII  -- assign a Biodiversity Intactness Index coefficient to each land-use
                    type (from PREDICTS), take the area-weighted mean. Paper section 2.4.

  Genuine saving -- eq. 2:
      GenuineSAV_t = GNSAV_t - DeprCapStock_t - DeplForStock_t - DeplMinStock_t - EmiVal_t
                    eq. 3, value of natural-capital depletion:
      sum_{i=t}^{t+T-1}  (qdepl_t * unitrent_t) / (1 + intrat)^(i-t)
                    with unit rent ENDOGENOUS in IEEM and intrat = 4% (Lange et al. 2018).

The question this probe answers is narrow and factual: which terms of those two
indicators are already present in a solved MUIOGO case, and which are missing?

READING LAND CORRECTLY (this cost one wrong first attempt, so it is written down):
a land technology's LAND AREA is its TotalAnnualTechnologyActivityByMode, NOT its
production. Land technologies output water flows (WTREVT/WTRGWT/WTRRUN) alongside any
land commodity, and LNDFOR outputs NO land commodity at all -- so reading area from
production silently drops forest and adds 10^9 m^3 water volumes to 10^3 km^2 areas.
The check that catches this: land-use areas must sum to the land resource RSCLND.
That closure identity is asserted below and must hold to 1e-3.

Run against the shipped CLEWs Demo, which solves all four scenarios.

    python experiments/ieem_indicator_probe.py

Nothing here is a calibrated result. The BII coefficients below are illustrative
stand-ins for country-specific PREDICTS means; they are here to prove the arithmetic
path, not to report a biodiversity number.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

CASE = Path(
    "/Users/marcelolafleur/Projects/MUIOGO/WebAPP/DataStorage/CLEWs Demo"
)

LAND_RESOURCE_TECH = "RSCLND"

# Land-use technologies -> cover class, with an illustrative BII coefficient.
# Real values are country-specific means from PREDICTS (Hudson et al. 2017;
# Newbold et al. 2016). These are rough literature central tendencies used ONLY
# to exercise the arithmetic.
LAND_TECH = {
    "LNDFOR": ("Forest", 0.95),
    "LNDMAIRNF": ("Cropland", 0.55),
    "LNDRICRNF": ("Cropland", 0.55),
    "LNDMAIIRR": ("Cropland", 0.55),
    "LNDRICIRR": ("Cropland", 0.55),
    "LNDBLT": ("Built-up", 0.35),
    "LNDWAT": ("Water bodies", 0.90),
}
BII_COEF = {name: coef for name, coef in LAND_TECH.values()}

SOCIAL_COST_CO2 = 30.0  # US$/tCO2, the value used in IDB-WP-01193 eq. 2
DISCOUNT = 0.04  # Lange et al. (2018), used in eq. 3
CLOSURE_TOL = 1e-3


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def land_by_year(scenario_dir: Path) -> tuple[dict, dict]:
    """Area (10^3 km^2) by cover class by year, plus the land-resource total.

    Area is the technology's annual ACTIVITY -- see module docstring.
    """
    rows = read_csv(
        scenario_dir / "csv" / "TotalAnnualTechnologyActivityByMode.csv"
    )
    col = "TotalAnnualTechnologyActivityByMode"
    cover: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    resource: dict[int, float] = defaultdict(float)
    for r in rows:
        tech, year, val = r["t"], int(r["y"]), float(r[col])
        if tech in LAND_TECH:
            cover[year][LAND_TECH[tech][0]] += val
        elif tech == LAND_RESOURCE_TECH:
            resource[year] += val
    return ({y: dict(v) for y, v in sorted(cover.items())}, dict(resource))


def check_closure(cover: dict, resource: dict, label: str) -> list[str]:
    """Land-use areas must sum to the land resource. Catches mis-reads."""
    problems = []
    for year, cls in cover.items():
        total, res = sum(cls.values()), resource.get(year)
        if res is None:
            problems.append(f"{label} {year}: no {LAND_RESOURCE_TECH} row")
        elif abs(total - res) > CLOSURE_TOL:
            problems.append(
                f"{label} {year}: land uses sum to {total:.4f} but "
                f"{LAND_RESOURCE_TECH}={res:.4f} (gap {total - res:+.4f})"
            )
    return problems


def composite_bii(cover: dict[str, float]) -> float | None:
    """Area-weighted mean BII over land-cover classes (IEEM sec. 2.4 method)."""
    total = sum(cover.values())
    if total <= 0:
        return None
    return sum(area * BII_COEF[k] for k, area in cover.items()) / total


def emissions_value(scenario_dir: Path) -> dict[int, float]:
    """EmiVal term of eq. 2: CO2 damage at the social cost of carbon."""
    rows = read_csv(scenario_dir / "csv" / "AnnualTechnologyEmission.csv")
    out: dict[int, float] = defaultdict(float)
    col = "AnnualTechnologyEmission"
    for r in rows:
        if r.get(col):
            out[int(r["y"])] += float(r[col]) * SOCIAL_COST_CO2
    return dict(sorted(out.items()))


def available_duals(scenario_dir: Path) -> list[str]:
    """Which shadow prices this solve actually exported."""
    d = scenario_dir / "csv"
    names = [
        "E8_AnnualEmissionsLimit",
        "EBb4_EnergyBalanceEachYear4_ICR",
        "UDC1_UserDefinedConstraintInequality",
        "UDC2_UserDefinedConstraintEquality",
    ]
    return [n for n in names if (d / f"{n}.csv").exists()]


def main() -> int:
    if not CASE.exists():
        print(f"case not found: {CASE}")
        return 1

    scenarios = sorted(p for p in (CASE / "res").iterdir() if p.is_dir())
    print(f"case: {CASE.name}   scenarios: {[s.name for s in scenarios]}\n")

    summary, all_problems = {}, []
    for sc in scenarios:
        cover, resource = land_by_year(sc)
        if not cover:
            print(f"--- {sc.name}: no land output found")
            continue

        problems = check_closure(cover, resource, sc.name)
        all_problems += problems

        years = sorted(cover)
        first, last = years[0], years[-1]
        emi = emissions_value(sc)
        b0, b1 = composite_bii(cover[first]), composite_bii(cover[last])

        print(f"--- {sc.name} ({first}-{last})")
        for y in (first, last):
            print(
                f"    {y}: "
                + ", ".join(
                    f"{k}={v:,.2f}" for k, v in sorted(cover[y].items())
                )
                + f"  | total={sum(cover[y].values()):,.3f}"
                f" vs {LAND_RESOURCE_TECH}={resource.get(y, float('nan')):,.3f}"
            )
        print(
            f"    closure: {'OK' if not problems else 'FAILED'}"
            f" (tol {CLOSURE_TOL})"
        )
        if b0 is not None and b1 is not None:
            print(
                f"    composite BII {first}: {b0:.4f} -> {last}: {b1:.4f} "
                f"({(b1 - b0) / b0 * 100:+.3f}%)   [illustrative coefficients]"
            )
        if emi:
            ey = sorted(emi)
            print(
                f"    EmiVal (eq.2 CO2 damage @ ${SOCIAL_COST_CO2:.0f}/t): "
                f"{ey[0]}={emi[ey[0]]:,.1f} -> {ey[-1]}={emi[ey[-1]]:,.1f}"
            )
        print(f"    duals exported: {available_duals(sc)}")

        summary[sc.name] = {
            "years": [first, last],
            "bii_first": b0,
            "bii_last": b1,
            "cover_first": cover[first],
            "cover_last": cover[last],
            "closure_ok": not problems,
            "duals": available_duals(sc),
        }

    print("\n=== eq.2 / eq.3 term availability in a solved MUIOGO case ===")
    verdict = [
        ("land-cover state vector (LULC)", "PRESENT",
         "solved annual areas by cover class, 10^3 km^2, closing exactly on the "
         "land resource"),
        ("composite BII", "COMPUTABLE NOW",
         "area-weighted mean over the state vector; needs PREDICTS coefficients only"),
        ("EmiVal (CO2 damage)", "COMPUTABLE NOW",
         "AnnualTechnologyEmission x social cost of carbon"),
        ("qdepl (quantity depleted)", "PRESENT",
         "resource-technology activity is the extraction quantity"),
        ("unitrent (eq.3 unit rent)", "MISSING -- BUT WIRED",
         "needs the dual of a land/resource balance; UDC2 equality duals ARE wired "
         "in Duals.json but no equality UDC exists in this case"),
        ("GNSAV, DeprCapStock", "OUT OF SCOPE FOR CLEWS",
         "national-accounts aggregates; OG-Core produces these"),
    ]
    for name, status, note in verdict:
        print(f"  [{status:>18}]  {name}\n{'':22}{note}")

    if all_problems:
        print("\n!! CLOSURE FAILURES -- land areas were read incorrectly:")
        for p in all_problems:
            print(f"   {p}")

    out = Path(__file__).with_name("ieem_indicator_probe_result.json")
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {out}")
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main())
