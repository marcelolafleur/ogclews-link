# What crosses the OG-CLEWS seam, and whether the land defects reach the macro model

**Date:** 2026-08-06
**Question:** the PHL CLEWs energy block is sound but its land and water blocks are badly calibrated.
Do the land and water errors propagate into the OG-Core macroeconomic results?

## Answer

**By name, no. By topology, yes — and on PHL today it is negligible for a reason that will not last.**

No CLEWs land or water code appears anywhere in `ogclews_link` outside the unwired
`env_accounts.py`. No channel reads land area, crop production or water volumes. But two structural
paths carry land-block quantities into the macro model regardless of what the authors intended.

Measured on the solved PHL case:

| path | mechanism | PHL today | shipped demo |
|---|---|---|---:|
| A — electricity price | LCOE graph walk reaches land technologies via power-plant cooling water | **0.18%** of the price numerator | **5.1%** |
| B — health channel | `emissions_by_year` sums the species over every technology, no block filter | **0.00%** — clean | 29% of CO2EQ |

## Correcting an earlier claim in this repo

`phl-what-to-fix-next.md` says: *"The land defects do not contaminate the energy answers. That was
measured, not assumed: fixing the crop yields moved the objective by 0.0015% and emissions not at
all."*

That statement is **true of the CLEWs LP solve and does not cover the link.** The objective is a cost
total; the link's default price path reads *per-technology costs* and reallocates them. A crop-yield
change that leaves the LP objective flat can still move land-technology cost and therefore the
electricity price ratio shipped to OG-Core. The conclusion happens to hold for PHL today, but not for
the reason given.

## Path A — how land cost gets into the electricity price

`signals.energy_price_ratio` with `kind='auto'` picks the curated `*Cost of electricity*.xlsx`
workbook if it is present in **both** scenario directories, and otherwise falls back to
`lcoe`. **No such workbook exists anywhere in the PHL case or the CLEWs-PHL repo** — I checked — so
PHL resolves to `lcoe` and the graph walk is live.

`lcoe.lcoe_by_year` allocates the cost of any non-generation technology whose output flows
transitively toward generation. Power plants consume cooling water, and cooling water traces back
through surface water and runoff to the land technologies that produce it:

```
PHL_POW_* ←PHL_PWR_WAT← PHL_DEM_PWR_SUR_WAT ←PHL_WTR_SUR← land clusters and LND*TOT
```

The allocation weight is a technology's share of output flowing that way, and it is computed on
**physical output summed across incommensurable units** — crop tonnes and water cubic metres added
together. In the demo that charges 14.9% of a rainfed-maize technology's annual cost to electricity.

`lcoe.py:23-25` shows the authors knew the walk reaches land — the `cost_floor` guard exists to
strip the negative-cost forest credit — but it removes only *negative*-cost technologies. Positive-cost
land and water technologies stay in.

### Measured on PHL `Base_v12`, year 2037

| technology | share of numerator | block |
|---|---:|---|
| `PHL_PRO_IMP_COAL` | 40.31% | energy |
| `PHL_PRO_EXTR_NG` | 0.76% | energy |
| `LNDCONHRTOT` | 0.043% | **land** |
| `LNDSGCHRTOT` | 0.029% | **land** |
| `LNDRCPHRTOT` | 0.025% | **land** |
| `LNDTOMHRTOT` | 0.022% | **land** |
| `LNDOTHHRTOT` | 0.022% | **land** |
| `LNDMZEHRTOT` | 0.019% | **land** |
| `LNDRCPHITOT` | 0.017% | **land** |
| all water technologies | <0.001% | water |

**Land total ≈ 0.18% of the price numerator. Water is effectively zero.**

## Why PHL is 0.18% and the demo is 5.1% — and why that is a warning, not a reassurance

Because **the PHL land block has almost no costs to allocate.** The only variable cost on any land,
crop or agricultural technology in the entire PHL model is the `-10` on forest mode 27; crop
production is costless. There is nothing to charge to electricity. The demo, by contrast, carries
real crop production costs of 42 to 77, which is exactly why its land share is 5.1%.

So two defects are cancelling: the land block contaminates the electricity price through a topology
it should not, and it fails to contaminate it much only because the land block is under-specified in
a second, independent way.

**The consequence is counterintuitive and worth stating plainly: adding realistic crop production
costs to CLEWs — an unambiguous calibration improvement — would silently move the electricity price
the macro model sees, by roughly an order of magnitude on this channel.** Anyone who fixes crop costs
without knowing about Path A will change their macro results and have no idea why.

The ratio structure does not save you either. Only the reform/base ratio enters OG, so an identical
mis-calibration in both scenarios partly cancels — but a wrong land cost inflates a *common* numerator
term, which **damps the price ratio toward 1** and attenuates the energy signal. That is a distortion
of magnitude, not a rounding error.

## Path B — clean on PHL, verified

`signals.emissions_by_year` filters on the species and then sums over every technology in the case
with no block filter. On the demo that means land technologies contribute 29% of CO2EQ and 100% of
CH4 and N2O.

On PHL the health species is `PM2_5`, and **every land, crop and agricultural technology has PM2_5
of exactly 0.0** — all 54 of them. The emitters are household coal cooking (1.16) and road transport.
So Path B carries nothing from the land block today.

That is contingent, not structural. If crop-residue burning were ever added — a realistic and
commonly modelled Philippine source — it would flow straight into the health channel and on to OG
mortality and GDP with no filter in the way.

## What is genuinely clean

- `investment` and `capital_intensity` are hard-filtered to the power-technology prefix.
- The opt-in `marginal` price source is fuel-filtered to the electricity commodity.
- `carbon_tax`, `energy_capex`, `emit_discount_rate`, `emit_energy_demand` read no CLEWs data at all.
- `og_wedge.py`, `framework.py` and `contract.py` read no CLEWs data.
- `env_accounts.py` is confirmed **not wired** — its only importers are the probe script and its test.

## Direction of flow

**CLEWs → OG:** an electricity price ratio, power-sector capex, power-fleet cost shares, an emissions
ratio.
**OG → CLEWs:** `demand_scaling.csv`, `EmissionsPenalty.csv`, `DiscountRate.csv`, applied to a case
copy.

Note the last one. **The macro side already writes a discount rate into CLEWs.** Given that the
discount rate inverts the CLEWs merit order (see `phl-cost-assumptions.md`), the coupled system has a
live channel by which an OG-side assumption reorders the energy build — worth knowing before running
anything coupled.

Land and water duals were scoped as a future channel and never built:
`og-clews-denovo-analysis.md` lists *"Land/water duals → ag productivity | OG side ready; needs CLEW +
dual extraction | coarse (TFP proxy only)"*.

## Recommendations

1. **Before any coupled PHL run, decide the price source explicitly** rather than letting `'auto'`
   fall through to `lcoe`. If the intent is an energy-only price, pass `supply_predicate` to exclude
   land and water technologies, or use `kind='marginal'`, which is fuel-filtered and clean.
2. **Fix `out_frac` or document it.** Summing crop tonnes and water cubic metres to weight a cost
   allocation is not defensible on its own terms, independent of calibration.
3. **Tie the crop-cost fix to a seam check.** If crop production costs are ever added, re-measure the
   land share of the electricity price before trusting any macro result.
4. **Re-measure Path A whenever the land block changes.** The decomposition is reproducible against
   any solved case.
