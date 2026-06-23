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

    @classmethod
    def from_dicts(cls, prod_dict, cons_dict, carrier="electricity"):
        """Discover the energy ports from a calibration's aggregation dicts, so the indices
        track whatever aggregation the model is built with -- no hand-set literals. The industry
        index is the PROD_DICT group holding ``carrier``; the good index is the CONS_DICT group
        holding it (PROD_DICT/CONS_DICT order = the model's column order). ``carrier`` is an
        ``aggregation.CARRIERS`` key (e.g. 'electricity'), a regex, or a list of SAM codes.
        Raises if the carrier is absent or split across groups (an ambiguous single index)."""
        from . import aggregation as ag

        def one(d, axis):
            hits = ag.locate(d, carrier)
            if not hits:
                raise ValueError(f"carrier {carrier!r} not found in the {axis} aggregation; "
                                 f"groups: {list(d)}")
            if len(hits) > 1:
                raise ValueError(f"carrier {carrier!r} is split across {axis} groups "
                                 f"{[h[1] for h in hits]}; pass an explicit code set/index")
            return hits[0][0]

        return cls(energy_industry_index=one(prod_dict, "production"),
                   energy_good_index=one(cons_dict, "consumption"))

    @classmethod
    def from_package(cls, pkg, carrier="electricity"):
        """Discover the energy ports from an installed OG country package's real PROD_DICT/
        CONS_DICT. For a model run at a *different* aggregation (e.g. a bespoke M=4 build), use
        ``from_dicts`` with that build's dicts so the index matches the model's columns."""
        from . import aggregation as ag
        _, prod, cons = ag.from_package(pkg)
        if prod is None or cons is None:
            raise ValueError(f"{pkg} does not expose PROD_DICT/CONS_DICT")
        return cls.from_dicts(prod, cons, carrier=carrier)


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


# --- Philippines: energy ports DISCOVERED from the M=4 coupling aggregation -------
# Industry index from the coupling PROD_DICT ("Electricity" -> column 1), good index from CONS_DICT
# ("Energy and water" -> column 1). Both dicts are VENDORED in _calibration, so discovery runs in the
# link env with no ogphl import -- and NO silent literal fallback: if the carrier can't be located (or
# is split across groups), from_dicts raises and we fail loud rather than guessing a (possibly wrong)
# index. NB: this is the M=4 *coupling* aggregation (electricity isolated at column 1), not the
# country package's native grouping (where electricity is fused with water); use Concordance.from_dicts
# with a different build's dicts to run at another aggregation.
def _discover_phl_concordance():
    from ._calibration import CONS_DICT, PROD_DICT
    return Concordance.from_dicts(PROD_DICT, CONS_DICT)


PHL_CONCORDANCE = _discover_phl_concordance()
