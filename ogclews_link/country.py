"""Country configuration -- the one place country-specific assumptions live, so the
channels and framework stay country-agnostic. PHL is the worked instance.
"""
from __future__ import annotations

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
    co2_emission: str = "CO2e"
    mindist_tpi: float = 1e-5

    def is_power(self, tech: str) -> bool:
        return tech.startswith(self.power_prefix)

    def is_public(self, tech: str) -> bool:
        return self.is_power(tech) and any(m in tech for m in self.public_power_markers)


_CLEWS = "/Users/mlafleur/Projects/CLEWS-OG/CLEWS_simulations"

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
)
