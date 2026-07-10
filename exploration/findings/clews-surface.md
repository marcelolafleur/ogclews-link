# CLEWS/MUIOGO surface: what the coupling could read and write

Evidence-only inventory of the OSeMOSYS parameter/variable/dual universe MUIOGO manages, and of
what the link currently uses out of it. No channel proposals here — see `channel-space-map.md` for
those.

**Sources (all paths absolute):**
- Catalogs: `/Users/mlafleur/Projects/MUIOGO/WebAPP/DataStorage/{Parameters,Variables,Duals}.json`
- Live case: `/Users/mlafleur/Projects/MUIOGO/WebAPP/DataStorage/Philippines_v9/`
  - Case metadata (tech/commodity/timeslice/scenario/constraint sets): `Philippines_v9/genData.json`
  - Result runs: `Philippines_v9/res/{Base_v8,Base_v9,PEP_v8,PEP_v9}/csv/*.csv` (representative run
    used below: `Philippines_v9/res/Base_v9/csv/`)
- Link code (branch `explore/channel-space`, worktree `~/Projects/ogclews-link-channels`):
  `ogclews_link/signals.py` (readers), `ogclews_link/clews_io.py` (writers),
  `ogclews_link/lcoe.py` (LCOE reader), `ogclews_link/muiogo_run.py` (the `PREFLIGHT_STEMS`
  export-contract table — the canonical list of CSV stems the link actually consumes)

**Headline counts:** 49 OSeMOSYS input parameters (`Parameters.json`) · 29 result variables
(`Variables.json`) · 4 duals (`Duals.json`) = 82 catalog entries. Live case (`genData.json`): 132
technologies, 57 commodities, 34 model years (2020–2053), 2 emission species (CO2e, PM2_5), 2
modes, 30 timeslices, 4 scenarios (BASE/COALPHASEOUT/RE/EV), 2 user-defined constraints
(RENEWABLES, EV), **0 storage units** (`osy-stg` is an empty list — `RS`/`RYS`/`RTSM` storage
parameters exist in the catalog but have no set members to apply to in this case).

---

## Part A — Readable surface (CLEWS → OG signals)

### A.1 Result variables cataloged in `Variables.json` (29), by OSeMOSYS index-set group

| Group (setrelation) | id | name | Used? |
|---|---|---|---|
| R (`r`) | OV | ObjectiveValue | unused |
| RT (`r,t`) | TTMPA | TotalTechnologyModelPeriodActivity | unused |
| RYT (`r,t,y`) | ANC | AccumulatedNewCapacity | unused |
| RYT | AIC | AnnualizedInvestmentCost | **used** (capital-intensity channel + LCOE) |
| RYT | CI | CapitalInvestment | **used** (public-investment channel: `power_capex_increment`) |
| RYT | AFOC | AnnualFixedOperatingCost | **used** (capital-intensity channel + LCOE) |
| RYT | AVOC | AnnualVariableOperatingCost | **used** (capital-intensity channel + LCOE) |
| RYT | NC | NewCapacity | unused |
| RYT | NONTU | NumberOfNewTechnologyUnits | unused |
| RYT | SV | SalvageValue | unused |
| RYT | TCA | TotalCapacityAnnual | unused |
| RYT | TEP | TechnologyEmissionsPenalty | unused |
| RYS (`r,s,y`) | NSC | NewStorageCapacity | unused (no storage in PHL v9 — see above) |
| RYS | ANSC | AccumulatedNewStorageCapacity | unused (no storage) |
| RYS | TSC | TotalStorageCapacity | unused (no storage) |
| RYS | SVS | SalvageValueStorage | unused (no storage) |
| RYS | CIS | CapitalInvestmentStorage | unused (no storage) |
| RYTM (`r,t,m,y`) | TATABM | TotalAnnualTechnologyActivityByMode | unused |
| RYTC (`r,t,f,y`) | ITNC | InputToNewCapacity | unused |
| RYTC | ITTC | InputToTotalCapacity | unused |
| RYTE (`r,t,e,y`) | ATE | AnnualTechnologyEmission | **used** (carbon + health channels; the `*ByMode` export is preferred when present) |
| RYCTs (`r,l,f,y`) | D | Demand | **used** (`emit_energy_demand` write-back baseline / preflight) |
| RYTEM (`r,t,e,m,y`) | ATEBM | AnnualTechnologyEmissionByMode | **used** (preferred variant of AnnualTechnologyEmission) |
| RYTEM | EBAC | EmissionByActivityChange | unused — **and not exported** by the live run (no matching CSV in `Base_v9/csv/`; catalog-only) |
| RYTMTs (`r,l,t,m,y`) | ROA | RateOfActivity | unused |
| RYTCMTs (`r,l,t,m,f,y`) | PBT | ProductionByTechnologyByMode | **used** (LCOE denominator: busbar generation) |
| RYTCMTs | ROPBT | RateOfProductionByTechnologyByMode | unused |
| RYTCMTs | ROUBT | RateOfUseByTechnologyByMode | unused |
| RYTCMTs | UBT | UseByTechnologyByMode | **used** (LCOE fuel-chain allocation) |

"Used" is read directly off `ogclews_link/muiogo_run.py`'s `PREFLIGHT_STEMS` table (the link's own
export-contract checklist) cross-checked against `signals.py`/`lcoe.py` call sites.

### A.2 Duals cataloged in `Duals.json` (4)

| Group | id | name (= CSV stem) | Used? |
|---|---|---|---|
| RYE (`r,e,y`) | AEL_d | E8_AnnualEmissionsLimit | unused |
| RYC (`r,f,y`) | EB_d | EBb4_EnergyBalanceEachYear4_ICR | **used, opt-in only** — `signals.commodity_shadow_price` / `commodity_shadow_price_ratio`, consumed via `energy_price_ratio(kind='marginal')`. Explicitly **never** the `'auto'` default (`signals.py` calls it a "short-run scarcity price ... degenerate in OSeMOSYS"); guarded by a minimum 3-year base/reform overlap (`_MARGINAL_MIN_OVERLAP_YEARS`) after a documented failure mode (a single binding year broadcast into a spurious +32% permanent shock on PHL). |
| RYCn (`r,cn,y`) | UDCI_d | UDC1_UserDefinedConstraintInequality | unused |
| RYCn | UDCE_d | UDC2_UserDefinedConstraintEquality | unused |

The live case's `UDC1`/`UDC2` duals key on `cn` = user-defined-constraint names `RENEWABLES` and
`EV` (from `genData.json → osy-constraints`) — i.e. the shadow price of the RE-target and
EV-penetration policy constraints. Entirely unused today; a real "how binding is the RE target"
signal.

### A.3 Result CSVs actually on disk for one run (`Philippines_v9/res/Base_v9/csv/`, 30 files)

All 4 run dirs (`Base_v8`, `Base_v9`, `PEP_v8`, `PEP_v9`) carry the identical 30-file set (each also
has `results.txt`, `data.txt`, `data_processed.txt` alongside `csv/`).

| CSV file | header | Used? |
|---|---|---|
| AccumulatedNewCapacity.csv | r,t,y,AccumulatedNewCapacity | unused |
| AnnualFixedOperatingCost.csv | r,t,y,AnnualFixedOperatingCost | **used** |
| AnnualTechnologyEmission.csv | r,t,e,y,AnnualTechnologyEmission | **used** |
| AnnualTechnologyEmissionByMode.csv | r,t,e,m,y,AnnualTechnologyEmissionByMode | **used** (preferred) |
| AnnualVariableOperatingCost.csv | r,t,y,AnnualVariableOperatingCost | **used** |
| AnnualizedInvestmentCost.csv | r,t,y,AnnualizedInvestmentCost | **used** |
| CapitalInvestment.csv | r,t,y,CapitalInvestment | **used** |
| Demand.csv | r,l,f,y,Demand | **used** (preflight baseline check) |
| DiscountedSalvageValue.csv | r,t,y,DiscountedSalvageValue | unused |
| E8_AnnualEmissionsLimit.csv | r,e,y,E8_AnnualEmissionsLimit,DiscountRate | unused (dual) |
| EBb4_EnergyBalanceEachYear4_ICR.csv | r,f,y,EBb4_EnergyBalanceEachYear4_ICR,DiscountRate | **used, opt-in** (dual/marginal) |
| InputToNewCapacity.csv | r,t,f,y,InputToNewCapacity | unused |
| InputToTotalCapacity.csv | r,t,f,y,InputToTotalCapacity | unused |
| NewCapacity.csv | r,t,y,NewCapacity | unused |
| ObjectiveValue.csv | r,ObjectiveValue | unused |
| ProductionByTechnologyByMode.csv | r_x,f,t,y,m,r_y,l,r,ProductionByTechnologyByMode | **used** |
| RateOfActivity.csv | r,l,t,m,y,RateOfActivity | unused |
| RateOfProductionByTechnologyByMode.csv | r_x,f,t,y,m,r_y,l,r,RateOfProductionByTechnologyByMode | unused |
| RateOfTotalActivity.csv | r,t,l,y,RateOfTotalActivity | unused — **and absent from `Variables.json`** (see below) |
| RateOfUseByTechnologyByMode.csv | r_x,f,t,y,m,r_y,l,r,RateOfUseByTechnologyByMode | unused |
| SalvageValue.csv | r,t,y,SalvageValue | unused |
| TechnologyEmissionsPenalty.csv | r,t,y,TechnologyEmissionsPenalty | unused |
| TotalAnnualTechnologyActivityByMode.csv | r,t,m,y,TotalAnnualTechnologyActivityByMode | unused |
| TotalCapacityAnnual.csv | r,t,y,TotalCapacityAnnual | unused |
| TotalTechnologyAnnualActivity.csv | r,t,y,TotalTechnologyAnnualActivity | unused — **and absent from `Variables.json`** |
| TotalTechnologyModelPeriodActivity.csv | r,t,TotalTechnologyModelPeriodActivity | unused |
| Trade.csv | r,rr,l,f,y,Trade | unused — **and absent from `Variables.json`** |
| UDC1_UserDefinedConstraintInequality.csv | r,cn,y,UDC1_...,DiscountRate | unused (dual) |
| UDC2_UserDefinedConstraintEquality.csv | r,cn,y,UDC2_...,DiscountRate | unused (dual) |
| UseByTechnologyByMode.csv | r_x,f,t,y,m,r_y,l,r,UseByTechnologyByMode | **used** |

**Discrepancy found:** three CSVs the live CBC solve actually exports —
`DiscountedSalvageValue`, `RateOfTotalActivity`, `TotalTechnologyAnnualActivity` — plus `Trade`,
have **no corresponding entry in `Variables.json`** (verified: none of the 29 cataloged variable
`name` values match these 4 CSV stems). MUIOGO's variable catalog is therefore a strict subset of
what its own solve run actually produces on disk; the input-side (`Parameters.json`) coverage was
not similarly checked for gaps.

---

## Part B — Writable surface (OG → CLEWS levers)

### B.1 Input parameters cataloged in `Parameters.json` (49), by index-set group

| Group | id | name | Used? |
|---|---|---|---|
| R (`r`) | DR | DiscountRate | **used** (`emit_discount_rate` → `clews_io.write_discount_rate`) |
| RT (`r,t`) | TMPAU | TotalTechnologyModelPeriodActivityUpperLimit | unused |
| RT | TMPAL | TotalTechnologyModelPeriodActivityLowerLimit | unused |
| RT | OL | OperationalLife | unused |
| RT | CAU | CapacityToActivityUnit | unused |
| RT | DRI | DiscountRateIdv | unused |
| RE (`r,e`) | MPEL | ModelPeriodEmissionLimit | unused |
| RYCn (`r,cn,y`) | UCC | UDCConstant | unused |
| RYTCn (`r,t,cn,y`) | CAM | UDCMultiplierActivity | unused |
| RYTCn | CNCM | UDCMultiplierNewCapacity | unused |
| RYTCn | CCM | UDCMultiplierTotalCapacity | unused |
| RYTs (`r,l,y`) | YS | YearSplit | unused |
| RYDtb (`r,y,dtb`) | DS | DaySplit | unused |
| RYSeDt (`r,y,se,dtb`) | DIDT | DaysInDayType | unused |
| RYT (`r,y,t`) | COTU | CapacityOfOneTechnologyUnit | unused |
| RYT | TAU | TotalTechnologyAnnualActivityUpperLimit | unused |
| RYT | TAL | TotalTechnologyAnnualActivityLowerLimit | unused |
| RYT | TAMinCI | TotalAnnualMinCapacityInvestment | unused |
| RYT | TAMinC | TotalAnnualMinCapacity | unused |
| RYT | TAMaxCI | TotalAnnualMaxCapacityInvestment | unused |
| RYT | TAMaxC | **TotalAnnualMaxCapacity** | unused |
| RYT | RC | **ResidualCapacity** | unused |
| RYT | FC | FixedCost | unused |
| RYT | CC | CapitalCost | unused |
| RYT | AF | **AvailabilityFactor** | unused |
| RYTM (`r,y,t,m`) | TAIML | TechnologyActivityIncreaseByModeLimit | unused |
| RYTM | TADML | TechnologyActivityDecreaseByModeLimit | unused |
| RYTM | TAMUL | TechnologyActivityByModeUpperLimit | unused |
| RYTM | TAMLL | TechnologyActivityByModeLowerLimit | unused |
| RYTM | VC | VariableCost | unused |
| RYTC (`r,y,f,t`) | ITCR | InputToTotalCapacityRatio | unused |
| RYTC | INCR | InputToNewCapacityRatio | unused |
| RYTCM (`r,f,t,y,m`) | OAR | OutputActivityRatio | unused |
| RYTCM | IAR | InputActivityRatio | unused |
| RS (`r,s`) | SLS | StorageLevelStart | unused (no storage set members) |
| RS | OLS | OperationalLifeStorage | unused (no storage) |
| RYS (`r,s,y`) | MSC | MinStorageCharge | unused (no storage) |
| RYS | RSC | ResidualStorageCapacity | unused (no storage) |
| RYS | CCS | CapitalCostStorage | unused (no storage) |
| RTSM (`r,t,s,m`) | TFS | TechnologyFromStorage | unused (no storage) |
| RTSM | TTS | TechnologyToStorage | unused (no storage) |
| RYTTs (`r,t,y,l`) | CF | CapacityFactor | unused |
| RYC (`r,f,y`) | SAD | **SpecifiedAnnualDemand** | **used** (`emit_energy_demand` → `clews_io.write_demand`, a per-year ratio artifact `demand_scaling.csv` meant to scale this parameter) |
| RYC | AAD | AccumulatedAnnualDemand | unused |
| RYCTs (`r,f,y,l`) | SDP | SpecifiedDemandProfile | unused |
| RYE (`r,e,y`) | EP | **EmissionsPenalty** | **used** (`emit_carbon_penalty`/carbon-tax channel → `clews_io.write_emissions_penalty`) |
| RYE | AEL | AnnualEmissionLimit | unused |
| RYTEM (`r,e,t,y,m`) | EACR | EmissionToActivityChangeRatio | unused |
| RYTEM | EAR | EmissionActivityRatio | unused |

**3 of 49 parameters are used** (DiscountRate, SpecifiedAnnualDemand, EmissionsPenalty) — exactly
the three keys `clews_io._WRITERS` handles (`Demand`, `EmissionsPenalty`, `DiscountRate`); confirmed
by `grep -n "clews_inputs\["` across `ogclews_link/*.py`, which shows exactly 3 write sites, all in
`channels.py` (`emit_carbon_penalty` → `EmissionsPenalty`; `emit_discount_rate` → `DiscountRate`;
`emit_energy_demand` → `Demand`).

**Specifically requested checks:**
- `TotalAnnualMaxCapacity` / `TotalAnnualMinCapacity` (and their `...Investment` variants) — cataloged, **unused**. These are the natural lever for "reform builds/retires capacity faster/slower" write-backs.
- `ResidualCapacity` — cataloged, **unused**. The natural lever for "OG-side investment changes the installed base CLEWS starts from."
- `AvailabilityFactor` — cataloged, **unused**. Could carry a climate/reliability signal (e.g. hydro/solar derating) but nothing writes it.
- Fuel prices/costs — **there is no dedicated "fuel price" parameter** in this OSeMOSYS variant. Fuel economics live in `VariableCost` (RYTM, per tech×mode) and `CapitalCost`/`FixedCost` (RYT) on the upstream extraction/import/processing technologies (`PHL_PRO_EXTR_*`, `PHL_PRO_IMP_*`, `PHL_PRO_PROC_*`) — a fuel-price write-back would mean writing `VariableCost` for those specific techs, not a standalone price parameter. All unused.
- `ReserveMargin` — **absent from the catalog entirely** (confirmed: no parameter name in `Parameters.json` contains "reserve" or "margin"). Standard OSeMOSYS has `ReserveMargin`/`ReserveMarginTagFuel`/`ReserveMarginTagTechnology`; this MUIOGO instance does not expose them as a manageable parameter group at all — not just unused, structurally unavailable via this interface.
- Land/water availability parameters — **no bespoke land or water parameter category exists.** Land (`PHL_LND*`) and water (`PHL_DEM_*_WAT`, `PHL_PUB_WAT`, `PHL_PWR_WAT`) are ordinary OSeMOSYS technologies/commodities using the same generic parameter set as everything else (`ResidualCapacity`, `TotalAnnualMaxCapacity`, `OutputActivityRatio`, etc. — see B.1). There is no `LandAvailability` or `WaterAvailability` parameter; any land/water lever would write the generic capacity/activity parameters scoped to the land/water technology codes.

### B.2 Artifacts `clews_io.py` currently emits (the write mechanics)

| Function | Output file | Target parameter | Columns |
|---|---|---|---|
| `write_demand` | `demand_scaling.csv` | SpecifiedAnnualDemand (as a ratio to be applied downstream — not the parameter file itself) | REGION, OG_ACTIVITY, OG_INDEX, CLEWS_FUEL, YEAR, DEMAND_RATIO |
| `write_emissions_penalty` | `EmissionsPenalty.csv` | EmissionsPenalty | REGION, EMISSION, YEAR, VALUE |
| `write_discount_rate` | `DiscountRate.csv` | DiscountRate | REGION, VALUE, NOTE |

Per `clews_io.py`'s module docstring and `country.py:43`, these are the producer side only — "writing
these is implemented; invoking OSeMOSYS on them is the external step (MUIOGO / the solver)." No code
in this worktree constructs a `clews_patch.json` or calls a MUIOGO endpoint; that loop-closure step
is designed (see memory: `clews-loop-closure-design`) but not present in `ogclews-link-channels`.

---

## Part C — v9 technology/commodity census (`Philippines_v9/genData.json`)

132 technologies, 57 commodities, grouped by sector prefix (from each `Tech`/`Comm` code's second
underscore-token).

### C.1 Technologies (132) by sector

| Sector | count | representative techs |
|---|---|---|
| POW (power) | 30 | PHL_POW_PP_COAL, _PP_COAL_CCS, _PP_NGCC(_CCS), _PP_HY_LA, _PP_SPV_T1, _PP_WOF_T1, _PP_WON_T1, _PP_NU, _PP_NUSMR, _PP_H2, _CHP_*_OLD, _GH2_*/_BH2_NG (hydrogen), _DAC, _ELEC (electrolyzers), _TD(+_AGR/_HOU/_INDU/_SER/_TRA) |
| TRA (transport) | 37 | 23-wheelers, cars, buses, light/heavy trucks, vans (each ×ELE/LIQ/NG/H2/PHEV variants), rail (freight/passenger), aviation, shipping |
| INDU (industry) | 15 | high/low process heat (OTHHPH/OTHLPH) × BIOM/COAL/NG/OIL/H2, two with CCS, PHL_INDU_PLANT_OTH |
| PRO (fuel supply/processing) | 15 | extraction (COAL/NG/OIL), imports (COAL/NG/OIL/UR), processing (BIOF/BIOM/COAL/NG/OIL), blending (BIOF/OIL/SFUEL) |
| LND (land) | 7 | PHL_LND, _BLT (built-up), _CRP (crop), _FOR (forest), _GRS (grassland), _OTH, _WAT (water bodies) |
| AGR (agriculture) | 9 | facilities/unit, heating (BIOM/COAL/ELE/NG/OIL), motive power (ELE/LIQ) |
| HOU (housing) | 6 | unit, cooking (BIOM/COAL/ELE/NG/OIL) |
| SER (services) | 7 | unit, heating (BIOM/COAL/ELE/NG/OIL/RES) |
| DEM (demand, water) | 4 | cooling water (groundwater/surface) for power; public-sector groundwater/surface water |
| MIN (mining) | 1 | PHL_MIN_PRC (precipitation) |
| PWR (legacy?) | 1 | PHL_PWR_GAS ("Power plants and chp that use gas") — separate prefix from POW, likely a legacy/duplicate naming artifact |

### C.2 Commodities (57) by sector

| Sector | count | representative commodities |
|---|---|---|
| TRA | 11 | electricity + passenger/freight-km measures (PKMC cars, PKMB buses, PKM23 2/3-wheelers, PKMA aviation, PKMR/FKMR rail, FKMTH/FKMTL trucks, FKMS shipping) |
| PRO | 10 | BIOF, BIOM, COAL(+COAL0 pre-processing), LIQ, NG(+NG0), OIL(+OIL0), UR |
| POW | 8 | AMMO, DACF (DAC-captured CO2), ELE / ELE1 (post-T&D), H2, HEAT / HEAT1 (post district-heating), SFUEL |
| LND | 7 | LND, LBLT, LCRP, LFOR, LGRS, LOTH, LWAT |
| AGR | 5 | ELE/ELEF, HEAT, MOT, PRO |
| INDU | 4 | ELE, OTH, OTHHPH, OTHLPH |
| SER | 3 | ELE/ELEF, HEAT |
| WTR (water) | 4 | EVT (evapotranspiration), GWT (groundwater), PRC (precipitation), SUR (surface water) |
| HOU | 3 | COOK, ELE, ELEF |
| PUB | 1 | PHL_PUB_WAT (water demand) |
| PWR | 1 | PHL_PWR_WAT (cooling water) |

### C.3 Crop / water / cooking activity check (Base_v9 run, `TotalTechnologyAnnualActivity.csv`, summed 2020–2053)

| Technology | Sum of TotalTechnologyAnnualActivity | Observation |
|---|---|---|
| PHL_LND_CRP (crop land) | **0.000** | Declared with unbounded `TotalCapacityAnnual` (999999.0 sentinel every year — the OSeMOSYS "no limit" default, not a real capacity), but **zero modeled activity** in this run. |
| PHL_LND_GRS (grassland) | **0.000** | Same pattern — present, unconstrained, inactive. |
| PHL_LND_FOR (forest) | 44,199.8 | Active. |
| PHL_LND_BLT (built-up) | 162.2 | Active. |
| PHL_LND_WAT (water bodies) | 632.5 | Active. |
| PHL_LND_OTH | 52.3 | Active. |
| PHL_LND (aggregate land) | 45,046.8 | Active. |
| PHL_DEM_PUB_SUR_WAT | 1,289.7 | Active — public surface-water demand. |
| PHL_DEM_PWR_SUR_WAT | 697.6 | Active — power-plant cooling, surface water. |
| PHL_DEM_PUB_GWT_WAT | 25.7 | Active — public groundwater demand. |
| PHL_DEM_PWR_GWT_WAT | 186.5 | Active — power-plant cooling, groundwater. |
| PHL_HOU_COOK_BIOM | 236.7 | Active. |
| PHL_HOU_COOK_ELE | 145.6 | Active. |
| PHL_HOU_COOK_COAL | 9,866.2 | Active (large — unverified whether this reflects a real coal-cooking share or a calibration artifact; flagged, not resolved here). |
| PHL_HOU_COOK_NG | **0.000** | Declared, inactive. |
| PHL_HOU_COOK_OIL | **0.000** | Declared, inactive. |

**Bottom line:** v9 declares the full land-use taxonomy (crop/grassland/forest/built-up/water) and a
full water-demand submodel (groundwater + surface, public + power cooling), and cooking technologies
across 5 fuels — but **crop land, grassland, cooking-with-NG, and cooking-with-oil carry zero
activity** in the Base_v9 solve. The technologies and their parameters (capacity, cost, output
ratios) all exist and are readable/writable; they are simply idle in this particular case/scenario
solve, not absent from the model structure.

---

## Part D — Unused-surface summary (the raw material for new channels)

**Readable, unused today (23 of 30 result CSVs / 4 duals not yet consumed):**
capacity build-out (AccumulatedNewCapacity, NewCapacity, TotalCapacityAnnual, InputToNewCapacity,
InputToTotalCapacity, TotalTechnologyModelPeriodActivity), activity/utilization detail (RateOfActivity,
RateOfTotalActivity, RateOfProductionByTechnologyByMode, RateOfUseByTechnologyByMode,
TotalAnnualTechnologyActivityByMode, TotalTechnologyAnnualActivity), retirement economics
(SalvageValue, DiscountedSalvageValue), TechnologyEmissionsPenalty (the realized cost of the carbon
price the link itself may have written), ObjectiveValue (total system cost — a single scalar per
region per run), Trade (inter-region flows — moot with one region, RE1, in this case), and **3 of 4
duals**: E8 (emissions-limit shadow price — how binding is the model's own emissions cap),
UDC1/UDC2 (RENEWABLES-target and EV-penetration shadow prices — how binding are the two active
policy constraints in this case).

**Writable, unused today (46 of 49 input parameters):** every capacity-limit and capacity-inheritance
parameter (TotalAnnualMax/MinCapacity(+Investment), ResidualCapacity), every technology-economics
parameter (CapitalCost, FixedCost, VariableCost, OperationalLife, CapacityToActivityUnit,
DiscountRateIdv), AvailabilityFactor and CapacityFactor, the full activity-ratio/emission-ratio set
(OutputActivityRatio, InputActivityRatio, InputToNewCapacityRatio, InputToTotalCapacityRatio,
EmissionActivityRatio, EmissionToActivityChangeRatio), all timeslice/calendar parameters (YearSplit,
DaySplit, DaysInDayType), all storage parameters (moot — no storage in PHL v9), all
user-defined-constraint parameters (UDCConstant, UDCMultiplier{Activity,NewCapacity,TotalCapacity}),
AccumulatedAnnualDemand, SpecifiedDemandProfile, ModelPeriodEmissionLimit, and AnnualEmissionLimit.
`ReserveMargin` is not just unused but structurally absent from the catalog. There is no dedicated
fuel-price or land/water-availability parameter category — those levers would have to ride the
generic capacity/cost/ratio parameters scoped to the relevant technology codes (`PHL_PRO_*` for
fuel, `PHL_LND_*`/`PHL_DEM_*_WAT` for land/water).
