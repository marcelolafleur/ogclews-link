# ogclews-link

A modular, **standalone** framework for the OG-Core ⇄ CLEWS/OSeMOSYS coupling: each economic
linkage is a small, guard-railed **channel** (a plain function); experiments are **configuration**;
a **CLI** runs them; the transforms are **unit-tested without solving**. The link is its own
environment and imports **no** OG-Core — to solve, it drives the country's OG model in *its* own
environment as a subprocess, so the link, MUIOGO, and each OG model stay independently installed.
This is the answer to "how do we manage this as it gets complex": a channel library + config-driven
experiments + clean environment boundaries, not a growing pile of one-off scripts.

## Architecture

```
ogclews_link/
  channels.py    the channels as plain functions (verified transform + guardrails + provenance);
                 emit_* = og→clews, run after the solve
  signals.py     source each channel's input from CLEWS outputs / OG results (cost index, dual, GBD, ...)
  experiments.py named, reproducible experiments — exp(ctx, solve) calling channels in order
  framework.py   ExperimentContext + run / run_across_steps / preflight (the solve callables are injected)
  runtime.py     the run orchestrator (numpy/stdlib, imports NO ogcore): looks up the model registry
                 and drives the country OG model's OWN interpreter as a subprocess
  og_runner.py   runs INSIDE the OG env — the only module importing ogcore + the country package:
                 export-baseline / solve-reform, exchanging data files with the link
  registry.py    OG-model discovery (un_code → package + env_python + version) + data/og_model_registry.json
  serde.py       the cross-env boundary: JSON overrides in, .npz solutions out (no pickle/ogcore crosses)
  contract.py    ScenarioPair / Concordance (discovers the energy ports; marks them None if electricity
                 can't be isolated, so dependent channels skip)
  country.py     CountryConfig (PHL): scenario paths, concordance, GBD, public-tech tags
  clews_io.py    serialize the og→clews artifacts (Demand, EmissionsPenalty, DiscountRate)
  health_pop.py / health_profile.py   signed age-profile mortality (disease_pop) + GBD morbidity shapes
  _calibration.py    vendored PHL PROD_DICT + CONS_DICT (the M=4 coupling aggregation, electricity isolated)
  _demog.py      vendored demographics (+ demographic_data/)
  report.py      macro / demand / incidence read-outs (import-light, tested)
  viz/           the figure/deck subpackage (python -m ogclews_link.viz)
  cli.py         ogclews-link {list | channels | run <name>}
tests/           transform + boundary (serde) + registry tests (numpy-only; ogcore/ogphl tests skip if absent)
```

The boundary matters: `channels`, `signals`, `framework`, `serde`, `registry`, `report` import only
numpy/pandas, so the economics is unit-testable with no solver. The link **never** imports ogcore;
`runtime` subprocesses the OG model's own interpreter (found via the registry) and `og_runner` — the
only ogcore-importing module — runs over there. Data crosses as JSON (parameter overrides) and `.npz`
(solutions); no pickle and no ogcore object ever crosses the environment boundary.

## The channels

Plain functions in `channels.py`. A channel takes the **already-sourced** value it needs (a `signals.*`
helper supplies it); `emit_*` channels run **after** the reform solve and emit CLEWS inputs. If a
country's OG aggregation can't isolate electricity, the energy-port channels **skip themselves**
(recorded in provenance) and the channels that don't need it still run.

| channel | direction | what it does |
|---|---|---|
| `energy_price` | clews→og | CLEWS energy price → `tau_c` wedge on the energy good → demand + incidence (+ optional recycle, energy `c_min`) |
| `investment` | clews→og | public power capex → OG public investment `alpha_I` → `K_g` |
| `capital_intensity` | clews→og | generation-mix capital share → the energy industry's capital exponent (factor-share lever) |
| `energy_capex` | policy | an ITC → the energy industry's cost of capital (capital-demand lever; opposite sign on energy K to `capital_intensity`) |
| `carbon_tax` | policy | a carbon price → OG consumption tax on the energy good (`tau_c`, optional recycle) |
| `emit_carbon_penalty` | og→clews | the same carbon price → CLEWS `EmissionsPenalty` |
| `emit_discount_rate` | og→clews | OG equilibrium market return → CLEWS `DiscountRate` |
| `emit_energy_demand` | og→clews | OG activity (`Y_m`/`C_i`) → CLEWS energy-service demand scaling |
| `health` | clews→og | CLEWS PM2.5 emissions → calibrated dose-response (M) → OG mortality (`disease_pop`) + morbidity (`e`) |

The `og→clews` channels emit CLEWS input files (the producer side of loop closure); the CLEWS re-run
that closes the loop is the external seam (MUIOGO) — in design now.

## Run

The link is a standalone `uv` project with its own venv and **does not need ogcore**. To solve, the
country's OG model must be installed in its own environment and registered in
`ogclews_link/data/og_model_registry.json` (or a file named by `$OGCLEWS_MODEL_REGISTRY`); the link
finds it there and subprocesses it.

```bash
uv run ogclews-link list                 # named experiments
uv run ogclews-link channels             # the channel functions + direction
uv run ogclews-link run coupled --out ./ogclews_runs --clews-run <CLEWS run dir>
```

`run` exports the OG baseline (cached; scenario-independent), applies the experiment's channels to a
fresh reform, solves it **in the OG env**, prints a report, and writes the og→clews CLEWS inputs +
a run manifest under `./ogclews_runs/<name>/`. `--workers` sets the OG solve's worker processes
(default 7).

## Test (no solve)

```bash
uv run pytest tests/        # 95 pass / 4 skip — the 4 skip when ogcore/ogphl aren't installed
```

The transform, boundary (`serde`), and registry tests run numpy-only in seconds; the few
country-integration tests skip gracefully without the OG packages.

## Managing complexity: scripts → framework → UI

- **Channels are the unit of reuse.** An experiment is a function calling channels in order; the CLI
  runs any of them reproducibly and the transforms are tested in isolation — this scales to many
  channels/experiments without duplicating run scripts.
- **Environment boundaries** keep the link, the OG models, and MUIOGO independently installed: the
  link presses go itself and drives each OG model in its own env (the model registry is the seam).
- **Later — the UI (MUIOGO).** MUIOGO (the GSoC orchestrator) calls this package as its OG-side
  engine over the CLI seam and visualizes results; it is the natural owner of the model registry.

## Status / honesty

The cross-env solve works end-to-end and reproduces the committed golden across the whole battery
(13/13, zero drift) and the real coupled PEP-vs-Base run. The channels are plain, unit-tested
functions. `health` is calibrated (country PM2.5 dose-response M; PHL ≈ 0.082); the `carbon_tax`→OG
ad-valorem conversion is still illustrative until its deflator is calibrated (flagged in-code), and
the energy `c_min` must be set below every income group's baseline energy consumption before use. The
loop-closure (emit a CLEWS scenario patch → MUIOGO re-solves → iterate) is the next architectural piece.
