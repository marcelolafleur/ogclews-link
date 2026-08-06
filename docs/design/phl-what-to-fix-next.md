# What to fix next in the PHL model — a decision brief

**Date:** 2026-08-06
**For:** deciding where effort goes, given the objective of a CLEWs calibration good enough to
inform policy scenarios.
**Case:** `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC`, run `Base_v12`, in the `muiogoai` world.

## The reframe that should drive the decision

This is an **energy model with land and water attached**, and all three policy scenarios defined in
the case are energy scenarios: `COAL_PHASEOUT`, `RE`, `EV`. Nothing in the scenario set touches land
or water.

That matters because the two sides are in completely different condition.

**The energy side is sound.** 2020 electricity generation comes out at 102.0 TWh against roughly 106
observed, and every technology share lands within about one percentage point:

| source | model | observed |
|---|---:|---:|
| coal | 57.1% | 57.0% |
| gas | 19.2% | 19.0% |
| geothermal | 10.7% | 10.0% |
| hydro | 7.1% | 8.0% |
| oil | 2.4% | 3.0% |
| solar | 1.4% | 1.3% |
| biomass | 1.2% | 1.0% |
| wind | 1.0% | 1.0% |

Generating capacity is 25.80 GW against about 26.3 observed. The base year is largely pinned —
`ResidualCapacity` supplies 24.09 of the 25.80 GW — which is normal, correct practice for a base
year, not a defect. And the trajectory tracks: 2021–2024 generation comes within 0–6% of observed
every year, on a demand path set before those outcomes were known.

**The land and water sides are not sound.** Crop yields are wrong by factors of 2 to 5 in both
directions, forest is 2.5 times observed, and water is free everywhere.

So the honest summary of what this model can answer today:

| question | can it answer? | why |
|---|---|---|
| Energy transition scenarios — coal phase-out, renewables, EVs | **yes** | energy side well specified; land errors move the objective 0.0015% |
| Power sector emissions | **yes** | follows from the generation mix, which is right |
| Crop, agriculture, food questions | **no** | yields wrong 2–5×, composition badly off |
| Irrigation and water questions | **no** | water is free; the nexus is inert |
| Land use, forest, biodiversity, land carbon | **no** | forest is a residual, 2.5× observed |

The land defects **do not contaminate the energy answers**. That was measured, not assumed: fixing
the crop yields moved the objective by 0.0015% and emissions not at all.

## The pending items, ranked by value for the money

### 1. Solve `PEP_v12`. Do this first.

**What it is.** The case defines a policy run — `PEP_v12` activates coal phase-out, renewables and
EV penetration together — and it has **never been solved on this machine.** Only `BASE` has.

**Pro.** It is about three minutes of compute and it directly serves the stated objective. Right now
there is no policy contrast at all: no one can say what any of these scenarios do, because none has
been run. It would also be the first real test of whether the model *responds* sensibly to a policy
shock, which base-year fit cannot tell you.

**Con.** None worth the name.

**Verdict: do it first.** Cheapest thing on the list and the most directly on-objective.

### 2. Run the otoole parity check on the two tested fixes.

**What it is.** Both corrections were verified by patching the solved MUIO case and re-solving. They
have not been run through CLEWs-PHL's own build path.

**Pro.** It converts "tested" into "tested the way this repo builds models", which is what any
maintainer will ask for. It gates items 3 and 4.

**Con.** Effort with no new insight — it confirms rather than discovers.

**Verdict: do it.** It is the gate on everything else in the land block.

### 3. Land the crop-yield fix.

**What it is.** The yields are GAEZ agro-climatic potential used as if they were observed actual
yields. Scaling each crop to observed harvested area puts all five crops within 1–5% of PSA 2020.

**Pro.** Unlocks every crop, food and agriculture result. Cheap, tested, and contained — the
objective moved 0.0015% and energy results already in circulation are unaffected. It is also a
precondition for the land-cover work and for irrigation meaning anything.

**Con.** The factors are national, not per-cluster, leaving a 1–5% residual. The PSA figures used
were taken from recollection in-session and need re-pulling from CountrySTAT. And a caveat worth
stating plainly: matching harvested area is not the same as validating the model — the targets were
imposed, not reproduced.

**Verdict: do it, after re-pulling the source data.**

### 4. Land the irrigation fix.

**What it is.** Irrigation withdrawal is about 25 times below the reported national figure. Scaling
to the reported total brings it in line.

**Pro.** Water withdrawal is a reported CLEWs output and it is currently indefensible. This makes it
defensible.

**Con.** Two real ones. First, it changes **nothing else at all** — land allocation stays identical
to the decimal place, because water carries neither cost nor constraint. So it buys a correct
reported number, not better model behaviour. Second, the target is contested: FAO AQUASTAT says
roughly 69 km³/yr, other sources say near 30. That is a factor of two on the headline number, and it
needs a sourcing decision before the fix means anything.

**Verdict: do it, but settle the target first.** Lower value than item 3 because it improves
reporting rather than behaviour.

### 5. Fix the base-year land cover. The big one.

**What it is.** The build reads a complete seven-class land-cover table, then discards three classes
including one holding 164,254 km² — 55% of the country. Forest absorbs the entire residual and comes
out at 179.78 ×10³ km² against 72.26 observed.

**Pro.** This is the difference between forest being a measured quantity and an accounting leftover.
Nothing land-related — land use, biodiversity, land carbon, natural capital — means anything until
it is fixed. If land questions are ever going to be asked of this model, this is the blocker.

**Con.** Substantially harder than items 3 and 4. The underlying land-cover product puts 55% of the
territory in a single class and carries no data at all for grassland or barren, so this probably
means revisiting the concordance against a better product (NAMRIA's national land cover) rather than
just writing more constraints. It is order-dependent — yields must be fixed first, or the model goes
infeasible or crushes forest to a third of its true size. And it will move results that people may
already have seen.

**Verdict: do it if land questions matter; skip it if this model is only ever going to answer energy
questions.** That is the real decision, and it is a scope question rather than a technical one.

### 6. Water nexus activation. Recommend against, for now.

**What it is.** Making water actually constrain anything — which needs dry-season timeslices with
precipitation availability factors, and ideally river-basin spatial units instead of yield clusters.

**Pro.** It is the only route to any water policy answer, and it is the thing that would make this a
genuine land–energy–water model rather than an energy model with water bookkeeping.

**Con.** It is a redesign, not a recalibration. It changes both the temporal and spatial resolution
of the model, which means a rebuild and a revalidation of everything. And it is not certain to
change conclusions: even with corrected withdrawals, only 33% of surface water is used, so 224 km³
of headroom remains. At annual national resolution the Philippines genuinely is not water-scarce —
the scarcity is seasonal and basin-level.

**Verdict: do not start this unless someone specifically needs water policy answers.** If they do,
say plainly that the current model cannot provide them, rather than producing numbers from a model
where water is free.

### 7. The forest valuation decision. Low priority.

**What it is.** The `-10` variable cost is the model's only representation of the value of standing
forest — a hardcoded constant, worth about $100/ha/yr, with no source.

**Pro.** Deriving it would make any natural-capital depletion figure defensible.

**Con.** It only matters if a natural-capital number is going to be published. It barely affects the
model's behaviour, because forest is a residual of demand-driven cropland. And any replacement is
still a valuation assumption, just a sourced one.

**Verdict: only if the environmental accounting is going to be published.** Otherwise leave it,
documented.

### 8. Per-cluster yield factors, and exporting the activity-limit shadow prices.

Both are refinements. The first closes the 1–5% residual on item 3; the second is now optional
because those shadow prices are already written to `results.txt` by every solve. Neither changes any
conclusion.

## Recommended sequence

1. **Solve `PEP_v12`** — three minutes, and it is the only thing that produces an actual policy
   result.
2. **Re-pull the PSA yield data and settle the irrigation target.** Data decisions, not modelling.
3. **Run the otoole parity check.**
4. **Land the yield fix, then the irrigation fix.**
5. **Then decide on the land-cover work** — the scope question above.

Items 1 to 4 make the model honest about agriculture and water reporting without disturbing the
energy results. Item 5 is what would make it a land model.

## What has not been checked

Stated so this brief is not read as broader than it is.

- **Costs.** Capital costs, fuel prices and discount rates were never assessed. They drive every
  scenario result, so they matter more for policy work than anything in the land block.
- **Demand projections beyond the aggregate.** Total electricity generation tracks observed to 2024,
  but sectoral demand detail was not examined. The model's 2053 generation of 375 TWh is a 3.7×
  increase on 2020 and that growth assumption was not tested.
- **Transport, industry and fisheries.** Not examined at all.
- **Whether the model responds *correctly* to a policy shock.** Base-year fit cannot establish this.
  Solving `PEP_v12` is the first step.
- The observed figures used throughout — generation mix, harvested areas, water withdrawals — were
  taken from recollection during the session and are right in magnitude, but should be re-pulled from
  PSA, DOE and AQUASTAT before anything is published.

## Item 1 done — the first policy result this model has ever produced (2026-08-06)

`PEP_v12` solved: CBC Optimal, 260 s, objective 375,953,763 against `Base_v12`'s 375,930,821 — a
difference of only **0.0061%**. That near-identical cost is the first thing to understand about this
result, and it is explained below.

### It produces a coherent decarbonisation pathway

| | 2020 | 2030 | 2040 | 2053 |
|---|---:|---:|---:|---:|
| CO2e, Base | 97.3 | 148.8 | 186.2 | 263.9 |
| CO2e, PEP | 97.3 | 146.6 | 132.1 | 139.5 |
| change | 0% | −1.5% | **−29.1%** | **−47.1%** |

Cumulative 2020–2053: **6,321 → 4,828 MtCO2e, −23.6%.**

By 2053 the policy run replaces 160 TWh of coal with 165 TWh of wind, 50 TWh of nuclear SMR
(`PHL_POW_PP_NUSMR`) and 14 TWh of extra gas.

### Two things a reader must know before quoting it

**1. Coal generation RISES in 2030, by 16 TWh, under the coal phase-out.** This is not an error but
it is counterintuitive, and it comes from how the phase-out is implemented:

- `PHL_POW_CHP_COAL_OLD` gets a declining *activity* cap: 209.45 → 178.56 → 0.
- `PHL_POW_PP_COAL` gets a *capacity* cap that only reaches 0 in the final year; its activity is
  never capped.

So in the interim the model retires old coal CHP (65.6 → 13.3 TWh in 2030) and substitutes into the
other coal plant (18.3 → 87.1 TWh), which is unconstrained. Coal-to-coal substitution, plus the extra
EV demand, makes 2030 coal higher than baseline. The phase-out is real by 2040; before then it moves
coal between technologies rather than out of the system. **Anyone presenting a 2030 number from this
scenario needs to know that.**

**2. The mix change is driven almost entirely by the coal caps, not by the renewables scenario.**
Wind's activity upper limit is 1594.08 in *both* runs, and nuclear SMR has no scenario-specific limit
either. Both are available in the baseline and the baseline simply does not build them. They appear
only once coal is constrained. So `RE` and `EV` shift demand and costs, but the generation-mix result
is a response to the coal constraint.

That also explains the near-identical objective: the alternatives were already close to coal in cost,
so forcing the switch costs almost nothing in the model's own terms. Whether that is a finding about
Philippine energy economics or an artefact of uninspected cost assumptions **cannot be settled from
this run** — see the costs gap below. It is the most important open question about this result.

### What it is worth

This is a usable policy result and the capability is demonstrated: the model runs a multi-scenario
policy case, reaches optimality in about four minutes, and produces a decarbonisation pathway with a
sensible structure. For proof-of-concept purposes that is the headline.

But two of its three headline numbers rest on technologies with essentially no deployment today —
165 TWh of wind from a base of zero, and 50 TWh of nuclear SMR — and their cost and resource
assumptions have not been checked. **Costs are now the highest-value unexamined area in this model**,
ahead of anything remaining in the land block.
