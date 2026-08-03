# How to improve the PHL CLEWs calibration — a tested recommendation

**Date:** 2026-08-03
**World:** `muiogoai` (installed) · `~/muiogoai/MUIOGO` detached at `928a13bb`
**Case:** `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC`, run `Base_v12` (CBC Optimal)
**Test case:** `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC_copy` — a sandbox copy; the original was
never modified.

## The one-paragraph version

The Philippine model's **crop demands are well calibrated** — rice 19.30 Mt against 19.29 observed,
maize 8.12 against 8.1, sugarcane 24.40 against ~24.4, coconut 14.49 against ~14.5. But its **crop
yields are GAEZ agro-climatic *potential* yields used as if they were observed *actual* yields**, so
the model grows the right amount of food on the wrong amount of land: rice on 2.30 Mha against 4.65
observed, maize on 0.98 against 2.58, while sugarcane sprawls over 2.22 Mha against 0.42. I applied a
per-crop yield-gap correction, re-solved, and **every corrected crop landed within 1–5% of observed
Philippine harvested area.** The fix is surgical — the objective moved 0.0015% and emissions not at
all. That is the highest-value calibration improvement available, and it is tested.

## Grade for the land–water domain

- **Calibration grade: Unacceptable** (land and water only; I did not assess the energy side)
- **Confidence: High** — every finding below is from the solved case or its generated input
- **Forcing profile:** clean. Of 153 flagged bound pairs, 131 are zero-pins for technologies absent
  in the base year (legitimate) and 22 are committed power-plant builds in 2021–2025 (good
  practice). **There is no forcing at all on land or water** — so the land outcomes are genuinely
  endogenous, and genuinely wrong. Nothing is being hidden by history-fixing.
- **Fitness:** unsuitable for any crop-specific, water, or land question. Conditionally suitable for
  energy-system questions, which the land errors barely touch (see the objective result below).

## Defect 1 — potential yields used as actual. FIXED AND TESTED.

`OutputActivityRatio` on the crop modes gives rice 6.2–8.6 t/ha and maize around 8 t/ha. Those are
Philippine *agro-climatically attainable* yields. Observed paddy is **4.15 t/ha** — the Philippine
rice yield gap is roughly 50%, and it is one of the best-documented in Asian agriculture. The model
assumes every farmer closes it.

Implied yields from the solve (output ÷ area), against observed:

| crop | model implied | observed | error |
|---|---:|---:|---|
| rice (RCP) | 8.40 t/ha | 4.15 | **2.0× too high** |
| maize (MZE) | 8.30 | 3.10 | **2.7× too high** |
| coconut (CON) | 4.67 | 4.00 | 1.2× high |
| sugarcane (SGC) | 11.00 | 58.0 | **5.3× too LOW** |
| vegetables (TOM proxy) | 4.50 | ~8 | 1.7× low |

Errors run in **both directions and roughly cancel in the total**, which is why the aggregate
cropland (11.37 Mha) looks plausible against ~12 Mha observed while every individual crop is wrong.
That is the classic right-aggregate-wrong-composition failure, and it invalidates anything
crop-specific, including irrigation withdrawals.

### The test

Scaled each crop's `OutputActivityRatio` by `model_area ÷ observed_harvested_area` (PSA 2020) —
4,800 records across 4 scenarios — and re-solved. **Optimal in 114 s.**

| crop | before | after | PSA 2020 target | after/target |
|---|---:|---:|---:|---:|
| coconut | 31.01 | 36.19 | 36.0 | **1.01×** |
| maize | 9.78 | 26.21 | 25.8 | **1.02×** |
| rice | 22.98 | 48.72 | 46.5 | **1.05×** |
| sugarcane | 22.18 | 4.20 | 4.2 | **1.00×** |
| vegetables | 12.22 | 7.00 | 7.0 | **1.00×** |
| other | 15.49 | 15.07 | no target | — |
| **total** | **113.66** | **137.40** | ~134.6 | 1.02× |

Areas in 10³ km². The 1–5% residuals are spatial: the model reallocates across the eight clusters,
which have different yields, so a single national factor lands close but not exact. One more
iteration, or per-cluster factors, would close it.

**Side effects — none worth worrying about.** Objective 375,930,821 → 375,936,578 (**+0.0015%**),
cumulative CO2e unchanged to four decimals, land closure still exact at 295.8131. So this correction
fixes agriculture without disturbing any energy result already in circulation.

## Defect 2 — the base-year land cover is never imposed. DIAGNOSED, NOT FIXED.

Forest is **179.78 ×10³ km² against 72.26 observed** (FAO FRA 2025: 7,226.39 kha). The yield fix
only moves it to 156.05 — still 2× observed. It is a separate defect with a separate cause.

The build reads a complete land-cover table —
`CLEWs-PHL/.../geospatial/summary_stats/PHL_LandCover_byCluster_summary.csv`, seven classes summing
to exactly 295,813.1 km² — and maps it (`clewsy.py:347`) to:

| class | area (10³ km²) | lower limit written? | model 2020 |
|---|---:|---|---:|
| Cropland | 43.37 | **no** — skipped | 113.66 |
| Forest land | 85.82 | **no** — skipped | 179.78 |
| Other agricultural land | **164.25** | **no** — skipped | **0.00** |
| Built-up land | 0.77 | yes | 0.77 ✓ |
| Water bodies | 1.60 | yes | 1.60 ✓ |
| Grassland & woodland | 0.00 (no data) | n/a | 0.00 |
| Barren | 0.00 (no data) | n/a | 0.00 |

`clewsy.py:410` reads `if col in ['Cropland', 'Forest land', 'Other agricultural land']: continue` —
deliberately leaving those three free so the optimiser can reallocate them over time. The
consequence is that **164,254 km², 55% of the country, is discarded** and forest absorbs the entire
residual. Only 2 of 7 classes are pinned; 8 mode-lower-limit rows exist in the whole model.

Two things are wrong here and they need separating:

1. **The concordance is too coarse.** `LCType10` — 55% of the national territory — is mapped to a
   single "Other agricultural land" bucket, and `LCType3/4/7/8` (grassland, barren) have no data at
   all. A land-cover product whose legend puts half a country in one class cannot calibrate a land
   model. Rebuild the concordance against a product with a usable legend (ESA CCI, Copernicus, or
   better, NAMRIA's national land cover).
2. **The base year should be pinned even if later years are free.** Leaving the margin free is a
   defensible *projection* choice; it is not a defensible *base-year* choice. Standard practice is to
   fix the base year to observed and let the transition optimise.

**Order matters:** do Defect 1 first. Pinning the base-year land cover *before* fixing yields would
have fought the demand ÷ yield requirement — the data's 43.37 ×10³ km² of cropland cannot produce
observed output at any plausible yield, so the model would have gone infeasible or forced forest to
collapse to ~15 ×10³ km². Yields first, then land cover.

## Defect 3 — water never binds. DIAGNOSED.

Every water commodity has a shadow price of essentially zero across all 34 years, before **and
after** adding 21% more cropland: `PHL_WTR_GWT`, `PHL_WTR_SUR`, `PHL_WTR_EVT`, `AGRWATPHL`,
`PHL_PUB_WAT` all at or below 4e-4. Water is free everywhere in a model whose reason for existing is
the land–energy–water nexus. Until some water constraint binds, the "W" in CLEWs is decorative here
and no water result means anything.

I did not diagnose the cause. It is the obvious next investigation after Defects 1 and 2.

## Recommended order of work

1. **Fix the crop yields** with per-cluster yield-gap factors from PSA CountrySTAT / FAOSTAT actual
   yields ÷ GAEZ potential. Tested above; expect crop areas within a few percent of observed. Cheap,
   safe, and it unlocks every agriculture and irrigation result.
2. **Rebuild the land-cover concordance and pin the base year.** Bigger job, needs a land-cover
   product with a real legend, and it is what makes the forest number — and therefore anything
   land-carbon or biodiversity — meaningful.
3. **Find out why water never binds.** Then the nexus is real.
4. **Solve `PEP_v12`.** Only `BASE` has ever been solved here, so there is no scenario contrast to
   test anything against.

Steps 1 and 2 together would move the land–water grade from Unacceptable to plausibly Acceptable.
Neither requires touching the energy side.

## Data sources for the fix

| what | source | note |
|---|---|---|
| actual crop yields and harvested area | **PSA CountrySTAT / OpenSTAT**, annual by crop and region | the authoritative national source; regional detail matches the cluster structure |
| cross-check | **FAOSTAT** QCL production/area/yield | consistent global series |
| potential yields already in the model | **GAEZ v4** via the CLEWs Global build | the *numerator* of the yield-gap ratio |
| forest area | **FAO FRA 2025**, PHL 7,226.39 kha | 72.26 ×10³ km² |
| national land cover | **NAMRIA** land cover, or ESA CCI / Copernicus | needed for Defect 2 |
| vegetables | the model uses a **GAEZ tomato proxy** — the build's own `KNOWN_LIMITATIONS.md` flags it | 1.22 Mha sat under "tomato" before the fix |

## What I did not do

- Did not assess the **energy** side; the grade above covers land and water only.
- Did not fix Defect 2 or 3.
- The yield factors used were **national single factors**, not per-cluster, which is why residuals
  are 1–5% rather than ~0.
- Observed yields and harvested areas were taken from PSA 2020 figures I did not re-download in this
  session; they should be re-pulled from CountrySTAT before any production use.
- The sandbox case `..._copy` (2.3 GB) still exists and holds the only yield-corrected solve. Kept
  deliberately — it is a unique result.
