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
constraint already carries a dual, and MUIOGO already exports it.

Verified in the shipped demo's solved output — `WebAPP/DataStorage/CLEWs Demo/res/REF/csv/
EBb4_EnergyBalanceEachYear4_ICR.csv`:

```
RE1,LND,2020,0.0,0.05
RE1,LND,2024,26.198336460057163,0.05
```

Commodities carrying a balance dual in that file: `AGRWAT COA CRPMAI CRPRIC DSL ELC001 ELC002
GAS HYD LBLT LND LWAT PUBWAT PWRWAT SOL TRABIO WND WTREVT WTRGWT WTRPRC WTRRUN WTRSUR` —
land, water and crops included.

**(b) `BAL_ENV_LAND` is a dead end.** It is an accounting identity (+1 `MINLNDTOT` activity,
−1 `ENV_LAND` activity, RHS 0), not a scarcity constraint. Its dual is ~0 by construction.
CLEWs-PHL's own validator *requires* it to be zero. Relaxing it relaxes no physical limit.
Do not build anything on it.

## 2. State of the PHL stack, as verified

> **Superseded on 2026-08-03 (stages 0–3 done).** Three claims below no longer hold; the
> corrections are in §8. In short: a solved PHL case **does** now exist, in the headless
> `muiogoai` world; the land dual **has** been observed and is the placeholder's token cost;
> and the land map is built. Read §8 with this section.

**~~No solved PHL case exists on this machine.~~** *(superseded — see §8.)* All three portable
archives ship inputs only, and the case installed under `~/Projects/MUIOGO` has no `res/`.
The historical solve happened on a different machine.

**Land is not scarce in the PHL model.** `MINLNDTOT` carries
`TotalTechnologyAnnualActivityUpperLimit` and `TotalAnnualMaxCapacity` of 999999 for every year,
zero capital/fixed cost, and a token variable cost of 0.0001. So the land dual will come out at
or near zero — an artefact of the placeholder bound, not a statement about Philippine land.

**The constraint that actually binds is not exported.** Scarcity lives on the eight
`LNDAGRPHLC01–08` cluster activity upper limits, which bind exactly (they sum to 295.8131 against
a solved terminal activity of 295.8132). Those are `TotalTechnologyAnnualActivityUpperLimit`
bounds — the `AAC*` constraint family — whose duals are **not** among the three families in
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
treats a zero dual as missing. For land that is economically wrong — a zero rent is a true zero
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
assistant's.* **Stage 3 is now complete, so this is the live decision.** The prediction that the
land price would be structurally ~zero is confirmed with numbers: the `PHL_LND` dual peaks at
1.0e-4 — exactly `MINLNDTOT`'s token variable cost, and one order of magnitude *below* CBC's
1e-3 dual-reporting resolution — so eq. 3 returns 0.0008, a number with no economic content.
The two runs disagree about *which* years even carry that token dual, which is LP degeneracy
and independent proof there is no signal there (§8). Giving the model a real national land area
is what would make the price mean anything.

**Stage 5 — export the binding duals.** Get the `AAC*` activity-limit duals into `Duals.json`.
Genuine MUIOGO work, useful well beyond this project. Note `Duals.json` is one of only four
tracked files under `WebAPP/DataStorage/`, so this one *does* touch MUIOGO's repo.

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
| land dual, max undiscounted | 2.10e+01 | **1.00e-04** |
| years priced | 1 of 16 | 6 of 34 |
| eq. 3 depletion PV | 5.7631 | **0.0008** |

The PHL figure is not a small rent, it is *not a rent*: 1.0e-4 is precisely `MINLNDTOT`'s token
variable cost, and it sits an order of magnitude below CBC's 1e-3 dual-reporting resolution
(`signals._MARGINAL_ZERO_ATOL`). All seven `ENV_LND_*` cover-tag commodities have **identically
zero** duals across all 34 years — they are pure accounting tags with no scarcity content, so
there is no better commodity to read instead.

The clincher is degeneracy: `BASE_CHK` and `Base_v12` are the same model at the same optimum
(objectives agree to 8 significant figures) with identical land in every year, yet they report
the token dual in **different years** — 2020/21/22/24/25/27/31/33 versus 2021/22/23/28/31/33.
A dual that moves between alternate optima while nothing physical changes is noise. The probe now
prints a `[!]` warning whenever every nonzero rent is ≤1e-3, so this cannot be mistaken for a
result later.

### Calibration warning, restated with numbers

Structurally right, numerically not credible. Base_v12 puts **61%** of national area under forest
against roughly 24% observed, **770 km²** under built-up (an order of magnitude low), and leaves
Grassland, Barren and Other at exactly zero for all 34 years. Total land 295,813 km² against
~298,170 km² actual is the one number that looks right. Mechanism checks only — never a
Philippine result. The illustrative BII moves 0.7945 → 0.7358 (−7.4%); the *direction* follows
from forest→cropland conversion and is believable, the level is not.
