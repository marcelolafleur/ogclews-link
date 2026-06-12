# ogclews-link

A standalone orchestration layer coupling **OG-Core** (an OLG general-equilibrium macro
model) and **CLEWS / OSeMOSYS** (a least-cost energy–land–water LP).

It is the code home for the de novo integration analysis in
`ogclews-schema/correspondence/og-clews-denovo-analysis.md`. The design principle is the
one the macro-energy linkage literature settled on: **keep both models independently
runnable**; the coupling is a separate layer that exchanges **quantities forward**
(activity/income → energy demand) and **prices/duals back** (energy price, carbon price,
investment → macro), iterated to the fixed point where the demand OG chooses at the
returned price equals the demand CLEWS met.

## Why standalone (not in the schema repo, not in MUIOGO yet)

- `ogclews-schema` is a spec/reference repo (and not a git repo); it holds the analysis
  and the interface contract, not runnable coupling code.
- `MUIOGO` is the eventual orchestrator, but it is a Flask app currently wired to
  OSeMOSYS only. Bolting research coupling code into it now entangles the experiment with
  the app and its release cycle. This package is what MUIOGO will later **import** as its
  OG-side engine.

## Layout

```
ogclews_link/
  contract.py       interface contract: ScenarioPair, Concordance, UnitMap (+ PHL defaults)
  clews_signal.py   energy-price signal from CLEWS (cost-index proxy now; LP dual = rigor)
  og_wedge.py       inject the energy price into OG-Core; read back demand + incidence
  iterate.py        the soft-link fixed-point driver (OG pass real; CLEWS re-run = MUIOGO seam)
experiments/
  exp01_demand_response.py   first test: does OG energy demand fall when CLEWS says costlier?
```

## The first test

`exp01` operationalizes the load-bearing feasibility finding: OG households already respond
to the effective energy price `(1 + tau_c_i) p_i` (EqHH_ciDem2), so the demand-response
channel is testable on the shipped model with no core change. It derives an energy-price
ratio from the CLEWS PEP-vs-Base cost export, applies it as a `tau_c` wedge on the energy
consumption good, solves baseline and reform, and reads the demand response **and its
incidence across income groups** — the result only OG-Core can give.

Heavy OG solves are guarded behind `RUN_SIM`; with it off the script just builds and prints
the signal + wedge so the setup can be inspected without a cluster.

## Status

Skeleton. The wedge mechanics (routes A `tau_c` and B `Z`) are implemented and unit-testable
without ogcore; the OG-PHL baseline builder and the dual-based loop closure are stubs marked
in-code. Three rigor rungs for the energy price (see `og_wedge`): (A) `tau_c` wedge,
(B) energy-industry `Z`, (C) energy-as-CES-input — a future OG-Core PR, the rigor endpoint.
