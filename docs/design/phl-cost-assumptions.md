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
