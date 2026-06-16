# OG-Core ⇄ CLEWS/OSeMOSYS — De Novo Interaction Analysis

Date: 2026-06-12. A fresh read of the two models' theory, deliberately *not* inheriting
the earlier channel registry (`integration_channel_registry.json`) or the OG-info
connector conclusions. Those are treated as one point in the design space, not the answer.

Grounded in primary sources: OG-Core theory book (`OG-Core/docs/book/content/theory/*.md`),
the OSeMOSYS manual + MathProg model code (`docs/OSeMOSYS-master/`), the CLEWS course, and
the macro-energy model-linking literature (TIMES-MACRO, MESSAGE-MACRO, MERGE; the `docs/tejas`
linking notes; IMPACCT).

---

## 1. The reframe (what reading the theory fresh changes)

The earlier work coupled the models through **quantities and reduced-form proxies**: push
`Y_m` forward into CLEWS demand, push an eyeballed electricity-cost-index back into TFP `Z`,
push capex into `alpha_I`. Reading the equations fresh changes three things:

1. **The load-bearing energy→macro channel is a price/dual channel, not a TFP knob.**
   OSeMOSYS is a linear program; the **shadow price of its commodity-balance constraint is the
   price of energy** — the endogenous, time- and region-resolved marginal cost of electricity,
   fuel, a crop, or water. The shadow price of an emissions cap is the **implied carbon price**.
   The old "electricity-cost-index → `Z`" was a hand-built average-cost proxy for exactly this
   marginal price. The right object is the dual.

2. **OG-Core has no energy in production at all.** The CES function takes exactly three inputs
   — private capital `K`, public capital `K_g`, labor `L` (`firms.md`, EqFirmsCESprodfun).
   There are no intermediate goods (the `io_matrix` maps production goods → consumption goods,
   not production → production). So energy can only enter OG as (a) one of the `I` consumption
   goods, (b) one of the `M` industries with its own output price `p_m`, (c) a TFP wedge `Z_m`,
   (d) a fiscal wedge `tau_c`/`tau_corp`, or (e) public capital `K_g`. Feeding energy cost into
   `Z` is smuggling energy through the one door that doesn't represent it.

3. **OG-Core is a richer macro core than the classic energy-macro models.** TIMES-MACRO,
   MESSAGE-MACRO, and MERGE bolt the energy LP onto a single-agent Ramsey growth core that
   yields GDP and consumption and nothing else. OG-Core adds full government budget closure
   (debt, taxes), household heterogeneity across age `S` and lifetime income `J`, and
   demographics. **So the meaningful interactions are the ones that engage that structure** —
   fiscal cost, distributional incidence, demographic feedback — not a generic energy↔GDP loop.

---

## 2. The structural seam

Each model is hollow exactly where the other is deep.

- **OG-Core solves** GE prices (`r`, `w`, `p_m`), the intertemporal/fiscal allocation
  (investment, debt, taxes), and the distribution across households; it **takes as given**
  energy demand, the discount rate, and carbon-tax policy. No energy, technology, emissions, or
  sub-annual time.
- **CLEWS/OSeMOSYS solves** least-cost capacity + dispatch (+ land + water), emissions, and —
  via duals — the price of every commodity and the carbon price; it **takes as given** the
  demand level, the discount rate, and cost trajectories. No behavioral demand response, no
  labor, no fiscal sector, no endogenous cost of capital.

The interface is **asymmetric**: quantities flow macro→energy, prices/duals flow energy→macro.
A correct coupled solution is the **fixed point where the energy demand OG-Core chooses at the
returned price equals the demand CLEWS was solved to meet** (marginal value of demand =
marginal cost of supply).

---

## 3. The meaningful interaction surface (ranked by use of each model's unique structure)

"Meaningful" = the two models genuinely share the object, coupling transmits information neither
has alone, and it is identified without double-counting or breaking either accounting identity.

1. **Energy price (commodity dual) → household budget → demand response + incidence.**
   The dual is the marginal cost of energy. Fed to OG households it makes demand price-responsive
   (closing the loop CLEWS can't) *and* reveals who bears higher prices (poorer households spend a
   larger income share on energy). No standard IAM produces that incidence. Richest channel; the
   one the prior work proxied most crudely.
2. **Energy-sector investment → capital market + fiscal closure → crowding-out and debt.**
   CLEWS `CapitalInvestment` is the capital the transition requires; in OG it competes for the
   savings pool (raising `r`, crowding out other investment) and, where public, lands on the budget
   as debt/taxes. OG's fiscal apparatus exists to price exactly this. Split private (`K`, crowds
   out `C`) vs public (`K_g`, crowds out `G`/debt); never also count it as autonomous OG investment.
3. **Carbon price / emissions → fiscal revenue + incidence (one-price discipline).**
   A carbon price appears once: either policy sets it (an `EmissionsPenalty` in CLEWS and a tax
   wedge in OG, same path both sides) or an emissions cap is set and its dual is the implied price.
   OG uniquely captures the revenue and its recycling/distribution. Caveat: a `tau_c` mapping
   mechanically inflates `cons_tax_revenue` — neutralize or it distorts the debt path.
4. **Equilibrium interest rate `r_t` → CLEWS discount rate.** OG produces an endogenous cost of
   capital; CLEWS discounts with a single exogenous `DiscountRate`. Feeding `r_t` in makes the two
   rank intertemporal trade-offs identically. Cheap, clean, one-way; a first-order consistency
   condition, not the afterthought the old registry treated it as.
5. **Economic activity / income → energy-service demand.** The forward driver (`Y_m` for industrial
   energy, `C_i`/income for residential/transport). Correct, but on its own a one-way push; becomes
   an equilibrium only when paired with (1).
6. **Emissions → health/damages → demographics (`rho`, `e`).** Genuinely meaningful and
   distinctively OG (mortality → population → labor → demand), but needs an external
   emissions→exposure→dose-response module OG doesn't contain. A bridge model, not a direct channel.
7. **Land/water scarcity duals → agricultural productivity.** CLEWS-CLEW produces a land rent and a
   water shadow price; OG has no land/water factor, so they enter only as a reduced-form TFP wedge on
   an ag sector. High conceptual interest, low near-term tractability; nearly absent from prior work.
8. **Wages → energy-sector labor costs.** Thin — CLEWS buries labor inside monetary cost params with
   no decomposition. A gap, not a channel. (This is what the earlier "structural gamma" work chased
   and found confounded.)

The prior research's headline energy→macro channel (cost → `Z`) sits at the *generic* end. The
richest channels (1, 2, 3, 6) engage OG's fiscal, distributional, and demographic structure and
were underweighted.

---

## 4. Thread 1 — the theoretical best

A **dual-exchanging iterated soft link that converges to the same fixed point a merged model
would** — informationally as complete as a hard link, differing only in that the solvers stay
separate (the TIMES-MACRO / MESSAGE-MACRO pattern). Its commitments:

- **Energy becomes a priced object inside OG** (a CES input and/or a consumption good carrying
  CLEWS's commodity dual) so the demand response is structural, as MACRO adds energy-service
  demands as production inputs.
- **Exchange is dual-based:** CLEWS exports commodity prices, the carbon dual, system cost, and
  capex; OG exports price-responsive demand and the equilibrium `r_t`.
- **Convergence is enforced** to the consistency conditions: demand fixed point, price fixed point
  (marginal value = marginal cost), cost subtracted from OG's resource constraint with the
  accounting identity intact every period, carbon price appearing once, investment with an explicit
  financing split, discount rates reconciled.
- **Stabilized** by a local quadratic/Taylor cost surrogate around each LP solution (so the macro
  side sees a smooth price slope, not a jumpy LP) plus baseline calibration so the coupled reference
  reproduces both standalone baselines.

A full **hard link is ruled out** (a theoretical conclusion, not convenience): OG solves an OLG
*transition path* while OSeMOSYS is a single *perfect-foresight* LP; OG has no scalar welfare to
fold the LP into; shocks can't be injected mid-solve (set on the parameter object before the
transition solver runs). Because OG carries fiscal and distributional structure the classic cores
lack, a realized OG-CLEWS is a step **beyond** TIMES-MACRO, not a re-implementation.

---

## 5. Thread 2 — the practical frontier

What is identifiable, available, stable, buildable, against the real frictions:

- **Duals aren't in CLEWS default output.** Extracting commodity/emission shadow prices needs the
  solver configured for marginals (GLPK/CPLEX/pyomo). Highest-value, least-exposed plumbing.
- **Demand is price-inelastic inside CLEWS**, so feeding a price back can oscillate. The elasticity
  must live in OG; the loop needs damping + baseline calibration to converge.
- **Units are arbitrary and unenforced** (CLEWS stores bare numbers; OG is real, numéraire =
  industry-M output, `factor` the only currency bridge and a steady-state object). A real ETL layer
  with curated unit/deflator/base-year maps is non-optional.
- **Time grids differ.** One OG period = `(ending_age − starting_age)/S` years (not 1 unless S=80);
  CLEWS has intra-year timeslices OG lacks. Demand-weight duals up; re-time period flows.
- **Double-counting hazards are enumerable** (energy cost as a wedge *and* in baseline TFP; carbon
  price on both sides; capex as CLEWS investment *and* OG autonomous investment; the `tau_c`
  phantom-revenue artifact). Each needs an explicit anti-double-count rule.
- **Foresight mismatch** (OLG transition vs perfect-foresight LP): decide which periods' duals feed
  which periods' OG parameters; possibly run CLEWS in limited-foresight windows.

The practical realization is a **staged soft link** where each near-term channel is an honest,
calibrated *proxy* for an ideal consistency condition, built in order of (rigor × data
availability). Its first job is not economics — it is the dual-extraction, unit, and time-mapping
plumbing everything rigorous depends on.

The two threads are the **same architecture at two maturities**: the practical path is a ladder of
approximations to the theoretical best, each rung replacing a proxy with a structural object. The
open design question is where on that ladder to stop for a given use case.

---

## 6. Theoretical feasibility test — where the shipped models already adapt vs need adjustment

The decisive question: **can OG-Core households react to an energy price?** Yes — already, in the
shipped model. Household demand for consumption good `i` (`households.md`, EqHH_ciDem2) is

    c_{i,j,s,t} = alpha_i * ( (1 + tau^c_{i,t}) p_{i,t} / p_t )^{-1} * c_{j,s,t} + c_min_{i}

— unit-elastic in the energy good's *effective* relative price above a Stone-Geary subsistence
floor (a necessity component + a discretionary one, which is economically right for energy). The
energy good's price `p_{i} = sum_m pi_{i,m} p_m` is built from the energy *industry's* output price,
which is its unit cost and moves only through `Z_m` or the factor shares. So there are three ways to
move the effective energy price the household faces, in increasing rigor:

- **(A) `tau_c` route — available now, demand-side.** Raise `tau_c` on the energy consumption good so
  the consumer price rises by the CLEWS-implied ratio. Cleanest price wedge (enters exactly the
  `(1+tau_c)p_i` term), but routes through government revenue → must be recycled (revenue-neutral) or
  it is a de-facto energy tax with fiscal effects.
- **(B) `Z` route — available now, supply-side.** Lower the energy *industry* TFP `Z_m` so its
  equilibrium price `p_m` (hence `p_i`) rises. Conflates "costlier" with "less productive"; use for
  the supply-cost/macro story, not the pure demand response.
- **(C) energy-as-CES-input — structural extension.** Add energy as a priced production input so cost
  passes through endogenously without a TFP or tax proxy. The rigor endpoint; a real OG-Core PR
  (extends the production function, FOCs, rents accounting), feasible because the CES is general, but
  not needed to start.

Feasibility by channel:

| Interaction | OG receiving/producing structure | Status | Adjustment if any |
|---|---|---|---|
| Activity/income → CLEWS demand | OG outputs `Y_m`, `C_i` | Ready (set CLEWS demand params) | none |
| **Energy price → demand response** | EqHH_ciDem2; energy good exists (PHL "Energy and water") | **Ready, no core change** via (A) or (B) | (C) optional for full rigor; or add a non-tax consumer price wedge param (small PR) to avoid phantom revenue |
| **Energy price → incidence** | households heterogeneous over `J×S` | **Ready** (incidence is an output once the wedge is applied) | none |
| Investment → public capital `K_g` | `alpha_I`, `alpha_I_m` time-varying; `K_g` LoM | Ready (param-level) | private-capex injection awkward → route as public, or via `inv_tax_credit` |
| Investment → crowding-out, `r`, debt | capital-market clearing + fiscal closure | Ready (output once investment injected) | none |
| Carbon price → fiscal revenue + incidence | `tau_c` by good/time; recycle via `alpha_T`/`alpha_G` | Ready (param-level) | one-price discipline; recycle the revenue |
| Discount rate `r_t` → CLEWS `DiscountRate` | OG outputs `r`/`r_p`; CLEWS param settable | Ready (CLEWS side) | reconcile real/nominal/annualization; make part of the iteration |
| Emissions → health → `rho`, `e` | `rho`, `e` time-varying inputs (PEP already hand-sets) | OG side ready; bridge missing | build/integrate external dose-response module |
| Land/water duals → ag productivity | OG ag-sector `Z` | OG side ready; needs CLEW + dual extraction | coarse (TFP proxy only) |
| Wages → energy labor cost | labor buried in CLEWS cost params | Not meaningful (thin seam) | — |

**Verdict.** Most channels are **ready at the parameter level — the receiving/producing structure
already exists.** The integration is mostly an orchestration + calibration job, not model surgery.
The one load-bearing theoretical question (price-responsive demand) is answered *yes* by existing
structure and is testable now. The one genuine optional extension is energy-as-production-input
(rigor endpoint, real PR). The real near-term work is infrastructure: dual extraction, units/time
mapping, and the damped iteration loop — i.e. Thread 2.

---

## 7. Research goal (charter for agentic work)

> Determine, from the first-principles structure of OG-Core (an OLG general-equilibrium model with
> full fiscal closure and household heterogeneity) and CLEWS/OSeMOSYS (a least-cost energy–land–water
> LP), the complete set of *meaningful, theoretically defensible* interactions between them — shared
> economic objects where one model endogenizes what the other must assume, coupling transmits
> information neither has alone, and the linkage is identified without double-counting or violating
> either model's accounting identities. Establish two parallel characterizations: (1) the
> **theoretical best** — the ideal dual-exchanging coupling and the exact consistency conditions a
> correct coupled solution must satisfy (energy quantity and its shadow price, energy-system cost and
> investment, the carbon price, the discount rate), drawing on the macro-energy linkage literature
> while exploiting the fiscal, distributional, and demographic structure that makes OG-Core a richer
> macro core than the single-agent cores those models use; and (2) the **practical frontier** — what
> is identifiable, extractable, unit-consistent, time-alignable, and numerically stable given that
> CLEWS demand is price-inelastic, its duals are not exposed by default, its units are arbitrary, and
> the OLG transition path cannot be hard-linked to a perfect-foresight LP. Treat the prior channel
> registry as one point in this space, not the answer. The deliverable is a defensible interaction
> taxonomy plus a staged path from calibrated proxy to dual-consistent integration, prioritizing the
> channels — energy-price incidence, transition investment and fiscal/debt cost, and carbon-revenue
> distribution — that only this pair of models can jointly resolve.

---

## 8. Source maps

Two structural maps and a methods survey underpin this analysis (built de novo from primary sources):
the OG-Core map (model identity, dimensional structure, exogenous inputs, endogenous outputs incl.
prices, accounting identities, silences, ports, coupling subtleties); the OSeMOSYS/CLEWS map (the LP,
sets, params, variables, **the dual side — commodity/emission/land/water shadow prices**, physical
balances, silences, ports); and the linking-methodology survey (hard vs soft, quantity vs price/dual,
TIMES-MACRO decomposition, the demand-elasticity reconciliation). Prototype code home:
a standalone `ogclews-link` package (keeps both models independently runnable; later imported by
MUIOGO as the orchestration engine).
