# OG-CLEWS integration — running status & coordination

**Purpose of this file:** the single living document for coordinating work on the OG-Core ⇄
CLEWS/OSeMOSYS soft-link across sessions, agents, and accounts. If you are a new agent with
only repo access, **read this top-to-bottom first** — it carries the context that isn't
obvious from the code. Keep it current: update the *Current state*, *Work plan*, and
*Changelog* as you go.

- **Last updated:** 2026-06-16
- **Code repo (this one):** `~/Projects/ogclews-link` (git). The orchestrator + channels live here.
- **Docs repo:** `~/Projects/ogclews-schema` (NOT git) — the de novo analysis & correspondence.
- **Note on the name "ogclews-integration":** there is no such directory locally; the integration
  code is *this* repo (`ogclews-link`). If a separate `ogclews-integration` repo is intended,
  this doc + the code move trivially.

---

## 1. What this is

We are building a **soft-link** between two models: **OG-Core** (an overlapping-generations
macro model; Philippine calibration = OG-PHL) and **CLEWS/OSeMOSYS** (a least-cost energy-land-
water LP, run/served by **MUIOGO**). Quantities flow macro→energy, prices/duals flow
energy→macro; the fixed point is where the marginal value of energy demand = its marginal cost
of supply. The economically load-bearing signal is the **dual of the OSeMOSYS commodity-balance
constraint** (the marginal energy price), not a TFP knob — OG-Core has no energy in production,
so coupling acts through the household energy-price wedge, fiscal closure, and demographics.

## 2. Architecture (decided)

`ogclews-link` is **the orchestrator**. It owns the experiment, the channels, the solve
sequencing, the iteration loop, convergence, and output/scenario management.

```
   you invoke ──▶ ┌──────────────────────────────────────┐
  (CLI / thin     │             ogclews-link             │  THE ORCHESTRATOR
   script /       │  experiment · channels · loop ·      │
   MUIOGO hook)   │  convergence · scenario/output mgmt  │
                  └──────────────┬───────────┬───────────┘
                   in-process    │           │   files + subprocess
                   (import)      ▼           ▼   (read run dir; re-solve)
                        ┌──────────────┐  ┌────────────────────┐
                        │ OG-PHL/ogcore│  │  CLEWS / OSeMOSYS   │
                        │  (untouched) │  │ via MUIOGO / solver │
                        └──────────────┘  └────────────────────┘
```

Decisions (do not relitigate without reason):
- **OG-PHL (and every OG country repo) stays standalone and UNTOUCHED.** ogclews-link is a
  *non-invasive consumer*: it `import`s `ogphl`/`ogcore` and drives them; it never edits OG-PHL's
  source or pyproject. It runs *inside* the OG-PHL uv venv (via `PYTHONPATH` today), which already
  provides ogcore+ogphl. "Repo vs venv": editing `.venv` (or PYTHONPATH) is fine; editing OG-PHL's
  tracked files is not.
- **Asymmetric driving:** OG is driven **in-process** (channels mutate live `Specifications`;
  health recomputes demographics via `ogcore.demographics`) — which is *why* ogclews-link must
  share the OG venv interpreter. CLEWS is driven **out-of-process**: read a run's output dir, and
  for loop-closure invoke a CLEWS solve by **subprocess** to MUIOGO/solver. You do NOT "import CLEWS".
- **MUIOGO integration = the same subprocess seam, both directions.** MUIOGO→ogclews-link (a
  ~15-line post-run hook in `API/Classes/Case/DataFileClass.py::run()`, after
  `generateCSVfromCBC()`/`generateResultsViewer()`, shelling out to the country-venv ogclews-link
  CLI and registering results in `resData.json` for the UI) and ogclews-link→MUIOGO (the
  `clews_runner` loop-closure hook) are one mechanism. Recommended integration model:
  **subprocess/CLI** (matches how MUIOGO already calls glpk/cbc; avoids fusing the light Flask
  venv with the heavy ogcore/dask/numba stack). *User has not finalized this fork — see Open
  questions.*

## 3. Current state

**Works today (validated):**
- CLEWS→OG one-way: read a CLEWS scenario, apply channels (energy_price, investment, carbon,
  health) to the OG reform, solve OG in-process, produce macro + distributional read-outs.
  Reproduced −16.6% energy demand + the income-group incidence on OG-PHL.
- OG→CLEWS producer side: og→clews channels emit CLEWS input artifacts (Demand, EmissionsPenalty,
  DiscountRate) after the OG solve.
- Figures rebuilt on an editorial theme (`style.py`): FT/Economist-grade, colorblind-safe
  palettes, kicker+claim titles, direct labels. Regenerate with `experiments/regen_figures.py`.
- **NEW (2026-06-16): the commodity DUAL is now extractable.** See §4.

**Stubbed / pending:**
- **Loop closure** (`framework.Runner` multi-pass): the iteration/damping/convergence logic is
  built, but the `clews_runner` hook that actually re-runs OSeMOSYS is unwired → multi-pass
  honestly degrades to one pass. This is the one plumbing gap to *run* the full bidirectional loop.
- **Unit/deflator bridge** (`contract.UnitMap.deflator` is a placeholder) → carbon/investment
  *magnitudes* are illustrative. Needed to *trust* quantitative claims.
- **Health channel — mortality fails ONLY in the lives-saved direction: SIGN, not magnitude;
  DECISION = make the shock accept negative targets (ACTIVE 2026-06-16).**
  A symmetric SS-only sweep (`experiments/sweep_mortality.py`, reusing the saved baseline at
  `ogclews_runs/validate_health/health/baseline` — do NOT re-solve it) is conclusive: at matched
  magnitudes **deaths-added CONVERGES** (+1,677 and +16,741 deaths/yr both solve) while **lives-saved
  FAILS** ("Steady state aggregate resource constraint not satisfied"; −1,677 and −16,800 both). So
  *reducing* mortality (cleaner air → faster population growth) breaks OG-PHL's SS at ANY magnitude —
  it is NOT the hand-roll or calibration (the hand-roll and `disease_pop` apply identical mechanics).
  The built-in `disease_pop` "works" only because it just ADDS deaths: its `brentq` brackets `[0, +∞)`
  (the COD cost-of-disease direction). The natural pollution framing (cleaner reform → fewer deaths →
  mortality DOWN) is exactly the failing direction. **DECISION (user):** investigate generalizing
  `disease_pop`/`brentq` to accept a NEGATIVE `excess_deaths` (lives-saved) target rather than a
  reframe. Suspected cause of the down-failure: OG-Core SS / open-economy closure can't converge to
  the higher `g_n` from the baseline guesses — confirm WITHOUT touching OG-Core. Morbidity (`e`,
  (T,S,J)) CONVERGES both directions and is unaffected. **GBD now sources BOTH inputs** (tested vs the
  real HIV/SA export): `health_profile.build_profile_from_gbd` → age shape h(s); NEW
  `health_profile.total_deaths_from_gbd` → the deaths-count target (GBD `Number` metric). The PHL
  ambient-PM2.5 GBD CSV still needs a manual IHME download (DATA.md; pull metric Rate + Number).
  Scripts in `experiments/`: `sweep_mortality` (symmetric SS-only sweep — the decisive one),
  `diagnose_health`, `solve_health_variants`, `test_builtin_pop`, `validate_health`. NOTE:
  j-distribution of *deaths* by income needs a model extension (mortality `rho` is (T+S,S), no j) —
  a direction the user is examining.
- **PHL-wiring debts** (portability): `runtime.build_baseline` hardcodes `ogphl` + `p.M,p.I=4,5`
  + PHL guesses AND reaches into `~/Projects/CLEWS-OG/OG_simulations` (a `sys.path` hack) for
  `PROD_DICT`/`get_pop_data`; `country.py` hardcodes absolute CLEWS paths; `cli.py` hardcodes PHL.

## 4. The duals (energy shadow price) — found + reader built

**Finding:** MUIOGO's CBC solve already emits constraint duals (`cbc ... -printing all`), the
parser keeps them, and the annual energy commodity-balance dual lands at
`WebAPP/DataStorage/<case>/res/<caserun>/csv/EBb4_EnergyBalanceEachYear4_ICR.csv`
(columns `r,f,y,<dual>,DiscountRate`, indexed by region/fuel/year). **No MUIOGO change is
required** for the annual per-fuel shadow price. (Timeslice duals `EBa11_EnergyBalanceEachTS5`
also exist in `results.txt` but aren't exported to CSV; a one-line `Duals.json` entry would add
them — optional.) Constraint = `EBb4_EnergyBalanceEachYear4_ICR` in
`MUIOGO/WebAPP/SOLVERs/model.v.5.4.txt`. The exported value is **discounted to start-year PV**
(`raw × (1+DR)^(y−start+0.5)`); un-discount for the raw per-year marginal.

**Reader built (`ogclews_link/signals.py`), verified against the real sample:**
- `commodity_shadow_price(source, *, fuel=None, undiscount=True, start_year=None)` → annual
  shadow-price Series for a fuel (default: electricity codes, prefix `ELC`). `source` = the CSV
  or a run/csv dir.
- `commodity_shadow_price_ratio(base_source, reform_source, *, fuel=None)` → reform/baseline
  ratio by year — the rigorous analogue of `cost_of_electricity_ratio` to drive the energy_price
  channel from the true LP dual.
- Verified: COA 2020 → 1.4834 (raw), GAS 2020 → 3.061, discount round-trip exact, self-ratio=1.0.

**What's left for the dual to be *used*:**
1. Wire `commodity_shadow_price_ratio` into the `energy_price` channel as a `price_source="dual"`
   option (replacing/augmenting the `cost_of_electricity_ratio` proxy and the controlled +20% shock).
2. Point it at a real run's CSV dir — needs the **MUIOGO-run reader / scenario source** (today
   `country.scenario` points at CLEWS-OG `v6-*` dirs, not MUIOGO `res/<caserun>` dirs).
3. Confirm the PHL electricity fuel code (demo uses `ELC001/ELC002`) and units vs the OG good.

## 5. Work plan (deployment framework, MVP-first)

Status: `[x]` done · `[>]` next · `[ ]` todo

- `[x]` Dual reader (`signals.commodity_shadow_price` / `_ratio`) — built + verified.
- `[~]` **Package:** console entry point (`ogclews-link = ogclews_link.cli:main`) **DONE** +
  `run` extra confirmed; `uv.lock` (make uv-native) still TODO.
- `[~]` **Config + manifest:** `--clews-run <dir>` flag + run manifest (`manifest.py`: country,
  scenario, channels+opts, CLEWS run dir, ogcore version, timestamp, provenance) **DONE**;
  moving country/scenario config out of `country.py` into a TOML registry still TODO.
- `[ ]` **CountryProvider seam:** factor `runtime.build_baseline` into a per-country provider;
  PHL provider wraps today's logic; **relocate `PROD_DICT` + `get_pop_data`** out of
  `CLEWS-OG/OG_simulations` INTO ogclews-link (kills the `sys.path` hack; keeps OG-PHL untouched).
- `[~]` **MUIOGO-run reader:** `muiogo_run.py` **DONE** (locate a run's `res/<caserun>/csv/`,
  list `ELC*` fuels, verify the EBb4 dual export is present — verified against the real
  `CLEWs Demo/res/REF` sample); a full scenario-source adapter (other channels + `genData.json`,
  vs the CLEWS-OG xlsx layout) still TODO.
- `[x]` **Wire the dual** into the energy_price channel (`price_source="dual"`) — share-diluted
  into the OG energy good like the cost-index path, with an empty/all-NaN guardrail.
- `[ ]` **MUIOGO post-run hook** (in the MUIOGO fork): subprocess the CLI + register output.
- `[ ]` **Loop closure:** wire `clews_runner` (invoke a MUIOGO CLEWS re-solve) so multi-pass
  iterates to a fixed point with the dual feedback.
- `[ ]` **Validation:** run the full 4-step batch (`experiments/run_across_steps.py`) — confirms
  rebuilt health convergence + regenerates figures on fresh data.

## 6. Repo / file map (`ogclews_link/`)

- `framework.py` — Channel ABC + registry + `ExperimentContext` + **`Runner`** (orchestration;
  injects `build_baseline`/`solve`/`apply_health`; has the `clews_runner` loop hook).
- `channels.py` — the 6 channels (energy_price, investment, carbon, discount_rate, health, demand).
- `signals.py` — CLEWS readers + OG extractors + **`commodity_shadow_price` (the dual)**.
- `runtime.py` — the ONLY ogcore-touching layer: `build_baseline` (PHL), `solve`, `apply_health_shock`.
- `country.py` / `contract.py` — `CountryConfig` (PHL) + `ScenarioPair`/`Concordance`/`UnitMap`.
- `report.py` / `figures.py` / `style.py` / `report_html.py` — read-outs, editorial figures, HTML.
- `cli.py` — `python -m ogclews_link {list|channels|run <name>}`.
- `experiments.py` — named experiments (incl. `ACROSS_STEPS`).
- `experiments/run_across_steps.py` — the 4-step batch. `experiments/regen_figures.py` — figures only.
- `tests/test_channels.py` — transform tests (numpy-only, no solve).

## 7. How to run (env)

OG-PHL provides the venv (ogcore 0.16.1 + ogphl). Run ogclews-link inside it via PYTHONPATH —
this touches nothing in OG-PHL:

```bash
PY=/Users/mlafleur/Projects/OG-PHL/.venv/bin/python
PP=/Users/mlafleur/Projects/ogclews-link
PYTHONPATH=$PP $PY -m ogclews_link channels                 # list channels
PYTHONPATH=$PP $PY tests/test_channels.py                   # transform tests (no solve)
PYTHONPATH=$PP $PY experiments/run_across_steps.py          # full 4-step solve (~minutes, multiprocess)
PYTHONPATH=$PP $PY experiments/regen_figures.py             # rebuild figures from existing pickles
```
**Dask gotcha:** use multiprocess (`num_workers=7`); the single-process threaded client starves
the event loop under numba → serial fallback. Never `--workers 1` for real runs.

## 8. Open questions / decisions pending

- **Integration model fork** (recommended: subprocess/CLI): subprocess vs in-process plugin vs
  service. *User dismissed the structured question — awaiting direction.*
- **First milestone fork:** validate-science-first vs package-first vs prove-the-MUIOGO-seam-first.
  *Awaiting direction.*
- **`ogclews-integration` repo:** does the user want a separate repo, or is `ogclews-link` it?
- **Dual specifics:** raw vs discounted shadow price for the household-facing price; PHL electricity
  fuel code + units vs the OG "Energy and water" good.

## 9. New agent / account — start here

1. Read this file + §2 architecture + §3 state.
2. Background context also lives in the user's auto-memory `og-clews-integration-state.md`
   (richer history; this repo doc is the actionable surface).
3. Env: run inside the OG-PHL venv via PYTHONPATH (§7). Don't modify OG-PHL.
4. The immediate buildable items are in §5 (Work plan). The dual reader (§4) is done and verified.
5. Update §3, §5, and §10 as you work.

## 10. Changelog

- **2026-06-16** — Investigated MUIOGO for the energy dual: it's already exported
  (`EBb4_..._ICR.csv`, CBC `-printing all`); no MUIOGO change needed. Built + verified the dual
  reader (`signals.commodity_shadow_price` / `_ratio`). Rebuilt figures on an editorial `style.py`
  theme. Wrote this coordination doc. Pending: wire the dual into the channel + a MUIOGO-run
  scenario source; the deployment-framework items in §5; the full 4-step validation run.
- **2026-06-16 (cont.)** — Wired the dual into the energy_price channel (`price_source="dual"`,
  share-diluted like the cost-index path, with an empty/all-NaN guard). Added `muiogo_run.py`
  (locate a run's `csv/`, list `ELC*` fuels, verify exports — tested against the real
  `CLEWs Demo/res/REF` sample). Added a run manifest (`manifest.py`) + `--clews-run` flag and the
  `ogclews-link` console entry point. 19/19 transform tests pass; adversarially reviewed. All
  independent of the health fix — no health-owned symbol touched.
- **2026-06-16 (health diagnosis)** — Resolved the mortality solve failure: a symmetric SS-only
  sweep proves it is **SIGN, not magnitude** — lives-saved (mortality down) fails the SS at any
  size; deaths-added converges. `disease_pop`/`brentq` only add deaths (`[0, +∞)`). **Decision
  (user): investigate generalizing the shock to accept negative (lives-saved) targets**, not a
  reframe. Added `health_profile.total_deaths_from_gbd` (GBD `Number` → deaths target) so GBD now
  supplies BOTH the age shape and the total; both readers tested vs the real HIV/SA export. 20/20
  transform tests pass. Added SS-only mode to `runtime.solve(time_path=False)`. The PHL ambient-PM2.5
  GBD CSV still needs a manual IHME download (DATA.md). Next: try negative-target `brentq` bracketing
  + confirm whether the down-failure is an OG-Core SS-closure limit (without touching OG-Core).
