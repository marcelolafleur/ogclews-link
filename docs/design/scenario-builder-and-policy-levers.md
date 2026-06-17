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

**The generality hook — a per-model registry, NOT a hardcoded catalog.** OG-Core carries only `p.M`
(the industry COUNT) — no names, no resource tags. So the industry structure is **derived per onboarded
model** by `industry_registry(p, names=, resource_index=)`:
- **count** comes from `p.M`; a **single-industry (M=1)** model reports `single_industry=True` and has no
  separable sectors — resource targeting is unavailable there, and `resolve_industry("energy", …)` raises
  with a clear message ("represent it as a consumption good or an economy-wide TFP/tax wedge"). This is
  the correct degradation for a 1-sector onboarding.
- **names** come from the country's calibration ordering (`list(PROD_DICT)`); if a model declares none,
  the registry falls back to `industry_0..M-1` (index-only — the UI must label or the user targets by
  index).
- **resource→index tags** are **declared by the country config** (e.g. `concordance.energy_industry_index`),
  because OG has no resource concept itself. An undeclared resource (e.g. agriculture/water on a model
  whose aggregation bundles them) raises an actionable "declare it in the country config / pass its
  index" error. The levers act on a validated integer index, so they're M-, ordering-, and country-
  agnostic. Onboarding a new model (any M, any country, single- or multi-industry) is: provide its
  `names` + `resource_index`; no lever code changes. Targeting agriculture/water for PHL still needs a
  finer aggregation that *creates* those industries (the calibration choice in the energy-as-input spec)
  — then the country just declares the new index.

## 2. The choice catalog a UI prompts from

A scenario = a list of `(channel, options)` (the existing `framework.Experiment`). For a builder/UI,
expose each lever as a structured choice with a default and a domain:

| Choice | Domain | Default | Notes |
|---|---|---|---|
| target industry | `industry_registry(p)` names + declared resources (M=1 → none) | energy (if declared) | derived per onboarded model; greys out undeclared/non-separable |
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
