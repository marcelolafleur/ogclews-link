# What we can take from IEEM

**Status:** research note. Nothing here is built into the runtime.
**Date:** 2026-07-31
**Subject:** IDB's Integrated Economic-Environmental Modeling platform (IEEM / IEEM+ESM),
assessed against MUIOGO (CLEWS/OSeMOSYS) and ogclews-link as they actually stand today.

## The short version

IEEM is not a competitor to CLEWS and it is not ahead of us on rigour. It is ahead of us on
**three specific deliverables** — a wealth/sustainability headline number, a biodiversity
indicator, and spatially-explicit ecosystem services — and every one of those turns out to be
a *post-processing* layer over model output rather than a modelling capability we lack.

I tested this rather than assuming it. Two of IEEM's headline indicator terms compute correctly
from a solved MUIOGO case today, with no new model machinery
([`experiments/ieem_indicator_probe.py`](../../experiments/ieem_indicator_probe.py)).

The one genuinely deep gap is different from the one I expected, and it is described in
[§5](#5-the-land-rent-gap-the-real-structural-finding).

## 1. What IEEM actually is

Recursive-dynamic CGE, built by Onil Banerjee (IDB) with Martín Cicowiez (CEDLAS/UNLP), running
in GAMS with an Excel front end. Its database is an **environmentally-extended Social Accounting
Matrix**: a standard SAM with SEEA physical accounts (water in gigalitres, energy, emissions,
land) attached to the industry accounts. Models exist for 20+ Latin American and Caribbean
countries — essentially every country in the region with supply-use tables.

`IEEM+ESM` adds two coupled models:

- **Dyna-CLUE** — land-use/land-cover change. Splits into a *non-spatial demand module* (fed by
  IEEM's land demands) and a *spatial allocation module* (raster, 300m grid).
- **InVEST** — ecosystem services. Four models used in the flagship paper: sediment delivery
  (RUSLE), carbon storage, annual water yield, nutrient delivery. Plus a Biodiversity Intactness
  Index composited from PREDICTS coefficients by land-use type.

The loop runs in **5-year steps**, 2020→2040: IEEM → Dyna-CLUE → InVEST → economic shock → back
into IEEM at t+1. The Colombia paper (IDB-WP-01193) claims this as the first implementation that
endogenises the ES→economy feedback rather than running it one-way.

### Openness, precisely

The `Open-IEEM` GitHub org holds **only** ecosystem-service geodata packets — 21 country repos,
last touched 2021 (Peru 2023). No model code. The CGE is GAMS, which means a commercial licence
to run it. "Open" here means open *data*, not open *model*.

## 2. The finding that should change how we talk about this

IEEM's celebrated "dynamic endogenous feedback" — the thing the flagship paper leads with — is,
in full, equation 1:

```
LPL_d = (SER_d / TAA_d) × 0.08
```

Land productivity loss in department *d* = (agricultural area under severe erosion ÷ total
agricultural area) × an 8% productivity penalty taken from one literature estimate
(Panagos et al. 2017). That single scalar, applied as a TFP haircut on agriculture, *is* the
economy↔ecosystem feedback.

That is exactly the same reduced-form object as ogclews-link's `morbidity_response` and the
`phi_j` pass-through weights in `energy_cost_push` — both of which our own code explicitly
labels as illustrative placeholders (`channels.py:192-193`, `channels.py:351`).

So: **we are not behind IEEM on feedback rigour. We are behind on having published, and on
having committed to a defensible coefficient.** Our repo is more honest about its placeholders
than IEEM's paper is about its one. Worth saying plainly when this comes up, because the
instinct on seeing "dynamic endogenous feedbacks between natural capital, ES and the economy"
is to assume something structurally deeper is happening. It is not.

## 3. What I tested, and what it showed

IEEM's wealth indicator is genuine savings (IDB-WP-01193 eq. 2):

```
GenuineSAV_t = GNSAV_t − DeprCapStock_t − DeplForStock_t − DeplMinStock_t − EmiVal_t
```

with natural-capital depletion valued (eq. 3) as `Σ (qdepl_t · unitrent_t) / (1+intrat)^(i−t)`,
unit rent endogenous, interest rate 4%.

This is an **accounting identity over model outputs**. It needs no CGE. I ran the terms against
the shipped `CLEWs Demo` case, all four scenarios:

| eq. 2 / eq. 3 term | Status in a solved MUIOGO case |
|---|---|
| Land-cover state vector | **Present** — annual areas by class, 10³km², closing exactly on the land resource |
| Composite BII | **Computable now** — area-weighted mean; needs PREDICTS coefficients only |
| `EmiVal` (CO₂ damage) | **Computable now** — `AnnualTechnologyEmission` × social cost of carbon |
| `qdepl` (quantity depleted) | **Present** — resource-technology activity *is* the extraction quantity |
| `unitrent` (unit rent) | **Missing — but the rail is already wired.** See §5 |
| `GNSAV`, `DeprCapStock` | Out of scope for CLEWS — OG-Core produces these |

The probe output, on real solved data:

```
--- CLMCHG (2020-2035)
    2020: Built-up=15.00, Cropland=6.38, Forest=253.60, Water=25.02 | total=299.997 vs RSCLND=299.997
    2035: Built-up=17.41, Cropland=9.38, Forest=248.19, Water=25.02 | total=300.000 vs RSCLND=300.000
    composite BII 2020: 0.9073 -> 2035: 0.8985 (-0.973%)
--- REF (2020-2035)
    2035: Built-up=17.41, Cropland=8.87, Forest=248.70, Water=25.02
    composite BII 2020: 0.9073 -> 2035: 0.8992 (-0.898%)
```

The indicator discriminates sensibly: the climate-change scenario loses more forest and needs
more cropland (degraded yields require more land for the same output), and BII falls further.

**Caveat, stated plainly:** the BII coefficients are illustrative literature central tendencies,
not country-specific PREDICTS means. The arithmetic path is proven; the number is not a result.

### One methodological trap, recorded because it cost me a wrong first answer

A land technology's **area is its `TotalAnnualTechnologyActivityByMode`, not its production.**
Land technologies output water flows (`WTREVT`/`WTRGWT`/`WTRRUN`) *alongside* any land
commodity, and `LNDFOR` outputs **no land commodity at all**. Reading area from production
silently drops forest entirely and adds 10⁹m³ water volumes to 10³km² areas. My first pass did
exactly that and produced a forest area larger than the country.

The check that catches it: land-use areas must sum to the land resource `RSCLND`. That closure
identity is asserted in the probe and must hold to 1e-3. **Anything downstream that reads CLEWS
land must assert this**, or it will be wrong silently.

That closure identity is also, incidentally, a real selling point: it is exactly the kind of
accounting consistency SEEA demands, and our model satisfies it exactly rather than
approximately.

## 4. Where our land block is genuinely better than theirs

Dyna-CLUE's demand module is the weak end of IEEM's chain — the paper itself notes it accepts
anything "ranging from simple trend extrapolations to complex economic models". IEEM feeds it
land demands derived from a CGE with fixed conversion elasticities.

CLEWS *optimises* land allocation under physical constraints and emits the same state vector
with an exact closure identity. For the LULC→ES chain, **our land input is better founded than
theirs.** What we lack is only:

- the **spatial downscaling** step (Dyna-CLUE is aggregate-demand → raster allocation), and
- the **ES models** themselves (InVEST — open source, well documented).

Both are free. InVEST datapackets are FAIR-published for 21 LAC countries. Neither requires
GAMS or anything from IDB.

## 5. The land-rent gap — the real structural finding

This is the one that matters, and it is not the gap I expected going in.

Three facts, each verified:

1. **CLEWS can price land.** `BAL_ENV_LAND` in the Philippines v12 case is a user-defined
   constraint with `Tag: 1` (`genData.json`). `model.v.5.4.txt:348` routes `UDCTag=1` into
   `UDC2_UserDefinedConstraintEquality`. `Duals.json` **already wires** `UDCE_d`
   "Shadow price - UDC Equality" for export. So the shadow price of the aggregate land balance
   — a scarcity rent on land — is already latent in any case that carries an equality land
   closure. The identical rail is demonstrably working for inequality UDCs (four
   `UDC1_...csv` files exist in the demo's solved output).

2. **The SAM already carries a land rent.** OG-PHL ships `ogphl/data/002_IFPRI_SAM_PHL_2018_SAM.csv`
   — a full 107×108 IFPRI SAM for the Philippines, 2018 — which has a distinct **land factor
   account `flnd`** with its own income flow.

3. **OG-Core throws it away.** `ogphl/input_output.py` sets
   `CAPITAL_ACCOUNTS = ["fcap", "flnd"]`, with the comment: *"Land income is grouped with capital
   because OG-Core has only two private factors."*

So the physical scarcity price exists in CLEWS, the economic rent exists in the SAM, and on the
OG side they are actively merged away. `unitrent` — the one missing term in IEEM eq. 3 — is
sitting on both sides of our stack, unconnected.

**This is the highest-value structural target I found**, and it is considerably more concrete
than "adopt SEEA framing".

## 6. Two corrections to my own earlier read

- **`p.io_matrix` is not an intermediate-use matrix.** It is **I×M** — a *consumption bridge*
  mapping industry outputs into consumption goods (`SS.py:277`, `structure_plots.py:402`).
  Production remains CES over K, K_g, L with **no intermediate inputs at all** (`firm.py:22`).
  So `docs/design/energy-as-production-input-spec.md` ("Option B") genuinely does need new
  structure on the firm side — it is not a data problem.
- **But the data barrier is lower than that spec implies.** The IFPRI SAM already in the repo
  contains the intermediate-use block that would populate an M×M matrix; `get_io_matrix`'s own
  docstring describes building from "direct intermediate-use cells". IEEM is a working
  demonstration of what that structure buys you. The barrier is OG-Core's firm side, not data.

## 7. What not to copy

- **Recursive-dynamic myopia.** IEEM's agents don't see the future. Our OLG perfect-foresight
  transition is the better instrument for exactly the intergenerational and fiscal questions
  DESA cares about. Don't trade that away for sector coverage.
- **The 5-year time step.** Fine for land; too coarse for energy dispatch or fiscal transitions.
- **GAMS.** Our one-command, free-solver, Apache-2.0 install is a real advantage with ministries.
- **Representative households.** IEEM cannot produce cohort or lifetime-welfare incidence.
  We can.

## 8. Recommended sequence

Ordered by value per unit of effort. Nothing here is started.

**(a) Land/resource shadow price → `unitrent`.** Add an equality land-closure UDC to a case that
lacks one, solve, confirm `UDC2_UserDefinedConstraintEquality.csv` appears, and read the land
rent. This unlocks eq. 3 and is the entry point for everything in §5. Cheapest real win.

**(b) Fix the UDC dual unit rule.** `Duals.json` gives `UDCI_d`/`UDCE_d` a `unitRule` of
`{"var": "number"}` — dimensionless. A land shadow price would render unitless in the Pivot.
This is the same bug class as #432 (just fixed for the energy-balance dual, commit `da372bdc`,
`EmiUnit`→`CommUnit`). Small, self-contained MUIOGO issue.

**(c) Genuine savings as a published indicator.** Terms are proven computable (§3). The
`ENV_WATER` publication rail already carries a proper provenance envelope — SHA256 manifests of
every input CSV and every modified view file
(`documentation/environmental_water_pivot_publication.json`). Ship it on that rail. Note the
Pivot **cannot compute derived quantities**: the indicator schema
(`DefaultObj.Class.js:238-256`) has no formula field, so this must be computed externally and
published, exactly as ENV_WATER is. Giving indicators a formula field is the right structural
fix, and is a well-scoped piece of work in its own right.

**(d) Composite BII.** Nearly free once (c)'s rail exists — it is an area-weighted mean over land
cover we already produce. Needs real PREDICTS coefficients for the country, which is a data task,
not a modelling one.

**(e) InVEST on CLEWS land output.** The genuinely new capability. Needs a downscaling step
(CLEWS land is aggregate; InVEST wants rasters). Biggest effort, and the one that would let us
claim ecosystem services outright. Worth scoping only after (a)–(d).

**(f) Split `flnd` out as a distinct factor in OG-Core.** The deep one. Large, touches OG-Core's
firm side, and shares that surface with the unbuilt Option B — so scope them together or not at
all.

Sequencing note: (c) needs national-accounts aggregates from OG-Core, which is what MUIOGO
PR #498 (OG-Core ingestion pipeline, draft) would provide. Worth coordinating rather than
building a parallel path.

## 9. Repo state this was assessed against

- **MUIOGO** `main` — OG-Core integration on main is *install and register a country repo as a
  subprocess*, nothing more. No frontend (PR #492), no calibration actions (#495), no run
  pipeline (#498, draft, +4106/−0). Verified: no `ogcore` references anywhere in `WebAPP/App`.
- **ogclews-link** `main` @ `c24eb7a` — 11 channels (not the 6 STATUS.md claims), plain functions
  with no ABC/registry. Loop closure is **one-pass**: `clews_driver.py` proves the CLEWS re-solve
  mechanism standalone but is not wired into `framework.run`, and `grep clews_runner` returns
  nothing. No land, water, natural-capital or wealth representation anywhere — code or docs.
- **STATUS.md is substantially stale** on architecture (see the audit findings: no `Runner` class,
  no `_calibration.py`, M/I discovered at runtime not hardcoded). It should be re-based on the
  code before anyone new reads it as current.

## Sources

Primary: Banerjee, Cicowiez, Malek, Verburg, Vargas & Goodwin (2020), *The value of biodiversity
in economic decision making: Applying the IEEM+ESM approach to conservation strategies in
Colombia*, IDB Working Paper IDB-WP-01193 — equations 1–3 and the §2 methods are read directly
from this paper. <https://hdl.handle.net/10419/237479>

Supporting: [IEEM User Guide](https://publications.iadb.org/en/integrated-economic-environmental-modeling-platform-ieem-ieem-platform-technical-guides-user-guide)
· [OPEN IEEM portal](https://openieem.iadb.org/)
· [CEDLAS platform overview](https://www.cedlas.econo.unlp.edu.ar/wp/en/the-open-ieem-platform-comprehensive-tools-for-integrating-natural-capital-and-ecosystem-services-in-evidence-based-public-policy-and-investment-design/)
· [Open-IEEM GitHub org](https://github.com/Open-IEEM)
· [Guatemala SDG application](https://www.sciencedirect.com/science/article/abs/pii/S0921800918303082)
· [Rwanda Green Growth application](https://www.sciencedirect.com/science/article/abs/pii/S0048969720322968)
