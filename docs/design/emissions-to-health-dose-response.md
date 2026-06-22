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

- **sector_share** — the emitting sector's share of ambient-PM2.5 **mortality** for that country.
- **CRF_elasticity** = ∂ln(Deaths)/∂ln(Concentration) at the country's baseline exposure (`< 1`, concave).

Both are **per-country lookups from GLOBAL datasets**, so the channel is country-agnostic: each repo
reads its own row. (For PHL: M ≈ 0.10 × 0.80 ≈ **0.08**, so −7.7% power emissions → ≈ −0.6% of 43,951 ≈
**−270 deaths**, vs the 1:1's −3,406.)

## Data sources (all global, country-resolved)
| input | source | values |
|---|---|---|
| sector share of PM2.5 mortality | **McDuffie et al. 2021**, *Nature Comms* `s41467-021-23853-y` (+ GBD MAPS/HEI); country tables in the supplementary | global 2017: residential **19.2%**, windblown dust **16.1%**, industry **11.7%**, **energy/power 10.2%**, agriculture ~8%, transport ~7.6% |
| CRF (concentration → mortality) | GBD MR-BRT/IER + **GEMM** (Burnett et al. 2018, *PNAS*) | concave/supralinear; elasticity **~0.78–0.86** over 15–40 µg/m³. The *share* is CRF-robust; the absolute death *total* is not (GEMM ≈ +60% vs MR-BRT) |
| baseline exposure (µg/m³) | GBD 2021/23, World Bank WDI `EN.ATM.PM25.MC.M3`, HEI State of Global Air | PHL ~23, IDN ~17, ZAF ~36, ETH ~17–50 |

Machine-readable per-country table: [`ogclews_link/data/pm25_health.json`](../../ogclews_link/data/pm25_health.json).

## Status of the per-country numbers
- **South Africa** — energy-coal share **is** published (20.5%, the largest single source) → M ≈ 0.15.
- **Philippines / Indonesia / Ethiopia** — energy share not in McDuffie's *main text*; the table uses the
  **global 10.2% anchor** (M ≈ 0.08) **PENDING** extraction of each country's value from McDuffie's
  supplementary tables. CRF elasticities are approximated from the concave curve at each exposure and
  should be recomputed from GEMM/IER when precision matters.

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
