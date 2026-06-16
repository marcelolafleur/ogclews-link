# OG-Core <-> CLEWS/OSeMOSYS Integration Worklog

## Purpose

This is the running design document for exploring a practical and theoretically sound integration between OG-Core and CLEWS/OSeMOSYS.

The immediate objective is not to "wire everything together." It is to identify:

- candidate exchange variables that are actually supported by both models,
- transformations that are economically interpretable,
- code touchpoints where those transformations would enter,
- and a phased experiment plan for testing them.

This worklog should stay close to:

- model theory,
- actual code structure,
- and the scenario meaning of each proposed linkage.

## Working Principles

1. Keep the models separate and orchestrated, not fused into one solver.
2. Prefer channels that already correspond to native model inputs or outputs.
3. Prefer ratio-based reform-vs-baseline transformations before level-based mappings.
4. Separate structural channels from reduced-form channels.
5. Record economic intuition explicitly, not just variable names.
6. Reject channels that imply double counting unless the accounting boundary is clear.

## Evidence Base in This Repo

### Existing synthesis and correspondence artifacts

- `correspondence/ogcore-clews-integration-synthesis-report.md`
- `correspondence/ogcore-docs-clews-informed-areas.md`
- `correspondence/ogcore-osemosys-investment-fiscal-findings.md`
- `correspondence/ogcore-clews-candidate-bridge-items.csv`
- `correspondence/ogcore-clews-interaction-map-high-level.csv`
- `correspondence/ogcore-clews-correspondence.csv`
- `correspondence/ogcore-osemosys-variable-interactions-impacct.csv`
- `correspondence/ogcore-osemosys-investment-fiscal-shortlist.csv`
- `correspondence/og_to_osemosys_demand_sample.py`

### Supporting documents

- `docs/tejas/OG-CLEWS Linking (1).pdf`
- `docs/tejas/TIMES-Macro_Decomposition-into-hard-linked-LP-and-NLP-problems.pdf`
- `docs/OG-CLEWsInterface.pdf`
- `docs/IMPACCT – An integrated assessment model for policy and financial decision-making in energy planning 1.pdf`
- `docs/OSeMOSYS-master/docs/manual/`
- `OG-Core/docs/book/content/`

## Model Structure Notes

### OG-Core structure

OG-Core is a dynamic general equilibrium model. The variables we care about for integration are not arbitrary knobs. They live inside a coherent macro accounting and optimization structure.

#### Production side

At the firm level, output is produced by a CES production function over private capital, public capital, and labor, scaled by total factor productivity `Z`.

Relevant code surface:

- `OG-Core/ogcore/firm.py`
- `get_Y(K, K_g, L, p, method, m=-1)`

Economic intuition:

- `Z` is the cleanest reduced-form way to say "the same capital and labor now produce more or less output."
- `K_g` is the cleanest way to say "public infrastructure changes productive capacity."
- `gamma`, `gamma_g`, and `epsilon` govern how strongly those inputs matter and substitute.

Implication for integration:

- If CLEWS tells us energy services become more expensive or less reliable, that does not directly alter OG-Core demand equations.
- The most defensible macro entry points are productivity-like or public-capital-like channels, not ad hoc physical-state variables.

#### Fiscal and public capital side

OG-Core has explicit pathways for government infrastructure investment and public capital accumulation.

Relevant code and documentation surfaces:

- `OG-Core/ogcore/parameters.py`
- time-path parameters include `alpha_I`, `alpha_bs_I`, `world_int_rate_annual`
- `OG-Core/ogcore/aggregates.py`
- `resource_constraint(Y, C, G, I_d, I_g, net_capital_flows, RM)`
- OG-Core theory docs on government and firms

Economic intuition:

- `alpha_I` and `alpha_bs_I` are not generic policy tags. They change public infrastructure investment, which then changes public capital and eventually output.
- Any OSeMOSYS investment feedback sent into OG-Core through these parameters should be interpreted as a claim about public infrastructure needs, not total system spending in the abstract.

#### Consumption tax and health-related channels

Relevant OG-Core input surfaces include:

- `tau_c`
- `rho`
- `chi_n`
- `e`

Economic intuition:

- `tau_c` is a policy incidence channel and creates government revenue.
- `rho` changes mortality and therefore demographics.
- `e` changes effective labor productivity.
- `chi_n` changes labor disutility and therefore labor supply choices.

Implication for integration:

- These channels can be powerful, but they are easy to misuse.
- A carbon price or pollution burden should not be mapped into these inputs without being explicit about the mechanism.

### OSeMOSYS/CLEWS structure

OSeMOSYS is a linear optimization model. It minimizes discounted system cost subject to demand satisfaction, technology, resource, and policy constraints.

Relevant code surface:

- `docs/OSeMOSYS-master/docs/manual/documents/OSeMOSYS code/osemosys_short_2017_11_08.txt`

#### Demand side

Key inputs:

- `SpecifiedAnnualDemand`
- `SpecifiedDemandProfile`
- `AccumulatedAnnualDemand`

Economic intuition:

- OSeMOSYS demand is an input, not an equilibrium outcome.
- If macro conditions are meant to change service demand, that change has to arrive through these parameters or through upstream demand-driver logic.

Implication for integration:

- OG-Core -> OSeMOSYS demand translation is structurally native.
- This is the strongest first coupling surface.

#### Cost and investment side

Key parameters and variables:

- `CapitalCost`
- `VariableCost`
- `FixedCost`
- `CapitalInvestment`
- `DiscountRate`
- `EmissionsPenalty`
- `TotalAnnualMaxCapacityInvestment`
- `TotalAnnualMaxCapacity`

Economic intuition:

- OSeMOSYS is very good at converting exogenous demand and policy assumptions into least-cost infrastructure and operating pathways.
- It is not a macro-fiscal model and does not endogenize government debt, household behavior, or incidence.

Implication for integration:

- Investment outputs can inform OG-Core if we define an explicit public/private interpretation.
- Policy levers like `EmissionsPenalty` are defensible because they are already native to OSeMOSYS.

## Integration Architecture Assumption

The working assumption is a soft-link / decomposition architecture:

1. Run OG-Core baseline and reform scenarios to generate macro signals.
2. Translate selected macro signals into CLEWS/OSeMOSYS demand and policy inputs.
3. Run CLEWS/OSeMOSYS baseline and reform scenarios.
4. Translate selected energy-system outcomes back into OG-Core shocks or controls.
5. Iterate only where the channel definition is stable and the stopping rule is clear.

This is closer to TIMES-Macro style decomposition and IMPACCT-style orchestration than to a merged solver.

## Channel Evaluation Rubric

Each candidate bridge is classified using three questions:

### 1. Theory fit

- `structural_core`: The target variable is a native and interpretable mechanism.
- `reduced_form_supported`: The target variable can support the shock, but only as a proxy.
- `speculative_or_high_assumption`: The mechanism is weak, incomplete, or likely to double count.

### 2. Scenario interpretation

What does the transformation mean in plain economic terms?

Examples:

- "Higher public energy infrastructure needs require higher public investment."
- "More expensive electricity lowers productivity in energy-intensive production."
- "Higher macro output raises final energy-service demand."

### 3. Accounting discipline

What must not be counted twice?

Examples:

- A carbon-price shock passed as both `tau_c` and `EmissionsPenalty`.
- Energy cost pressure passed into both `Z` and broad OG-Core prices.
- Pollution burden passed into both `e` and `chi_n` without decomposition.

## Initial Channel Set for Deep Work

### Channel A: OG-Core activity/output -> OSeMOSYS demand inputs

Status:

- Structural core
- Phase 1
- Active

Candidate variables:

- OG-Core `Y_m`
- possibly OG-Core `C_i`
- OSeMOSYS `AccumulatedAnnualDemand`
- OSeMOSYS `SpecifiedAnnualDemand`
- OSeMOSYS `SpecifiedDemandProfile`

Code touchpoints:

- OG-Core output definitions and variables docs
- OSeMOSYS demand parameters and energy-balance equations

Economic intuition:

- If the macroeconomy grows differently across sectors, final energy-service demands should not remain fixed on an unrelated path.
- This is the most natural forward coupling because OSeMOSYS already expects demand exogenously.

Working transformation options:

1. Ratio-based demand scaling from a base-year demand path.
2. Sector-concordance weighted mapping from `Y_m` to energy-service demand classes.
3. Annual demand path plus separate timeslice-profile logic.

Key open questions:

- Should the primary macro driver be sectoral output `Y_m`, consumption `C_i`, or both?
- Which OSeMOSYS demand parameter is canonical for each demand category?
- How should annual macro signals map into timeslice profiles?

Current implementation anchor:

- `correspondence/og_to_osemosys_demand_sample.py`

### Channel B: OSeMOSYS `CapitalInvestment` -> OG-Core `alpha_bs_I` / `alpha_I`

Status:

- Structural core, with tagging assumptions
- Phase 1
- Active

Candidate variables:

- OSeMOSYS `CapitalInvestment[r,t,y]`
- OG-Core `alpha_bs_I`
- OG-Core `alpha_I`

Economic intuition:

- New public energy infrastructure is a public investment burden.
- In OG-Core terms, that burden belongs in public infrastructure investment only if the relevant OSeMOSYS technologies are interpreted as publicly financed or publicly provided.

Working transformation options:

1. Public-share ratio vs baseline -> `alpha_bs_I`
2. Public investment share of GDP -> `alpha_I`
3. Keep private-system investment out of this channel unless a separate financing mechanism is defined

Key open questions:

- What technology tagging determines "public" versus "private"?
- Is the country setup expected to use `baseline_spending=True`?
- Should the transform stay ratio-based until we have explicit currency/deflator rules?

### Channel C: OSeMOSYS electricity-system cost signal -> OG-Core `Z`

Status:

- Reduced-form supported
- Phase 1
- Active with guardrails

Candidate variables:

- OSeMOSYS electricity cost index or derived unit-cost measure
- OG-Core `Z`

Economic intuition:

- More expensive or more constrained electricity can act like a productivity drag on sectors that rely on energy as an essential intermediate condition.
- This does not mean electricity cost literally is TFP. It means `Z` is being used as a disciplined proxy for economy-wide efficiency pressure.

Working transformation options:

1. Relative electricity cost change vs baseline -> lagged `Z` multiplier
2. Sector-specific exposure weights if OG-Core industry detail supports them
3. Smoothing/damping to prevent implausible volatility

Key open questions:

- What exact OSeMOSYS result should define the electricity cost index?
- Is the transform economy-wide or only for mapped industries?
- What lag structure is economically defensible?

## Detailed Variable-Level Assessment

This section tightens the active channels from conceptual candidates into more specific interconnections.

### Interconnection 1: OG-Core activity and consumption -> OSeMOSYS demand inputs

#### Variables and dimensions

OG-Core side:

- `Y_m`: total output by industry, dimensions `T x M`
- `C_i`: total consumption by consumption good, dimensions `T x I`

Relevant OG-Core theory:

- Household demand is defined over consumption goods `C_i`.
- Production goods and consumption goods are linked by the fixed coefficient matrix `Pi^I`, where:
  - `p_i,t = sum_m pi_i,m p_m,t`
  - `C_m,t = sum_i pi_i,m C_i,t`
- For goods-market clearing:
  - for industries `m = 1, ..., M-1`, `Y_m,t = C_m,t`
  - industry `M` is special because its output also absorbs private investment, public investment, government consumption, debt-related flows, and remittances.

Implication:

- `C_i` is the cleaner macro driver for household or final-consumption demand categories.
- `Y_m` is the cleaner macro driver for industrial activity or sector output demand categories.
- `Y_m` for the numeraire/capital-good industry should not be used naively as a household-demand proxy.

OSeMOSYS side:

- `SpecifiedAnnualDemand[r,f,y]`
- `SpecifiedDemandProfile[r,f,l,y]`
- `AccumulatedAnnualDemand[r,f,y]`

Relevant OSeMOSYS logic:

- `SpecifiedAnnualDemand` and `SpecifiedDemandProfile` enter time-slice demand balance:
  - `SpecifiedAnnualDemand[r,f,y] * SpecifiedDemandProfile[r,f,l,y]`
- `AccumulatedAnnualDemand` enters annual energy balance directly.
- `SpecifiedAnnualDemand` and `AccumulatedAnnualDemand` are mutually exclusive for the same commodity-year.

#### Recommended mapping rule

Use two distinct demand bridge families, not one:

1. Final-demand bridge

   Use `C_i` for household/commercial/service demand categories:

   `DemandIndex_d,t = sum_i A_d,i * (C_i,t^reform / C_i,t^base)^eta_d,i`

   `SpecifiedAnnualDemand_d,t^reform = SpecifiedAnnualDemand_d,t^base * DemandIndex_d,t`

2. Activity-demand bridge

   Use `Y_m` for industrial or output-linked demand categories:

   `ActivityIndex_d,t = sum_m B_d,m * (Y_m,t^reform / Y_m,t^base)^eta_d,m`

   `AccumulatedAnnualDemand_d,t^reform = AccumulatedAnnualDemand_d,t^base * ActivityIndex_d,t`

For profiled demands:

- keep `SpecifiedDemandProfile` fixed in the first pass unless there is an independent reason to alter within-year demand shape.
- treat annual demand growth and profile shape as separate transforms.

#### Economic interpretation

- `C_i` says households consume more or less of a class of goods and services.
- `Y_m` says a sector produces more or less output and therefore uses more or less energy-service input.
- These are not the same statement and should not be collapsed into one demand driver by default.

#### Preferred use cases

Use `C_i` when the CLEWS demand category is:

- residential electricity,
- household transport service,
- household fuels,
- commercial/service final demand if represented as final consumption.

Use `Y_m` when the CLEWS demand category is:

- industrial energy use,
- process heat,
- agriculture production activity,
- freight/industrial transport tied to production activity.

#### Failure modes

- Mapping the same CLEWS demand category from both `C_i` and `Y_m` without decomposition.
- Using `Y_m` from the capital-good/numeraire industry as if it were household final demand.
- Defining both `SpecifiedAnnualDemand` and `AccumulatedAnnualDemand` for the same commodity-year.
- Changing annual demand and profile shape simultaneously without knowing which effect drove the result.

### Interconnection 2: OSeMOSYS `CapitalInvestment` -> OG-Core `alpha_bs_I` / `alpha_I`

#### Variables and dimensions

OSeMOSYS side:

- `CapitalInvestment[r,t,y]`: annual undiscounted investment in new capacity of technology `t`
- derived conceptually from:
  - `CapitalInvestment[r,t,y] = CapitalCost[r,t,y] * NewCapacity[r,t,y]`

OG-Core side:

- `alpha_I`: exogenous fraction of GDP allocated to public infrastructure investment
- `alpha_bs_I`: proportional adjustment to baseline infrastructure spending when `baseline_spending=True`
- `I_g`: aggregate public infrastructure investment, dimensions `T`
- `K_g`: public capital stock, dimensions `T`

Relevant OG-Core equations:

- if `baseline_spending=False`:
  - `I_g,t = alpha_I,t * Y_t`
- if `baseline_spending=True`:
  - `I_g,t = alpha_bs_I,t * I_g,t^baseline`
- public capital law of motion:
  - `K_g,t+1 = ((1 - delta_g) * K_g,t + I_g,t) / ((1 + g_n,t+1) * exp(g_y))`

#### Recommended mapping rule

The bridge should begin with a public-investment subset:

`I_pub^clews[r,y] = sum_{t in T_pub} phi_pub[r,t,y] * CapitalInvestment[r,t,y]`

where:

- `T_pub` is the set of technologies treated as public infrastructure,
- `phi_pub` is the public financing share in `[0,1]`.

Then use one of two transform variants.

Variant A: baseline-relative reform multiplier

Use only when the CLEWS public-investment concept and OG baseline infrastructure concept are harmonized:

`alpha_bs_I,t = I_pub,t^clews,reform / max(I_pub,t^clews,base, eps)`

Variant B: increment-over-OG-baseline

Use when the CLEWS delta is credible but the baseline concepts are not identical:

`DeltaI_pub,t = I_pub,t^clews,reform - I_pub,t^clews,base`

`alpha_bs_I,t = 1 + DeltaI_pub,t^converted / max(I_g,t^OG,base, eps)`

Use `alpha_I` only when the intended interpretation is explicitly "public investment share of GDP":

`alpha_I,t = I_pub,t^converted / Y_t`

#### Economic interpretation

- This is not a generic energy-system cost feedback.
- It is a public-finance and productive-capital channel:
  - more public energy infrastructure spending raises `I_g`,
  - which raises `K_g`,
  - which raises productive capacity through the public-capital term in firms' production.

#### Preferred use cases

Good candidates for `T_pub` include:

- transmission and distribution,
- public grid reinforcement,
- public charging infrastructure,
- publicly financed water-energy infrastructure,
- other infrastructure assets clearly financed or provided by government.

Bad candidates by default:

- privately financed generation,
- household investment,
- firm-owned process equipment,
- assets financed entirely outside government accounts.

#### Failure modes

- Treating total `CapitalInvestment` as public spending.
- Feeding the same transition burden into both `alpha_bs_I` and a productivity penalty.
- Using `alpha_I` when the scenario is really a baseline-relative reform.
- Ignoring currency year, deflator, and numeraire issues when not using a pure ratio transform.

### Interconnection 3: OSeMOSYS electricity-cost pressure -> OG-Core `Z`

#### Variables and dimensions

OG-Core side:

- `Z[m,t]`: total factor productivity by industry and time-path parameter
- dimensions `T+S x M` as an input parameter, used over `T x M` in transition path production

Relevant OG-Core production logic:

- `Y_m,t = Z_m,t * F(K_m,t, K_g,m,t, L_m,t)`

This means a change in `Z` is an efficiency or productivity wedge, not a price variable.

OSeMOSYS side:

There is no single native variable called "cost of electricity generation" in the core model file.
The usable ingredients are:

- `AnnualVariableOperatingCost[r,t,y]`
- `AnnualFixedOperatingCost[r,t,y]`
- `CapitalInvestment[r,t,y]`
- `DiscountedOperatingCost[r,t,y]`
- `TotalDiscountedCostByTechnology[r,t,y]`
- electricity production output such as `ProductionAnnual[r,f,y]` for the electricity commodity or an equivalent post-processed generation total

#### Recommended cost-index hierarchy

Use this priority order:

1. Preferred:

   a post-processed CLEWS electricity unit-cost series already defined for the scenario package

2. Second-best:

   an annualized electricity-system cost index built from electricity technologies only:

   `c_elec,y = CostElec_y / GenerationElec_y`

3. Avoid as first pass:

   raw `CapitalInvestment / Generation` in the same year without smoothing, because new-capacity spikes will create artificial volatility.

#### Recommended mapping rule

Let:

`DeltaC_y = (c_elec,y^reform / c_elec,y^base) - 1`

Then define a lagged and damped productivity multiplier:

`Z_m,y^reform = Z_m,y^base * exp(-theta_m * Smooth(Lag(DeltaC_y)))`

where:

- `theta_m` is an exposure parameter by industry,
- `Lag` delays the macro effect relative to the cost change,
- `Smooth` dampens OSeMOSYS volatility before it hits OG-Core.

#### Economic interpretation

- This is a reduced-form proxy for the idea that more expensive electricity can reduce productive efficiency in electricity-dependent sectors.
- It is not equivalent to saying that electricity prices literally are TFP.
- The more sectorally disaggregated OG-Core is, the more defensible it is to apply this only to exposed industries rather than to the whole economy.

#### Preferred use cases

- energy-intensive sectors,
- electricity-dependent industrial sectors,
- consultant-style one-sector "energy industry" experiments when the country model structure is coarse.

#### Failure modes

- Using raw, unsmoothed CLEWS cost swings.
- Applying a power-sector cost shock uniformly to all industries.
- Double counting by also passing the same cost pressure through public investment or broad price channels.
- Using a carbon-penalty-inclusive cost index if carbon policy is already imposed elsewhere as an explicit policy lever.

### Interconnection 4: Policy carbon price -> OSeMOSYS `EmissionsPenalty`

This remains a good policy-consistency channel, but it is not the same thing as taking a CLEWS shadow price and feeding it into OG-Core.

Specific rule:

- use a scenario-level exogenous carbon price path when the scenario itself includes carbon pricing.
- keep that distinct from:
  - OSeMOSYS endogenous shadow prices,
  - OG-Core `tau_c`,
  - or any derived macro feedback.

Relevant OSeMOSYS logic:

- `EmissionsPenalty[r,e,y]` enters discounted technology emissions penalty.

Relevant OG-Core caution:

- `tau_c` directly affects consumption-tax revenue.
- Therefore, mapping a CLEWS shadow price into `tau_c` changes fiscal outcomes unless a revenue-offset rule is explicitly defined.

## Refined Working Conclusions

1. `C_i` and `Y_m` should be treated as different demand drivers with different use cases.
2. `alpha_bs_I` is the most natural first OG-Core target for public-investment feedback if `baseline_spending=True` is part of the scenario setup.
3. `Z` can support an electricity-cost feedback only as a documented reduced-form proxy, and only with lag, damping, and exposure rules.
4. `EmissionsPenalty` is better treated as a shared policy input than as a feedback artifact.
5. The first executable transform should likely be the demand bridge because it is the least assumption-heavy and the most native to both model structures.

## Deferred but Important Channels

### Pollution -> `rho`

Potentially strong, but requires an explicit emissions -> exposure -> health translation.

### OG-Core interest rates -> OSeMOSYS `DiscountRate`

Useful for scenario harmonization, but needs a clear real/nominal and annualization policy.

### OG-Core fiscal envelope -> OSeMOSYS capacity investment caps

Plausible, but requires technology-specific conversion from budget space to installable capacity.

### Carbon policy mapping

Potentially useful, but the integration should distinguish:

- an exogenous policy path applied to both models,
- from a CLEWS-derived shadow-price feedback sent into OG-Core.

Those are not the same thing.

## Working Hypotheses

1. The first production-quality bridge should be demand-led.
2. Public investment is the cleanest first feedback channel.
3. Electricity-cost-to-`Z` can be explored, but only as a documented reduced-form proxy.
4. Health channels should wait until the epidemiological bridge is explicit.
5. Full fiscal closure remains in OG-Core.

## Experiment Backlog

### Backlog A: Demand bridge prototype

Goal:

- Compare `Y_m`-based versus `C_i`-based demand scaling for a small set of demand categories.

What to test:

- ratio-based transform behavior,
- baseline/reform pairing,
- sector concordance sensitivity,
- annual-to-timeslice profile handling.

### Backlog B: Public investment bridge prototype

Goal:

- Test how OSeMOSYS public investment paths can map into `alpha_bs_I`.

What to test:

- public/private technology tagging,
- ratio vs level mapping,
- effect on `I_g`, `K_g`, and output path interpretation.

### Backlog C: Electricity-cost-to-`Z` prototype

Goal:

- Explore a guarded transform from electricity cost changes to a `Z` multiplier.

What to test:

- lag structure,
- damping,
- sector exposure weights,
- sensitivity of OG-Core macro outcomes to the mapping choice.

## Open Decisions

1. What is the first canonical scenario package for experiments?
2. What is the authoritative sector concordance?
3. What is the default policy for ratio-based vs level-based exchange?
4. Which channels are allowed to iterate and which remain one-way?
5. What evidence threshold is required before a reduced-form channel is promoted?

## Near-Term Deliverables

1. A structured channel registry used by both the worklog and dashboard.
2. A minimal dashboard showing interaction map, channel status, and experiment status.
3. First transform prototypes for the three active channels.
4. A decision memo narrowing the first executable integration path.
