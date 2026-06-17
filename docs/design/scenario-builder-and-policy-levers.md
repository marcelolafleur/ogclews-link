# Scenario builder & generic policy levers

**Status:** design note + first primitives built. **Cross-refs:** `energy-as-production-input-spec.md`
(the energy-cost representation), `og-clews-denovo-analysis.md` (the channel/coupling architecture),
STATUS.md (MUIOGO = the GSoC UI that imports this package as its OG-side engine).

## Why this note

Scenarios are getting combinatorial: {channels} × {options} × {industries/resources} × {revenue uses}.
A user shouldn't hand-edit Python to explore them. Two things make that tractable, and both are now
seeded: (1) **generic, resource-agnostic policy levers** so the same primitive serves energy today and
agriculture/water later; (2) a **declarative choice catalog with defaults + templates** that a UI
(MUIOGO) can prompt from.

## 1. Generic policy levers (built: `ogclews_link/policy_levers.py`)

Every lever targets an industry **by index**, so it is resource-agnostic:

- `set_investment_incentive(p, industry, inv_tax_credit=, delta_tau=, tau_b_mult=, phase_years=)` —
  bias **private** capex in any industry by lowering its cost of capital (existing per-industry `(T+S,M)`
  firm-tax params; OG has no exogenous private-investment quantity, so this is the correct incentive
  channel). **Validated (SS, `experiments/run_energy_itc.py`):** a 20% energy ITC raises the energy
  industry's private capital **+5.0%** (targeted — other industries move <0.02%), aggregate K +0.01%,
  GDP ≈0 (−0.001%). Economic read: the ITC *reallocates* capital into energy as intended, but in OG
  alone it's a distortion toward a small sector (≈0 aggregate gain) — its payoff lives on the
  **CLEWS side** (emissions/energy-security) that OG doesn't price, which is precisely what the
  soft-link is for. A builder should surface that an in-OG capex subsidy looks ~free/slightly-negative
  on GDP; the benefit is the coupled CLEWS outcome.
- `route_revenue(p, pct_gdp_path, to=)` — direct a tax's revenue to `transfers` (`alpha_T`),
  `public_investment` (`alpha_I`→K_g), `government_consumption` (`alpha_G`), or `deficit` (no-op → the
  budget closure / debt-ratio rule absorbs it).

**The generality hook — `INDUSTRY_CATALOG`:** maps friendly names (energy, agriculture, water,
manufacturing, …) to their M=4 index **and a `separable_m4` flag**. Energy is separable today
(`Electricity`, index 1); **agriculture and water are bundled into "Natural Resources" in M=4**, so they
are flagged non-separable — `resolve_industry` warns and the UI can grey them out until a purpose-built
aggregation separates them (the same calibration choice in the energy-as-input spec). So the *code* is
already generic; the *data/aggregation* is the gate for agriculture/water — adding them is a catalog
entry + a finer SAM aggregation, not new lever code.

## 2. The choice catalog a UI prompts from

A scenario = a list of `(channel, options)` (the existing `framework.Experiment`). For a builder/UI,
expose each lever as a structured choice with a default and a domain:

| Choice | Domain | Default | Notes |
|---|---|---|---|
| target industry | `INDUSTRY_CATALOG` keys (separable ones enabled) | energy | greys out non-separable until calibrated |
| energy carrier | electricity / fuels / energy+water | electricity | drives θ_m & the dual to use (see energy spec) |
| energy-cost representation | investment-crowding-out / I-O-calibrated-Z / tau_c(recycled) | investment | never stack on the same cost |
| private-capex incentive | ITC % / accelerated-depreciation / CIT cut | none | `set_investment_incentive` |
| revenue use | transfers / public-investment / govt-consumption / deficit | transfers(recycled) | `route_revenue` |
| shock size `g` | from CLEWS dual ratio, or a manual % | CLEWS dual | dual is the rigorous source |
| phase-in years | int | 5 | |

Defaults encode the *defensible* choices (investment channel for capex; recycled revenue; dual-sourced
price), so a user who accepts defaults gets a sound scenario; advanced users override.

## 3. Templates

Named, pre-assembled scenarios (the existing `experiments.EXPERIMENTS` / `ACROSS_STEPS` are the seed).
Examples a UI would offer one-click:
- **Energy transition (structural):** investment→K_g (capex) + I-O-calibrated Z (operating cost) +
  carbon tax → `public_investment`.
- **Clean-air health:** the health channel (mortality + morbidity), cleaner-air direction.
- **Carbon tax, revenue-use comparison:** the same carbon price routed to transfers vs infrastructure vs
  deficit (three runs) — the distributional/GDP trade-off.
- **Energy investment push:** energy ITC (`set_investment_incentive`) ± accelerated depreciation.

## 4. The UI seam (MUIOGO)

Per STATUS.md, MUIOGO is the orchestrator/UI and imports this package as its OG-side engine via the
subprocess/CLI seam. So the scenario builder is: MUIOGO reads the **choice catalog + templates** from
here, prompts the user (defaults pre-filled, non-separable targets disabled), assembles the
`(channel, options)` list, and calls the existing CLI (`python -m ogclews_link run <experiment>`). No new
solve machinery — the builder is a thin declarative layer over the channels + levers that already exist.

## 5. Guardrails the builder must enforce

- **No double-counting:** never route the same energy cost through investment *and* Z *and* tau_c
  (channels already warn; the builder should hard-block the combination).
- **Recycle or it's a tax:** a `tau_c`/carbon revenue stream must be routed (transfers/infra/deficit), or
  it's an un-modeled fiscal expansion.
- **Separability:** disable agriculture/water/finer targets until the calibration supports them.
- **Magnitudes:** flag uncalibrated units (CLEWS-MUSD vs GDP) and placeholder dose-responses.
