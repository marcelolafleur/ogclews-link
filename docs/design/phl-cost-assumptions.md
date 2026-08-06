# PHL cost assumptions — what drives the policy result

**Date:** 2026-08-06
**Case:** `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC`, run `Base_v12`, `muiogoai` world.
**Why this document:** the `PEP_v12` policy run decarbonises by 24% cumulatively at an objective cost
of 0.0061%, and replaces coal with 165 TWh of wind and 50 TWh of nuclear SMR. Whether that is a
finding about Philippine energy economics or an artefact of cost assumptions is the single most
important question about the result. This is the audit.

## Summary

Three cost problems, in order of how much they move the answer.

1. **The discount rate is 5% real**, against a Philippine official social discount rate of about
   10%. Halving the rate gives capital-intensive generation a 20 to 50 percentage-point cost
   advantage over fuel-intensive generation. **At 10% the merit order inverts.**
2. **Operational lives are internally inconsistent and several are implausible** — gas at 100 years,
   solar at 60, hydro at 25. Each error moves that technology's annualised capital cost by 25 to 30%.
3. **The coal price path is very flat** — 3.03 rising to 4.00 USD/GJ over 33 years, in a market that
   traded between 2.6 and 17 USD/GJ within the last five years.

Efficiencies and 2020 capital costs, by contrast, look sound.

## What the parameters actually are

| technology | capital 2020 | capital 2053 | fixed O&M | life | efficiency | capacity factor |
|---|---:|---:|---:|---:|---:|---:|
| coal (PP) | 2200 | 2200 | 45.3 | 25 | 43.8% | availability 100% |
| coal CHP (old) | 2800 | 2800 | 45.0 | 40 | 31.9% | availability 100% |
| gas CCGT | 1200 | 1200 | 21.6 | **100** | 60.4% | availability 100% |
| onshore wind | 1497 | 825 | 41.7 | 25 | — | **17.7%** |
| solar PV | 995 | 323 | 13.9 | **60** | — | 18.1% |
| nuclear SMR | 4482 | 3765 | 227.1 | 40 | 38.0% | availability 100% |
| geothermal | 4400 | 4400 | 115.0 | 40 | — | availability 100% |
| hydro (large) | 3000 | 3000 | 37.4 | **25** | — | 16.0% |

Capital in USD/kW, fixed O&M in USD/kW/yr, life in years. Capacity factors are `YearSplit`-weighted
annual averages computed from the model's own `CapacityFactor`. Thermal technologies carry no
timeslice-level capacity factor, so their availability defaults to 100% and their utilisation is set
endogenously.

Fuel prices, USD/GJ (the model's `VariableCost` on the supply technologies, which in MUSD/PJ is
numerically USD/GJ):

| fuel | 2020 | 2053 |
|---|---:|---:|
| coal, imported | 3.033 | 4.000 |
| coal, domestic | 2.723 | 3.248 |
| gas, imported | 9.984 | 10.748 |
| gas, domestic | 8.981 | 9.673 |
| oil, imported | 13.951 | 21.334 |

Coal is **3.3 times cheaper per GJ than gas**, which is what makes coal dominate the baseline.

## Problem 1 — the discount rate inverts the merit order

Computing LCOE from the model's own parameters at its own 5% rate, and again at 10%:

| technology | LCOE @5% | LCOE @10% | sensitivity |
|---|---:|---:|---:|
| solar PV | **41.8** | 71.6 | **+71%** |
| geothermal | 42.4 | 64.5 | +52% |
| coal (PP) | 47.9 | **57.8** | **+21%** |
| nuclear SMR | 55.7 | 78.2 | +40% |
| coal CHP (old) | 58.0 | 72.1 | +24% |
| gas CCGT | 68.9 | 75.7 | +10% |
| onshore wind | 95.6 | 133.6 | +40% |
| hydro (large) | 178.5 | 262.4 | +47% |

USD/MWh, 2020 capital costs. Thermal LCOEs assume 100% availability so they are lower bounds.

**Merit order at 5%:** solar, geothermal, **coal**, nuclear SMR, coal CHP, gas, wind, hydro.
**Merit order at 10%:** **coal**, geothermal, solar, coal CHP, gas, nuclear SMR, wind, hydro.

Coal moves from third to first; solar from first to third; nuclear SMR from fourth to sixth. The
mechanism is simply that fuel-intensive plant is much less sensitive to the discount rate than
capital-intensive plant — coal rises 21% where solar rises 71%.

This matters directly for the policy result. At the model's 2053 capital costs, wind comes out at
about 65 USD/MWh against coal at about 56 — wind is still dearer, but only by 16%. So when coal is
capped, substituting into wind costs very little, which is exactly why the objective barely moves.
**Wind wins on the constraint, not on cost, and the small cost gap that makes that cheap depends on
the discount rate.**

## Problem 2 — implausible operational lives

- **Gas CCGT at 100 years.** Real CCGT life is 25 to 30. At 5%, the capital recovery factor over 100
  years is 0.0504 against 0.0651 over 30, so gas capital is understated by roughly 23%. It also
  explains why gas is the least discount-sensitive technology in the table, at +10% — an artefact,
  not a property of gas.
- **Solar PV at 60 years.** Real life is 25 to 30. Solar capital is understated by roughly 26%.
  Combined with the 5% rate, this is why solar comes out cheapest in the model.
- **Hydro at 25 years.** Real hydro life is 50 to 80 years and Philippine plants routinely exceed 50.
  Hydro capital is therefore **overstated** by roughly 30%, which is why it lands at 178 USD/MWh and
  the model never builds any. That is a mis-specification suppressing a real Philippine resource.

Coal at 25, wind at 25, nuclear and geothermal at 40 are all defensible.

## Problem 3 — the fuel price path

Imported coal rises from 3.03 to 4.00 USD/GJ across 33 years, a 32% real increase. Indonesian thermal
coal, the Philippines' main source, traded near 2.6 USD/GJ in 2020 and above 17 USD/GJ in 2022. A
path that flat is a strong implicit assumption that coal stays cheap, and it is the assumption most
favourable to the baseline continuing to burn coal.

Gas at 9.98 rising to 10.75 USD/GJ is a reasonable long-run figure. Oil rising 13.95 to 21.33 is the
steepest path in the set, which is inconsistent with the flat coal path unless deliberate.

## What is sound

- **2020 capital costs** are broadly in line with international benchmarks: coal 2200, CCGT 1200,
  wind 1497, solar 995 USD/kW.
- **Efficiencies** are all plausible: supercritical coal 43.8%, old subcritical CHP 31.9%, CCGT
  60.4%, nuclear 38.0%.
- **Solar capacity factor** at 18.1% is right for the Philippines.
- **Learning rates** on wind (1497 → 825) and solar (995 → 323) are aggressive but within the range
  of published projections.

## What is questionable but secondary

- **Onshore wind capacity factor 17.7%.** Philippine wind plant achieves closer to 28%. This makes
  wind look *worse* than reality, partially offsetting the discount-rate bias in the opposite
  direction.
- **Nuclear SMR capital at 4482 USD/kW.** Published SMR estimates run 6,000 to 12,000 USD/kW and the
  one cancelled US project implied far more. 4482 is optimistic by a factor of 1.5 to 3, and the
  model builds 50 TWh of it.
- **Hydro capacity factor 16.0%** with capacity of 5.13 GW against roughly 4 GW actual — a
  compensating pair of errors that produces roughly the right generation for the wrong reasons.

## The bottom line for policy use

The `PEP_v12` result is not evidence that decarbonising the Philippine power system is nearly free.
It is evidence that **under a 5% discount rate, with gas and solar lives that are too long and a flat
coal price, the alternatives sit close enough to coal that forcing a switch costs almost nothing in
the model's own accounting.**

That is a conditional statement, and the conditions are checkable. The discount rate alone is worth
testing before any of these numbers are presented — which is the sensitivity run recorded below.

## Tested against benchmarks, and against a 10% discount rate (2026-08-06)

Two things changed my diagnosis. Both are corrections to what is written above.

### Correction 1 — the discount rate is NOT the main driver

I built `Philippines_v12_DISCOUNT10` (inputs copied, `DR` = 0.10, original untouched) and solved both
runs. Both reached optimality.

| | Base | PEP | policy cost |
|---|---:|---:|---:|
| DR = 5% | 375,930,821 | 375,953,763 | **0.0061%** |
| DR = 10% | 172,241,781 | 172,250,477 | **0.0050%** |

The policy cost gets *smaller* at 10%, not larger — a discounting artefact, because the coal cap
bites after 2040 and a higher rate shrinks late costs. And the technology choice is largely robust:

| 2053 generation, TWh | PEP @5% | PEP @10% |
|---|---:|---:|
| onshore wind | 165.3 | **140.7** |
| solar PV | 74.6 | **123.3** |
| nuclear SMR | 50.1 | **57.9** |
| gas CCGT | 31.4 | 45.2 |
| coal | 43.8 | 32.8 |

Wind and nuclear are still built at 10%. So the qualitative story — coal out, wind/solar/nuclear/gas
in — **survives a doubling of the discount rate.** The LCOE merit-order inversion computed above is
real arithmetic, but in the full system optimisation it does not flip the build, because the model
builds wind and nuclear when it **runs out of cheaper options**, not because they are cheap. Solar and
geothermal are resource-limited; wind and nuclear fill the remaining gap at whatever they cost.

That is a more robust result than I expected, and it is good news for the policy conclusion. The
discount rate should still be corrected — 5% is half the mandatory rate and any Philippine government
audience will measure against 10% — but it is not what makes decarbonisation look nearly free.

### Correction 2 — coal capital cost is 37% too high, and that IS a driver

| technology | model | Philippines benchmark | Vietnam catalogue | IEA India |
|---|---:|---:|---:|---:|
| coal | **2200** | **1605** (BNEF 2025) | 1460–1630 | 1200 |
| gas CCGT | 1200 | 1123 | 770 | 700 |
| onshore wind | 1497 | 1593 | 1500 | 1120 |
| solar PV | 995 | 548 | 930 | 640 |
| nuclear SMR | **4482** | none exists | — | 2800 (large) |

USD/kW. The model's 2200 for coal sits at the **United States** level (IEA WEO puts US coal at 2100)
and is 1.37× the Philippine benchmark, 1.8× India, 1.4–1.5× Vietnam. Real Philippine projects
corroborate: GNPower Dinginin ≈1310, GNPower Mariveles ≈1580 USD/kW.

The consequence, computed with Philippine-grounded inputs throughout: **at 5% real, onshore wind and
the model's 2200 USD/kW coal both come out at 64.6 USD/MWh — an exact tie.** Correct coal to its real
Philippine cost and move to 10%, and wind becomes **25% more expensive** than coal. So the model
penalises coal and that is a large part of why the alternatives look free.

### Correction 3 — the wind resource ceiling is physically impossible

This is the most serious problem in the model and it is not a cost problem at all.

The onshore wind activity cap is 1594.08 PJ = **442.8 TWh/yr**:

| against | TWh/yr | model allows |
|---|---:|---:|
| NREL unconstrained good-to-excellent resource | 195.2 | **2.27×** |
| NREL/USAID screened "Restricted" potential | 184.4 | **2.40×** |
| DOE PEP total wind plan to 2050 | 92.8 | **4.77×** |

And what it actually builds — 165.3 TWh — needs **70.7 GW** at the capacity factor Burgos actually
achieves. That is 92% of NREL's *entire unconstrained* good-to-excellent resource, on 21,000–29,000
km² at modern turbine density, which is **1.9–2.6 times all the good-to-excellent windy land in the
country**. Installed capacity today is 0.502 GW and has sat at 0.427 GW for ten straight years. The
implied build rate is 2,307 MW/yr for 27 consecutive years against a realised 7.5 MW/yr.

**Where the Philippine wind resource actually is: offshore.** 27–58 GW after environmental and social
screening, at 45–47% capacity factor — 40 GW offshore delivers ~161 TWh, the same as the model's
onshore build from a fifth of the capacity. The model has an offshore technology,
`PHL_POW_PP_WOF_T1`, and gives it a capacity factor of **15.4% against a real 45–47%**. That single
error makes offshore uneconomic and forces the build onshore, where the resource does not exist.

### Other corrections from the benchmark set

- **2020 generation was 101.76 TWh, not 106** (2020 was the COVID dip). So the model's 102.0 TWh is
  **+0.2% — essentially exact**, better than the 4% gap reported earlier in this repo.
- **Philippine geothermal achieves 63%**, not the 80–90% of generic catalogues. The model gives it no
  timeslice capacity factor at all, so it runs at 100% availability.
- **Onshore wind capacity factor**: operator-reported Burgos averages 26.7% over 2019–2024. The
  model's 17.7% is low; the DOE-derived national 33% is too high and fails a consistency check.
- **Coal delivered 2020 was 2.48 USD/GJ** against the model's 3.03 — the model is 22% high for 2020,
  though its flat path does bracket 2023–24 actuals (5.07, 3.76). Verify the calorific value is
  ~22.1 GJ/t (the DOE official figure); assuming 17.6 GJ/t would overstate USD/GJ by 25%.
- **The Philippines imported no LNG before April 2023.** A 2020 gas price should be Malampaya, not
  LNG. Malampaya is oil-linked and now ~12.1 USD/GJ, at parity with imported LNG, and the field is
  expected dry around 2027.
- **Nuclear SMR at 4482 USD/kW** against NREL ATB Moderate 8000, Conservative 10,000, and the
  cancelled NuScale project's implied ~20,130. A Philippine first-of-a-kind belongs at the
  conservative end or above. The 50 TWh built implies 6.3 GW against a government ambition of
  1.2 GW by 2032.
- **Actual contracted Philippine prices** (Green Energy Auction, pay-as-bid): GEA-2 onshore wind
  100.9 USD/MWh nominal, roughly 80 constant-real; solar 75.4 nominal, roughly 60 real. The model's
  implied 2053 wind cost of ~65 is optimistic against those.
- **The discount rate should be technology-differentiated, not just raised.** Philippine hurdle rates
  run the *opposite* way to a low uniform rate: BNEF puts Philippine coal at 16% and CCGT at 18%
  nominal against solar 13% and wind 14%; IEA uses 4–7% for solar and wind but 8–9% for coal, gas and
  nuclear. A single 5% prices a first-of-a-kind nuclear plant at the same risk as a solar farm.
- The NEDA social discount rate of **10% real is mandatory** for public investment appraisal (ICC
  Memorandum, 30 September 2016, updating from 15%), and a published Philippine OSeMOSYS study
  (Dixon et al., *Climate* 13(1):14, 2025) uses 10%.

### Revised verdict

The `PEP_v12` pathway is **more robust than I first thought on cost, and less credible than I thought
on physics.**

1. The technology choice survives doubling the discount rate. That is a genuine result.
2. But coal is penalised by a capital cost 37% above the Philippine benchmark, which is a large part
   of why the switch looks costless.
3. And the onshore wind build is physically impossible — 92% of the entire national resource, on
   twice the available land, at 300× the historical build rate.

**Ranked fixes, all single-parameter and within the existing structure:**

1. **Cap onshore wind at the screened resource** — 184.4 TWh (664 PJ), not 442.8 TWh. This is the one
   that changes the answer most, and it is a one-line change.
2. **Fix the offshore wind capacity factor** — 15.4% → 45%. Lets the model use the resource the
   country actually has.
3. **Coal capital cost** 2200 → ~1605 USD/kW.
4. **Discount rate** 5% → 10% central, ideally technology-differentiated.
5. **Nuclear SMR capital** 4482 → 8000–10,000 USD/kW.
6. **Geothermal capacity factor** → 63%.
