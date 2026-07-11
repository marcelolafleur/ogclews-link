# New-channel feasibility — exhaustive exploration

> ⚠️ **v6-ERA — RETIRED 2026-07-11.** v6 is dead; **v9 (`Philippines_v9`) is the only scenario, ever.**
> Every CLEWS data reference / number below is v6 and **VOID — do not use or cite.** The v-agnostic
> economic/coding conclusions were carried into the live v9 deliverable
> [`channel-space-map.md`](../channel-space-map.md); anything data-specific must be re-verified on v9.
> Kept only as a dated audit trail.

**Date:** 2026-06-18 · **Branch:** `channel-exploration` (off `deployment-framework`) · **Scope:** five
brainstormed channel ideas (LDC graduation, household cooking pollution, remittances vs diaspora bonds,
precipitation/temperature, crop production/food prices), assessed against the *actual* CLEWS and OG-Core/OG-PHL
structures on disk, plus a web data/literature pass per idea.

**Method:** (1) mapped the channel framework + every existing channel's OG entry point; (2) read the live CLEWS
`v6-Base`/`v6-PEP` outputs and the OG-PHL baseline (`runtime.build_baseline`) to see what signals/primitives
actually exist; (3) ran targeted extractions on the CLEWS files to test whether a base→reform signal is present
for each idea; (4) verified OG-Core primitives in the installed package + `ogphl_default_parameters.json`; (5)
ran five web-research sub-agents for external data availability and modeling precedent. Findings below cite the
evidence. **No trunk code was changed** — this branch holds only this document.

---

## TL;DR — the one organizing finding

**The OG side is rich and already wired for almost all of these. The binding constraint is the CLEWS *signal*
side.** OG-Core/OG-PHL exposes native hooks for remittances, foreign-debt financing, food as a 35.7%-share good,
agricultural TFP, heat-labor productivity, and mortality — so the *economics* of every idea has a home. What
varies enormously is whether the live CLEWS (`v6-Base`→`v6-PEP`) actually *emits a differential signal* to drive
the channel.

| # | Channel idea | OG entry point | OG-side ready? | CLEWS signal in PEP? | External data? | Verdict |
|---|---|---|---|---|---|---|
| 3 | **Remittances vs diaspora bonds** | `alpha_RM_*`,`g_RM`,`eta_RM` / `world_int_rate`+`zeta_D`→`alpha_I` | ✅ native, **already calibrated** (7.2% GDP) | ❌ none (financial, via investment channel) | ✅ excellent (BSP, KNOMAD) | **HIGH** — buildable now as a *transition-financing* channel |
| 5 | **Crop production / food prices** | `tau_c[Food]`, `Z[NatRes]`, `c_min[Food]` | ✅ Food = **35.7%** good; plumbing exists | ❌ `PHL_LND_CRP=0` (crop not populated) | ✅ excellent (IRRI, IFPRI, FAO) | **HIGH (OG) / build external** — climate-crop → food wedge |
| 2 | **Household cooking pollution** | extends `health` channel (`rho`, `e`) | ✅ health channel exists | ⚠️ techs exist but **inert + mis-calibrated** | ✅ good (GBD HAP, WHO) | **MEDIUM** — needs cooking recalibration + clean-cooking scenario |
| 4 | **Precipitation / temperature** | `e` (heat-labor), `Z` (crop), `rho`, `delta` | ✅ all hooks exist | ❌ climate is exogenous; base=reform | ✅ abundant (CCKP, ILO, IRRI) | **MEDIUM** — external *absolute* shock; honesty constraint |
| 1 | **LDC graduation** | tariff/`tau_c` wedge, `world_int_rate`, `alpha_G`/`alpha_T` | ✅ hooks exist | ❌ none | ✅ (UN DESA, WTO) | **LOW for PHL** (not an LDC) / **HIGH** if re-aimed at a real LDC |

**Two channels that weren't on the list but fell out of the data — and are stronger CLEWS fits than three that
were:**

| Bonus | What | CLEWS signal in PEP? | Verdict |
|---|---|---|---|
| **A** | **PM2.5 sharpening of the existing health channel** (swap CO2e→PM2.5 dose proxy) | ✅ PM2.5 tracked, **falls ~15–21%** in PEP | **QUICK WIN** — more honest *and* materially different signal |
| **B** | **Water scarcity / cost channel** | ✅✅ **strongest** live non-energy signal: power-sector water **+5–12×** in PEP | **EXPLORE** — most CLEWS-native *new* channel available |

---

## Foundation 1 — what the live CLEWS actually emits

The integration's CLEWS is a full **Climate-Land-Energy-Water** OSeMOSYS model (not energy-only as a first glance
suggests). `TotalAnnualTechnologyActivityByMode` carries **132 technologies** across AGR (9), water DEM (4),
household HOU (6), INDU (15), LND (7), MIN (1), POW (30), PRO (15), SER (7), TRA (37). Emissions are tracked for
**both `CO2e` and `PM2_5`** (`signals.emissions_by_year` only reads CO2e today — `signals.py:118`).

But "has a technology" ≠ "has a usable base→reform signal." Tested each idea's signal directly:

| CLEWS signal | Base | PEP | Differential? | Implication |
|---|---|---|---|---|
| Power-sector water (`PHL_DEM_PWR_SUR_WAT`, 2050) | 38.8 | 191.4 | **×4.9** | transition has a large water footprint — real, novel signal |
| Power-sector groundwater (`PHL_DEM_PWR_GWT_WAT`) | 2.4 | 28.5 | **×12** | "" |
| Total PM2.5 (2050) | 161.2 | 136.7 | **−15%** (−21% at 2040) | health co-benefit, transport-driven |
| Total CO2e (2050) | — | — | **×0.62** | power-driven; what `health` reads today |
| Cooking biomass (`PHL_HOU_COOK_BIOM`) | 236.7 | 236.7 | **none** | cooking untouched by this reform |
| Cooking coal (`PHL_HOU_COOK_COAL`) | = | = | **none** | "" |
| Cooking electric (`PHL_HOU_COOK_ELE`) | 137.4 | 83.6 | −39% (**wrong sign** for a clean story) | cooking block is stylized |
| Cooking-attributable PM2.5 | 0.04 | 0.04 | **none** | trivial; PM2.5 here is ~100% transport |
| Crop land (`PHL_LND_CRP`, all years) | **0** | **0** | n/a | crop production not populated |
| Temperature / precipitation | — | — | **n/a** | exogenous input, identical base=reform |

So the only **live, reform-differential, non-energy-price** CLEWS signals are: **emissions (CO2e and PM2.5)**,
**power capex** (already used by the investment channel), and **water demand**. Cooking, crop, and climate
either don't move or aren't represented in this scenario pair.

## Foundation 2 — what OG-Core/OG-PHL actually exposes

Verified against the installed `ogcore` and `ogphl_default_parameters.json`. The model is an **open-economy OG**
with far more native machinery than the existing six channels use:

- **Remittances are first-class and already on:** `alpha_RM_1 = alpha_RM_T = 0.072`, `g_RM = 0.03` in the PHL
  baseline (OG-Core ships these at 0; OG-PHL overrides to the real ~7–8% of GDP). `eta_RM` is the S×J incidence
  matrix (who receives). Remittances enter the household budget as an untaxed lump-sum transfer distributed by
  `eta_RM`; labor-supply response is the pure income effect (no `chi_n` edit needed).
- **Foreign financing exists:** `world_int_rate_annual = 0.04`, `initial_foreign_debt_ratio = 0.2`, `zeta_D`
  (foreign share of *new* gov debt). The natural home for diaspora bonds.
- **Food is the 2nd-largest consumption good.** `alpha_c` from `ogphl.input_output`: **Food 0.357**, Energy &
  water **0.014**, Non-durables 0.021, Durables 0.103, Services 0.505. A food-price wedge has ~**25×** the
  consumption weight of the energy wedge. `tau_c` is good-indexed `(T+S, I)`; `c_min` is per-good `(I,)` and
  currently all-zero (`runtime.py:62`) — so a Stone-Geary food floor is a one-line set.
- **Agriculture is sector M=0** ("Natural Resources" = rice/maize/veg/root/fish/forestry/mining/water, per
  `_calibration.py:11`) with its own TFP `Z (T+S, M)`. Food processing sits in Manufacturing M=3 (`afood`,`abeve`).
- **Labor / demography / capital:** `e (T,S,J)` earnings ability, `rho (T+S,S)` mortality, `omega` population,
  `chi_n` labor disutility, `delta_annual` depreciation, `imm_rates`, `zeta`/`tau_bq` bequests — all present.

The channel pattern to extend (`framework.py:44` `Channel` ABC → `apply()`/`validate()` → `register()`;
experiments in `experiments.py`; transform tests in `tests/test_channels.py`) is clean and well-documented.

---

## 1 · LDC graduation

**Verdict — LOW for the PHL instance; HIGH for the framework applied to an actual graduating LDC.** The
Philippines is not, and has never been, a Least Developed Country (it's a World Bank lower-middle-income country;
UN DESA uses it as a *non-LDC comparator*). There is no trigger to calibrate and no CLEWS hook. The live
graduating cohort — **Bangladesh, Nepal, Lao PDR (all 24 Nov 2026)**, then Cambodia/Senegal/Solomon Islands — is
where the channel would be meaningful.

- **Mechanism on graduation:** (a) loss of trade preferences (EU EBA → standard GSP; preference-margin loss
  ~10% in clothing) → an export-weighted tariff increase (Bangladesh +8.9 pp gross, ~4–6 pp utilization-weighted;
  ~US$6 bn / ~6% of graduating-LDC exports); (b) "dual graduation" → loss of IDA concessional finance, higher
  borrowing cost; (c) ODA decline (DAC 0.15–0.20% GNI LDC target); (d) loss of TRIPS pharma flexibilities + ~130
  ISMs. Smooth-transition window phases this over 3–6 yr.
- **OG entry point:** trade shock → tariff-like wedge on a tradable / `tau_c` (lossy in a single-good map; the
  real shock is concentrated in EU garments); financing → `world_int_rate_annual` (+50–150 bps phased) +
  `initial_foreign_debt_ratio`; aid → `alpha_G`/`alpha_T`; (optional) lost TA → small `−Z` drift.
- **Modeling precedent:** WTO–EIF (2022) *Trade Impacts of LDC Graduation* (partial-equilibrium, WITS SMART);
  Bekkers & Cariola (2022/24); GTAP/CGE Bangladesh (GDP −1.53%, RMG −11.8%).
- **Data:** UN DESA CDP indicator values + Handbook (free); WTO/UNCTAD preference & tariff data; OECD DAC ODA;
  World Bank IDA rules. All free.
- **Blocker:** undefined for PHL — ship it (if at all) as an *inactive/not-applicable* channel for PHL and
  document why; or re-point the framework at Bangladesh/Nepal, where it's well-precedented and fully calibratable.

## 2 · Household cooking pollution

**Verdict — MEDIUM. Feasible and data-rich, but gated on the CLEWS energy side, not the health side.** The
existing `health` channel (age-specific mortality via `disease_pop` + morbidity on `e`) is exactly the right
shape — household air pollution (HAP) is the *same disease set* as ambient PM2.5 with a *different, more bimodal*
age skew (heavy under-5 via LRI/neonatal **and** elderly cardiovascular). So this should **extend the health
channel as a parallel pollution sub-channel**, not be a new channel.

The blocker is the cooking block: in `v6-PEP` biomass/coal cooking are identical base→reform, electric cooking
*falls*, and cooking-attributable PM2.5 is ~0.04 of ~161 kt (the model's PM2.5 is ~100% transport). The block is
also mis-calibrated vs reality — the Philippines is heavily LPG (~LPG 35–40% / biomass 45–55% / charcoal ~10–13%
/ electric ~2–3%; ~half the population still on solid fuels), not ~100% coal+biomass.

- **What it needs:** (a) recalibrate the cooking block to realistic fuel shares; (b) author a **clean-cooking
  transition scenario** (solid-fuel households → LPG/electric over time); (c) extend the health channel — drive
  it off the **solid-fuel cooking share** mapped to a HAP personal-PM2.5 exposure (not CO2e, not the tiny ambient
  cooking PM2.5), with a **HAP-specific age profile** `h_HAP(s)`.
- **Double-counting:** GBD estimates HAP and ambient PM2.5 jointly; add HAP only as *incremental indoor exposure
  of the solid-fuel sub-population* or the same deaths get counted twice.
- **Data:** IHME GBD "Household air pollution from solid fuels" (`rei_id` ~87 — verify in GBD Results tool,
  `location_id 16`); WHO GHO cooking-fuel DB; World Bank `EG.CFT.ACCS.ZS`; DHS PHL; BAR-HAP / ESMAP valuation
  tools. PHL HAP burden ~order 10⁴ deaths/yr and *declining* as access rises.
- **Feasibility verdict:** the health-channel extension is low-risk and well-supported; the channel is only
  meaningful after the (non-trivial) CLEWS cooking-block recalibration + clean-cooking scenario.

## 3 · Remittances vs diaspora bonds

**Verdict — HIGH. The single most "ready" idea on the OG side; the only catch is the CLEWS link is
financial-thematic, not biophysical.** OG-Core ships native, verified machinery for *both* arms, and the PHL
baseline already runs remittances at **7.2% of GDP** — so this is a parameter experiment, not new core code.

- **The "vs" experiment:** same diaspora resources either flow to **households** (remittances — support
  consumption, reduce labor supply via income effect, risk RER appreciation/Dutch disease) or to the
  **government** as **diaspora bonds** (external borrowing funding public investment, repaid at a possibly
  below-market "patriotic discount").
  - *Remittances arm:* set `alpha_RM_1`/`alpha_RM_T` (≈0.073), `g_RM`, and shape `eta_RM` to working-age,
    lower-income households. Note OG-Core *subtracts* aggregate `RM` in the resource constraint while adding it
    to household budgets — it's a **redistribution + labor-supply** device, not a free windfall (key for reading
    welfare results honestly).
  - *Diaspora-bond arm:* raise `zeta_D` / `initial_foreign_debt_ratio` and route proceeds to **`alpha_I`** via
    the *existing* investment channel (whose `alpha_I` home is the audit-confirmed F3b); set the tranche rate
    below `world_int_rate_annual` for the patriotic discount (a sensitivity axis — PHL has no true diaspora-bond
    precedent, only retail $-bonds, ~US$1.6 bn debut 2021).
- **The CLEWS tie:** Arm B finances the **transition capex** the investment channel already reads from CLEWS
  power capex. So frame the whole thing as *"financing the energy transition: household consumption support vs
  diaspora-funded public investment."* That makes it CLEWS-*relevant* (capex requirement) without pretending
  there's a biophysical remittance signal.
- **Data:** BSP OF remittances (PHL 2024 personal remittances **US$38.3 bn, 8.3% of GDP**); World Bank
  KNOMAD/WDI; diaspora-bond precedents (Israel, India RIBs/IMDs, Nigeria 2017). Ketkar & Ratha is the canonical
  reference.
- **Blocker:** none structural — only the honest scoping (financing story, not energy-demand driver) and the
  reduced-form bond representation (`zeta_D`/world-rate, no distinct tranche object).

## 4 · Precipitation / temperature

**Verdict — MEDIUM, and *different in kind*.** All the OG hooks exist (`e` for heat-labor, `Z` for crop, `rho`
for heat-mortality, `delta` for disasters), the data is abundant and PHL-applicable, and the damage functions are
standard. But **CLEWS treats climate as exogenous and applies the same physical climate to base and reform**, so
there is **no reform-differential climate signal**. This can only be an **external-data channel** delivering an
*absolute level* shock applied **identically to baseline and reform** — honest framing is *"both futures are X%
poorer under warming,"* never *"PEP causes/avoids this climate damage."* That partly breaks the framework's
read-a-differential pattern and must be labelled accordingly.

- **PHL magnitude:** +1.8–2.2 °C by ~2050 (PAGASA); wetter wet-season / drier dry-season (bidirectional, not a
  scalar); disaster losses ~1.2% GDP/yr today rising toward 7% by 2030 (tail); rice ~−10%/°C night-temp (IRRI).
- **OG entry points & sketch:** `e` ← ILO "Working on a Warmer Planet" hours-lost (−2% to −5% for exposed worker
  types at +2 °C); `Z[NatRes]` ← `Z·(1−γ·ΔT)`, γ≈0.06–0.10/°C; `delta_annual` ← +1.2%→ disaster increment;
  `rho` ← heat deaths **via the health channel**. Minimal viable: `e` + `Z[NatRes]` (best-identified, least
  double-counting).
- **Citations:** Dell-Jones-Olken (2012), Burke-Hsiang-Miguel (2015, *growth*-rate effect), ILO (2019),
  Kjellstrom Hothaps, Nordhaus DICE. Note NGFS Phase-V chronic-damage function (Kotz-Wenz) was **retracted Dec
  2025** — use NGFS as a scenario *source*, not a settled damage function.
- **Data:** World Bank CCKP (PHL), ISIMIP, CMIP6/ESGF, PAGASA, Climate Impact Lab, ILO annex. All free.
- **Blockers:** no CLEWS differential (the central one); double-counting with the health channel (heat
  mortality) and *within* the climate channel (aggregate GDP elasticities already embed labor+ag+capital — pick
  bottom-up sectoral **or** top-down, not both); level-vs-growth framing diverges by an order of magnitude over
  OG's horizon; must use an SSP/RCP consistent with the PEP energy pathway.

## 5 · Crop production / food prices

**Verdict — HIGH on the OG side, LOW on the CLEWS-signal side → build it now as an external climate-crop → food
wedge; do not gate it on a CLEWS crop module.** Food is good I=0 at a **35.7%** share with good-indexed `tau_c`
and Stone-Geary `c_min` already in OG-Core's household problem, and agriculture is sector M=0 with its own `Z` —
so a regressive, welfare-heavy food channel is a near drop-in parallel to the energy channel. But `PHL_LND_CRP=0`
across all years: CLEWS emits **agricultural *energy demand*** (`PHL_AGR_*`, nonzero) but **not crop
production/yield/price**.

- **Why not wait for CLEWS:** the OSeMOSYS land tooling (`CLEWs_GAEZ`/GeoCLEWs on GAEZ v4 + FAOSTAT) produces
  agro-climatic *potential yield* and crop-water metrics — **not** actual production, land allocation, or prices.
  So even a populated `PHL_LND_CRP` would need an economic step to become a price, meaning the external-data step
  is unavoidable regardless. Build option (a) now; leave CLEWS-native crop coupling as a documented future
  extension, not a dependency.
- **OG entry point (ranked):** (1) **`tau_c[Food]` price wedge** — clones the proven `energy_price` plumbing;
  `tau_c[Food,t] = (1 + ε·ΔYield_t)^(−σ_pass) − 1` translating a climate yield loss (IRRI ~10%/°C, or an IFPRI
  IMPACT scenario) into a consumer-price rise (importer pass-through high, σ_pass≈0.5–1). (2) **`Z[NatRes]`
  ag-TFP shock** — the GTAP-canonical, more structurally honest route (price emerges endogenously, propagates
  through the I-O to food processing in M=3). (3) **`c_min[Food]`** — not the shock, the *regressivity
  amplifier*, calibrated from the food-poverty line + FIES decile gradient. A robust design runs (1) and (2) and
  compares.
- **PHL magnitude:** food ~35% of spending (≈37% at 2020 peak), strongly regressive; rice self-sufficiency ~77–82%
  (large importer → world-price pass-through dominant); price shocks 2008/2018/2023–24 (rice inflation ~20%);
  typhoons recurrent acute shocks (Kristine 2024: rice = 72% of ag losses). Yield-loss estimates span ~2–32% —
  treat as a **sensitivity range**, not a point.
- **Data:** PSA FIES (decile food shares), FAOSTAT + FAO GIEWS/FPMA (prices, imports), IFPRI IMPACT
  (climate-scenario yields/prices to 2050), IRRI (rice per-°C elasticity). All free.

---

## Cross-cutting / bonus findings

### Bonus A — sharpen the existing health channel: CO2e → PM2.5 (quick win)
`signals.emissions_ratio` drives the health channel off the **CO2e** ratio (`signals.py:122`), but PM2.5 is the
health-relevant pollutant, is already tracked in the same files, and moves *differently*: PEP CO2e/Base → **0.62**
(power-driven) vs PM2.5/Base → **~0.85** (transport-driven). Swapping the dose proxy to PM2.5 (filter
`e == "PM2_5"` in `emissions_by_year`) is a small, honest change that materially changes the health signal and
removes the "CO2 isn't what kills people" caveat the channel currently flags. Lowest-effort, highest-honesty
improvement found.

### Bonus B — a water scarcity / cost channel (the most CLEWS-native *new* idea)
The **single strongest non-energy base→reform CLEWS signal** is water: the PEP transition raises power-sector
water demand **×4.9 (surface)** and **×12 (groundwater)** by 2050, and shifts public water from groundwater to
surface. This is a genuine, large, reform-differential biophysical signal that *no current channel uses*. It maps
to the energy transition's water footprint — a real constraint in a typhoon/drought-exposed country. OG entry is
less clean than the others (water is inside the 1.4% "Energy & water" good; better routed as a cost-push on
`Z[NatRes]`/`Z[Electricity]`, or as water-infrastructure `alpha_I`), so it needs design work — but it is the most
defensible *CLEWS-driven* new channel on offer, and it wasn't on the brainstorm list.

---

## Recommendation — build order

1. **Bonus A (PM2.5 health proxy)** — hours, not days; pure honesty win; unblocks a better cooking story later.
2. **Remittances vs diaspora bonds** — highest OG readiness (native + pre-calibrated), clean experiment, ties to
   the existing investment channel as "how the transition is financed." Mostly a parameter + provenance exercise.
3. **Crop / food prices** — highest *welfare leverage* (35.7% good); build as external climate-crop → `tau_c[Food]`
   with `Z[NatRes]` as the structural alternative and `c_min[Food]` for regressive incidence.
4. **Climate temp/precip** — valuable but constrained to an honest *absolute-level* framing; start with `e`
   (ILO heat-labor) + `Z[NatRes]`; reconcile `rho` with the health channel before wiring it.
5. **Water channel (Bonus B)** — most novel CLEWS-native signal; needs an OG-entry design decision first.
6. **Household cooking pollution** — extends the health channel cleanly, but gated on CLEWS cooking-block
   recalibration + a clean-cooking scenario; do after the cooking block is fixed.
7. **LDC graduation** — not applicable to PHL; revisit only if the framework is re-aimed at a graduating LDC.

**What needs a solve to validate (hold for explicit go):** prototyping any of #2–#6 to a measured GDP/welfare
number requires an OG solve (minutes). The transforms themselves can be unit-tested without solving, following
the existing `tests/test_channels.py` pattern.

---

## Prototypes — built and tested (this branch)

All seven ideas (5 + 2 discovered) are now prototyped as real channels following the existing `Channel`
pattern: each a verified transform with guardrails, a transform-level test (no OG solve), an experiment, and
any needed signal reader. **`tests/test_channels.py`: 37 passed, 0 failed** (was 25). Magnitudes are
illustrative pending calibration — flagged in every `validate()`.

| Channel id | OG primitive(s) touched | Class (`channels.py`) | Experiment | Live-data check |
|---|---|---|---|---|
| `remittances` | `alpha_RM_1/T`, `g_RM`, `eta_RM` | RemittancesChannel | `remittances_boom` | baseline α_RM=7.2% verified |
| `diaspora_bonds` | `alpha_I`, `world_int_rate_annual`, `zeta_D` | DiasporaBondChannel | `diaspora_bond_finance` | finite issuance → SS tail clean |
| `food_price` | `tau_c[Food]`, `Z[NatRes]`, `c_min[Food]` | FoodPriceChannel | `food_price` | Food=35.7% good (alpha_c) |
| `climate_damage` | `e` (heat-labor), `Z[NatRes]` | ClimateDamageChannel | `climate_damage` | absolute-shock guardrail |
| `water_stress` | `Z` cost-push / `alpha_I` | WaterStressChannel | `water_stress` | **water ratio 5.34× @2050** |
| `cooking_health` | `health_shock` (disease_pop) + bimodal HAP h(s) | CookingHealthChannel | `cooking_health` | **solid-fuel Δ +0.5% (inert, as predicted)** |
| `ldc_graduation` | `tau_c`, `world_int_rate`, `alpha_G` | LDCGraduationChannel | `ldc_graduation` | no-ops for PHL (not an LDC) |
| **Bonus A** (PM2.5 proxy) | `health` channel `pollutant=` option | HealthChannel + `emissions_by_year(species=)` | — | **PM2.5 0.85 vs CO2e 0.62 @2050** |

New signal readers (`signals.py`): `clews_activity_by_year`, `water_demand_ratio`, `cooking_solid_fuel_change`,
`emissions_by_year(species=)`. New concordance ports (`contract.py`): `food_good_index`, `agri_industry_index`.
New country flag (`country.py`): `is_ldc` (PHL = False → `ldc_graduation` no-ops).

**Validated on real CLEWS, end-to-end (not stubbed):** water `PHL_DEM_PWR` reform/base = **5.34× by 2050**
(strong live signal); cooking solid-fuel change = **+0.5%** (inert — the cooking block is untouched by PEP, as
the analysis found); PM2.5 ratio **0.85** vs CO2e **0.62** at 2050 (different enough that the PM2.5 dose proxy
materially changes the health signal).

**Honesty guardrails worth re-reading before any headline run** (each stated in-code in `validate()`):
`climate_damage` is an *absolute* shock with no CLEWS differential (must also hit the baseline, or it reads as
PEP-attributable — it isn't); `cooking_health` is *inert* until a clean-cooking scenario + cooking-block
recalibration exist; `food_price` is *external-data* driven (no CLEWS crop signal); `diaspora_bonds` is a
*reduced-form* of an external bond; `ldc_graduation` is *not applicable* to PHL.

**Still needs a solve (held for explicit go):** measuring the GDP/welfare effect of any experiment requires
`python -m ogclews_link run <experiment>` (an OG solve, minutes each).
