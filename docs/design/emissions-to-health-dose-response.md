# Emissions → health: the dose-response as a country-agnostic channel method

How the health channel converts a CLEWS **sector PM2.5 emissions change** into a change in
**ambient-PM2.5-attributable deaths** — calibrated and per-country, not the naive 1:1. This is the
*method* (it travels to any OG country repo); the per-country numbers are lookups from global datasets.

## The chain — and why 1:1 is wrong
CLEWS outputs Δ(energy/power-sector PM2.5 emissions). The real link is two steps:
1. **emissions → ambient concentration.** The energy sector is only PART of ambient PM2.5 (residential,
   industry, transport, agriculture, windblown dust dominate in most countries). A naive "deaths scale
   1:1 with the sector's emissions" implicitly treats the sector as **100%** of ambient PM2.5 — the
   biggest error.
2. **concentration → deaths.** The concentration-response function (CRF) is **concave**, so a % change
   in concentration is NOT the same % change in deaths.

## The method (country-agnostic)
    deaths_change = total_ambient_PM2.5_deaths[country]      # GBD (we have this: PHL 43,951, 2023)
                    × M[country]
                    × emissions_change_fraction              # CLEWS: the sector's Δ (e.g. PHL -7.7%)
    M[country] = sector_share[country] × CRF_elasticity(exposure[country])

- **sector_share** — the energy/power sector's share of ambient-PM2.5 **mass** for that country
  (= McDuffie "Energy Coal" + "Energy NonCoal"). A proportional emissions cut moves the concentration;
  the elasticity then maps that to deaths — so the **mass** share is the correct input, not the
  attributed death share (which is an average, not the marginal response).
- **CRF_elasticity** = ∂ln(Deaths)/∂ln(Concentration) at the country's baseline exposure (`< 1`, concave).

Both are **per-country lookups from GLOBAL datasets**, so the channel is country-agnostic: each repo
reads its own row. (For PHL: M ≈ 0.098 × 0.84 ≈ **0.082**, so −7.7% power emissions → ≈ −0.63% of 43,951 ≈
**−270 deaths**, vs the 1:1's −3,406.)

## Data sources (all global, country-resolved)
| input | source | values |
|---|---|---|
| energy sector share of PM2.5 mass | **McDuffie et al. 2021**, *Nature Comms* `s41467-021-23853-y`, **Supplementary Data 1** (per-country, 2017; energy = "Energy Coal" + "Energy NonCoal") | extracted in full to the CSV below; global energy **10.2%** (residential 19.0, dust 16.1, industry 11.7, transport 7.8, agri 5.1) |
| CRF (concentration → mortality) | GBD MR-BRT/IER + **GEMM** (Burnett et al. 2018, *PNAS*) | concave/supralinear; elasticity **~0.78–0.86** over 15–40 µg/m³ (declining with exposure). The *share* is CRF-robust; the absolute death *total* is not (GEMM ≈ +60% vs MR-BRT) |
| baseline exposure (µg/m³) | McDuffie Supp Data 1 (2017, population-weighted) | PHL 18.4, IDN 18.0, ZAF 28.8, ETH 32.6 |
| total ambient-PM2.5 deaths | the country's own **GBD export** (not McDuffie) | PHL 43,951 (2023) |

Data files:
- [`ogclews_link/data/pm25_health.json`](../../ogclews_link/data/pm25_health.json) — curated, with computed `M` for the active countries.
- [`ogclews_link/data/mcduffie2021_pm25_source_shares.csv`](../../ogclews_link/data/mcduffie2021_pm25_source_shares.csv)
  — **verbatim mirror of McDuffie Supp Data 1** (regions + 204 countries + sub-national; all sectors +
  death totals). To add a future country: read its row, `energy_total_pct = energy_coal + energy_noncoal`,
  `M = energy_total_pct/100 × elasticity(exposure)`.

## Per-country values (firm — extracted from McDuffie Supp Data 1)
| country | exposure µg/m³ | energy share (coal + non-coal) | CRF elasticity* | **M** |
|---|---|---|---|---|
| Philippines | 18.4 | **9.8%** (5.8 + 4.0) | 0.84 | **0.082** |
| Indonesia | 18.0 | **9.8%** (8.3 + 1.5) | 0.84 | **0.082** |
| Ethiopia | 32.6 | **10.1%** (0.8 + 9.3) | 0.76 | **0.077** |
| South Africa | 28.8 | **22.5%** (20.5 + 2.0) | 0.78 | **0.176** |

The energy **share** is now firm and country-specific (the global-anchor placeholder is retired; validated:
the file's "Global" row reproduces the literature's 10.2% energy / 11.7% industry exactly). South Africa's
M is ~2× the others — its power fleet is coal-heavy, so the health channel matters most there.

*CRF elasticities remain approximated from the concave curve at each exposure (the one soft term left);
recompute from GEMM/IER parameters when precision matters.

## In the OG model (the channel)
`channels.HealthChannel` (id `health`, CLEWS→OG) turns the dose-response into a demographic + labour shock:

1. **Trigger — PM2.5, not CO₂.** `signals.emissions_ratio(...)` reads the reform/base ratio of the
   country's *health* species (`CountryConfig.health_emission`, default `PM2_5`) over the first decade →
   `demis` (< 0 = cleaner). A decarbonization reform moves CO₂e and PM2.5 by *different* ratios (CCS cuts
   CO₂ not PM2.5; coal→gas cuts PM2.5 sharply), so the health channel must use PM2.5.
2. **Dose-response.** `M = CountryConfig.pm25_dose_response` (resolved from `data/pm25_health.json`;
   PHL 0.082). `M = 1.0` + a loud guardrail if a country has no row.
3. **Mortality → demographics.** Target `excess_deaths = total_ambient_PM2.5_deaths × M × demis` (signed;
   cleaner reform → negative → lives saved). The runtime's `health_pop.disease_pop` solves a scale on the
   age-specific mortality bump `ρ += shock_scale · g_t · h(s)` (clipped) to hit that target, then recomputes
   the population (`get_pop_objs`). The age shape `h(s)` is **GBD ambient-PM2.5 deaths-by-age** (elderly-
   skewed), so the extra survivors are mostly past working age → small GDP effect. Lives-saved (negative
   target) solves leave an intrinsic ~Walras residual that scales with the target; `CountryConfig.rc_ss`
   (1e-5) is the post-solve SS gate, ~10× tighter than ogcore's `RC_TPI` default.
4. **Morbidity → productivity.** Effective labour by age `e` is scaled by `benefit = −morbidity_response ·
   M · demis`: a cleaner reform raises productivity. `morbidity_response` (peak per-person YLD rate) and the
   age shape `g(s)` come from **GBD YLD-by-age** (working-age chronic causes). This is the *main* output
   gain. `M` is reused here as the morbidity elasticity proxy (the morbidity CRF differs slightly from
   mortality's but is the same order).

Totals (`total_ambient_PM2.5_deaths`, YLD rate) come from the country's **own GBD export**
(`IHME-GBD_2023_DATA/`), never McDuffie — McDuffie supplies only the sector *share*.

## Future expansions (kept deliberately)
- **Other ambient sectors — same method, different `sector_share`.** A transport-electrification channel
  uses the transport share (~7.6% global); an industry channel uses ~11.7%. The data file keeps **all**
  sector shares, not just energy, so those channels drop in without new research.
- **Household / indoor air pollution (HAP) — a SEPARATE GBD risk factor.** A future "household fuel
  changes" channel (biomass/charcoal cooking → clean fuels/electric) acts mainly on **indoor** exposure,
  which GBD treats as a **distinct risk factor** ("Household air pollution from solid fuels") with its own
  large attributable burden — biggest in low-income / high-solid-fuel-use settings (Ethiopia, rural
  Indonesia/Philippines). That channel should use the **GBD HAP rei** (a separate IHME export — our
  current GBD file is **ambient only**) + the **% of population using solid fuels**, NOT the ambient
  residential share. McDuffie's "residential" sector = residential combustion's contribution to *outdoor*
  ambient PM2.5 — related, but not the indoor HAP exposure. Keep the two distinct when that channel is built.

## Citations
- McDuffie, E.E. et al. (2021). *Source sector and fuel contributions to ambient PM2.5 and attributable
  mortality across multiple spatial scales.* Nature Communications 12:3594. `s41467-021-23853-y`.
- Burnett, R. et al. (2018). *Global estimates of mortality associated with long-term exposure to outdoor
  fine particulate matter.* PNAS 115(38):9592–9597 (GEMM). + GBD 2019 MR-BRT/IER.
- World Bank WDI `EN.ATM.PM25.MC.M3` (GBD-sourced); HEI *State of Global Air*.
