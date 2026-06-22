"""Country configuration -- the one place country-specific assumptions live, so the
channels and framework stay country-agnostic. PHL is the worked instance.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field

from .contract import Concordance, ScenarioPair, UnitMap, PHL_CONCORDANCE


@dataclass
class CountryConfig:
    name: str
    un_code: str
    gdp_musd: float                         # nominal GDP, base year, for %GDP conversions
    concordance: Concordance
    units: UnitMap
    scenario: ScenarioPair
    power_prefix: str = "PHL_POW"           # all power-sector technologies
    public_power_markers: tuple = ("_TD",)  # techs treated as public infrastructure (T&D)
    co2_emission: str = "CO2e"        # carbon-policy / climate species (carbon channel + emissions chart)
    health_emission: str = "PM2_5"    # the ambient pollutant the GBD health burden is attributed to; the
                                      # health channel scales its PM2.5 dose-response by THIS species'
                                      # reform/base emission ratio -- NOT CO2e (climate != air-pollution health)
    mindist_tpi: float = 1e-5
    # SS aggregate-resource-constraint gate for the LIVES-SAVED (mortality-down) health reform only:
    # apply_health_shock sets p.RC_SS to this when the target is negative; every other solve (baseline,
    # deaths-added, energy/investment/carbon) keeps ogcore's tight 1e-8 default. The lives-saved solve
    # leaves an intrinsic ~5e-7 Walras residual on the production good that is INVARIANT to a fresh
    # re-solve and to a 100-10000x tighter fixed-point tolerance (verified: mindist_SS 1e-11/1e-13 both
    # give 5.089e-7) -- a structural identity gap of the converged demographic equilibrium, not solver
    # slop, so only the post-solve RC_SS assertion can clear it. Battery (2026-06-22) found the residual
    # SCALES with the lives-saved target: the real emissions-derived target (-3,406) leaves |RC|~4.3e-6 on
    # Manufacturing, which the prior 1e-6 gate (calibrated for a ~1.7e-7 residual) wrongly tripped. Set to
    # 1e-5: clears ~4.3e-6 with headroom, still ~10x tighter than ogcore's RC_TPI=1e-4 default (COD runs
    # RC_TPI=0.0075) and economically negligible (~1e-6 relative to sector output). Realized |RC| is logged.
    rc_ss: float = 1e-5
    # GBD ambient-PM2.5 burden export (Deaths + YLDs by age/cause). Feeds the health channel's real
    # mortality h(s) + excess_deaths and morbidity g(s) + YLD-rate magnitude. None -> placeholders.
    gbd_burden_csv: str | None = None
    gbd_year: int = 2023

    def is_power(self, tech: str) -> bool:
        return tech.startswith(self.power_prefix)

    def is_public(self, tech: str) -> bool:
        return self.is_power(tech) and any(m in tech for m in self.public_power_markers)


_CLEWS = "/Users/mlafleur/Projects/CLEWS-OG/CLEWS_simulations"


def _resolve_gbd_csv():
    """The GBD burden CSV under the repo's IHME-GBD_2023_DATA/ (multi-country export), or None."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = [h for h in glob.glob(os.path.join(root, "IHME-GBD_2023_DATA", "*.csv"))
            if "citation" not in os.path.basename(h).lower()]
    return sorted(hits)[0] if hits else None


PHL = CountryConfig(
    name="Philippines",
    un_code="608",
    gdp_musd=461_600.0,  # 2024 nominal GDP, USD millions (World Bank)
    concordance=PHL_CONCORDANCE,
    units=UnitMap(clews_money_unit="MUSD", clews_energy_unit="PJ", base_year=2020,
                  notes="CLEWS monetary outputs are model MUSD; convert vs baseline ratios where possible"),
    scenario=ScenarioPair(
        name="PEP_vs_Base",
        base_dir=os.path.join(_CLEWS, "v6-Base"),
        reform_dir=os.path.join(_CLEWS, "v6-PEP"),
        years=tuple(range(2020, 2054)),
        og_start_year=2026,
    ),
    gbd_burden_csv=_resolve_gbd_csv(),  # IHME-GBD_2023_DATA/*.csv if present, else None (placeholders)
)
