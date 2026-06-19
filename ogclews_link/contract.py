"""The interface contract between OG-Core and CLEWS/OSeMOSYS.

Everything that must be agreed for a coupling to be reproducible lives here, as
explicit, reviewable data -- not buried in a run script. See the de novo analysis
(docs/design/og-clews-denovo-analysis.md), section 5/6.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScenarioPair:
    """A baseline/reform pairing -- the unit of every coupled run."""
    name: str
    base_dir: str          # CLEWS baseline output folder
    reform_dir: str        # CLEWS reform output folder
    years: tuple           # calendar years present in the CLEWS export
    og_start_year: int     # OG-Core start_year, for time-grid alignment


@dataclass
class Concordance:
    """Maps CLEWS objects to OG-Core indices, and pins the energy ports.

    ``energy_industry_index`` is the OG industry m whose output price carries the
    energy cost (route B). ``energy_good_index`` is the OG consumption good i that
    households buy and react to (route A). Both must be verified against the country
    calibration (e.g. OG-PHL ``calibration_values.PROD_DICT`` / ``CONS_DICT``).
    """
    energy_industry_index: int
    energy_good_index: int


@dataclass
class UnitMap:
    """The unit/currency bridge. CLEWS stores bare numbers; OG is real, numeraire =
    industry-M output, with ``factor`` (a steady-state object) as the only currency
    bridge. Pin every conversion explicitly -- there is no internal guard on either side.
    """
    clews_money_unit: str = "model"     # e.g. 'MUSD_2020'
    clews_energy_unit: str = "PJ"
    base_year: int = 2020
    deflator: float = 1.0               # to OG numeraire / base year
    notes: str = ""


# --- Philippines defaults (verify indices against calibration_values before use) ---

PHL_CONCORDANCE = Concordance(
    energy_industry_index=1,   # M=4 order [NaturalResources, Electricity, ConsTradeServices, Manufacturing]
    energy_good_index=1,       # I=5 order [Food, "Energy and water", Non-durables, Durables, Services]
)
