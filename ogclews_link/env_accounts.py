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
import itertools
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DEMO_LAND_MAP",
    "PHL_V12_LAND_MAP",
    "LandClosureError",
    "LandMap",
    "area_changes",
    "composite_index",
    "conversion_carbon",
    "depletion_flow",
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

    Two routes to a cover class, because cases differ in where the class lives:

    * ``classes`` -- technology code -> label, for cases (the demo) where each
      cover class is its own technology. Matches whatever the mode is.
    * ``mode_classes`` -- technology code -> mode -> label, for cases (PHL v12)
      where one terminal technology (``ENV_LAND``) carries the cover classes in
      its MODES. A mode of that technology with no label is simply not counted,
      which the closure check then reports.

    ``mode_classes`` wins when a technology appears in both.

    Args:
        resource_tech: the technology carrying the total land endowment.
        classes: land-use technology code -> cover-class label. Several
            technologies may share a label (e.g. four crop technologies -> Cropland).
        mode_classes: technology code -> mode -> cover-class label.
    """

    resource_tech: str
    classes: dict[str, str] = field(default_factory=dict)
    mode_classes: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.classes and not self.mode_classes

    def label(self, tech: str, mode: str | None = None) -> str | None:
        by_mode = self.mode_classes.get(tech)
        if by_mode is not None:
            return by_mode.get(str(mode).strip()) if mode is not None else None
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

# Philippines v12 (`Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC`). The cover-class
# vector lives in ENV_LAND's 8 MODES, not in separate technologies.
#
# The mode -> class assignment is NOT guessed: it is read off the solved run's own
# generated model input, where `param InputActivityRatio` gives one slice per
# commodity with the mode as its row index --
#   [RE1,ENV_LAND,ENV_LND_FOREST,*,*]: <mode 1>, ... ENV_LND_CROPLAND -> 7, PHL_LND -> 8
# all with ratio 1. Verified against `res/Base_v12` (CBC Optimal, provenance
# `muiogo verify` clean): the seven cover modes close on MINLNDTOT to 1e-4 over all
# 34 years.
#
# Mode 8 consumes the land resource PHL_LND *directly* rather than a cover tag, so it
# is untagged land, and it belongs in the closure sum: MINLNDTOT = modes 1-7 + mode 8.
# It is identically zero in Base_v12 (all land is tagged), but it is mapped
# explicitly rather than dropped so that if it ever goes positive it shows up as
# Unallocated area instead of breaking closure for no visible reason.
#
# CALIBRATION WARNING. These classes are structurally right and numerically not
# credible: CLEWs-PHL's own KNOWN_LIMITATIONS.md says the land block was never
# calibrated to observed land allocation. Base_v12 puts 61% of national area under
# forest (against roughly 24% observed) and 770 km^2 under built-up (an order of
# magnitude low), and leaves Grassland, Barren and Other identically zero for all
# 34 years. Use for mechanism checks only, never as a Philippine result.
PHL_V12_LAND_MAP = LandMap(
    resource_tech="MINLNDTOT",
    mode_classes={
        "ENV_LAND": {
            "1": "Forest",
            "2": "Grassland",
            "3": "Other",
            "4": "Barren",
            "5": "Built-up",
            "6": "Water bodies",
            "7": "Cropland",
            "8": "Unallocated",
        }
    },
)


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
        ValueError: if `land_map` maps no technology at all -- an empty map can
            only ever produce an empty answer, which would misread as "the case
            has no land".
        LandClosureError: if areas do not sum to the land resource, or the map
            matched nothing in a non-empty activity file.
    """
    if land_map.is_empty:
        raise ValueError(
            f"land map for resource '{land_map.resource_tech}' maps no technology: "
            "an empty map cannot distinguish 'no land in this case' from 'wrong "
            "map for this case'. Build the map first (for PHL v12 that is stage 3 "
            "of docs/design/phl-testcase-plan.md)."
        )

    rows = _read_csv(_scenario_csv_dir(scenario_dir) / ACTIVITY_FILE)
    cover: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    resource: dict[int, float] = defaultdict(float)

    for r in rows:
        raw = r.get(ACTIVITY_COL)
        if not raw:
            continue
        tech, year, val = r["t"], int(r["y"]), float(raw)
        label = land_map.label(tech, r.get("m"))
        if label is not None:
            cover[year][label] += val
        elif tech == land_map.resource_tech:
            resource[year] += val

    cover_out = {y: dict(v) for y, v in sorted(cover.items())}
    resource_out = dict(sorted(resource.items()))

    if check_closure:
        if rows and not cover_out and not resource_out:
            raise LandClosureError(
                f"the land map (resource '{land_map.resource_tech}', "
                f"{len(land_map.classes) + len(land_map.mode_classes)} mapped "
                f"technologies) matched nothing in a non-empty {ACTIVITY_FILE} -- "
                "wrong map for this case?"
            )
        problems = []
        for year in sorted(set(cover_out) | set(resource_out)):
            total = sum(cover_out.get(year, {}).values())
            res = resource_out.get(year)
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
    scenario_dir: str | Path,
    social_cost: float,
    *,
    species: str | Collection[str],
) -> dict[int, float]:
    """The CO2-damage term of genuine savings (IEEM eq. 2, ``EmiVal``).

    ``species`` is REQUIRED because a case's emission file routinely carries
    several species and summing them prices everything at the social cost of
    carbon. The shipped demo has ``CH4, CO2, CO2EQ, N2O`` -- where CO2EQ already
    aggregates the others, so an unfiltered sum double-counts CO2 and misprices
    CH4/N2O; PHL v12 carries ``CO2e`` and ``PM2_5``, where an unfiltered sum
    prices particulates at the SCC. Pick the one species (usually the CO2e
    aggregate) that matches your ``social_cost``'s denominator.

    Args:
        scenario_dir: a solved run dir (or its `csv/` subdir).
        social_cost: currency per emission unit. IEEM uses US$30/tCO2.
        species: emission code(s) to include, e.g. ``"CO2EQ"`` (demo) or
            ``"CO2e"`` (PHL v12). Matched exactly against the file's `e` column.

    Returns:
        year -> damage value.

    Raises:
        ValueError: if the file has rows but none match `species` -- almost
            always a species-code mismatch, not a zero-emission case.
    """
    wanted = {species} if isinstance(species, str) else set(species)
    rows = _read_csv(_scenario_csv_dir(scenario_dir) / EMISSION_FILE)
    out: dict[int, float] = defaultdict(float)
    matched = False
    for r in rows:
        if r.get("e") not in wanted:
            continue
        matched = True
        raw = r.get(EMISSION_COL)
        if raw:
            out[int(r["y"])] += float(raw) * social_cost
    if rows and not matched:
        present = sorted({r.get("e", "") for r in rows})
        raise ValueError(
            f"emissions_damage: no rows for species {sorted(wanted)} in "
            f"{EMISSION_FILE}; species present: {present}"
        )
    return dict(sorted(out.items()))


def depletion_flow(stock: dict[int, float]) -> dict[int, float]:
    """Net decline of a stock series -- the `qdepl` flow IEEM eq. 3 wants.

    eq. 3 prices the quantity DEPLETED each year, not the standing stock.
    From an annual stock series the observable analogue is the year-on-year
    net decline, floored at zero: a year where the stock grows depletes
    nothing (the World Bank ANS convention for net forest depletion), it
    does not earn a credit. The first year has no predecessor and yields
    no flow.

    Args:
        stock: year -> standing stock (e.g. forest area by year).

    Returns:
        year -> quantity depleted, for every year after the first.
    """
    years = sorted(stock)
    return {
        curr: max(stock[prev] - stock[curr], 0.0)
        for prev, curr in itertools.pairwise(years)
    }


def area_changes(stock: dict[int, float]) -> dict[int, tuple[float, float]]:
    """Year -> (area lost, area gained), keeping the two directions apart.

    `depletion_flow` floors gains at zero, which is right for eq. 3 but throws
    away information that land-carbon accounting needs. This keeps both.

    Args:
        stock: year -> area (one cover class).

    Returns:
        year -> (lost, gained), both non-negative, for years after the first.
    """
    years = sorted(stock)
    out = {}
    for prev, curr in itertools.pairwise(years):
        d = stock[curr] - stock[prev]
        out[curr] = (max(-d, 0.0), max(d, 0.0))
    return out


def conversion_carbon(
    cover: dict[int, dict[str, float]],
    stock_factors: dict[str, float],
    *,
    regrowth_credit: float = 0.0,
) -> dict[int, float]:
    """Carbon released when land changes cover class -- the LULUCF term.

    This is the term a CLEWS case cannot give you: no land technology in either
    the PHL v12 or the shipped demo case carries an emission ratio for
    conversion, so land-use carbon is absent from `AnnualTechnologyEmission`
    entirely. On PHL that omission is worth roughly a fifth of everything the
    energy and industry sectors emit across the horizon.

    ASYMMETRY IS THE POINT, and it is why this belongs here rather than in the
    solver. Clearing a hectare releases its standing stock within a year or
    two; regrowing that hectare takes decades and saturates (IPCC 2019
    Refinement Table 4.9 updated: roughly 7.1 tCO2/ha/yr for secondary forest
    under 20 years, 5.6 over 20, and 1.5 -- statistically indistinguishable
    from zero -- for primary). OSeMOSYS's own
    ``EmissionToActivityChangeRatio`` is area-SYMMETRIC: it would hand back a
    regrowth credit exactly equal to the clearing debit, i.e. instant carbon
    recovery. That is wrong, and it is unfixable inside a linear program with
    no memory.

    So ``regrowth_credit`` defaults to 0.0: land gained earns nothing. That is
    the conservative treatment and the right default for a case where cover
    only ever moves one way. Raise it toward 1.0 only with an explicit
    justification for how fast the stock actually returns.

    Args:
        cover: year -> {class label -> area}, as returned by `land_use_by_year`.
        stock_factors: class label -> carbon stock per unit area. For PHL the
            defensible figure is the country's own Forest Reference Level
            (2023) gross factor, 292 tCO2 per hectare of forest cleared; mind
            the area units of your cover series. Classes absent here are
            skipped, so a factor for Forest alone gives forest-only carbon.
        regrowth_credit: fraction of the stock factor credited to area gained.
            0.0 (default) credits nothing.

    Returns:
        year -> net carbon released, positive for a release. Years after the
        first only; a year with no qualifying change yields 0.0.
    """
    if not 0.0 <= regrowth_credit <= 1.0:
        raise ValueError(
            f"regrowth_credit must be in [0, 1], got {regrowth_credit}"
        )
    series: dict[str, dict[int, float]] = defaultdict(dict)
    for year, classes in cover.items():
        for label, area in classes.items():
            series[label][year] = area

    out: dict[int, float] = defaultdict(float)
    for label, factor in stock_factors.items():
        for year, (lost, gained) in area_changes(series.get(label, {})).items():
            out[year] += (lost - gained * regrowth_credit) * factor
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

    In IEEM the unit rent is endogenous to the CGE. Our analogue is a CLEWS shadow price:
    the shadow price of the resource's balance constraint. Land is an ordinary
    commodity, so its balance constraint already carries a shadow price and MUIOGO already
    exports it -- `EBb4_EnergyBalanceEachYear4_ICR.csv` has the `LND` rows. Read it
    with ``signals.commodity_shadow_price(fuel="LND", drop_zero=False)``:
    `drop_zero` MUST be off, because for land a zero shadow price is a true zero (land was
    abundant that year) and belongs in the sum, not a missing observation as it
    would be for electricity. See docs/design/phl-testcase-plan.md §1(a).

    Args:
        quantities: year -> quantity depleted -- a FLOW (see `depletion_flow`),
            never a standing stock.
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
