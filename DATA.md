# Data the health channel needs (not yet on disk)

The health channel applies pollution mortality via the **disease_pop method** from
DeBacker, Evans & LaFleur, *The Macroeconomic Returns to Public Health Investments*
(the `CostOfDisease` repo): an age-specific shock `rho(s,t) = rho0 + kappa·g_t·h(s)`,
phased in, then the population is recomputed. Two inputs must come from data; both are
PLACEHOLDERS today (loudly flagged in `health_profile.py` and the channel's `validate()`).

## 1. The age profile h(s) — IHME GBD (required)

No air-pollution mortality-by-age data is on disk (only a CLEWS PM2.5 *emissions* file).
Download it from the IHME GBD Results tool and point the channel at it.

- Portal: https://vizhub.healthdata.org/gbd-results/
- GBD round: **GBD 2023** (to match the HIV extract used in CostOfDisease)
- Context/hierarchy: **Risk** (deaths attributable to a risk factor)
- Risk (rei): **Ambient particulate matter pollution** (`rei_id 86`)
- Cause: **All causes** (`cause_id 294`)
- Location: **Philippines** (`location_id 16`)
- Sex: **Both** (`sex_id 3`)
- Measure: **Deaths** (`measure_id 1`); Metric: **Rate** (`metric_id 3`, deaths per 100,000)
- Age: the fine bins `<1 year`, `12-23 months`, `2-4 years`, then 5-year groups `5-9`…`90-94`, and `95+ years`
- Year: latest available

Save the CSV, then build the 100-age profile (same logic as the HIV builder):

```python
from ogclews_link import health_profile
h = health_profile.build_profile_from_gbd(
    "<path>/IHME-GBD_pm25_PHL.csv", location_name="Philippines", year=2023,
    key_col="rei_name", key_value="Ambient particulate matter pollution")
# then run the health channel with profile_path=<saved profile>, or pass `h` directly.
```

(A GBD *risk* export keys on `rei_name`, not `cause_name` — `build_profile_from_gbd`
handles that via `key_col`.)

## 2. The dose-response and morbidity magnitudes (required, placeholder now)

- `mortality_response` (emissions change → `kappa`): currently a placeholder scalar. The
  defensible version derives expected change in pollution-attributable deaths from the CLEWS
  emissions change (ideally PM2.5, not CO2e) × a concentration-response (GBD relative risks /
  IER), then sets `kappa` (or solves it to a deaths target, as CostOfDisease does with `brentq`).
- `morbidity_response` (emissions change → effective-labor `e` haircut): placeholder. CostOfDisease
  builds its labor wedge from absenteeism/impairment studies (ILO, Keogh et al.); the pollution
  analogue would use working-age morbidity (e.g. low-birthweight, cardiopulmonary work-loss).

## Caveat carried from the HIV study

In CostOfDisease ~98% of the GDP loss came from mortality — but that is because HIV kills
**working-age** adults. Ambient PM2.5 deaths skew **elderly**, who are mostly out of the
workforce, so expect the mortality→GDP channel to be **weaker** and the working-age
morbidity/productivity channel to matter relatively more. Do not carry over the 98% result.
