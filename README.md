# ogclews-link

A modular framework for the OG-Core ⇄ CLEWS/OSeMOSYS integration: each economic linkage is
a small, guard-railed **channel**; experiments are **configuration**; a **CLI** runs them;
the transforms are **unit-tested without solving**. This is the answer to "how do we manage
this as it gets complex" — a channel library + config-driven experiments, not a growing pile
of one-off scripts.

## Architecture

```
ogclews_link/
  framework.py   Channel ABC + registry + ExperimentContext + Runner (orchestration)
  channels.py    the 6 channels (each: verified transform + guardrails + provenance)
  signals.py     extract signals from CLEWS outputs + OG results (+ the dual stub)
  country.py     CountryConfig (PHL): paths, indices, concordance, GDP, public-tech tags
  contract.py    ScenarioPair / Concordance / UnitMap
  recycle/...    (in channels.py) revenue recycling via alpha_T
  report.py      macro / demand / incidence read-outs (import-light, tested)
  clews_io.py    serialize OG->CLEWS artifacts (demand, EmissionsPenalty, DiscountRate)
  health_pop.py  bidirectional disease_pop: signed (lives-saved/excess-deaths) age-profile mortality
  health_profile.py  GBD pollution mortality age-shape h(s) + morbidity age shapes
  _demog.py      vendored total_deaths / extrapolate_demographics / baseline_pop (+ demographic_data/)
  _calibration.py    vendored PHL PROD_DICT (no more sys.path hacks into CLEWS-OG / CostOfDisease)
  runtime.py     the ONLY ogcore-touching layer: build baseline, solve, apply mortality
  progress.py    live convergence bar
  experiments.py named, reproducible experiments
  cli.py         python -m ogclews_link {list|channels|run <name>}
tests/test_channels.py   transform-level tests (no ogcore, no solve)
```

The split matters: `framework`, `channels`, `signals`, `report` import only numpy/pandas, so
the economics is unit-testable without ogcore. `runtime` is the only module that imports
ogcore/ogphl, and the Runner is handed its methods — so the heavy solve is injected, not
hard-wired.

## The channels

| id | direction | theory | what it does |
|---|---|---|---|
| `energy_price` | clews→og | structural | CLEWS energy price → `tau_c` wedge on the energy good → demand response + incidence (+ optional revenue recycle, energy `c_min`) |
| `investment` | clews→og | structural | CLEWS power capex increment → OG public investment `alpha_I` → crowding-out, debt |
| `carbon` | policy | structural | one carbon price → OG consumption tax (`tau_c`, recycled) **and** CLEWS `EmissionsPenalty` |
| `discount_rate` | og→clews | structural | OG equilibrium `r_p` → CLEWS `DiscountRate` |
| `health` | clews→og | reduced-form | CLEWS emissions → (illustrative dose-response) → OG mortality / `e` / `chi_n` |
| `demand` | og→clews | structural | OG activity (`Y_m`/`C_i`) → CLEWS energy-service demand scaling |

`clews→og` and `policy` channels mutate the OG **reform** params before the reform solve;
`og→clews` channels run **after** the solve and emit CLEWS input files (the producer side of
loop closure). The actual CLEWS re-run + dual extraction is the external seam (MUIOGO / the
solver) — see `signals.commodity_shadow_price`.

## Run

```bash
PY=/Users/mlafleur/Projects/OG-PHL/.venv/bin/python
PP=/Users/mlafleur/Projects/ogclews-link

PYTHONPATH=$PP $PY -m ogclews_link list           # named experiments
PYTHONPATH=$PP $PY -m ogclews_link channels       # registered channels
PYTHONPATH=$PP $PY -m ogclews_link run clean_incidence --workers 1   # build, apply, solve, report
```

`--workers 1` uses the single-process threaded client (stable scatter); raise it for the
multi-process path. Results + any CLEWS input artifacts land under `./ogclews_runs/<name>/`.

## Test (no solve)

```bash
PYTHONPATH=$PP $PY tests/test_channels.py
```

Exercises every channel's transform on array fixtures and the real CLEWS readers against the
actual `v6-Base`/`v6-PEP` files. 12 tests, ~1 second, no ogcore solve.

## Managing complexity: scripts vs UI

- **Now — a config-driven CLI framework (this).** Channels are the unit of reuse; an
  experiment is a list of `(channel, options)`; the CLI runs any of them reproducibly and the
  transforms are tested in isolation. This scales to many channels/experiments without
  duplicating run scripts. Example-style scripts (e.g. `PEP_simulation.py`,
  `energy_price_simulation.py`) become thin wrappers or are subsumed by named experiments.
- **Later — a UI (MUIOGO).** Once the channels stabilize, MUIOGO (the GSoC orchestrator) can
  import this package as its OG-side engine and expose channel selection + scenario building
  interactively. Build the UI on top of the stable framework, not instead of it.

## Status / honesty

Transforms implemented and tested; the CLEWS→OG channels are fully runnable now; the OG→CLEWS
channels emit inputs but the CLEWS re-run is external. The `health` dose-response and the
`carbon`→OG ad-valorem conversion are illustrative and flagged in-code. The energy `c_min`
must be calibrated below every income group's baseline energy consumption before use. The
loop-closure (iterate OG↔CLEWS with the commodity **dual**, not the cost-index proxy) is the
next architectural piece.
