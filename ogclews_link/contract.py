"""The interface contract between OG-Core and CLEWS/OSeMOSYS.

Everything that must be agreed for a coupling to be reproducible lives here, as
explicit, reviewable data -- not buried in a run script. See the de novo analysis
(docs/design/og-clews-denovo-analysis.md), section 5/6.
"""
from __future__ import annotations

from dataclasses import dataclass, field


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

    ``energy_industry_index`` is the OG industry m whose output price carries the energy cost (route B).
    ``energy_good_index`` is the OG consumption good i that households buy and react to (route A). Either
    is ``None`` when the country's OG aggregation cannot isolate the carrier (e.g. electricity is fused
    with water in a single group) -- ``unavailable`` records why. Channels that need an unavailable port
    SKIP themselves (recording the reason); channels that don't (health off CLEWS emissions, public
    investment, the discount-rate emit) still run.
    """
    energy_industry_index: int | None
    energy_good_index: int | None
    unavailable: dict = field(default_factory=dict)   # port name -> why it couldn't be resolved

    @classmethod
    def from_dicts(cls, prod_dict, cons_dict, carrier="electricity"):
        """Discover the energy ports from a calibration's aggregation dicts, so the indices track
        whatever aggregation the model is built with -- no hand-set literals. The industry index is the
        PROD_DICT group holding ``carrier``; the good index is the CONS_DICT group holding it
        (PROD_DICT/CONS_DICT order = the model's column order). ``carrier`` is an ``aggregation.CARRIERS``
        key (e.g. 'electricity'), a regex, or a list of SAM codes. A port the carrier can't be resolved to
        -- absent, or SPLIT across groups (can't isolate one index) -- comes back ``None`` with a recorded
        reason (NOT a raise and NOT a silent guess), so the dependent channels can be skipped per country."""
        from . import aggregation as ag

        def resolve(d, axis):
            hits = ag.locate(d, carrier)
            if not hits:
                return None, f"carrier {carrier!r} not found in the {axis} aggregation (groups: {list(d)})"
            if len(hits) > 1:
                return None, (f"carrier {carrier!r} is split across {axis} groups {[h[1] for h in hits]} "
                              "-- cannot isolate a single index")
            return hits[0][0], None

        ind, ind_why = resolve(prod_dict, "production")
        good, good_why = resolve(cons_dict, "consumption")
        unavailable = {}
        if ind_why:
            unavailable["energy_industry_index"] = ind_why
        if good_why:
            unavailable["energy_good_index"] = good_why
        return cls(energy_industry_index=ind, energy_good_index=good, unavailable=unavailable)

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
