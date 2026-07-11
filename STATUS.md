# OG-CLEWS integration — running status & coordination

**Purpose of this file:** the single living document for coordinating work on the OG-Core ⇄
CLEWS/OSeMOSYS soft-link across sessions, agents, and accounts. If you are a new agent with
only repo access, **read this top-to-bottom first** — it carries the context that isn't
obvious from the code. Keep it current: update the *Current state*, *Work plan*, and
*Changelog* as you go.

- **Last updated:** 2026-06-17 · run instructions corrected 2026-07-01 (see banner)
- **Code repo (this one):** `~/Projects/ogclews-link` (git). The orchestrator + channels live here.
- **Docs repo:** `~/Projects/ogclews-schema` (NOT git) — the de novo analysis & correspondence.
- **Note on the name "ogclews-integration":** there is no such directory locally; the integration
  code is *this* repo (`ogclews-link`). If a separate `ogclews-integration` repo is intended,
  this doc + the code move trivially.

> ⚠️ **To RUN the coupled model, follow [`README.md`](README.md)** — the authoritative, current end-to-end
> walkthrough (`ogclews-link run coupled`). This is a historical coordination doc: several sections below
> **predate the current cross-env architecture** and are superseded. The link now runs in its OWN venv and
> subprocesses the OG model's interpreter via a model **registry** (ogcore **0.16.3**, M=8, `run coupled`) —
> not "inside the OG-PHL venv via PYTHONPATH". In particular §2's in-process/in-venv driving, §3/§6's
> `Runner` class and "6 channels" framing, and §7's `PYTHONPATH … run_across_steps.py` method are out of
> date; §7 has been corrected to point at the current command.

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
- **NEW (2026-06-17): the health channel SOLVES end-to-end (mortality + morbidity), DECOMPOSED.**
  The full 4-step suite (energy price → +investment → +carbon → +health) converges on ALL steps; the
  +health step adds GDP +0.086%→+0.093%. Verified split (stacked health bar in `waterfall_gdp.png`):
  the +0.007pp is essentially ALL **morbidity** (productivity, +0.0075pp) — the **mortality**
  (lives-saved) contribution is ≈ −0.0005pp, i.e. ~0, because PHL PM2.5 deaths skew elderly (saved
  lives add retirees, not workers). So do NOT report the GDP gain as a "lives-saved" effect; it is the
  (placeholder) morbidity multiplier. See §3.

**Stubbed / pending:**
- **Loop closure** (`framework.Runner` multi-pass): the iteration/damping/convergence logic is
  built, and the **CLEWS re-run seam is now built and validated** (`clews_driver`, on branch
  `channel/clews-run-seam` / PR #14): copy a MUIOGO case, patch it via the case's own code→opaque-ID
  registry, re-solve in MUIOGO's own environment, re-read — proven on PHL v9 (+10% household-
  electricity demand → +4.28% production / +3.72% cost through MUIOGO's own pipeline; re-solving the
  same store reproduces to 0.002%). The remaining gap is narrower than before: wire `framework.run`'s
  `clews_runner` hook to that driver + add the residual-based convergence controller. Until that lands,
  multi-pass still degrades to one pass — but the re-solve *mechanism* it needs is no longer missing.
- **Unit/deflator bridge** (`contract.UnitMap.deflator` is a placeholder) → carbon/investment
  *magnitudes* are illustrative. Needed to *trust* quantitative claims.
- **Health channel — RESOLVED & HARDENED (2026-06-17): the cleaner-air (lives-saved) solve works,
  and the earlier narrative is corrected.** The lives-saved SS does NOT fail structurally; it leaves
  an INTRINSIC ~5e-7 aggregate-resource-constraint (Walras) residual on the production good. Verified
  to be a property of the converged equilibrium, NOT solver slop: invariant to a fresh re-solve
  (`reform_use_baseline_solution=False` → same 5.089e-7) AND to a 100–10,000× tighter fixed-point
  tolerance (`mindist_SS`=1e-11 and 1e-13 both → same 5.089e-7). The SS fixed point (`sol.success` @
  `mindist_SS`) and household FOCs converge tightly regardless; only the post-solve `RC_SS` *assertion*
  (ogcore `SS.py:1144`) trips. So loosening that gate IS necessary — but only for the lives-saved
  direction, and only slightly. The fix:
  - (1) `health_pop.disease_pop` — a bidirectional, NON-MONOTONE-ROBUST `disease_pop`. Accepts a SIGNED
    `excess_deaths` target (negative = lives saved, the direction the published `[0,+∞)` bracketing
    couldn't reach). The realized year-`phase_years` excess-deaths curve is not monotone in the shock
    (survivorship feedback + the 0.0 clip), so the solver scans outward from 0 to the FIRST sign change
    (smallest-magnitude root) and reports the true achievable extremum on infeasibility — a plain
    doubling-walk can falsely reject a feasible target or land on a non-minimal root.
  - (2) `apply_health_shock` sets `p.RC_SS = country.rc_ss` = **1e-6** (was 1e-4) for the lives-saved
    reform ONLY (gated on `target < 0`); the deaths-added direction converges at the tight 1e-8 (8e-11
    observed) and is NOT loosened. 1e-6 keeps ~6× headroom over the realistic cumulative residual
    (~1.7e-7) and is ~100× tighter than ogcore's own `RC_TPI`=1e-4 (COD runs `RC_TPI`=0.0075). The
    realized |RC| is logged on every loosened solve so drift toward the gate is visible.
  - **Two effects, shown SEPARATELY in the GDP waterfall** (not a separate script): the channel applies
    BOTH a mortality effect (the disease_pop population recompute) AND a morbidity effect (an
    effective-labor `e` productivity shift). The +health GDP increment is dominated by the (placeholder)
    morbidity multiplier, not the lives saved — so `run_across_steps` re-solves the cumulative reform
    with health = mortality-only (1 extra solve) and the **health bar in `waterfall_gdp.png` is drawn as
    a stacked bar: mortality (lives saved) + morbidity (productivity, the remainder)**. One bar per
    channel; only health carries sub-parts. (The earlier standalone `health_decomposition.py` was folded
    into this and removed.) **Verified (full TPI run):** mortality marginal ≈ −0.0005pp (≈0), morbidity
    +0.0075pp — the GDP gain is the morbidity placeholder, not the lives saved.
  - **Morbidity now takes an AGE distribution too** (mirroring mortality's h(s)): `morbidity_profile`
    on the health channel; default uniform ("all active ages"), or a non-uniform shape via
    `health_profile.working_age_profile` / `morbidity_shape_to_S`. Magnitude carried by
    `morbidity_response` (placeholder, pending data).
  - **GBD sources BOTH mortality inputs** (tested vs the real HIV/SA export): `build_profile_from_gbd`
    → age shape h(s); `total_deaths_from_gbd` → the deaths target (`Number` metric). Until the PHL
    ambient-PM2.5 CSV lands (manual IHME download; DATA.md) a flagged PLACEHOLDER 64k total stands in.
  - **`welfare_by_J` renamed `consumption_by_J`** (report/figures): it is % change in composite
    CONSUMPTION, not lifetime utility; the thin top-income group is GE-sensitive, so read it as
    consumption incidence. **24/24 transform tests pass** (incl. bidirectional + non-monotone bracketing,
    morbidity age-profile, vendored-demog self-containment).
  - Remaining: real GBD PHL PM2.5 CSV; a calibrated dose-response / `morbidity_response`; and the
    j-distribution of *deaths* by income (mortality `rho` is (T+S,S), no j).
  - Scripts: `sweep_mortality`,
    `test_health_bidirectional`, `validate_health`, `diagnose_health`, `solve_health_variants`.
- **PHL-wiring debts** (portability): `runtime.build_baseline` still hardcodes `ogphl` + `p.M,p.I=4,5`
  + PHL guesses, and `country.py`/`cli.py` hardcode PHL + absolute CLEWS scenario paths. **RESOLVED
  (2026-06-17): the two absolute-path `get_pop_data` loads are GONE** — `total_deaths` /
  `extrapolate_demographics` / `baseline_pop` are vendored in `ogclews_link/_demog.py` (reading the
  vendored `ogclews_link/demographic_data/` CSVs) and `PROD_DICT` in `ogclews_link/_calibration.py`;
  no more `sys.path` hack into CLEWS-OG, no CostOfDisease-by-path `exec_module`, so the solve path runs
  on any checkout (the transform suite no longer skips the dependency).

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
- `[x]` **Health bidirectional solve** — `health_pop.disease_pop` accepts negative (lives-saved)
  targets + scoped `RC_SS`; the cleaner-air health channel converges (2026-06-17).
- `[x]` **Validation:** full 4-step batch (`experiments/run_across_steps.py`) re-run — ALL steps
  incl. +health converge; figures + report regenerated; mechanism verified (rho↓ elderly, e↑ working).

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

## 7. How to run

**Authoritative, current instructions live in [`README.md`](README.md)** (the end-to-end coupled-run
walkthrough). The link now runs in its OWN venv and subprocesses the OG model's interpreter via the model
registry — you no longer run it "inside the OG-PHL venv via PYTHONPATH":

```bash
uv run ogclews-link models register --path ../OG-PHL     # once per machine (writes og_model_registry.json)
export OGCLEWS_CLEWS_CASE=Philippines_v9 OGCLEWS_CLEWS_BASE_RUN=Base_v9 OGCLEWS_CLEWS_REFORM_RUN=PEP_v9
uv run ogclews-link run coupled --out ./ogclews_runs      # full coupled solve (first run several min; baseline cached)
uv run pytest tests/                                      # transform + unit tests (no solve)
```
**Dask gotcha:** the OG solve uses multiprocess workers (`--workers`, default 7); never `--workers 1`
(the single-process threaded client starves the event loop under numba → serial fallback).

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
- **2026-06-17 (health SOLVES)** — Implemented the bidirectional fix and it works. The down-failure
  was a TOLERANCE NEAR-MISS, not structural: the lives-saved SS converges to a ~5e-7 resource-constraint
  residual, tripping only ogcore's 1e-8 `RC_SS`. Fix: (1) `health_pop.disease_pop` — signed-target
  bidirectional `disease_pop` (clip floor + negative bracketing; reuses COD's `total_deaths`/
  `extrapolate_demographics`; built-in `get_pop_objs`); (2) `apply_health_shock` scopes `RC_SS`=1e-4 to
  the health reform only. SS sweep: down FAILED at 1e-8, CONVERGED at 1e-4. Full 4-step suite re-run:
  ALL steps incl. +health solve (target −658 lives → scale −7.8e-05; GDP +0.093%); mechanism verified
  (elderly mortality ↓, working `e` ↑, `g_n` holds); figures + report regenerated. 21/21 transform tests
  (incl. bidirectional calibration). Adversarially reviewed; review fixes applied (scoped RC_SS, profile
  validation, placeholder guardrail). Remaining: the PHL ambient-PM2.5 GBD CSV (manual IHME) for the real
  magnitude; the j-distribution-of-deaths model extension.
- **2026-06-17 (health HARDENED — review follow-ups)** — Acted on a deeper adversarial audit + the
  user's questions. (a) **Is loosening necessary?** Tested rigorously: the ~5e-7 residual is INTRINSIC
  — invariant to `reform_use_baseline_solution=False` and to `mindist_SS`=1e-11/1e-13 (all 5.089e-7),
  so the fixed point converges fine and only the post-solve `RC_SS` assertion trips → loosening is
  needed, but **tightened 1e-4 → 1e-6 and gated to the lives-saved direction only** (deaths-added
  converges at 1e-8); realized |RC| now logged. (b) **Mortality vs morbidity shown SEPARATELY as a
  stacked health bar in the GDP waterfall** — `run_across_steps` re-solves the cumulative reform with
  health = mortality-only (1 extra solve) and stacks mortality (lives saved) + morbidity (the remainder)
  in `waterfall_gdp.png`; the +health GDP increment is dominated by the placeholder morbidity multiplier,
  not the lives saved. (No standalone decomposition script — folded into the figure.) (c) **Morbidity now
  takes an age distribution** (`morbidity_profile`; `working_age_profile`/`morbidity_shape_to_S`),
  mirroring mortality's h(s). (d) **Portability fixed**:
  vendored `total_deaths`/`extrapolate_demographics`/`baseline_pop` (`_demog.py`, with the
  `demographic_data/` CSVs) and `PROD_DICT` (`_calibration.py`) — both absolute-path `get_pop_data`
  loads removed. (e) **Bracketing made non-monotone-robust** (outward scan to the first/minimal root;
  true achievable-extremum feasibility message). (f) `welfare_by_J` → `consumption_by_J` (it is
  composite consumption, not utility). 24/24 transform tests pass; full 4-step suite + the mortality-only
  decomposition solve re-run in the OG-PHL venv — ALL converge (GDP +0.026→+0.075→+0.086→+0.093%);
  verified split mortality ≈ −0.0005pp / morbidity +0.0075pp. Committed on branch `health-channel-hardening`.
