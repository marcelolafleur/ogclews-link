# The OG-Core × CLEWS integration framework — explanation

A companion to the diagrams and deck: what the framework is, how to read each figure, and the
key takeaway of each. Written for an energy-economy / IAM audience; doubles as speaker notes and
a text source for your own slides. Content tracks `ogclews_link/channels.py`, `STATUS.md`, and
`docs/design/`.

## In one paragraph

We soft-link two models that are each hollow exactly where the other is deep. **OG-Core** is an
overlapping-generations general-equilibrium macro model (Philippine calibration, OG-PHL) with full
fiscal closure and household heterogeneity over age `S` and lifetime income `J` — but it takes
energy demand, the discount rate, and carbon policy as given, and has *no energy in production*.
**CLEWS/OSeMOSYS** is a least-cost energy–land–water linear program that solves capacity, dispatch,
emissions, and — through its constraint duals — the price of every commodity and the carbon price,
but has no behavioural demand, no labour, no fiscal sector, and an exogenous discount rate.
Quantities flow macro→energy; prices and duals flow energy→macro. A correct coupled solution is the
**fixed point** where the energy demand OG-Core chooses at the returned price equals the demand
CLEWS was solved to meet. The link is realized as seven small, guard-railed, unit-tested **channels**,
assembled into reproducible **experiments** by a config-driven CLI (`ogclews-link`), with a scenario
builder on top.

## 1 · The structural seam (`architecture.pdf`)

Two panels — OG-Core (blue) and CLEWS (teal) — each listing what it **solves** and what it **takes
as given**. Between them, the asymmetric exchange: the top arrow carries *quantities and rates*
(energy-service demand `Y_m, C_i`; the equilibrium rate `r_p`) macro→energy; the bottom arrow carries
*prices, duals, and damages* (the energy commodity dual; transition capex; emissions→health)
energy→macro. The card below states the fixed-point condition. **Takeaway:** a *hard* link is ruled
out (OG solves an OLG transition path; OSeMOSYS is a single perfect-foresight LP), so the link is a
disciplined soft link that keeps both models independently runnable.

## 2 · The seven channels

**Plain-language flows (`ch_*.pdf`) — the main channel explanation.** Each is a mechanism explainer:
the trigger, the **specific OG-Core object it moves** (or reads), and the resulting effect — with the
scope/condition caveats that keep it honest. CLEWS→OG and policy channels *move* an OG parameter;
OG→CLEWS channels *read* an OG output (nothing in OG changes — the macro effect only returns via the loop).

- **Health** (`ch_health`) — PM2.5 emissions ratio × external GBD dose-response. **Mortality** moves
  `ρ` (mortality by age) → population recompute → **demographics** (saved lives skew elderly → few extra
  workers, ~0 output); **morbidity** moves `e` (effective labour by age) → **productivity** (a fitter
  working-age population → output per worker — the main effect). Dose-response magnitudes are placeholders.
- **Energy prices** (`ch_energy`) — moves `τ_c`, a **consumption-tax / price wedge** on the energy good,
  into the household demand FOC. Demand falls; the incidence is **regressive only when energy is a
  necessity (`c_min`>0)** — the bare wedge is ~homothetic. It is a tax wedge, so the revenue accrues to
  government: **recycle via `α_T`** to isolate the pure price/distributional effect (un-recycled it's a
  tax-transfer, not a resource cost).
- **Carbon price** (`ch_carbon`) — moves the same `τ_c` wedge but on **household energy only** (OG has no
  energy in production, so industrial/economy-wide carbon is unpriced on the OG side — that is the CLEWS
  `EmissionsPenalty`). Revenue is **optionally** recycled via `α_T` → roughly revenue-neutral *if recycled*.
- **Investment** (`ch_investment`) — **public infrastructure only**: routes grid/T&D capex to `α_I` →
  public capital `K_g` (productive via `γ_g`, raises output) against debt/tax financing (crowds out
  spending). Private generation capex has its **own channel** (capital intensity, next), or rides the
  cost-push / a capex incentive — **not** this public channel.
- **Capital intensity** (`capital_intensity`) — the private-generation twin of investment: CLEWS→OG,
  **moves** the energy industry's capital share `γ[m]`. A capex-heavy clean buildout (renewables/CCS)
  makes energy structurally more capital-intensive → it pulls in capital, raises the cost of capital and
  crowds out other industries (all endogenous), and lowers energy's labour share (the residual
  `1 − γ − γ_g`). Calibrated from the CLEWS power-fleet capital-cost-share ratio. One of three views of
  generation capex (`γ` / cost-push `Z` / ITC) — use one.
- **Cost of capital** (`ch_discount`) — *reads* `r_p` (equilibrium cost of capital) → CLEWS `DiscountRate`
  → which long-lived projects are least-cost. As an OG→CLEWS driver, its macro effect returns via the loop.
- **Demand** (`ch_demand`) — *reads* `Y_m`/`C_i` (activity) → CLEWS `SpecifiedAnnualDemand` → more
  capacity (cost & emissions). Like the discount rate, it bites only once the loop runs.

**Technical reference (`channels.pdf`, appendix).** The same seven at the variable level: each is a
wire between a named OG-Core parameter and a named CLEWS variable. Direction = colour + arrowhead;
theory status = line style (solid = structural, dashed = reduced-form).

| Channel | OG-Core object | CLEWS object | Direction | Theory |
|---|---|---|---|---|
| `energy_price` | `tau_c` on the energy good → demand FOC + incidence | commodity-balance **dual** (ELC shadow price) | CLEWS→OG | structural |
| `investment` | `alpha_I` → `K_g` (public capital) → crowding-out, debt | `CapitalInvestment` (power-sector capex, T&D) | CLEWS→OG | structural |
| `capital_intensity` | `gamma[m]` (energy industry capital share) → capital pull, crowding-out, ↓labour share | power-fleet capital-cost-share ratio | CLEWS→OG | structural |
| `health` | `rho` (mortality), `e` (effective labour) | emissions → dose-response (external GBD bridge) | CLEWS→OG | reduced-form |
| `carbon` | `tau_c` on household energy (optional `alpha_T` recycle) | `EmissionsPenalty` | policy (both) | structural |
| `discount_rate` | `r_p` (equilibrium cost of capital) | `DiscountRate` | OG→CLEWS | structural |
| `demand` | `Y_m`, `C_i` (activity, consumption) | `SpecifiedAnnualDemand` (scaled) | OG→CLEWS | structural |

`clews→og` and `policy` channels mutate the OG **reform** parameters *before* the reform solve;
`og→clews` channels run *after* the solve and emit CLEWS input files. **Takeaway — the load-bearing
channel is `energy_price` via the dual:** the economically meaningful energy→macro signal is the
*dual of the OSeMOSYS commodity-balance constraint* (the marginal electricity price), not a TFP knob.
Because OG-Core has no energy in production, it enters through the household price wedge `tau_c` on the
energy good — which makes demand price-responsive *and*, because households are heterogeneous over
`S×J`, reveals **incidence** no single-agent IAM can produce. The carbon price obeys one-price
discipline: set once, fed to OG (`tau_c`, recycled) and CLEWS (`EmissionsPenalty`) on the same path.

## 3 · The iterated soft-link (`loop.pdf`)

The orchestrator (`ogclews-link`) drives a damped quantity/price exchange to the fixed point — the
MESSAGE-MACRO / TIMES-MACRO pattern. OG is driven **in-process** (`import ogcore`; channels mutate
the live `Specifications`); CLEWS is driven **out-of-process** (read a run directory; re-solve by
subprocess). **Honesty:** the dashed segment is the external CLEWS re-solve — *not yet wired*, so the
multi-pass loop honestly degrades to one pass today. What is validated now is a single CLEWS→OG pass.

## 4 · The scenario builder (`scenarios.pdf`)

Scenarios are combinatorial ({channels} × {options} × {industries} × {revenue uses}), so the builder
tames them with: a **choice catalog** whose defaults encode the defensible choice (investment channel
for capex, dual-sourced price, recycle on); two **generic, resource-agnostic levers**
(`set_investment_incentive`, `route_revenue`) that target an industry by *index* via a per-model
registry; and named **templates** (energy transition, clean-air health, carbon-tax revenue-use
comparison, energy investment push). One CLI runs any of them; MUIOGO (the UI) prompts from this same
catalog. Four **guardrails** are enforced throughout: no double-counting, recycle-or-it's-a-tax,
separability, and flag uncalibrated magnitudes.

## 5 · Example outputs (the curated figures)

Real read-outs from the four-step `across_steps` run on OG-PHL, in the editorial house style
(honest by construction: direction/magnitude words are derived from the data, and the source line
carries the caveats).

- **`waterfall_gdp`** — channel decomposition: the marginal contribution of each policy step to
  output, with the health bar split into mortality vs morbidity. *Magnitudes are illustrative* (a
  +20% cost-index proxy, not the dual; uncalibrated units; carbon revenue not recycled).
- **`energy_by_income`** — the distributional incidence only OG-Core can produce: energy-good demand
  change by lifetime-income group, one line per step.
- **`health_gdp_split`** — the +health GDP gain is dominated by the (placeholder) *morbidity*
  multiplier, **not** lives saved: PHL PM2.5 deaths skew elderly, so saved lives add retirees, not
  workers. Do not report the gain as a lives-saved effect.
- `welfare_cev_by_group`, `macro_transition`, `headline_dashboard` — welfare incidence, transition
  paths, and an overview.

## 6 · The maturity roadmap (`maturity.pdf`)

Where each channel sits today on the rigor axis (illustrative shock → calibrated proxy → structural
object → dual-consistent fixed point) and where it is heading. Filled marker = today; open marker =
target. **Takeaway:** the practical frontier is a *ladder of approximations* to the dual-exchanging
theoretical best — each rung replaces a proxy with a structural object. `discount_rate` is essentially
ready (one-way); `energy_price` has the dual wired and needs a real run + the loop; `carbon`/
`investment` need the unit/deflator bridge; `health` needs the real GBD dose-response.

## 7 · Honest status

**Validated now:** CLEWS→OG one pass (apply `energy_price`, `investment`, `carbon`, `health`; solve
OG; macro + distributional + fiscal read-outs); reproduced −16.6% energy demand + income-group
incidence on OG-PHL; producer side emits CLEWS inputs; the commodity dual reader is built and
verified; `health` solves end-to-end; 24/24 transform tests pass (numpy-only, no solve).
**Stubbed / placeholder:** loop closure (the external CLEWS re-solve); the unit/deflator bridge
(so carbon/investment magnitudes are illustrative); the health dose-response and morbidity response
(pending the real GBD PHL ambient-PM2.5 export); energy `c_min` must be calibrated before use.
