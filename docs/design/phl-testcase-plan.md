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

**No solved PHL case exists on this machine.** All three portable archives ship inputs only, and
the installed case has no `res/`. Nothing can be read until someone solves it. The historical
solve happened on a different machine, so no PHL dual has ever been observed here.

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
demo. Our reader discards the mode column, so this needs a code change, not a config change.

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
appear. Building the real map is a modelling decision, not transcription: 32 technologies consume
`PHL_LND`, including a solar plant with no demo analogue, and 24 crop options must collapse into
one Cropland label.

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

**Stage 0 — fix the four bugs in §3.** Cheap, done against the demo where we have ground truth.
Make the empty-map case *raise*, not return empty.

**Stage 1 — prove the whole chain on the demo.** Read the `LND` dual with
`commodity_shadow_price(fuel="LND", drop_zero=False)`, feed it into `natural_capital_depletion`
with a genuine depletion *flow*, and get a real non-zero number. The demo has both a solved case
and a year where land actually prices (2024). This is the honest end-to-end test and it is
available today, with no PHL dependency.

**Stage 2 — solve PHL once.** The unknown is whether it solves in reasonable time.
`~/Projects/MUIOGO-AI` is the headless path — the `muiogo-provision` skill installs the case and
`muiogo-run` solves it. The country manifest `clews/countries/PHL.json` lists three cases and
marks `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC` recommended. Nothing downstream can start
until this exists.

**Stage 3 — build the PHL land map.** Real modelling judgment (see §2). Must handle
`ENV_LAND`'s 8 modes and must close on the land resource, or it is wrong.

**Stage 4 — decide whether PHL gets a binding land endowment.** *Marcelo's call, not the
assistant's.* Right now the 999999 placeholder means the land price is structurally zero and the
whole natural-capital line comes out empty. Giving the model a real national land area is what
would make the price mean anything. Not needed until stage 3 completes.

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
| `~/Projects/MUIOGO` | the GUI/solver; read-only until stage 5 |
| `~/Projects/MUIOGO-AI` | headless driver + skills; the path to solving PHL |
| `~/Projects/CLEWs-PHL` | PHL model package, v12 lineage, archives only (no solve) |
| `~/Projects/OG-PHL` | macro side; not needed before stage 5 |
| `~/Projects/OG-Core` | local checkout on `feature/structure-plots`, 15 ahead of master |
