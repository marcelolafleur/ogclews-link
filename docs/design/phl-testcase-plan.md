# PHL as the test case — findings and plan

**Status:** live plan. Start here; `ieem-comparative-assessment.md` is the background.
**Date:** 2026-08-03
**Branch:** `research/ieem-comparative-assessment` (worktree `~/Projects/ogclews-link-ieem`)

Read this before touching anything. It records a multi-repo recon whose main result was to
**invalidate the first step of the earlier plan**. Repeating that recon costs an hour; reading
this costs five minutes.

## 1. Two corrections — read these first

**(a) The land shadow price needs no new constraint.** The earlier note said to build an
equality user-defined constraint to get it. Wrong. Land is an ordinary commodity, so its balance
constraint already carries a shadow price, and MUIOGO already exports it.

Verified in the shipped demo's solved output — `WebAPP/DataStorage/CLEWs Demo/res/REF/csv/
EBb4_EnergyBalanceEachYear4_ICR.csv`:

```
RE1,LND,2020,0.0,0.05
RE1,LND,2024,26.198336460057163,0.05
```

Commodities carrying a balance shadow price in that file: `AGRWAT COA CRPMAI CRPRIC DSL ELC001 ELC002
GAS HYD LBLT LND LWAT PUBWAT PWRWAT SOL TRABIO WND WTREVT WTRGWT WTRPRC WTRRUN WTRSUR` —
land, water and crops included.

**(b) `BAL_ENV_LAND` is a dead end.** It is an accounting identity (+1 `MINLNDTOT` activity,
−1 `ENV_LAND` activity, RHS 0), not a scarcity constraint. Its shadow price is ~0 by construction.
CLEWs-PHL's own validator *requires* it to be zero. Relaxing it relaxes no physical limit.
Do not build anything on it.

## 2. State of the PHL stack, as verified

> **Superseded on 2026-08-03 (stages 0–3 done).** Three claims below no longer hold; the
> corrections are in §8. In short: a solved PHL case **does** now exist, in the headless
> `muiogoai` world; the land shadow price **has** been observed and is the placeholder's token cost;
> and the land map is built. Read §8 with this section.

**~~No solved PHL case exists on this machine.~~** *(superseded — see §8.)* All three portable
archives ship inputs only, and the case installed under `~/Projects/MUIOGO` has no `res/`.
The historical solve happened on a different machine.

**Land is not scarce in the PHL model.** `MINLNDTOT` carries
`TotalTechnologyAnnualActivityUpperLimit` and `TotalAnnualMaxCapacity` of 999999 for every year,
zero capital/fixed cost, and a token variable cost of 0.0001. So the land shadow price will come out at
or near zero — an artefact of the placeholder bound, not a statement about Philippine land.

**The constraint that actually binds is not exported.** Scarcity lives on the eight
`LNDAGRPHLC01–08` cluster activity upper limits, which bind exactly (they sum to 295.8131 against
a solved terminal activity of 295.8132). Those are `TotalTechnologyAnnualActivityUpperLimit`
bounds — the `AAC*` constraint family — whose shadow prices are **not** among the three families in
`WebAPP/DataStorage/Duals.json`. This is the real, well-scoped MUIOGO gap.

**PHL land-cover state lives in `ENV_LAND`'s 8 modes**, not in separate technologies as in the
demo. ~~Our reader discards the mode column~~ — fixed in stage 0; `LandMap.mode_classes` now
carries the mode-level map, and §8 records the verified assignment.

**The land block is explicitly uncalibrated.** `documentation/KNOWN_LIMITATIONS.md` in CLEWs-PHL
states it "has not been calibrated to observed historical land allocation, yields, irrigation
withdrawals or water balances"; vegetables use a GAEZ tomato proxy. Any PHL land number from this
model is a mechanism check, never a result.

**`Base_v12` and `PEP_v12` land accounts are bit-identical** in every row and year. The two
available runs give no land-side contrast; any land variation must come from a new scenario.

**No land-carbon accounting exists.** Zero land technologies carry an `EmissionActivityRatio`;
the only emissions are CO2e and PM2_5 on 33 energy/transport/industry technologies. A land-use
carbon term cannot be computed from this model as it stands.

**Naming — the demo mapping will silently match nothing on PHL.** PHL uses `MINLNDTOT`,
`PHL_LND`, and `LND*TOT`/`L*TOT` codes. The demo's `RSCLND`/`LNDFOR`/`LNDBLT`/`LNDWAT` do not
appear. ~~Building the real map is a modelling decision, not transcription: 32 technologies
consume `PHL_LND` … and 24 crop options must collapse into one Cropland label.~~ *(Partly
superseded — see §8.)* Going through `ENV_LAND`'s modes turned out to make this much easier
than feared: the model has **already** collapsed the 24 crop options into a single `CROPLAND`
mode, so no crop-aggregation judgment was needed. The mode→class assignment is transcription
after all — readable straight off the solved run's generated input.

**Size.** The installed diagnostic case is ~500 MB unpacked (`RYTM.json` 115 MB,
`RYTCM.json` 95 MB). `clews_driver.copy_case` does a full `copytree`, so each experiment copy
costs that. Not fatal, but not the ~MB the demo trains you to expect.

## 3. Bugs in our own code, found by the recon

All four are in `ogclews_link/env_accounts.py` unless noted. None are fixed yet.

1. **An empty land map fails silently** (`env_accounts.py:150`). `PHL_V12_LAND_MAP` has an empty
   `classes` dict, so pointing the probe at PHL returns `({}, {})` and prints "no land output" —
   which reads as *the case has no land* rather than *your map is wrong*. Highest-risk item,
   because it defeats the closure check that was supposed to catch exactly this.
2. **`emissions_damage` sums all emission species.** On PHL that prices PM2_5 at the social cost
   of carbon. Needs a species filter. The existing test does not catch it because its fixture is
   CO2-only.
3. **Mode is discarded** in `land_use_by_year`. Harmless on the single-mode demo; on PHL the
   cover-class vector lives in `ENV_LAND`'s 8 modes, so a mode-blind read is wrong.
4. **Stock passed where eq. 3 wants a flow.** The probe feeds forest *area* into
   `natural_capital_depletion`, which wants *quantity depleted*. Currently harmless because rents
   are empty; the moment rents are supplied it silently produces a wrong number.

Also, in existing code: **`signals.commodity_shadow_price` defaults to `drop_zero=True`**, which
treats a zero shadow price as missing. For land that is economically wrong — a zero rent is a true zero
(land was abundant) and belongs in the present-value sum. On the demo it would drop 15 of 16 years.

## 4. The OG side is independent — and not ready

The land price, biodiversity index and carbon-damage term all come from CLEWS alone. **Nothing on
the OG side blocks stages 0–5 below.** The macro model is needed only for the full genuine-savings
figure, which is late.

Do not build on either PHL calibration yet:

- **OG-PHL PR #85** (new calibration) is a **draft**, and needs **OG-Core #1189**, which is open,
  unmerged, and in no release (latest 0.18.1 predates it). Its headline parameter moved
  0.823 → 2.677 → 2.783 within its own commit series.
- **OG-PHL PR #63** (multi-industry M=8) is **CONFLICTING / CHANGES_REQUESTED** against main.
- **The two are not composable** today; both branch off main independently and neither contains
  the other.
- **No OG-Core PR or issue self-identifies as a Philippine blocker.** If a plan says "we are
  waiting on PR X", that PR does not exist as such.

Confirmed on the OG-Core side: production is a three-input CES over K, K_g, L (`firm.py:22`) —
no land, no natural resource, no intermediates. `p.io_matrix` is I×M (a consumption bridge), not
an M×M use matrix. Two private factors only.

## 5. The plan

**Stage 0 — fix the four bugs in §3. DONE** (2026-08-03, commit `7049079`). The empty map now
raises; `emissions_damage` requires a species; mode-level cover reading added; `depletion_flow`
added. 13 new tests.

**Stage 1 — prove the whole chain on the demo. DONE** (same commit). Non-zero depletion on all
four demo scenarios; REF = 5.7631, hand-checked against 21.034 × 0.3082 / 1.04³.

**Stage 2 — solve PHL once. DONE — it was already solved.** No solve was launched: the headless
`muiogoai` world already carries two CBC-Optimal runs of
`Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC`, solved 2026-08-03 at install time and clean under
`muiogo verify`. See §8. The stage's open question — does it solve in reasonable time — is
answered: about 2.5 minutes from input generation to results.

**Stage 3 — build the PHL land map. DONE** (see §8). Verified against the solve: closes on
`MINLNDTOT` to 0.00e+00 at both endpoints and ≤1e-4 across all 34 years.

**Stage 4 — decide whether PHL gets a binding land endowment.** *Marcelo's call, not the
assistant's.* **Read §9 before deciding: the premise of this stage is wrong.** PHL already has a
binding, realistically-sized land endowment — eight cluster limits that bind exactly and sum to
the true national area. Adding a national land total would duplicate their sum, never bind, and
leave its shadow price at ~0. The actual obstacle is a `-10.0` variable cost on the land clusters that
dominates their shadow prices. `MINLNDTOT`'s shadow price really is a meaningless 1.0e-4 (§8), but that is
because `MINLNDTOT` is not where land scarcity lives.

**Stage 5 — export the binding shadow prices.** Get the `AAC*` activity-limit shadow prices into `Duals.json`.
Genuine MUIOGO work, useful well beyond this project. Note `Duals.json` is one of only four
tracked files under `WebAPP/DataStorage/`, so this one *does* touch MUIOGO's repo.
**No longer a blocker for us:** the `AAC2` shadow prices are already written to `res/<run>/results.txt`
by every solve, so we can read them today without touching MUIOGO at all (§9). Stage 5 is now a
convenience — worth doing for MUIOGO's other users, not needed for this project.

## 6. Ground rules that still hold

- **MUIOGO stays untouched** through stages 0–4. Case data is gitignored
  (`.gitignore:51`, `WebAPP/DataStorage/*` minus four config files), and `clews_driver.copy_case`
  sandboxes by copying. Only stage 5 touches MUIOGO's repo.
- **Nothing is pushed.** Two commits sit on this branch; all other repos are clean.
- **`AGENTS.md` in this repo is load-bearing** — verify branch + HEAD + what the interpreter
  actually imports before any solve. It was written after a battery ran stale code via import
  shadowing.

## 7. Repos in play

| Repo | Role |
|---|---|
| `~/Projects/ogclews-link-ieem` | this worktree — where the work happens |
| `~/Projects/ogclews-link` | main checkout, branch `main` |
| `~/Projects/MUIOGO` | the GUI/solver; read-only until stage 5. **Holds the solved demo case.** |
| `~/Projects/MUIOGO-AI` | headless driver source |
| `~/muiogoai` | **the installed headless world — holds the solved PHL case.** Reach it only through the `muiogo-ai` launcher |
| `~/Projects/CLEWs-PHL` | PHL model package, v12 lineage, archives only (no solve) |
| `~/Projects/OG-PHL` | macro side; not needed before stage 5 |
| `~/Projects/OG-Core` | local checkout on `feature/structure-plots`, 15 ahead of master |

## 8. Stage 2–3 findings (2026-08-03)

### The solved PHL case, and where it lives

The solve exists in the **installed `muiogoai` world**, which is a different place from the
`~/Projects/MUIOGO` checkout §2 was written about — that checkout still has no PHL `res/`, so
§2 was not wrong, just looking in the only place that existed at the time.

```
world:  muiogoai (installed)   workspace ~/muiogoai   MUIOGO detached at 928a13bb
case:   Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC   (2.3 GB unpacked)
runs:   BASE_CHK, Base_v12 — both CBC "Optimal", objective 375930821.34, 24 csv files
verify: `muiogo-ai verify --case … --run Base_v12` → "On-disk results still match the record."
```

Only the `BASE` scenario is active; `PEP_v12` is defined but unsolved, so there is still no
land-side scenario contrast (§2's point stands).

Reach the case with `muiogo-ai case-path --case '<name>'`, never by composing a path — a
same-named case in the other world is exactly how the wrong data gets read.

**Trap for the next reader.** `RUN.json`'s `results_sha256` digests the **`csv/` directory**
(each filename plus each file's hash), *not* `results.txt`. Hashing `results.txt` and comparing
looks like an integrity failure when nothing is wrong. Use `muiogo-ai verify`.

### The verified mode → cover-class map

Read off `res/Base_v12/data.txt`, where `param InputActivityRatio` carries one slice per
commodity with the mode as its row index, all ratios 1:

| mode | commodity | label | 2020 | 2053 |
|---:|---|---|---:|---:|
| 1 | `ENV_LND_FOREST` | Forest | 179.7818 | 136.5595 |
| 2 | `ENV_LND_GRASSLAND` | Grassland | 0 | 0 |
| 3 | `ENV_LND_OTHER` | Other | 0 | 0 |
| 4 | `ENV_LND_BARREN` | Barren | 0 | 0 |
| 5 | `ENV_LND_BUILT` | Built-up | 0.7698 | 1.0458 |
| 6 | `ENV_LND_WATER` | Water bodies | 1.5984 | 1.5984 |
| 7 | `ENV_LND_CROPLAND` | Cropland | 113.6631 | 156.6094 |
| 8 | `PHL_LND` | Unallocated | 0 | 0 |

Mode 8 consumes the land resource *directly* rather than a cover tag, so it is untagged land and
belongs in the closure sum: `MINLNDTOT = modes 1–7 + mode 8`. It is identically zero here (all
land is tagged) but is mapped explicitly so that if it ever goes positive it surfaces as area
rather than breaking closure for no visible reason.

Closure: 0.00e+00 at both endpoints, ≤1e-4 over all 34 years. The whole horizon is one story —
forest → cropland, −43.22 against +42.95 — with built-up taking the small remainder.

### Why stage 4 is now the binding decision

| | demo (`REF`) | PHL (`Base_v12`) |
|---|---:|---:|
| land shadow price, max undiscounted | 2.10e+01 | **1.00e-04** |
| years priced | 1 of 16 | 6 of 34 |
| eq. 3 depletion PV | 5.7631 | **0.0008** |

The PHL figure is not a small rent, it is *not a rent*: 1.0e-4 is precisely `MINLNDTOT`'s token
variable cost, and it sits an order of magnitude below CBC's 1e-3 shadow-price reporting resolution
(`signals._MARGINAL_ZERO_ATOL`). All seven `ENV_LND_*` cover-tag commodities have **identically
zero** shadow prices across all 34 years — they are pure accounting tags with no scarcity content, so
there is no better commodity to read instead.

The clincher is degeneracy: `BASE_CHK` and `Base_v12` are the same model at the same optimum
(objectives agree to 8 significant figures) with identical land in every year, yet they report
the token shadow price in **different years** — 2020/21/22/24/25/27/31/33 versus 2021/22/23/28/31/33.
A shadow price that moves between alternate optima while nothing physical changes is noise. The probe now
prints a `[!]` warning whenever every nonzero rent is ≤1e-3, so this cannot be mistaken for a
result later.

### Calibration warning, restated with numbers

Structurally right, numerically not credible. Base_v12 puts **61%** of national area under forest
against roughly 24% observed, **770 km²** under built-up (an order of magnitude low), and leaves
Grassland, Barren and Other at exactly zero for all 34 years. Total land 295,813 km² against
~298,170 km² actual is the one number that looks right. Mechanism checks only — never a
Philippine result. The illustrative BII moves 0.7945 → 0.7358 (−7.4%); the *direction* follows
from forest→cropland conversion and is believable, the level is not.

## 9. The land price is already on disk — and it is mostly a parameter (2026-08-03)

This section **reframes stage 4** and demotes stage 5. Read it before deciding either.

### `results.txt` carries every constraint shadow price, `AAC2` included

`res/<run>/results.txt` is CBC's full solution dump — 1.69M lines for PHL — and it lists
constraint rows with their shadow prices, not just variables. Column 4 is the shadow price.

Verified against MUIOGO's own export rather than assumed: for
`EBb4_EnergyBalanceEachYear4_ICR`, column 4 reproduces the shipped
`csv/EBb4_…csv` values across **848** (commodity, year) pairs above the 1e-3 shadow price resolution,
to a worst relative error of 3.0e-4 — which is the 8-significant-figure print precision, not a
discrepancy. The two differ only by MUIOGO's convention `csv = raw × (1+DR)^(y − sy + 0.5)`.

So the `AAC*` family that §2 correctly identified as unexported is **not unavailable**. It is
sitting in a file every solve already writes. Stage 5 would make it convenient for MUIOGO's
other users; it is not on our critical path.

### The eight clusters bind exactly and partition national land

`TotalTechnologyAnnualActivityUpperLimit` on `LNDAGRPHLC01–08` is flat across all 34 years, and
solved activity equals the limit in every one. Their 2020 areas sum to **295.8131** — identical
to `MINLNDTOT` and to `ENV_LAND`'s all-mode total, gap `+0.0000`. These eight limits *are* the
Philippine land endowment, at a realistic 295,813 km² against ~298,170 km² observed.

Every cluster carries a nonzero `AAC2` shadow price in all 34 years, of order 10 — against `MINLNDTOT`'s
1.0e-4. That is why stage 4's premise fails: **land is already scarce in this model.** A new
national land constraint would equal the sum of the cluster limits, so it would never bind and
its shadow price would stay at zero.

### …but ~97% of that shadow price is a `-10.0` variable cost

All eight clusters carry `VariableCost = -10.0` in mode 27 — a *negative* cost, i.e. a reward of
10 per unit of activity. Mode 27 stays available whether or not it is used, so it puts an
**opportunity-cost floor of 10.0 under every cluster's land shadow price**. Netting it out:

| cluster | area | shadow price (PV) | real shadow price | − floor | genuine scarcity |
|---|---:|---:|---:|---:|---:|
| `LNDAGRPHLC01` | 9.1115 | −9.7586 | 9.9996 | 10.0 | **−0.0004** |
| `LNDAGRPHLC02` | 23.6817 | −10.1012 | 10.3507 | 10.0 | **0.3507** |
| `LNDAGRPHLC03` | 103.2149 | −9.7586 | 9.9996 | 10.0 | **−0.0004** |
| `LNDAGRPHLC04` | 27.3872 | −9.7586 | 9.9996 | 10.0 | **−0.0004** |
| `LNDAGRPHLC05` | 27.1799 | −10.2535 | 10.5068 | 10.0 | **0.5068** |
| `LNDAGRPHLC06` | 18.7069 | −10.0370 | 10.2849 | 10.0 | **0.2849** |
| `LNDAGRPHLC07` | 18.3850 | −9.7586 | 9.9996 | 10.0 | **−0.0004** |
| `LNDAGRPHLC08` | 68.1460 | −9.7585 | 9.9995 | 10.0 | **−0.0005** |

Five of eight sit at 10.0000 to four decimals — they bind on the reward alone, with no scarcity
content. Only clusters 02, 05 and 06 carry a genuine premium, 0.28–0.51, over 69.57 of 295.81
(**23.5%** of national land). Coherence check: the clusters that price are a minority, which is
consistent with cropland expanding into abundant forest rather than against a hard limit.

**Taking the `AAC2` shadow price at face value overstates the marginal *scarcity* value of land by
20× to 35×** — but the floor is not noise; §10 shows it is the model's entire valuation of forest.
Shadow prices are negative because these are upper limits in a minimization; use the absolute value.

### What this means for the decision

1. **Do not add a national land endowment.** It would be redundant against the cluster limits and
   would price at zero. Stage 4 as written would not produce a land price.
2. **Interrogate the `-10.0` first.** ✅ **Answered — see §10.** Not a numerical device: it is the
   model's *only* representation of the economic value of standing forest, and it is a hardcoded,
   undocumented constant.
3. **A defensible scarcity premium exists today** for 23.5% of national land, over and above the
   forest valuation — small, positive, and confined to three clusters.
4. **Do not build the extractor yet.** Any `results.txt` shadow-price reader has to commit to a
   treatment of the forest floor, and after §10 that is a disclosure decision, not a coding one.

Unverified and flagged: the cluster→cover-class correspondence is not established, so these
per-cluster rents cannot yet be attributed to Forest or Cropland — which eq. 3 needs. Cluster 02
runs in modes 3/24/30 and cluster 03 in 8/11/26/27/30, so the mode structure is richer than the
single-mode floor story and deserves its own read before the rents are used per class.

## 10. What the `-10.0` is for (2026-08-03)

**Short answer: it is the model's only representation of the economic value of standing forest,
and it is a hardcoded constant with no source, no units and no documentation.**

### Where it comes from

`CLEWs-PHL/Philippines_v12_CLEWs_build/overrides/workflow/scripts/clewsy.py:449-467`, in the
model-*generation* step — so it is baked in before MUIOGO ever sees the case:

```python
# Negative variable cost for forest:
...
value = -10
mode = ModeList.index('Forest land')+1
```

That comment is the entire rationale on record. It confirms mode 27 = `Forest land`, and applies
`-10` to every land cluster, every year. Nothing in `documentation/`, `data_sources/` or
`KNOWN_LIMITATIONS.md` mentions it — I searched. It is not in the assumption register, so it has
never been through the source-traceability discipline the rest of the build follows.

### Why the model needs it

`clewsy.py:410-411` is the key. When writing mode-level lower limits it does:

```python
if col in ['Cropland', 'Forest land', 'Other agricultural land']:
    continue
```

So Built-up, Water, Grassland and Barren are **pinned** by lower limits — Built-up growing with
population — while Cropland, Forest and Other are left **free** for the optimiser. That is exactly
the behaviour observed: Water/Grassland/Barren perfectly flat over 34 years, Built-up drifting up
+0.28, and all the movement in forest (−43.22) against cropland (+42.95).

Forest mode consumes `LFORTOT` (from `LNDFORTOT`) plus precipitation and outputs only water flows —
evapotranspiration, surface runoff, groundwater recharge. **It produces no crop commodity**, so it
satisfies no demand and, to a cost-minimiser, has no value whatsoever. Without the `-10` the
optimiser would convert the entire free margin to cropland at zero cost. The `-10` is the only
brake on deforestation in the model.

### How thin the land economics actually is

In the whole PHL model, the `-10` on those 8 clusters is the **only** variable cost on any land,
crop or agricultural technology — 8 rows, and nothing else. **Crop production is costless in the
objective.** So the land-allocation economics reduces to: *forest pays 10, crops are free, and
cropland expands only as far as crop demand forces it.*

Contrast the shipped demo, which has a genuine trade-off — crops at 42/53/57/77 against forest at
`-29.4`, and forest is likewise the sole negative cost in that model. So the negative-cost-for-
forest idea is a **CLEWs convention, not a PHL invention**; what PHL lost is the crop cost side.

### Units, inferred

Not documented. Inferring from `PHL_POW_PP_COAL` capital cost = 2200, which is USD/kW at any
plausible reading, costs are MUSD and capacity GW. Land activity is `10^3 km2` (stated in
`ENVIRONMENTAL_ACCOUNTING.md:237`). So:

> `-10` MUSD per `10^3 km2` per year = **−100 USD/ha/yr** for holding land as forest.
> (Demo, for comparison: `-29.4` → −294 USD/ha/yr.)

$100/ha/yr is not an absurd figure for tropical-forest ecosystem services, which is the trap — it
is plausible enough to pass unchallenged, and it was never derived.

### What it means for our accounts

**The natural-capital depletion term is a linear function of this constant.** Double it and forest
loss is valued twice as highly *and* less of it happens. IEEM's whole premise for eq. 3 is that the
unit rent is endogenous to the CGE; here it is a magic number in a build script. Consequences:

- **Land cover and the biodiversity index shape are unaffected** — they are physical areas, and
  they still close exactly. Those two deliverables stand.
- **Natural-capital depletion cannot be published from this model without disclosing that its unit
  rent is an undocumented assumed constant.** That is a disclosure obligation, not a bug.
- **The right economic reading of the land shadow price** is
  `max(forest value, marginal agricultural value)`. Netting out the 10 gives the excess of
  agriculture over forest, which is a real number (0.28–0.51 on 3 clusters); the 10 itself is a
  policy/valuation parameter, not a scarcity signal.
- **Concept mismatch to flag:** `-10` is an annual value per unit *area*, whereas ANS-style forest
  depletion prices a *stock* (timber resource rent per unit harvested). Multiplying area lost by
  10 gives the annual rental value forgone, not the capitalised stock loss. Capitalising would mean
  `10/r`. Which of the two eq. 3 wants is a definitional choice worth settling explicitly.

### The question this raises for stage 4

Stage 4 was "should PHL get a binding land endowment?" It already has one. The real question is
narrower and more answerable: **should the forest valuation be derived rather than assumed?** If
yes, that is a calibration task with a literature (forest ecosystem-service valuation for the
Philippines) and it would make the natural-capital line defensible. If no, everything downstream
carries an undocumented `-10` and must say so.
