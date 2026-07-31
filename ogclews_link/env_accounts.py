"""Environmental accounts read off a solved CLEWS case.

Exploratory. Nothing here is wired into `framework.run` or any channel.

The point of this module is to compute the environmental-accounting indicators that
IEEM (IDB's platform) publishes and we currently do not: a land-cover state vector, a
biodiversity index over it, the CO2-damage term of genuine savings, and the
natural-capital depletion term. See `docs/design/ieem-comparative-assessment.md`.

These are POST-PROCESSING over a solved case. They need no change to OSeMOSYS, to
MUIOGO, or to OG-Core, and they never write to the case they read.

READING LAND CORRECTLY -- the one trap
--------------------------------------
A land technology's AREA is its ``TotalAnnualTechnologyActivityByMode``, not its
production. Land technologies output water flows (evapotranspiration, groundwater
recharge, runoff) alongside any land commodity, and some -- forest in the shipped demo
-- output NO land commodity at all. Reading area from production therefore drops forest
entirely and adds 10^9 m^3 water volumes into a 10^3 km^2 total.

The check that catches it: land-use areas must sum to the land resource. Call
`land_use_by_year` and it asserts this for you; if you read land any other way, assert
it yourself.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DEMO_LAND_MAP",
    "PHL_V12_LAND_MAP",
    "LandClosureError",
    "LandMap",
    "composite_index",
    "emissions_damage",
    "land_use_by_year",
    "natural_capital_depletion",
]

CLOSURE_TOL = 1e-3
ACTIVITY_FILE = "TotalAnnualTechnologyActivityByMode.csv"
ACTIVITY_COL = "TotalAnnualTechnologyActivityByMode"
EMISSION_FILE = "AnnualTechnologyEmission.csv"
EMISSION_COL = "AnnualTechnologyEmission"


class LandClosureError(RuntimeError):
    """Land-use areas did not sum to the land resource -- the read is wrong."""


@dataclass(frozen=True)
class LandMap:
    """How one case names its land technologies.

    Case-specific: the shipped demo and the Philippine v12 build use different
    technology codes for the same cover classes, so this must be passed in rather
    than guessed.

    Args:
        resource_tech: the technology carrying the total land endowment.
        classes: land-use technology code -> cover-class label. Several
            technologies may share a label (e.g. four crop technologies -> Cropland).
    """

    resource_tech: str
    classes: dict[str, str] = field(default_factory=dict)

    def label(self, tech: str) -> str | None:
        return self.classes.get(tech)


# The shipped `CLEWs Demo` case.
DEMO_LAND_MAP = LandMap(
    resource_tech="RSCLND",
    classes={
        "LNDFOR": "Forest",
        "LNDMAIRNF": "Cropland",
        "LNDRICRNF": "Cropland",
        "LNDMAIIRR": "Cropland",
        "LNDRICIRR": "Cropland",
        "LNDBLT": "Built-up",
        "LNDWAT": "Water bodies",
    },
)

# Philippines v12 carries parallel ENV_LND_* area stocks and an ENV_LAND terminal.
# Placeholder: the v12 case ships no solved results in the MUIOGO checkout, so this
# mapping is UNVERIFIED against real output. Confirm the technology codes before use.
PHL_V12_LAND_MAP = LandMap(resource_tech="MINLNDTOT", classes={})


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _scenario_csv_dir(scenario_dir: str | Path) -> Path:
    """Accept either a run dir or its `csv/` subdir."""
    p = Path(scenario_dir)
    return p if p.name == "csv" else p / "csv"


def land_use_by_year(
    scenario_dir: str | Path,
    land_map: LandMap = DEMO_LAND_MAP,
    *,
    check_closure: bool = True,
    tol: float = CLOSURE_TOL,
) -> tuple[dict[int, dict[str, float]], dict[int, float]]:
    """Land area by cover class by year, and the land-resource total by year.

    Areas are technology ANNUAL ACTIVITY -- see the module docstring.

    Args:
        scenario_dir: a solved run dir (or its `csv/` subdir).
        land_map: the case's land technology naming.
        check_closure: assert areas sum to the land resource. Leave this on.
        tol: closure tolerance.

    Returns:
        (cover, resource) -- cover[year][class] = area; resource[year] = total.

    Raises:
        LandClosureError: if areas do not sum to the land resource.
    """
    rows = _read_csv(_scenario_csv_dir(scenario_dir) / ACTIVITY_FILE)
    cover: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    resource: dict[int, float] = defaultdict(float)

    for r in rows:
        raw = r.get(ACTIVITY_COL)
        if not raw:
            continue
        tech, year, val = r["t"], int(r["y"]), float(raw)
        label = land_map.label(tech)
        if label is not None:
            cover[year][label] += val
        elif tech == land_map.resource_tech:
            resource[year] += val

    cover_out = {y: dict(v) for y, v in sorted(cover.items())}
    resource_out = dict(sorted(resource.items()))

    if check_closure and cover_out:
        problems = []
        for year, cls in cover_out.items():
            total, res = sum(cls.values()), resource_out.get(year)
            if res is None:
                problems.append(
                    f"{year}: no '{land_map.resource_tech}' row to close against"
                )
            elif abs(total - res) > tol:
                problems.append(
                    f"{year}: land uses sum to {total:.6f} but "
                    f"{land_map.resource_tech}={res:.6f} "
                    f"(gap {total - res:+.6f})"
                )
        if problems:
            raise LandClosureError(
                "land-use areas do not close on the land resource; the land map is "
                "probably incomplete or the wrong variable was read. "
                + "; ".join(problems)
            )

    return cover_out, resource_out


def composite_index(
    cover: dict[str, float], coefficients: dict[str, float]
) -> float | None:
    """Area-weighted mean of a per-cover-class coefficient.

    This is the shape of IEEM's composite Biodiversity Intactness Index (their sec.
    2.4): assign each land-use class a coefficient, weight by area. It is equally the
    shape of a carbon-density or habitat-quality index -- only the coefficients differ.

    Coefficients are a REQUIRED argument on purpose. Real values are country-specific
    (for BII, PREDICTS-derived means); there is no defensible default, so this module
    ships none.

    Args:
        cover: cover-class label -> area, for one year.
        coefficients: cover-class label -> coefficient.

    Returns:
        The weighted mean, or None if there is no area.

    Raises:
        KeyError: if a cover class present in `cover` has no coefficient.
    """
    total = sum(cover.values())
    if total <= 0:
        return None
    missing = set(cover) - set(coefficients)
    if missing:
        raise KeyError(f"no coefficient for cover class(es): {sorted(missing)}")
    return sum(area * coefficients[k] for k, area in cover.items()) / total


def emissions_damage(
    scenario_dir: str | Path, social_cost: float
) -> dict[int, float]:
    """The CO2-damage term of genuine savings (IEEM eq. 2, ``EmiVal``).

    Args:
        scenario_dir: a solved run dir (or its `csv/` subdir).
        social_cost: currency per emission unit. IEEM uses US$30/tCO2.

    Returns:
        year -> damage value.
    """
    rows = _read_csv(_scenario_csv_dir(scenario_dir) / EMISSION_FILE)
    out: dict[int, float] = defaultdict(float)
    for r in rows:
        raw = r.get(EMISSION_COL)
        if raw:
            out[int(r["y"])] += float(raw) * social_cost
    return dict(sorted(out.items()))


def natural_capital_depletion(
    quantities: dict[int, float],
    unit_rents: dict[int, float],
    *,
    discount: float = 0.04,
    base_year: int | None = None,
) -> float:
    """Present value of natural-capital depletion (IEEM eq. 3).

        sum_t  (qdepl_t * unitrent_t) / (1 + intrat)^(t - base_year)

    In IEEM the unit rent is endogenous to the CGE. Our analogue is a CLEWS dual:
    the shadow price of the resource's balance constraint. For land that means the
    dual of an equality land-closure user-defined constraint, which MUIOGO already
    wires for export -- but which no shipped case currently carries, so `unit_rents`
    cannot yet be populated from a demo solve. See the assessment note.

    Args:
        quantities: year -> quantity depleted.
        unit_rents: year -> unit rent. Years absent here are skipped.
        discount: IEEM uses 4% (Lange et al. 2018).
        base_year: discount to this year; defaults to the earliest shared year.

    Returns:
        Present value of depletion. 0.0 if no year has both a quantity and a rent.
    """
    shared = sorted(set(quantities) & set(unit_rents))
    if not shared:
        return 0.0
    base = base_year if base_year is not None else shared[0]
    return sum(
        quantities[y] * unit_rents[y] / (1.0 + discount) ** (y - base)
        for y in shared
    )
