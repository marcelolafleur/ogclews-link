# OG-CLEWS integration — status & handoff

**Purpose:** one orientation doc for the multi-lane integration of `ogclews-link` (OG-PHL ⇄ CLEWS) into
a runnable tool. Read this first to know what exists, who owns what, how it merges, and how to run it.
Lives on the `energy-production-input-design` branch; **promote into the trunk's `STATUS.md` once the
trunk exists.** Last updated: 2026-06-17.

## 1. Lane map (the trunk + tributaries)

There is ONE trunk you track; feature lanes merge into it (the user runs the merges). The MUIOGO UI is a
separate repo, not a branch here.

| branch | worktree | role | owner | status | merges → |
|---|---|---|---|---|---|
| **`deployment-framework`** | `~/Projects/ogclews-link-deploy` | **TRUNK**: the runnable tool + integration point | tool/deploy agent | to be created | — |
| `health-channel-hardening` | `~/Projects/ogclews-link` (shared) | health science, channels, runtime, country, GBD | health agent | active | → trunk (is the base) |
| `energy-production-input-design` | `~/Projects/ogclews-link-energy` | energy levers, route-C design, policy levers | this lane | **done/ready** | → trunk (now; clean-additive) |
| `results-visualization` | `~/Projects/ogclews-link-viz` | figures / presentation layer | viz agent | **not ready** | → trunk (LATER) |
| MUIOGO hook + UI | `~/Projects/MUIOGO` | the analyst UI + post-run seam | MUIOGO agent | gap | separate repo |

**Merge order:** trunk = `health` (base) **+ `energy`** (now, no conflicts); **defer `viz`** until it's at
a checkpoint (it only feeds the presentation step); MUIOGO stays its own repo. Commands in §4.

## 2. What's done, by lane

### Energy lane (`energy-production-input-design`) — built, tested, clean-additive (13 commits, zero file overlap)
- **Route-C design spec** (`docs/design/energy-as-production-input-spec.md`): the theoretically-correct
  energy-cost representation = energy as a priced CES production input, priced by the CLEWS commodity
  **dual**, on the **M=4 platform** (M=7 deferred to a calibration assessment). Phase-2 (the OG-Core PR);
  out of scope for now.
- **I-O-calibrated route-B bridge** (works with what we have, no model change):
  - `energy_calibration.py` — θ_m (energy cost share by industry) from the PHL SAM. Finding: electricity
    ~0.5% (tiny), **fuels material** (Manufacturing 3.23%; chemicals 14.8%, metals 11.4% in the fine
    detail). Carrier choice dominates.
  - `io_energy_passthrough.py` — Leontief price model: per-industry **direct + indirect** cost-push from
    an energy-price shock (indirect amplification **1.1–2.4×**), mapped to a calibrated per-industry Z
    haircut.
  - **Verified model run** (`run_io_calibrated_energy_shock.py`): +20% energy+fuels → **GDP −1.87%**
    (correct sign; fixes the tau_c "+GDP" artifact).
- **Generic policy levers** (`policy_levers.py`, 5/5 tests):
  - `set_investment_incentive` — bias **private** capex in any industry (ITC / accelerated depreciation /
    CIT). **Verified:** 20% energy ITC → energy private capital **+5.0%** (GDP ≈0 — a distortion in OG
    alone; payoff is CLEWS-side).
  - `route_revenue` — transfers / public-investment / govt-consumption / deficit.
  - `industry_registry` — **onboarding-generic**: count from `p.M`, names from the country PROD_DICT,
    resource→index **declared by the country config**; single-industry (M=1) degrades cleanly. Not
    hardcoded to PHL.
- **Scenario-builder design** (`docs/design/scenario-builder-and-policy-levers.md`): the declarative
  choice catalog + defaults + templates + the MUIOGO UI seam + guardrails.

### Health lane (`health-channel-hardening`) — owner: health agent (active)
The 6 channels, GBD-wired health (mortality via `disease_pop` + morbidity via `e`), `runtime`,
`country.py`/`contract.py`, vendored `_demog.py`/`_calibration.py` + the PHL `demographic_data/` CSVs.
The bidirectional `disease_pop` + scoped `RC_SS` hardening is committed here.

### Viz lane (`results-visualization`) — owner: viz agent (NOT ready)
Figures/presentation (`viz_health.py`, `viz_transition.py`, `style.py`, `figures.py`). Merge LAST — it
only feeds the presentation step; nothing else depends on it.

### MUIOGO (`~/Projects/MUIOGO`) — separate repo (the UI + seam)
Flask app that runs CLEWS/OSeMOSYS (GLPK→CBC) and writes CSVs (incl. the EBb4 commodity dual). The
post-run hook to call ogclews-link is **not wired yet** (see §3 gaps).

## 3. The run interface (how it actually runs)

**Two isolated venvs, one subprocess seam, a file handoff.** MUIOGO (Flask venv, no ogcore) runs CLEWS
→ writes CSVs to `WebAPP/DataStorage/<case>/res/<run>/csv/`. ogclews-link (the **OG-PHL uv venv**, has
ogcore+ogphl) reads those CSVs, builds OG-PHL, applies channels, solves, writes results. They never
import each other.

**Run it today (standalone, works):**
```bash
PYTHONPATH=~/Projects/ogclews-link  ~/Projects/OG-PHL/.venv/bin/python -m ogclews_link run <experiment> --workers 1
#   python -m ogclews_link list | channels     # the menu
```
→ reads the configured CLEWS scenario (`v6-Base` vs `v6-PEP`), applies channels, solves, writes
`./ogclews_runs/<exp>/{reform/TPI, ogclews_manifest.json, clews_inputs/}`.

**Gaps to run it *from the MUIOGO button* (deployment-lane work):**
1. **Scenario redirect** — `--clews-run <dir>` currently records provenance only; the scenario paths are
   hardcoded in `country.py`. Must override the scenario source to consume a real MUIOGO run dir.
2. **MUIOGO post-run hook** — in `MUIOGO/API/Classes/Case/DataFileClass.py` `run()` (~line 2230, after
   `generateResultsViewer()`): a ~15-line `subprocess.run([OG_venv_python, "-m", "ogclews_link", "run",
   exp, "--clews-run", res_path])`. Not present.
3. **Results → UI** — ogclews-link writes to `./ogclews_runs/` (outside MUIOGO); write OG results into
   MUIOGO `view/` + register in `resData.json`.
4. **Loop closure** — the OG-side multi-pass loop is wired; the CLEWS re-solve hook (`clews_runner`) is
   the external seam (bigger, later).

## 4. Create the trunk (the user runs these)

```bash
git -C ~/Projects/ogclews-link checkout -b deployment-framework health-channel-hardening
git -C ~/Projects/ogclews-link merge energy-production-input-design   # clean-additive, no conflict
# do NOT merge results-visualization yet
git -C ~/Projects/ogclews-link worktree add ~/Projects/ogclews-link-deploy deployment-framework
```

## 5. Next steps (sequenced)

1. **Create the trunk** (§4) — health base + energy.
2. **Launch the deployment agent** (prompt in §6). It starts on the **separable, non-colliding** work:
   the MUIOGO seam (separate repo) · the `--clews-run` scenario+dual reader · a TOML/`config.py` registry
   (new module) · uv packaging + console entry point · the `run→present` driver (a new module that
   *calls* viz, doesn't edit `figures.py`).
3. **Defer** the multi-country `CountryProvider` (rewrites `country.py`/`runtime.py` — collides with the
   health lane until health merges).
4. **Merge `viz`** when ready → the presentation step lights up.
5. **Merge health updates** up to the trunk periodically.

## 6. Deployment-lane prompt (ready to launch — base/sequencing corrected)

> You're building OG-PHL ⇄ CLEWS (`ogclews-link`) into a usable, end-to-end tool — the "deployment
> framework." Today it's research scripts; make it a clean, configurable, reproducible tool an analyst
> drives, and the integration point across lanes.
>
> **Your lane / the trunk:** `~/Projects/ogclews-link-deploy` (branch `deployment-framework`). It is the
> **integration trunk**: base = `health-channel-hardening` **with `energy-production-input-design` merged
> in** (the energy levers + I-O calibration + policy levers). `results-visualization` is **NOT merged yet**
> (it isn't ready and only feeds presentation) — build the present step to *call* it and light it up when
> it merges. If the trunk doesn't exist, ask the user to run §4 above.
>
> **Read first:** `STATUS.md` §2 (architecture) + §5 (MVP checklist); `docs/design/INTEGRATION-HANDOFF.md`
> (this doc — lane map, run interface, what's done); `docs/design/og-clews-denovo-analysis.md` §7 +
> README "scripts vs UI"; the energy lane's `docs/design/{energy-as-production-input-spec, scenario-builder-and-policy-levers}.md`.
>
> **MVP target:** analyst picks a country + a CLEWS scenario/run dir + a channel set, runs one command,
> gets a solved, decomposed, presented result (macro + incidence + health + figures) reproducibly, with a
> manifest. Then the MUIOGO seam that calls this as a subprocess.
>
> **Start here (separable, non-colliding — do in this order):**
> 1. The **MUIOGO post-run hook** in `~/Projects/MUIOGO` (separate repo — the cleanest big piece): a ~15-
>    line subprocess call to the OG-venv CLI after the CLEWS run, + route results back to the UI.
> 2. The **`--clews-run` scenario-source redirect** + MUIOGO-run reader (consume `res/<run>/csv/`, incl.
>    the EBb4 commodity **dual**) so `price_source="dual"` runs on a real MUIOGO run.
> 3. A **`config.py`/TOML registry** (NEW module — declare country/scenario/channels; do NOT edit
>    `country.py`).
> 4. **uv packaging** + console entry point + extras.
> 5. The **`run→present` driver** (NEW module that orchestrates run → decompose → present by *calling*
>    viz's functions; do not edit `figures.py`).
>
> **Wait for a lane to merge:** the multi-country **`CountryProvider`** refactor — it rewrites
> `country.py`/`runtime.py`, which the active **health** lane owns. Do it as a proposal, or after health
> merges into the trunk.
>
> **Coordination rules (3 lanes live):** do NOT edit files the active lanes own (`runtime.py`/`country.py`
> = health; `figures.py`/`report_html.py` = viz) — build NEW modules or propose the refactor. MUIOGO is a
> separate repo (non-colliding). Commit to `deployment-framework`. Don't run the full OG solve to test
> plumbing — reuse the solved pickles at `~/Projects/ogclews-link/ogclews_runs/`.
>
> **First step:** read the docs + survey the CLI/runtime/manifest/muiogo_run + the MUIOGO seam, then
> propose a scoped MVP + sequencing to the user before writing code. Shortest path to "analyst runs one
> command → solved + presented result."
