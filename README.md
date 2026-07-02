# ogclews-link

A modular, **standalone** framework for the OG-Core ⇄ CLEWS/OSeMOSYS coupling: each economic
linkage is a small, guard-railed **channel** (a plain function); experiments are **configuration**;
a **CLI** runs them; the transforms are **unit-tested without solving**. The link is its own
environment and imports **no** OG-Core — to solve, it drives the country's OG model in *its* own
environment as a subprocess, so the link, MUIOGO, and each OG model stay independently installed.

The link does **not** author a country's calibration. It **discovers** what each OG model ships
(its multisector aggregation, its demographics) and **uses it, or skips** the channels it can't
support — see the discover/use/skip design below.

## Architecture

```
ogclews_link/
  channels.py    the channels as plain functions (verified transform + guardrails + provenance);
                 emit_* = og→clews, run after the solve
  signals.py     source each channel's input from CLEWS outputs / OG results (cost index, dual, GBD, ...)
  experiments.py named, reproducible experiments — exp(ctx, solve) calling channels in order
  framework.py   ExperimentContext (carries the per-run concordance) + run / run_across_steps / preflight
  runtime.py     the run orchestrator (numpy/stdlib, imports NO ogcore): looks up the model registry
                 and drives the country OG model's OWN interpreter as a subprocess; caches the baseline
  og_runner.py   runs INSIDE the OG env — the only module importing ogcore + the country package:
                 loads the country's calibration, solves the baseline (by continuation when needed),
                 solves the reform, and exports data files for the link
  discovery.py   LINK-SIDE calibration discovery — reads a package's param JSONs + PROD_DICT/CONS_DICT
                 (ast, no import) to enumerate calibrations + their couplability (no solve, no subprocess)
  registry.py    OG-model registry (repo key → package + env_python + version + chosen calibration +
                 saved discovery status) + data/og_model_registry.json
  models.py      `ogclews-link models register | calibrations | list`
  serde.py       the cross-env boundary: JSON overrides in, .npz solutions out (no pickle/ogcore crosses)
  contract.py    ScenarioPair / Concordance (discovers the energy ports from a model's own PROD_DICT/
                 CONS_DICT; marks them None if electricity can't be isolated, so dependent channels skip)
  country.py     CountryConfig (PHL): scenario paths, units, GBD, public-tech tags
  health_pop.py / health_profile.py   signed age-profile mortality (disease_pop) + GBD morbidity shapes
  report.py      macro table + demand / incidence read-outs (import-light, tested)
  viz/           the figure/deck subpackage (python -m ogclews_link.viz)
  cli.py         ogclews-link {list | channels | run <name> | models ...}
tests/           transform + boundary (serde) + discovery + registry tests (numpy-only; ogcore/ogphl tests skip if absent)
```

The boundary matters: everything except `og_runner` imports only numpy/pandas, so the economics is
unit-testable with no solver. The link **never** imports ogcore; `runtime` subprocesses the OG model's
own interpreter (found via the registry) and `og_runner` runs over there. Data crosses as JSON
(parameter overrides) and `.npz` (solutions) — no pickle and no ogcore object ever crosses.

## How the coupling decides what it can do (discover / use / skip)

- **Calibration.** The link reads the OG package's own parameter files. If the package ships a
  multisector (M>1) calibration that **isolates electricity as its own industry**, the link uses it and
  the energy channels engage. Otherwise the baseline stays single-industry and the energy channels skip.
  The chosen calibration is recorded in the registry by `models register` (auto-picked, or `--calibration`).
- **Concordance.** Which OG industry/good is "electricity" is **discovered per run** from the package's
  `PROD_DICT`/`CONS_DICT` (never a hand-set index). If electricity is fused with water, or the
  consumption good is too diluted, the relevant channels skip and record why.
- **Solve.** A heterogeneous-capital-share multisector baseline does **not** cold-solve (OG-Core seeds
  every industry price at 1, which is wrong when capital shares differ). The link solves the steady
  state by **continuation** (a flat-gamma anchor morphed to the calibrated values), then runs the
  transition path off it. If the continuation can't converge, the run fails loudly rather than shipping
  a wrong equilibrium.
- **Demographics.** The link refreshes demographics the same way the OG models do — via
  `ogcore.demographics` (UN data portal → the GitHub `EAPD-DRB/Population-Data` backup) — and **fails
  safely to the model's own built-in (baked) demographics** when the live data is unavailable. It never
  substitutes its own copy.

## The channels

Plain functions in `channels.py`. `emit_*` channels run **after** the reform solve and emit CLEWS inputs.
A channel skips itself (recorded in provenance) when the country's calibration can't supply the energy
port it needs.

| channel | direction | what it does |
|---|---|---|
| `energy_price` | clews→og | CLEWS energy price → `tau_c` wedge on the energy good → demand + incidence (+ optional recycle) |
| `investment` | clews→og | public power capex → OG public investment `alpha_I` → `K_g` |
| `capital_intensity` | clews→og | generation-mix capital share → the energy industry's capital exponent |
| `energy_capex` | policy | an ITC → the energy industry's cost of capital (opposite sign on energy K to `capital_intensity`) |
| `carbon_tax` | policy | a carbon price → OG consumption tax on the energy good (`tau_c`, optional recycle) |
| `emit_carbon_penalty` | og→clews | the same carbon price → CLEWS `EmissionsPenalty` |
| `emit_discount_rate` | og→clews | OG equilibrium market return → CLEWS `DiscountRate` |
| `emit_energy_demand` | og→clews | OG activity (`Y_m`/`C_i`) → CLEWS energy-service demand scaling |
| `health` | clews→og | CLEWS PM2.5 emissions → calibrated dose-response (M) → OG mortality (`disease_pop`) + morbidity (`e`) |

---

# End-to-end walkthrough — reproduce the PHL multi-industry coupled run

This drives the whole stack the way it is meant to be used: the energy side (MUIOGO/CLEWS), the OG
country model (OG-PHL with its multi-industry calibration), and the link that couples them.

### Prerequisites
- `git`, and [`uv`](https://docs.astral.sh/uv/) (the package/venv manager all three projects use)
- Python 3.11 (3.10–3.12 supported)
- [`gh`](https://cli.github.com/) (to check out the OG-PHL PR), authenticated

### The pieces
1. **MUIOGO** — the CLEWS/OSeMOSYS energy side (and GUI). Produces the energy-system scenarios.
2. **OG-PHL @ PR #63** — the OG-Core country model with the multi-industry (M=8) calibration.
3. **ogclews-link** (this repo) — the coupling layer.
4. **CLEWS scenario outputs** (a *base* and a *reform*) — read by the link's energy channels.

### Step 1 — MUIOGO (the energy side)
```bash
git clone https://github.com/EAPD-DRB/MUIOGO.git
cd MUIOGO
./scripts/setup.sh      # macOS/Linux: venv + GLPK/CBC solvers + demo data   (Windows: scripts\setup.bat)
./scripts/start.sh      # launch the app to build/run CLEWS scenarios        (Windows: scripts\start.bat)
```
MUIOGO runs OSeMOSYS/CLEWS and writes a scenario folder per run (the OSeMOSYS output CSVs plus a
`Cost of electricity generation_*.xlsx` workbook). You need **two**: a baseline and a reform. See
MUIOGO's own README for details.

### Step 2 — OG-PHL at PR #63 (multi-industry, M=8)
```bash
git clone https://github.com/EAPD-DRB/OG-PHL.git
cd OG-PHL
gh pr checkout 63 -R EAPD-DRB/OG-PHL    # "Multi-industry (M=8) calibration from the Philippine SAM"
uv sync                                 # builds OG-PHL's own .venv (ogcore + deps)
uv run python -c "import ogphl; print(ogphl.UN_COUNTRY_CODE, list(ogphl.PROD_DICT))"
# -> 608  ['Agriculture and Fishing','Mining','Electricity','Water','Construction','Trade and Transport','Services','Manufacturing']
```
This PR ships `ogphl_multisector_default_parameters.json` (M=8, I=5, with `alpha_c` + `io_matrix`) and
isolates electricity as its own production group — the thing that makes PHL couplable on energy.

### Step 3 — the link: install and register the OG model
```bash
git clone https://github.com/SeaCelo/ogclews-link.git
cd ogclews-link
uv sync
uv run ogclews-link models register --path ../OG-PHL
```
`register` discovers the calibrations **link-side** (no solve) and auto-picks the couplable one. Expect:
```
registered og-phl (ogphl 0.1.0) -> .../OG-PHL/.venv/bin/python
  calibration: ogphl_multisector_default_parameters.json
   * ogphl_multisector_default_parameters.json  M=8 I=5  [energy industry=2 good=1]
        route-A good is 39% electricity  -- DILUTED (mostly non-electricity; demand-side wedge is approximate)
        electricity isolated as its own industry -- couplable on energy
```
Inspect any time with `uv run ogclews-link models list` and `uv run ogclews-link models calibrations og-phl`.

### Step 4 — point the link at your CLEWS scenarios (from your MUIOGO install — no hardcoded paths)
The link resolves the **base** and **reform** scenario dirs from config / your MUIOGO installation
(first match wins):
1. CLI flags `--clews-base <dir> --clews-reform <dir>`, or env `$OGCLEWS_CLEWS_BASE` / `$OGCLEWS_CLEWS_REFORM`;
2. the **MUIOGO install** — set `$OGCLEWS_MUIOGO_HOME` (or place MUIOGO at `../MUIOGO` next to this repo),
   `$OGCLEWS_CLEWS_CASE`, and `$OGCLEWS_CLEWS_BASE_RUN` / `$OGCLEWS_CLEWS_REFORM_RUN`; the link then reads
   `<MUIOGO>/WebAPP/DataStorage/<case>/res/<run>/csv`.

```bash
export OGCLEWS_CLEWS_CASE=Philippines_v9        # a case in your MUIOGO DataStorage
export OGCLEWS_CLEWS_BASE_RUN=Base_v9           # the baseline caserun
export OGCLEWS_CLEWS_REFORM_RUN=PEP_v9          # the reform caserun
```
The run prints the resolved scenario dirs (and a `NOT FOUND` notice + guidance if unset). The
emissions/capex channels read MUIOGO's raw OSeMOSYS CSVs directly. (`Base_v9`/`PEP_v9` is the
base/reform pair the committed M=8 golden was regenerated on.)

> **Energy-price source.** The `coupled` experiment's `energy_price` uses the `"auto"` source: it reads a
> curated *Cost of electricity generation* workbook if one ships beside the scenario, else it falls back to
> the OSeMOSYS commodity-balance **dual** (`EBb4…`). A pure-MUIOGO scenario has no workbook, so it uses the
> dual — and for PHL that dual is **near-flat**, so the energy-price channel contributes ≈ 0 and the coupled
> result is driven by the investment + health legs. The path resolution above is country/install-agnostic.

### Step 5 — run the coupled scenario
```bash
uv run ogclews-link run coupled --out ./ogclews_runs
```
What happens, printed live:
1. looks up OG-PHL in the registry and subprocesses **its** interpreter;
2. **demographics**: UN portal → GitHub backup → the model's built-in (fail-safe);
3. **baseline**: heterogeneous γ ⇒ solves the M=8 steady state by **continuation**, then the transition path
   (the baseline is cached and reused; first run is several minutes);
4. applies the coupled channels to a fresh reform and solves it;
5. prints the report + macro table; writes the og→clews CLEWS inputs and a run manifest.

Other useful flags: `--workers N` (OG solve processes, default 7), `--rebuild-baseline` (force a fresh
baseline solve, ignoring the cache — e.g. to pick up newer UN demographics), `--no-progress`.

### Step 6 — where the results are
Under `./ogclews_runs/coupled/`:
- **`macro_table.csv`** — headline % change reform vs baseline (`Y, C, K, L, r, w`), by year + a 10-yr
  window + the steady state (OG-Core `macro_table` style; also printed in the report).
- **`clews_inputs/`** — the og→clews artifacts that close the loop back to CLEWS:
  `EmissionsPenalty.csv`, `DiscountRate.csv`, `demand_scaling.csv`.
- **`ogclews_manifest.json`** — provenance: country, the discovered concordance, the channels that ran,
  the scenario, the OG model version.
- **`reform/`** — the solved reform (`.npz` for the link + OG-Core's `SS`/`TPI` pickles).

The solved baseline is cached at `./ogclews_runs/_og_baseline_cache/og-phl-<version>-<calibration>/`
and reused by any later run against the same model/version/calibration (the continuation runs once).

### Step 7 — build the browser portal (optional)
`run coupled` writes the OG-native pickles + CSVs above. A separate step turns them into a figure deck and
a self-contained `index.html` portal (no re-solve). It runs under the **OG model's interpreter** (it reads
OG-Core pickles, so it needs `ogcore`) — use the `env_python` shown by `uv run ogclews-link models list`:
```bash
PYTHONPATH=$PWD <OG-model-venv-python> -m ogclews_link.viz --coupled-run ./ogclews_runs/coupled --country phl
```
Then open `./ogclews_runs/coupled/index.html`. A pre-built example is at `ogclews_runs/coupled_phl_m8/index.html`.

### What to expect (PHL M=8 coupled — the committed golden, real CLEWS prices)
- **Channels fire**: the `energy_full` composite (cost-push + recycled wedge at the real near-flat PHL
  electricity price — its contribution is ≈ 0 by construction), `investment`, `emit_carbon_penalty`,
  `health` (≈ −279 deaths via the calibrated PM2.5 dose-response), `emit_discount_rate`, `emit_energy_demand`.
- **Small macro effects, real signs** (reform vs baseline, from `results/golden.json`): `Y` **−0.017%**
  at the steady state, **+0.165%** at t0 and **+0.396%** at t10 (transition stimulus from the
  investment leg, a small long-run cost); `C` +0.47% at t10.
- The run prints `[provenance] energy price source: 'auto' resolved to 'dual'` (a pure-MUIOGO case has
  no cost workbook) and records the resolved source in the manifest.
- The baseline steady state solves cleanly via continuation (resource-constraint error ≈ 1e-13).

> **One remaining illustrative conversion.** The `carbon_tax`→OG ad-valorem conversion uses an
> uncalibrated deflator (flagged in-code); everything else in `coupled` runs on the real CLEWS signals.

### Notes / fail-safe behavior
- **Offline / no UN data**: demographics fall back to the model's built-in calibrated values, and the
  `health` mortality shock skips (the baseline still solves).
- **A country whose calibration can't isolate electricity** (single-industry, or electricity fused with
  water): the energy channels skip with a recorded reason; the non-energy channels still run.
- **A CLEWS case without a PM2.5-type emission species**: the `health` channel skips with a recorded
  reason (it will not misapply the PM2.5 dose-response to a GHG); the other channels still run.

---

# Onboarding your own country / MUIOGO case

The walkthrough above reproduces the **PHL reference instance**; the link itself is country-agnostic.
Connecting your own MUIOGO CLEWS case + OG country model takes three declarative pieces — none of them
edits link source:

### 1. Your CLEWS case (MUIOGO) — the export contract
The channels read MUIOGO's standard result CSVs from `<MUIOGO>/WebAPP/DataStorage/<case>/res/<run>/csv`.
`run` pre-checks both scenario dirs and prints a checklist **before** the expensive OG solve. The stems
it looks for, and what each one drives:

| CSV stem | drives |
|---|---|
| `EBb4_EnergyBalanceEachYear4_ICR` | the energy price (`auto`/`dual` source). **Only exported when the case is solved with CBC and `-printing all`.** |
| `Demand` | the demand write-back baseline (`emit_energy_demand`) |
| `CapitalInvestment` | the public-investment channel (power capex delta) |
| `AnnualizedInvestmentCost`, `AnnualFixedOperatingCost`, `AnnualVariableOperatingCost` | the capital-intensity channel |
| `AnnualTechnologyEmission(ByMode)` | the carbon + health channels |

A missing stem is a warning, not a wall: the channel that needs it skips or fails loudly at its point
of use, and the rest of the run proceeds.

### 2. Your OG country model — register it
```bash
uv run ogclews-link models register --path ../OG-XXX
```
The model must be an OG-Core country package (like OG-PHL/OG-ZAF) exposing `UN_COUNTRY_CODE` and
`PROD_DICT`/`CONS_DICT`, with its own `.venv`. Registration discovers the couplable multisector
calibration link-side (no solve) — energy coupling needs the calibration to isolate electricity as its
own production group; otherwise the energy channels skip with a recorded reason and the non-energy
channels still run.

### 3. Your country entry — a countries JSON (no source edit)
Copy [`ogclews_countries.example.json`](ogclews_countries.example.json) to `ogclews_countries.json`
(or point `$OGCLEWS_COUNTRIES` / `--countries` at it), fill in your entry, then:
```bash
uv run ogclews-link run coupled --country og-xxx --out ./ogclews_runs
```
(`--country` also accepts the country name or UN code; `$OGCLEWS_COUNTRY` sets a default.)

The fields, and what goes wrong if they're wrong (everything mis-set fails **loudly** — no silent zeros):

| field | meaning | if wrong |
|---|---|---|
| `name` | country name; also keys the shared GBD/PM2.5 data lookups (IHME location name) | health falls back to placeholders / M=1 guardrail |
| `un_code` | UN M49 code (provenance; demographics use the OG package's own `UN_COUNTRY_CODE`) | cosmetic |
| `og_repo` | **must equal the registry key** from `models register` | `ModelNotInstalledError` naming the key |
| `gdp_musd` | nominal GDP, USD millions | mis-scales the investment shock (%GDP conversion) |
| `og_start_year` | OG-Core start year (CLEWS↔OG year alignment) | loud year-alignment warning |
| `power_prefix` | prefix of ALL power-tech codes in your CLEWS export | **error** naming the prefix + the tech codes present |
| `public_power_markers` | substrings marking grid/T&D (public) techs | loud warning + zero public capex |
| `electricity_fuel` | the commodity whose EBb4 dual is the household electricity price | unset with several `ELC*` commodities → **error** listing them |
| `clews_region` | the case's OSeMOSYS region code (write-back artifacts address it) | artifacts name a nonexistent region (CLEWS merge no-ops) |
| `co2_emission`, `health_emission` | **exact** species codes in your `AnnualTechnologyEmission*` export | read paths **error** listing the species present; health records a skip; the EmissionsPenalty write-back warns |
| `units`, `scenario`, `gbd_burden_csv`, `pm25_dose_response`, `mindist_tpi`, `rc_ss` | optional/advanced (see `country.py` docstrings) | defaults documented in-code |

Scenario dirs normally come from the MUIOGO-install env vars (Step 4 above), not the JSON — the same
resolution applies to every country.

### Orchestrating from MUIOGO (programmatic use)
Everything the CLI does is a plain function call — the intended deployment is MUIOGO (or a driver
script) invoking the link directly:
```python
from ogclews_link import country, experiments, framework, runtime
cc  = country.resolve_country("og-xxx", config_file="ogclews_countries.json")
ctx = framework.run(experiments.get("coupled"), cc,
                    export_baseline=runtime.export_baseline, solve_reform=runtime.solve_reform,
                    out_root="./ogclews_runs")
```
The og→clews artifacts (`clews_inputs/`: `EmissionsPenalty.csv`, `DiscountRate.csv`,
`demand_scaling.csv`) address the case's `clews_region` and name their target commodity
(`electricity_fuel`) — the return path a CLEWS-side merge consumes. Invoking OSeMOSYS on them (the
MUIOGO `/updateData` → new caserun loop) is the external step today.

---

## Test (no solve)
```bash
uv run pytest tests/        # 170 pass / 3 skip — the skips need ogcore/ogphl installed
```
The transform, boundary (`serde`), discovery, and registry tests run numpy-only in seconds; the few
country-integration tests skip gracefully without the OG packages.

## Status / honesty
The cross-env solve runs end-to-end and the full PHL M=8 coupled stack has been validated through the
intended install → register → run flow. The link discovers and uses each country's own calibration and
demographics (or skips), solves hard multisector baselines by continuation, and reports an OG-Core-style
macro table. `health` is calibrated (country PM2.5 dose-response M; PHL ≈ 0.082). Everything
country-specific is declarative: the OG model via the registry (`models register`), the country via a
countries JSON (`--country`, no source edit), the CLEWS scenario location via the MUIOGO install / env /
CLI (no hardcoded paths). The `coupled` energy price runs on the real CLEWS signal (`auto`: workbook if
present, else the raw MUIOGO EBb4 dual) and records which source it used in the manifest. Config
mismatches fail loudly (power prefix, emission species, electricity fuel) instead of producing silent
zeros. Open items: the `carbon_tax`→OG ad-valorem deflator is uncalibrated (illustrative); the
loop-closure (emit a CLEWS scenario patch → MUIOGO re-solves → iterate) is the next architectural piece —
the og→clews artifacts already address the case's region/commodity for it; the link's legacy vendored
`demographic_data/` CSVs are now unused.