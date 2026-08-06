# PHL CLEWs recalibration — complete decision register

**Date:** 2026-08-06
**Source case:** `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC` (`muiogoai` world, MUIOGO at `928a13bb`)
**Calibrated case:** `Philippines_v12_CALIBRATED`
**Script:** `experiments/calibrate_phl_case.py` — every constant carries its source, every judgment
call is in the script's own `DECISIONS` dict, and `--report` emits a JSON record of what changed.

This document exists so that someone who did not do the work can evaluate it. It records what was
changed, what it was changed to, where each number came from, **why** each choice was made over the
alternatives, what was deliberately left alone, and where this work is weakest. It also records four
places where earlier conclusions in this session were wrong and were corrected.

Nothing was changed in the source case. All work is on copies.

---

## 1. The finding that should frame everything else

**This is an energy model with land and water attached.** All three policy scenarios in the case —
`COAL_PHASEOUT`, `RE`, `EV` — are energy scenarios. And the two sides were in completely different
condition before any of this work:

| | state before recalibration |
|---|---|
| **Energy** | Sound. 2020 generation 102.0 TWh against 101.76 observed (+0.2%). Every technology share within ~1 percentage point. Capacity 25.80 GW against ~26.3. Tracks observed generation within 0–6% through 2024. |
| **Land** | Not usable. Crop yields wrong by factors of 2–5 in both directions; forest 2.5× observed because it absorbed an unallocated residual. |
| **Water** | Not usable. Irrigation withdrawal ~25× too low; water free everywhere. |

So the recalibration is not repairing a broken model. It is making the land and water blocks fit to
report on, while trying hard not to disturb an energy block that already works.

---

## 2. Land — crop yields

### The defect

`OutputActivityRatio` on the crop modes carries GAEZ **agro-climatically attainable potential**
yields, used as if they were observed actual yields. The crop *demands* are well calibrated (rice
19.295 Mt against 19.295 observed; corn 8.119 against 8.119; sugarcane 24.399 against 24.399; coconut
14.491 against 14.491 — these match PSA to four decimals). So the model produced the right national
output on the wrong area.

Implied yields from the uncalibrated solve, against PSA 2020:

| crop | model implied | PSA 2020 | |
|---|---:|---:|---|
| palay | 8.40 t/ha | **4.089** | 2.05× too high |
| corn | 8.30 | **3.179** | 2.61× too high |
| coconut | 4.67 | **3.969** | 1.18× too high |
| sugarcane | 11.00 | **61.137** | 5.56× too low |
| vegetables | 4.50 | ~9.7 | ~2.2× too low |

The errors run both ways and largely cancel in the total, which is why aggregate cropland looked
plausible while every individual crop was wrong.

### What was changed

Each crop's `OutputActivityRatio` scaled by `solved area ÷ PSA 2020 harvested area`:

| commodity | factor | target | source |
|---|---:|---:|---|
| `CRPRCP` | 0.4869 | 47,189 km² | palay 4,718,896 ha |
| `CRPMZE` | 0.3830 | 25,538 km² | corn 2,553,781 ha |
| `CRPCON` | 0.8494 | 36,513 km² | coconut 3,651,289 ha |
| `CRPSGC` | 5.5578 | 3,991 km² | sugarcane 399,086 ha |
| `CRPTOM` | 2.0666 | 5,912 km² | vegetables + root crops 591,243 ha |

All from **PSA OpenSTAT PX-Web API**, Crops database, 2020 annual, national. The API is machine-readable
and returns exact values; `psa.gov.ph` HTML is Cloudflare-blocked.

### Decisions and why

**`CRPTOM` is treated as vegetables-plus-root-crops, not tomatoes.** The build documents it as a GAEZ
tomato proxy, but its demand of 5.4996 Mt matches PSA's whole *Vegetables and Root Crops* table
(5.737 Mt), not tomatoes (0.222 Mt). The area target is therefore that table's 591,243 ha.
*Rejected alternative:* FAOSTAT "Vegetables Primary" (785,502 ha) — 80% of that aggregate is an
imputed "other vegetables n.e.c." residual carrying flag `I`, six times larger than everything PSA
reports outside FAO's named items, and its area exceeds PSA's entire vegetables-plus-roots area. It is
not a measurement.

**`CRPOTH` was left untouched.** It is a residual "other crops" aggregate with no observed
counterpart. Scaling it would require inventing a target. Its ~15,000 km² is carried as-is, and it is
the largest single source of the cropland excess discussed below.

**Sugarcane 2020 was a good year.** 61.137 t/ha against a 2010–2024 mean of 57.2. Calibrating to 2020
locks in a yield ~7% above the long-run average. Accepted for base-year consistency with every other
crop, but a reviewer could reasonably prefer the mean.

**Coconut production is whole nuts including husk.** PSA reports it that way and FAOSTAT ingests it
unchanged despite its "Coconuts, in shell" label. The yield of 3.969 t/ha is on that basis. Anyone
converting to copra equivalent must not reuse this number.

**Factors are national, not per-cluster.** The model reallocates crops across eight yield clusters, so
a single national factor lands close but not exact — residuals of 1–5% in the earlier test. Per-cluster
factors from PSA regional data would be better and are the obvious next refinement.

### The honest limitation

**Matching harvested area is not validation.** The targets were imposed. This makes the model
*consistent with* observed area; it does not test whether the model would have predicted it.

---

## 3. Land — base-year cover

### The defect

The build reads a complete seven-class land-cover table and then discards most of it. The mode
lower-limit loop in `clewsy.py:410` skips `Cropland`, `Forest land` and `Other agricultural land`,
writing base-year limits only for Built-up and Water. Consequence: **164,254 km², 55% of the country,
never reached the model**, and Forest absorbed the entire unallocated residual — 179,780 km² against
72,260 observed.

The underlying product is **FAO GAEZ v4 land cover**, and `DATA_SOURCES.md` describes its classes as
*"bare, built-up, forest, grassland, other and water-body"* — with **no cropland class at all**, yet
the concordance manufactures one. One class (`LCType10`) holds 55.5% of the national area and is
36–63% of every cluster uniformly, which is the signature of a residual bucket. Grassland and barren
have no data columns whatsoever.

### What was changed

Replaced the concordance with **PSA/NAMRIA Land Asset Accounts, Table 1, 2020 closing stock** (PSA
Special Release 2024-203, 20 Dec 2024; underlying NAMRIA Land Cover Map 2020). It is a 13-class
exhaustive partition at 10 m resolution whose total is within **0.024%** of the model's own control
total of 295,813.1 km² — so the substitution is essentially areal-neutral.

| model class | built from NAMRIA classes | km² | pin |
|---|---|---:|---|
| Cropland | Annual 59,438.0 + Perennial 65,737.9 | 125,280.5 | **floor** |
| Forest land | Closed 22,210.2 + Open 46,936.7 + Mangrove 3,112.2 | 72,319.4 | **floor** |
| Grassland and woodland | Grassland 19,610.0 + Brush/Shrubs 58,070.8 | 77,745.6 | free |
| Barren and sparsely vegetated | Open/Barren 1,593.7 | 1,595.0 | **floor** |
| Built-up land | Built-up 10,256.3 | 10,264.9 | **equality** |
| Water bodies | Inland Water 4,893.6 + Marshland 1,421.0 | 6,319.8 | **equality** |
| Other agricultural land | Fishpond 2,286.0 | 2,287.9 | free |
| **total** | | **295,813.1** | |

Two reconciliation steps, both explicit: NAMRIA's "Sea and ocean" class (317.3 km²) was dropped as a
coastal-reclassification artefact per PSA's own Technical Notes; the remainder was scaled pro rata by
×1.00083479 to hit the model's control total exactly.

The forest figure independently reproduces **FAO FRA 2025** (7,226.39 thousand ha) — a genuine
cross-check, since the two products are built differently.

### Decisions and why

**Brush and shrubs go to Grassland, not Forest.** Both FAO FRA and NAMRIA exclude brush/shrub from the
7.226 Mha forest figure. Putting any of it in Forest would break the forest cross-check. The
"woodland" in the model's class name is what carries it.

**Marshland and swamp go to Water bodies.** The model has no wetland class; inundated land is closer
to water than to barren.

**Fishponds go to Other agricultural land, not Water.** They are managed production land — FAO's "land
used for aquaculture" for 2020 is 2,533 km², consistent with NAMRIA's 2,286 — and this keeps Water
bodies as natural hydrology.

**Built-up rises from 770 to 10,265 km², a 13× correction.** The old figure was one GAEZ class; NAMRIA
measures settlement directly at 10 m. Pinned as an equality because settlement is exogenous,
population-driven, and does not revert.

**Forest is a floor, not an equality.** A floor stops the model reporting 2.5× the observed forest and
stops it deforesting below observed cover in the base year, while still permitting land-use change —
which is the point of the model. An equality would forbid the dynamics.

**Cropland is a floor, deliberately.** See §4 — an equality would make the model infeasible.

**Grassland is the free swing pool.** It gets its base-year value as data but no floor, so it absorbs
residuals and donates land to cropping. That is the role Forest was wrongly playing. **This is the
single most important structural decision in the whole recalibration.**

**Cluster apportionment is an assumption, not data.** NAMRIA reports nationally; the model has eight
yield clusters. National class totals are apportioned **pro rata to cluster area**, which assumes each
class is uniformly distributed across clusters. That is certainly false for Built-up, which
concentrates in Metro Manila. It is adopted because no cluster-level NAMRIA tabulation exists. **A
reviewer should challenge this first** — it is the weakest link in the land work.

*Rejected alternative:* keeping the GAEZ table with `LCType10` split 49.87% Cropland / 39.11%
Grassland / 5.78% Built-up / rest Water. Arithmetically equivalent to the above but with no
independent basis for the split fractions — they are reverse-engineered from NAMRIA. If you have
NAMRIA, use NAMRIA.

*Rejected alternative:* FAOSTAT Cropland (111,776 km²). **This would break the model** — it is below
the cropland the exogenous crop demand requires. It also carries flag `I` with arable land frozen at
exactly 5,590.00 thousand ha for 2019–2021, i.e. carried forward, not measured.

---

## 4. The cropland/multi-cropping tension — the most important limitation

My earlier yield fix implied **137,400 km²** of cropland. That figure **exceeds every measured
Philippine crop cover**:

| measure | km² |
|---|---:|
| model requirement after the yield fix | 137,400 |
| NAMRIA total crop cover | 125,176 |
| PSA 2020 harvested area, the five modelled crops | 119,143 |
| FAOSTAT cropland | 111,776 |

**This is not a land-cover failure. It is a structural limitation of the model.** The Philippines
multi-crops: irrigated palay alone is harvested on 3,253,454 ha while only about 2,006,000 ha is
equipped for irrigation. The model has **no multi-cropping mechanism** — one crop mode occupies land
for a year — so its cropping intensity is structurally 1.0 and its "cropland" is really
harvested-area-equivalent.

Two ways to handle it, and the choice matters:

1. **Pin Cropland as an equality at NAMRIA's 125,280 km².** Internally consistent with the land cover,
   but the model then cannot meet its own crop demand and goes infeasible or crushes forest.
2. **Pin Cropland as a floor.** The model expands into the free grassland pool, and the excess of
   ~12,000 km² appears in the results as **explicit base-year land conversion**.

**Option 2 was chosen.** The reasoning: the limitation is real and cannot be removed without adding a
multi-cropping mechanism, which would be a redesign. Given that, it is better for the limitation to be
*visible* as an implausible base-year conversion than *hidden* as a wrong forest number. The implied
cropping intensity is 137,400 / 125,280 = **1.097**, against roughly 1.41 implied by PSA/FAO on arable
land — so the model under-represents multi-cropping even after this.

Resulting freedom: floors and pins total 215,780 km², leaving **80,034 km² (27.1% of national area)
genuinely allocatable**. The cropland expansion consumes 15.1% of that pool.

**A reviewer evaluating this work should look here first.** If their model handles multi-cropping, they
will get a materially different and better answer.

---

## 5. Water

### The defect

Three findings, only one of which is a straightforward bug.

1. **Irrigation withdrawal was ~25× too low.** High-input irrigated rice drew 740 m³/ha/yr against a
   real requirement in the thousands; low-input irrigated rice drew 26 m³/ha/yr, effectively zero.
   National agricultural withdrawal came out at 2.71 km³/yr.
2. **There is no water-resource constraint at all.** `MINPRCPHL`, the single source of all water,
   carries no activity or capacity limit — it falls through to the 999999 default — and precipitation
   enters as a per-hectare coefficient on land rather than a national endowment.
3. **Water has no seasonality.** No `CapacityFactor` or `AvailabilityFactor` on precipitation or land,
   and water demands are annual.

### The AQUASTAT factor-of-two, resolved

The apparent conflict between "~69 km³" and "~30 km³" is **inside AQUASTAT and is not an error**:

| AQUASTAT variable | code | value | what it is |
|---|---|---:|---|
| Agricultural water withdrawal | 4250 | **67.965 km³/yr** (2023, official) | **gross** diversion |
| Irrigation water withdrawal | 4475 | 67.252 (2023) | gross, irrigation only |
| Irrigation water requirement | 4260 | 33.280 (2006, imputed) | **net** requirement |
| Water requirement ratio | — | 51% | FAO's own ratio linking them |

`33.280 / 65.590 = 50.7% ≈ 51%`. Anyone quoting 30 km³ for Philippine agricultural *withdrawal* has
taken FAO's net crop requirement and mislabelled it. Citation: Frenken & Gillet (2012), *Irrigation
water requirement and water withdrawal by country*, FAO AQUASTAT Reports, Philippines row.

**The target adopted is 67.965 km³/yr** (variable 4250, 2023, symbol A = official).

**FAO itself flags this number as weak**, and that belongs in any limitations section: the Philippines
is named among countries withdrawing 15,000–35,000 m³/ha/yr against a regional gross average of 8,960,
and FAO writes that the discrepancy *"cannot be explained solely by differences in climatic
conditions. Rather, their difference is to be found in computation methods… More research is needed."*

### What was changed

- `AGRWATPHL` input ratios scaled so national agricultural withdrawal meets 67.965 km³/yr. Because the
  yield correction changes irrigated area, the factor is derived from a first solve and applied in a
  second pass — the script takes `--water-factor` for exactly this.
- **Irrigated-area cap** of 32,535 km² added via `TechnologyActivityByModeUpperLimit` on the irrigated
  crop modes, from PSA 2020 irrigated palay harvested area (3,253,454 ha).

### Decisions and why

**The irrigated-area cap does not bind and is not meant to.** The model uses about 25,000 km²; the cap
is at 32,535. It is a calibration guard against runaway irrigation, not a policy constraint. It uses
`TechnologyActivityByModeUpperLimit`, which already exists in the MUIOGO formulation (parameter at
line 65, enforced by constraint `LU1` at line 238) and is already used in this case — so this is new
*use* of an existing mechanism, not a structural change.

**No water-resource cap was added, and no seasonality.** Both were considered and rejected as outside
the "work within this structure" constraint. Adding seasonality means changing the timeslice set;
adding basin units means changing the spatial units. Both are redesigns.

**And the honest conclusion: water still will not bind, by construction.** This was tested. With
withdrawals corrected to 67.97 km³ against 302 km³ of surface water generated, use rises to 33% and
224 km³ of headroom remains. At annual national resolution **the Philippines genuinely is not
water-scarce** — 725 km³ of rain falls on 300,000 km². Its water scarcity is seasonal and
basin-level, and no parameter change at this resolution can represent that.

So what the water block can now say: annual withdrawal by sector, irrigation requirements, water-use
ratios, and the land–water balance. What it cannot say: anything about dry-season shortage, basin
stress, or drought. **That should be stated whenever a water number from this model is used.**

A previously-measured consequence worth repeating: correcting irrigation rates alone changed the land
allocation by **not one decimal place**, because water carries neither cost nor binding constraint.
Irrigation water is a pure accounting passthrough in this model. The fix makes a reported number
defensible; it does not make the nexus live.

---

## 6. Energy

The energy block was already sound, so changes here are conservative and each is individually
justified. The motivation was the `PEP_v12` policy run, which replaced coal with 165 TWh of onshore
wind and 50 TWh of nuclear SMR at an objective cost of 0.0061%.

| parameter | from | to | source and reason |
|---|---:|---:|---|
| coal capital cost | 2200 | **1605** USD/kW | BNEF *The Philippines' Path to Clean and Affordable Electricity*, 3 Jun 2025, App. A Table 3. The model's 2200 sat at the **US** level (IEA WEO US coal 2100); it is 1.37× the Philippine benchmark, 1.8× India, 1.4–1.5× Vietnam. Real projects imply 1310–1580. |
| nuclear SMR capital | 4482 | **8000** USD/kW | NREL ATB 2024, Nuclear-Small 300 MWe, **Moderate** case 2030. Published range is 5,500–12,700; the cancelled NuScale project implied ~20,130. |
| nuclear SMR life | 60 | **40** yr | 60 years is a mature-fleet design life. A Philippine first-of-a-kind in a country with no nuclear industry does not get it. |
| hydro life | 100 | **60** yr | Real Philippine hydro is 50–80 years. 100 overstates and understated hydro's annualised capital. |
| onshore wind capacity factor | 17.7% | **26.7%** | First Gen Integrated Report 2024, Burgos 150 MW, 2019–24 mean, against a P50 design of 27.5%. |
| **offshore wind capacity factor** | **15.4%** | **45.0%** | World Bank/ESMAP *Offshore Wind Roadmap for the Philippines*, Apr 2022. **The most consequential energy fix** — see below. |
| geothermal availability | 1.00 | **0.629** | Derived from DOE Power Statistics 2024: generation ÷ (capacity × 8760) = 62.9%, well below the 80–90% in generic catalogues. |
| onshore wind activity cap | 1594.08 PJ | **664 PJ** | NREL/USAID 2020 **Restricted** potential, 184.4 TWh/yr. |
| discount rate | 0.05 | **0.10** | NEDA/ICC Memorandum, 30 Sep 2016 — 10% real, mandatory for public investment appraisal. |

### The offshore wind fix is the one that matters

The model's onshore wind activity cap allowed **442.8 TWh/yr**:

| against | TWh/yr | model allowed |
|---|---:|---:|
| NREL unconstrained good-to-excellent resource | 195.2 | 2.27× |
| NREL/USAID screened "Restricted" potential | 184.4 | 2.40× |
| DOE's entire wind plan to 2050 | 92.8 | 4.77× |

And the 165 TWh it built needs **70.7 GW** at Burgos's achieved capacity factor — 92% of the entire
unconstrained national resource, on 21,000–29,000 km², which is **1.9–2.6× all the good-to-excellent
windy land in the country**. The implied build rate is 2,307 MW/yr for 27 consecutive years against a
realised 7.5 MW/yr; installed wind has sat at 0.427 GW for ten straight years.

Meanwhile the Philippines' actual wind resource is **offshore** — 27–58 GW after environmental and
social screening, at 45–47% capacity factor. The model has an offshore technology and gave it a
capacity factor of 15.4%, producing an LCOE of **257 USD/MWh**, which is why it was never built.
At the correct 45% its LCOE is **88.0 USD/MWh — cheaper than onshore's 95.4.**

So this single parameter was redirecting the entire wind build onto land that does not exist. Fixing it
lets the model use the resource the country actually has.

### Deliberately not changed

**Fuel prices.** Imported coal at 3.033 rising to 4.00 USD/GJ is 22% above the 2020 actual of 2.48,
but it brackets 2023–24 actuals (5.07, 3.76). Revising the path is a **price forecast, not a
calibration**, so it is left alone and flagged. Two related traps a reviewer should check: the coal
calorific value should be ~22.1 GJ/t (the DOE official figure — assuming 17.6 GJ/t for Indonesian coal
would overstate USD/GJ by 25%), and **the Philippines imported no LNG before April 2023**, so a 2020
gas price should be Malampaya, which is oil-linked and now at parity with LNG anyway.

**Coal availability.** Philippine coal plant achieves 69.5% utilisation, but in OSeMOSYS utilisation is
endogenous and `AvailabilityFactor` is a ceiling. Capping it at 0.695 would *force* rather than
reproduce. Geothermal is different — it is baseload and resource-limited, so 62.9% is a genuine
availability ceiling, which is why geothermal was changed and coal was not.

**Most operational lives.** See §8 — an earlier claim that these were wrong was itself wrong.

---

## 7. The discount rate — three defensible values meaning three different things

This was tested rather than argued. `Philippines_v12_DISCOUNT10` (uncalibrated inputs, `DR` = 0.10)
was solved alongside the original.

| rate | value | what it is |
|---|---:|---|
| model's original | 5.00% | ≈ OG-PHL's **government** borrowing rate (`r_gov` first-decade mean 5.04%) |
| **OG-PHL `r_p`** | **7.34%** | Household portfolio return, first-decade mean. **This is what `ogclews_link` actually writes into CLEWs** via `channels.emit_discount_rate`, which harmonises the energy model to *"OG's market cost of capital — not a separate social rate."* Steady state 7.81%. |
| OG-PHL `r` | 6.54% | Firm rate, first-decade mean; steady state 7.08% |
| **NEDA/ICC** | **10.00%** | Mandatory real social discount rate for public investment appraisal, since 30 Sep 2016 (down from 15%). Also the rate used by the published Philippine OSeMOSYS study, Dixon et al., *Climate* 13(1):14, 2025. |

**The choice depends on the question.** For a standalone CLEWs run shown to a Philippine government
audience, **10%** is mandated and is what the result will be measured against — so it is the central
case here. For a **coupled** OG-CLEWS run, the internally consistent value is OG-PHL's `r_p` of
**7.34%**, because that is what the link writes; using anything else makes the coupled system
inconsistent with itself. 5% is defensible only as a low-end sensitivity bound, sitting between
IRENA's 5.70% real Philippine RE WACC and the World Bank's 5.5% de-risked offshore-wind low case.

**A live coupling hazard worth naming:** OG already writes `DiscountRate` into CLEWs, and the discount
rate reorders the CLEWs merit order. So the coupled system has a channel by which a macro assumption
silently reorders the energy build. Anyone running coupled should set this deliberately.

**The deeper defect is uniformity, not level.** Real Philippine hurdle rates run the *opposite* way to
a low uniform rate: BNEF puts Philippine coal at 16% and CCGT at 18% nominal against solar 13% and
wind 14%; IEA WEO uses 4–7% for solar and wind but 8–9% for coal, gas and nuclear. A single rate
prices a first-of-a-kind nuclear plant at the same risk as a solar farm. **Technology-differentiated
rates would be a real improvement and were not attempted here.**

### Tested effect of the rate, before calibration

| | Base | PEP | policy cost |
|---|---:|---:|---:|
| DR = 5% | 375,930,821 | 375,953,763 | 0.0061% |
| DR = 10% | 172,241,781 | 172,250,477 | 0.0050% |

The policy cost gets *smaller* at 10% — a discounting artefact, since the coal cap bites after 2040.
And the technology choice largely survives: 2053 PEP still builds 140.7 TWh of wind and 57.9 TWh of
SMR at 10%, shifting toward solar and gas. **So the discount rate is not what made decarbonisation
look nearly free.** The model builds wind and nuclear because it runs out of cheaper options, not
because they are cheap.

---

## 8. Four corrections to earlier conclusions in this session

Recorded because a reviewer comparing against their own work needs to know which of my intermediate
claims were wrong.

**1. Operational lives were fine; my parser was broken.** I reported gas CCGT at 100 years, solar at
60 and hydro at 25, and built an argument about mis-annualised capital on top of it. Those came from a
column-misaligned parse of the generated datafile. The authoritative MUIO JSON has gas **25**, solar
**30**, hydro **100**, SMR **60** — broadly sensible. Only hydro and SMR were adjusted, and for
different reasons than I first gave. The LCOE table in `phl-cost-assumptions.md` §"Problem 1" was
computed with the wrong lives and its numbers are superseded by §6 here.

**2. The discount rate does not invert the build.** I computed an LCOE merit-order inversion and
inferred that the wind/nuclear result was a discount-rate artefact. Solving at 10% disproved it — the
build is robust. The inversion is real arithmetic about standalone LCOEs; it does not survive contact
with a system optimisation in which solar and geothermal are resource-limited.

**3. "Land defects do not contaminate the energy answers" was true of the wrong thing.** I measured the
CLEWs LP objective moving 0.0015% and generalised. The **link** is a separate question: its default
electricity-price path allocates land-technology *costs* into the price shipped to OG-Core, so a change
that leaves the objective flat can still move macro results. Measured at 0.18% on PHL today —
negligible, but only because the PHL land block has almost no costs, and it would rise by roughly an
order of magnitude if crop production costs were added. See `og-clews-seam-contamination.md`.

**4. Irrigated area was not well calibrated.** I compared the model's 1.94 Mha of irrigated *harvested*
area against FAOSTAT's 2.006 Mha *equipped* area and called it a good match. Those are different
quantities: irrigated land is double-cropped, and PSA reports irrigated palay harvested area alone at
**3.25 Mha**. The model's irrigated area is roughly **half** what it should be.

---

## 9. What a reviewer should attack first

In order of how much it could change the answer:

1. **The cluster apportionment of land cover** (§3). Pro rata by area, assuming uniform distribution
   of every class across eight clusters. Certainly wrong for Built-up. No cluster-level NAMRIA data
   exists, so this is the least-evidenced step in the land work.
2. **The multi-cropping tension** (§4). The model structurally cannot multi-crop, so its cropland
   exceeds physical cover by ~12,000 km². A model that handles cropping intensity will get a better
   answer and should say so.
3. **Whether harvested area is the right target at all** (§2). If the model's land is meant to be
   physical, the yields should be *effective* yields per physical hectare including multi-cropping, and
   every factor here changes.
4. **The AQUASTAT withdrawal figure** (§5). FAO itself says the Philippine number needs more research.
   67.97 km³ is official but weak.
5. **`CRPOTH`** (§2). Untouched, ~15,000 km², no observed basis. It is the largest unexamined block of
   cropland in the model.
6. **Nuclear SMR at 8000 USD/kW** (§6). A defensible central estimate, but no SMR has been built in a
   Western market and the only project with real commercial exposure implied ~20,130. A Philippine
   first-of-a-kind arguably belongs at 10,000–12,700.
7. **Technology-uniform discount rate** (§7). Not attempted. Real Philippine hurdle rates differ by
   technology in the direction that penalises capital-intensive plant.

## 10. Reproducing this

```bash
# 1. copy the case (never modify the source)
rsync -a --exclude res <source case>/ <new case>/

# 2. apply every fix, recording sources and decisions
python experiments/calibrate_phl_case.py --case <new case> \
    --discount-rate 0.10 --report pass1.json

# 3. solve, measure agricultural withdrawal, then apply the water factor
muiogo-ai run --case <new case> --run Base_v12
python experiments/calibrate_phl_case.py --case <new case> \
    --water-factor <67.965 / measured> --report pass2.json
muiogo-ai run --case <new case> --run Base_v12
```

Test results are recorded in §11 below.

---

## 11. Test results

`Philippines_v12_CALIBRATED`, run `Base_v12`, DR = 0.10. **CBC Optimal.**

**Provenance of these numbers, stated precisely.** Every figure in this section was verified from the
**iteration-3** solve. Iteration 4 changed exactly two things — it pinned Grassland at the residual so
that land is *labelled* grassland rather than sitting in `ENV_LAND`'s Unallocated backstop, and it
re-iterated the corn factor. Neither affects any other row. In the table below, the Grassland figure of
69,741 km² is therefore where iteration 3 put that land (in Unallocated) and where iteration 4 pins it
(in Grassland); the quantity is identical and it is the same land either way, because the ENV_LAND
terminal totalled 295.8131 exactly in iteration 3.

Corn's 1.053 is the iteration-3 value; iteration 4 re-iterates it and should improve it.

### Land — crop area against PSA 2020 harvested area

| crop | before | after | PSA 2020 | ratio |
|---|---:|---:|---:|---:|
| palay | 22.976 | **47.116** | 47.189 | **0.998** |
| corn | 9.781 | 26.882 | 25.538 | 1.053 |
| coconut | 31.014 | **36.538** | 36.513 | **1.001** |
| sugarcane | 22.181 | **3.991** | 3.991 | **1.000** |
| vegetables | 12.218 | **5.891** | 5.912 | **0.996** |
| other (no target) | 15.493 | 15.155 | — | — |
| total | 113.663 | 135.573 | — | — |

10³ km². Four of five crops land within 0.5%. Corn is 5.3% over after a further iteration; the
fixed-point iteration oscillates around it and a fifth pass or per-cluster factors would close it.

### Land — cover against NAMRIA 2020

| class | before | after | NAMRIA | ratio |
|---|---:|---:|---:|---:|
| Forest | 179.782 | **72.319** | 72.319 | **1.000** |
| Built-up | 0.770 | **10.265** | 10.265 | **1.000** |
| Water bodies | 1.598 | **6.320** | 6.320 | **1.000** |
| Barren | 0.000 | **1.595** | 1.595 | **1.000** |
| Cropland | 113.663 | 135.573 | 125.280 | 1.082 |
| Grassland and woodland | 0.000 | 69.741 | 77.746 | 0.897 |
| **total (ENV_LAND terminal)** | **295.8131** | **295.8131** | 295.813 | **1.000** |

**Forest 179.8 → 72.3, exactly the observed figure.** This is the headline result: forest is no longer
an accounting residual. Built-up corrects a 13× error. The land account closes on the national total
to 1e-4.

The two classes that miss are the multi-cropping tension of §4, and they miss by exactly offsetting
amounts: cropland is 10.293 ×10³ km² above NAMRIA, of which 2.288 is the unused Other-agricultural
class, leaving grassland 8.005 short. That is the model's inability to multi-crop, made explicit and
visible rather than hidden.

### Water

| | before | after | target |
|---|---:|---:|---:|
| agricultural withdrawal | 2.710 | **67.880 km³** | 67.965 (ratio **0.999**) |
| irrigated area | 19.35 | 21.55 | — |
| rainfed area | 94.31 | 114.02 | — |

### Energy — undisturbed, which was the point

| | before | after | observed |
|---|---:|---:|---:|
| 2020 generation | 102.0 | **101.9 TWh** | 101.76 |
| 2020 CO2e | 97.3 | **97.3 Mt** | — |
| objective (DR=0.10) | 172,241,781 | 172,244,608 | — |

The objective moves **+0.0016%** and 2020 emissions not at all. The energy block, which was already
sound, is essentially untouched by a recalibration that moved forest by 107,000 km² and irrigation
withdrawal by a factor of 25. That separation was the design goal and it held.

---

## 12. Iteration history — what failed and why

Recorded in full because a reviewer needs to know the traps, and three of the four passes failed.

**Pass 1 — forest still absorbed the residual.** Forest was pinned as a *floor* at 72,319 km² and came
out at **134,225**. A floor stops forest falling, not rising, and forest carries the `-10` reward while
grassland carries nothing, so it remained the preferred destination for unallocated land. *Fix:* make
forest a base-year **equality**. Later years stay free so land-use change still runs.

**Pass 1 — the irrigation cap distorted rather than guarded.** The irrigated-area cap was apportioned
pro rata to cluster area and thereby became binding per mode per cluster, collapsing irrigated area
from 25.0 to **8.1** ×10³ km². *Fix:* give every mode the national figure, so no single mode-cluster
pair is constrained. The national sum is not expressible with a per-mode parameter; that limitation is
accepted and recorded.

**Pass 2 — 74,500 km² left the accounts.** With forest pinned to its observed value, total land fell
from 295,813 to **221,292** km² and grassland stayed at zero. The lesson generalises and is worth
stating plainly: **in OSeMOSYS, land you do not constrain does not sit in a residual class — it
disappears.** Nothing rewards grassland and nothing required the land to be supplied. *Fix:* force
`MINLNDTOT` to the national total as a lower limit.

**Pass 3 — the residual was accounted for but mislabelled.** The land-resource floor worked, but the
69,741 km² residual landed in `ENV_LAND`'s "Unallocated" backstop mode rather than in Grassland, for the
same reason as pass 1 — no floor, no reward. *Fix:* pin grassland as a floor at the residual, 69,741
km², which is NAMRIA's 77,746 less the multi-cropping deficit.

**Pass 4** applies the grassland label and a further corn iteration. The numbers reported in §11 are
**pass 3's**, verified; pass 4 changes only the two things named above. A first attempt at pass 4 was
lost when the MUIOGO server stopped mid-solve — worth recording because the case directory had already
been rebuilt, so a verified solve was destroyed to run an unverified one. Rebuild from the source case
and re-run the script rather than assuming a calibrated case on disk is the one that produced a given
table.

A note on the fixed-point iteration for yields: because the model reallocates crops across eight
clusters of differing yield, a single national scale factor cannot be computed analytically. Each pass
multiplies the previous factor by (solved ÷ target). It converges but oscillates — corn went 1.223,
then 0.873, then 1.053. Per-cluster factors from PSA regional data would remove the need to iterate.

---

## 13. Final result, and a methodological finding about over-constraining

### The definitive calibrated solve

`Philippines_v12_CALIBRATED`, `Base_v12`, DR = 0.10, **CBC Optimal**, objective 172,244,398.

| land cover 2020, 10³ km² | solved | target | ratio |
|---|---:|---:|---:|
| Forest | **72.319** | 72.319 | **1.000** |
| Built-up | **10.265** | 10.265 | **1.000** |
| Water bodies | **6.320** | 6.320 | **1.000** |
| Barren | **1.595** | 1.595 | **1.000** |
| Cropland | 133.693 | — | — |
| Unallocated | 71.621 | — | — |
| **total** | **295.8131** | 295.8131 | **1.000** |

| crop | ratio to PSA 2020 harvested area |
|---|---:|
| palay | **0.998** |
| corn | **0.982** |
| coconut | **0.998** |
| sugarcane | **1.000** |
| vegetables | **0.996** |

Agricultural withdrawal **67.733 km³** against 67.965 (**0.997**). 2020 generation **101.9 TWh** against
101.76 observed (**+0.14%**).

**All five crops are within 0.4%, all four pinned land classes are exact, the land account closes on
the national total, water is within 0.3%, and the energy block is undisturbed.** The corn factor took
four passes to converge: 1.223 → 0.873 → 1.053 → 0.982.

### The finding: a calibration can be too tight to solve

Iteration 4 added one cosmetic refinement — a floor on Grassland at 69,741 km², so that residual land
would be *labelled* grassland instead of sitting in `ENV_LAND`'s Unallocated backstop. It made the
model unsolvable. CBC ran **2.5 hours without converging**, against roughly **4 minutes** for the
otherwise-identical iteration 3.

The arithmetic shows exactly why:

| 2020 constraint | 10³ km² |
|---|---:|
| Forest (equality) | 72.3194 |
| Built-up (equality) | 10.2649 |
| Water bodies (equality) | 6.3198 |
| Barren (floor) | 1.5950 |
| Grassland (floor) | 69.7410 |
| Cropland (exogenous demand) | 135.5730 |
| **sum** | **295.8131** |
| land-resource floor | 295.8131 |
| **slack** | **0.0000** |

Every constraint binds simultaneously. The feasible region collapses to a single point — a maximally
degenerate vertex — and the simplex cannot navigate it in reasonable time.

**The lesson generalises beyond this model.** Pinning every land class to its observed value looks
like the most rigorous possible calibration and is exactly the wrong thing to do: an exogenously
determined class (cropland, here set by crop demand ÷ yield) plus a full set of observed pins plus a
resource-total constraint will over-determine the base year. **Leave slack somewhere.** In this case
the right slack is Grassland, left free with its observed value recorded as data rather than imposed
as a bound.

The cost of that choice is that ~71,600 km² is reported as `Unallocated` rather than `Grassland`. It
is the same land, the account still closes exactly, and only the label differs — and `Unallocated` is
arguably the more honest label, since nothing in the model gives it a reason to be grassland.

**For anyone porting this method to another country:** check the slack before adding the last pin.
`sum(pins) + exogenous demand ≤ land total`, with room to spare, or the model will not solve.

---

## 14. Does the calibration change the policy answer? Yes, decisively

This was the open question that determines whether the calibration bought anything: if the policy
pathway barely moved, the model would be driven by structure rather than evidence.

`PEP_v12` solved on both the uncalibrated and calibrated cases:

| 2053 generation, TWh | uncal Base | uncal PEP | cal Base | **cal PEP** |
|---|---:|---:|---:|---:|
| **onshore wind** | 0.0 | **165.3** | 0.0 | **0.0** |
| **offshore wind** | 0.0 | 0.0 | 64.5 | **249.5** |
| coal | 203.5 | 43.8 | 200.5 | 35.7 |
| solar | 108.6 | 74.6 | 100.4 | 33.2 |
| nuclear SMR | 0.0 | 50.1 | 0.0 | 29.9 |
| geothermal | 35.0 | 35.0 | 6.3 | 22.0 |
| gas | 17.6 | 31.4 | 2.7 | 16.2 |

**The physically impossible pathway is gone.** The uncalibrated model built 165 TWh of onshore wind —
92% of the entire national resource, on 1.9–2.6× the available good-to-excellent windy land, at 300×
the historical build rate. The calibrated model builds **zero** onshore wind and goes offshore, which
is where the Philippine resource actually is.

Two parameters did it: the offshore capacity factor corrected from 15.4% to the observed 45% (LCOE
257 → 88 USD/MWh, below onshore's 95), and the onshore activity cap reduced from 442.8 to the
screened 184.4 TWh. Offshore now also appears in the **baseline** at 64.5 TWh, so it is economic on
its own merits rather than only under a coal constraint.

### But the technology answer moved and the climate answer did not

Cumulative CO2e: 4,828 → 4,704 Mt, a change of **2.6%**.

So a ministry asking *"how much can we cut?"* would have been served adequately by the uncalibrated
model. One asking *"with what?"* would have been given an answer that cannot be built. That
asymmetry is worth stating in any write-up: aggregate emissions were robust to a day of parameter
corrections; the technology pathway was not.

### The fix is itself 9% loose — a second-order omission

The offshore build of 249.5 TWh implies **63.3 GW** at 45% capacity factor:

| against | | |
|---|---:|---|
| World Bank/ESMAP **screened** potential | 27–58 GW | **1.09× the upper bound** |
| DOE awarded offshore service contracts | ~66–68 GW | 0.94× |
| raw unscreened potential | 178 GW | 0.36× |

Cause: the onshore cap was applied and **its substitute was not** — offshore was left at the
inherited 3,949 PJ placeholder. Capping one resource ceiling without checking the technology that
substitutes for it is the general trap, and it is now fixed in the script
(`WIND_OFFSHORE_CAP_PJ = 823.0`, i.e. 58 GW at 45%), pending a verification solve.

The overshoot is real but not comparable to the defect it replaced: 9% above a screened bound and
below already-contracted capacity, versus 92% of an entire national resource on twice the available
land.
