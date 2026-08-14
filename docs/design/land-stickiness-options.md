# Making land allocation sticky in CLEWs — options assessment

**Status:** design assessment, nothing built. Companion to `phl-testcase-plan.md` §14.
**Date:** 2026-08-11
**Question:** a linear cost-minimiser moves land in instant, all-or-nothing lurches; real land
use is sticky. What could change — in case data, in MUIOGO's OSeMOSYS formulation
(`WebAPP/SOLVERs/model.v.5.4.txt`), or in solver class — to get realistic inertia?

## Why the lurching happens

An LP allocates each hectare to whichever use is marginally best, all at once. Real allocation
is smooth because land quality is heterogeneous, conversion costs money and takes time, and
owners don't re-optimise annually. Frameworks with smooth land supply get this from nonlinear
sharing functions — GCAM's logit, CGE transformation elasticities — which an LP cannot express
directly. But an LP can approximate every *economic cause* of stickiness with linear pieces.
The menu below is ordered by cost of adoption.

## Tier 1 — data only, works today, no solver change

**(a) Growth-rate limits — already in the formulation.** `LU3_TechnologyActivityIncreaseByMode`
(`model.v.5.4.txt:240`) caps any technology-mode's activity at
`(1 + TechnologyActivityIncreaseByModeLimit) ×` last year's. Capping cropland expansion *is*
capping conversion in this model, since cropland growth ≡ forest loss. Two caveats:
- **Increase-only.** There is no decline-rate twin, so deforestation speed cannot be capped
  directly on the forest technology — only indirectly via the expanding uses.
- **The zero trap.** The limit is multiplicative, so a technology at zero can never start.
  Harmless for land classes that always have positive area; fatal for new crop options.
- *Doctrine check:* source the rate from something real (clearing/land-development capacity,
  historical maximum), never tune it to reproduce the observed trajectory.

**(b) Conversion costs** (§14 item 3). One-way conversion technologies whose `VariableCost` is a
sourced clearing cost. Makes moves costly; does not by itself smooth them — once the margin
crosses the threshold, the LP still moves everything the bounds allow. Necessary, not sufficient.

**(c) Rising conversion supply curves.** Tier the conversion technologies: the first N km²/yr at
the easy-land clearing cost, the next tranche steeper, the next steeper again (capacity-limited
steps). Piecewise-linear rising marginal cost is the LP-native approximation of a smooth land
supply curve — the closer cousin of a CGE transformation elasticity that an LP can actually
express. Pure case data: a handful of parallel technologies with `TAU` slices and increasing
`VariableCost`. This is the single highest-value smoothing instrument available without touching
the solver. Tranche sizes/costs should come from land-quality gradients (slope, remoteness —
GAEZ-style), which keeps it physics, not outcome-tuning.

**(d) Land conversion as capital.** Give the conversion technology a `CapitalCost` and an
`OperationalLife` instead of (or alongside) a variable cost: converted land becomes a *stock*
built by investment, with sunk cost and vintage dynamics — inertia arises the same way it does
for power plants, which is the most OSeMOSYS-native mechanism available. Reversion then requires
its own investment, giving natural asymmetry. Data only, but a bigger restructuring of the land
block than (b)/(c).

**(e) Keep and sharpen the cluster heterogeneity.** The eight `LNDAGRPHLC*` clusters already
differentiate land quality; heterogeneous yields/costs are what make interior solutions (mixed
allocation) optimal rather than corners. More differentiation → less lurching, with zero new
machinery.

## Tier 2 — small formulation changes (GMPL edits, still pure LP)

**(f) Split-variable adjustment costs.** Add `ActivityChangeUp[r,t,m,y] ≥ 0`,
`ActivityChangeDown[r,t,m,y] ≥ 0` with
`Activity[y] − Activity[y−1] = Up − Down`, and a per-unit `ActivityChangeCost` on each in the
objective. This is the standard adjustment-cost smoother (the LP analogue of investment
adjustment costs), it penalises churn in both directions, and — worth noticing — **it is also
the structural fix for the credit-farming exploit**: define `EmissionByActivityChange` from `Down`
(deforestation) and `Up` (regrowth) with *separate* ratios (292 stock vs 6.81 removal), and the
§13 asymmetry problem disappears at the formulation level rather than by case-data discipline.
Mirrors the existing E10/E11 pattern (`model.v.5.4.txt:279-282`); modest edit; CBC/GLPK fine.

**(g) A decline-rate twin of LU3.** `TechnologyActivityDecreaseByModeLimit`, one constraint,
symmetric with `LU3`. Fixes (a)'s increase-only gap so deforestation speed can be capped on the
forest technology itself. Trivial edit; same zero-trap caveat inverted (a use at its floor).

Both (f) and (g) are upstream-worthy: they generalise beyond land (plant retirement churn,
demand-side stock turnover) and follow patterns already in the file.

## Tier 3 — out of reach without changing model class

True smooth sharing — GCAM's logit, CGE CET — is nonlinear and (for logit) non-convex. CBC is
LP/MIP; GLPK likewise. A convex quadratic adjustment cost could be piecewise-linearised (which
collapses back to (c)/(f)), but genuine logit sharing would mean a different solver and a
different model class. Not recommended: the whole value of CLEWs here is the transparent LP with
exact duals; (c)+(f) capture most of the economic content of smoothness without giving that up.

## Recommendation

For v16: **(b) now** (it shares an implementation with the one-way carbon tech), **(c) as the
smoothing instrument** when the conversion technology is built, **(a) only with a sourced rate**,
and **(e) preserved**. Revisit (f)/(g) as upstream MUIOGO/OSeMOSYS proposals once v16 shows
whether data-only stickiness suffices — (f) doubles as the structural fix for the §13 exploit,
which strengthens the upstream case considerably.

Doctrine line, restated for land dynamics: **rates and costs must come from physical or
institutional facts (clearing capacity, land-development cost, quality gradients); the observed
conversion trajectory stays a validation target.** Tuning any Tier-1 parameter until the model
reproduces history is forcing with extra steps.
