# OG-Core and CLEWs/OSeMOSYS Integration Synthesis Report

## 1. Purpose and scope

This report synthesizes the work completed so far on OG-Core and CLEWs/OSeMOSYS integration.
It combines the findings from:

- the initial correspondence-table work,
- the CLEWs course material review,
- OG-Core documentation review,
- the IMPACCT-style integration framing,
- variable-level candidate mapping,
- theory-fit screening,
- and investment/fiscal channel assessment.

The objective is to establish a technically defensible integration strategy and a prioritized set of interaction channels for implementation.

## 2. Executive synthesis

### 2.1 Main conclusion

The strongest integration pattern is:

1. **Demand-led forward coupling (OG-Core -> OSeMOSYS/CLEWs)**
2. **Targeted feedback coupling (OSeMOSYS/CLEWs -> OG-Core)**
3. **Shared scenario governance and results layer**

This is consistent with the IMPACCT architecture and with how CLEWs/OSeMOSYS is practically used.

### 2.2 Guiding principle

The CLEWs course materials consistently support the principle:

**Demands are the drivers.**

That makes OG-Core-to-CLEWs demand-driver coupling the most native and robust first coupling surface.

### 2.3 Prioritized interaction classes

- **Phase 1 (high confidence):** demand drivers, public investment feedback, electricity-cost-to-productivity, core metadata/time/unit contracts.
- **Phase 2 (moderate confidence):** pollution-to-labor productivity, discount-rate harmonization, fiscal-envelope constraints, policy-cost proxies with guardrails.
- **Phase 3 (exploratory):** broad macro-price passthrough, operating-cost-to-fiscal accounts, reliability penalties, structural transformation links.

## 3. Evidence base used

### 3.1 Existing project artifacts

- `correspondence/ogcore-clews-correspondence.csv`
- `correspondence/ogcore-clews-interaction-map-high-level.csv`
- `correspondence/ogcore-clews-interactions-conceptual.csv`
- `correspondence/ogcore-clews-candidate-bridge-items.csv`
- `correspondence/ogcore-docs-clews-informed-areas.md`
- `correspondence/clews-course-assessment.md`
- `correspondence/ogcore-osemosys-variable-interactions-impacct.csv`
- `correspondence/ogcore-osemosys-investment-fiscal-shortlist.csv`
- `correspondence/ogcore-osemosys-investment-fiscal-findings.md`

### 3.2 Documentation base

- OG-Core theory and parameter documentation in `OG-Core/docs/book/content/`.
- OSeMOSYS manual source in `docs/OSeMOSYS-master/docs/manual/`.
- Integration framing from `docs/IMPACCT – An integrated assessment model for policy and financial decision-making in energy planning 1.pdf`.
- Consultant worked example and preliminary mapping from `docs/OG-CLEWsInterface.pdf`.

## 4. Integration architecture (synthesized)

### 4.1 Core architecture

1. **Orchestrator-led coupling** to manage run sequence and feedback loops.
2. **Shared scenario registry** with strict baseline vs reform pairing.
3. **Formal interface layer** for metadata, units, time mapping, and sector concordances.
4. **Explicit feedback loop definitions** with lag/smoothing rules.
5. **Shared results/KPI layer** for cross-model diagnostics and reporting.

### 4.2 Why this architecture fits both models

- OG-Core naturally provides macro trajectories (output, consumption, fiscal paths, prices, rates).
- OSeMOSYS/CLEWs naturally solves least-cost system design under exogenous demands and constraints.
- The strongest two-way design therefore starts with macro-informed demands and returns selected system outcomes as disciplined reduced-form macro shocks.

## 5. High-level interaction areas

| Interaction area | Direction | Priority | Synthesis finding |
|---|---|---:|---|
| Final demand pathways | OG-Core -> CLEWs | High | Best first-class linkage; aligns with demand-led optimization. |
| Public investment coordination | CLEWs -> OG-Core | High | Strong bridge via infrastructure investment profile to OG public-capital controls. |
| Energy system cost feedback | CLEWs -> OG-Core | High | Useful reduced-form macro feedback when carefully normalized vs baseline. |
| Emissions and pollution externalities | CLEWs -> OG-Core | High | Important, but requires external exposure/health translation modules. |
| Time-scale reconciliation | Bidirectional | High | Annual OG signals must map to CLEWs timeslices through explicit profiles/weights. |
| Spatial-sector concordance | Bidirectional | High | Required for reproducibility and non-spurious mapping. |
| Policy package consistency | Bidirectional | High | Prevents contradictory assumptions across models. |
| Scenario governance and iteration | Bidirectional | High | Essential for reproducible coupling and loop stability. |

## 6. Variable-level interaction candidates (prioritized)

### 6.1 Phase 1: implement first

| Candidate channel | Direction | Theory fit | Readiness | Notes |
|---|---|---|---|---|
| `Y_m` -> demand drivers (`AccumulatedAnnualDemand` / `SpecifiedAnnualDemand`) | OG-Core -> OSeMOSYS | Structural core | Strong | Requires concordance and intensity assumptions. |
| Macro annual demand -> `SpecifiedDemandProfile` | OG-Core -> OSeMOSYS | Structural core | Strong | Requires profile definitions that sum to 1. |
| `CapitalInvestment` -> `alpha_bs_I` / `alpha_I` | OSeMOSYS -> OG-Core | Structural core | Demonstrated | Best via baseline-relative ratios and public/private tagging. |
| Electricity system cost index -> `Z` | OSeMOSYS -> OG-Core | Reduced form | Demonstrated | Use relative changes, lag, and smoothing; keep sector mapping explicit. |
| Scenario/time/unit/concordance contract | Bidirectional | Structural core | Required | Foundational for all other channels. |

### 6.2 Phase 2: add with guardrails

| Candidate channel | Direction | Theory fit | Readiness | Guardrail needed |
|---|---|---|---|---|
| Pollution exposure proxy -> `e` | OSeMOSYS(+health) -> OG-Core | Reduced form | Strong | External exposure-response and working-age application logic. |
| OG rates (`r`, `r_gov`, `world_int_rate_annual`) -> `DiscountRate` | OG-Core -> OSeMOSYS | Reduced form | Strong | Real/nominal and annualization conventions must be explicit. |
| OG fiscal envelope -> `TotalAnnualMaxCapacityInvestment` / `TotalAnnualMaxCapacity` | OG-Core -> OSeMOSYS | Reduced form | Moderate | Currency-to-capacity conversion recipe required. |
| Carbon pricing policy -> `EmissionsPenalty` | Policy/OG -> OSeMOSYS | Strong (policy lever) | Strong | Keep incidence interpretation explicit in macro narrative. |

### 6.3 Phase 3: exploratory or high-assumption

| Candidate channel | Direction | Theory fit | Risk |
|---|---|---|---|
| Broad macro prices (`p_m`, `w`) -> cost scalars (`CapitalCost`, `VariableCost`, `FixedCost`) | OG-Core -> OSeMOSYS | Speculative/high-assumption | High double-counting risk. |
| Operating-cost outcomes -> OG fiscal accounts (`G`, `TR`, debt closure) | OSeMOSYS -> OG-Core | Speculative/high-assumption | Incidence and pass-through model missing. |
| Pollution proxy -> `chi_n` (labor disutility) | OSeMOSYS(+health) -> OG-Core | Speculative/high-assumption | Must be separated from `e` channel to avoid overlap. |
| Reliability metrics -> `Z` penalty | OSeMOSYS -> OG-Core | Speculative/high-assumption | Requires calibrated reliability-stress function. |
| Capacity mix outcomes -> macro structural paths | OSeMOSYS -> OG-Core | Speculative/high-assumption | Primarily narrative unless formal mechanism added. |

## 7. Economic-theory assessment (OG-Core lens)

### 7.1 Channels with strongest theoretical defensibility

- Demand-driver coupling from macro activity to energy-service demand.
- Public investment feedback through OG-Core fiscal/public-capital machinery.
- Policy lever mapping where OSeMOSYS has explicit constructs (for example, emissions penalty).

### 7.2 Channels that are valid but reduced-form

- Electricity cost pressure to productivity (`Z`).
- Pollution to labor productivity (`e`) and mortality (`rho`) when translated through explicit external epidemiology.
- Discount-rate harmonization as a scenario consistency mechanism.

### 7.3 Channels likely to be spurious without extra structure

- Direct broad mapping from macro prices to all OSeMOSYS costs.
- Direct mapping from OSeMOSYS operating costs to OG budget aggregates.
- Simultaneous pollution impacts on `e`, `chi_n`, and `rho` without decomposition.

## 8. Investment and fiscal synthesis

### 8.1 What OSeMOSYS can represent directly

- Capacity expansion and investment (`NewCapacity`, `TotalCapacityAnnual`, `CapitalInvestment`).
- Technology cost structures (`CapitalCost`, `VariableCost`, `FixedCost`).
- Policy-like pricing through `EmissionsPenalty`.
- Feasibility envelopes via capacity/investment constraints.

### 8.2 What should remain in OG-Core (or external finance layer)

- Full government budget closure.
- Debt and debt-service dynamics.
- Transfers and broad spending composition.
- Tax incidence and macro-distributional fiscal mechanisms.
- Endogenous financing market structure and risk pricing.

### 8.3 Practical implication

The most credible fiscal integration is a **soft link**:

- Keep full fiscal closure in OG-Core.
- Pass selected fiscal feasibility or policy signals into OSeMOSYS constraints/prices.
- Bring back selected OSeMOSYS investment burdens to OG public-investment controls.

## 9. Interface contract requirements (minimum viable)

A reusable integration implementation needs a formal contract covering:

1. **Scenario metadata:** run ID, baseline/reform pairing, region IDs.
2. **Time mapping:** calendar-year alignment, lag conventions, timeslice aggregation/disaggregation.
3. **Units and price basis:** real vs nominal, base year, deflators, ratio-vs-level policy.
4. **Sector concordance:** versioned matrix for OG sectors/goods to CLEWs demands/commodities/technologies.
5. **Transform definitions:** equations, parameters, smoothing, thresholds.
6. **Validation diagnostics:** unit/bounds/sign checks, volatility flags, plausibility checks.
7. **Provenance tracking:** source files, extraction recipes, and transform versions.

## 10. Recommended implementation sequence

### Phase 1 (build stable core)

1. Finalize scenario/time/unit/concordance contract.
2. Implement OG -> OSeMOSYS demand-driver pipeline.
3. Implement OSeMOSYS -> OG public investment feedback.
4. Implement electricity-cost-to-`Z` feedback with lag/smoothing guardrails.
5. Stand up shared KPI results package for validation.

### Phase 2 (expand with controlled complexity)

1. Add one health channel (`e` or `rho`) with external epidemiology module.
2. Add discount-rate harmonization and one fiscal constraint channel.
3. Add one explicit policy-price channel (`EmissionsPenalty`) to test policy coherence.

### Phase 3 (exploratory extension)

1. Evaluate speculative channels only with dedicated auxiliary models.
2. Promote channels to production only after passing double-counting and identifiability tests.

## 11. Key open decisions before full paper drafting

1. Target country calibration and sector resolution for OG-Core integration.
2. Canonical concordance version and ownership process.
3. Ratio-based vs level-based data exchange policy by channel.
4. Health-model choice for emissions/exposure translation.
5. Governance rules for iterative feedback-loop stopping criteria.

## 12. Final synthesis statement

The current body of work supports a credible integration pathway where OG-Core and CLEWs/OSeMOSYS interact through a demand-led forward pipeline and a small, prioritized set of disciplined feedback channels. The integration is strongest when constrained by a formal interface contract, explicit theory-based channel selection, and phased implementation that separates structural channels from exploratory reduced-form hypotheses.
