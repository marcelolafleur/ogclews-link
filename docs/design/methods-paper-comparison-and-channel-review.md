# Methods-paper comparison and channel review

**Date:** 2026-08-04  
**Manuscript reviewed:** `paper/linkages-intro` at `ca40cc3`  
**Comparative source reviewed:** `research/ieem-comparative-assessment` in the
`ogclews-link-ieem` worktree  
**Purpose:** investigation brief for revising the methods paper and checking its technical claims
against the latest development state.

## Scope and evidence boundary

This review focuses on two questions:

1. Does the comparison with other model-linking papers identify a clear, defensible contribution?
2. Does the paper describe and validate the ogclews-link channels consistently and precisely?

This is not a completion review. The abstract, discussion, conclusion, appendices, and further
results are works in progress and are outside the present assessment.

The technical evidence available for this review is the writing worktree at `ca40cc3`, including
its code, battery definition, committed golden record, and validation notes. Development has
continued elsewhere. Accordingly, every technical concern below is a **question to investigate**,
not a claim that the latest implementation is wrong. The latest development repo should be treated
as authoritative when it conflicts with this snapshot.

## Executive assessment

The comparison and channel framework already give the paper a credible intellectual centre. The
strongest contribution is not that the framework is more broadly “integrated” than IEEM or
CLEWs--IO. It is that it connects a bottom-up resource-system model to a macroeconomic partner with
forward-looking cohorts, income heterogeneity, demography, and fiscal closure, while making the
interface itself explicit and auditable.

The comparison is strongest when it is organised by **capability and policy question**:

- IEEM adds spatial land allocation, ecosystem services, and natural-capital wealth accounting.
- CLEWs--IO adds sectoral employment accounting to the CLEWs optimisation.
- ogclews-link adds forward-looking household behaviour, cohort and income-group incidence,
  demography, and fiscal structure.

The paper's second strong contribution is methodological discipline: named interfaces, explicit
signal provenance, accounting rules, validation gates, and the shadow-price-hygiene protocol. This
is potentially a publishable contribution in its own right, especially if the paper distinguishes
clearly among implementation verification, economic validation, calibration, and closed-loop
validation.

The principal issue to investigate is internal terminology. In the reviewed snapshot, the words
“channel,” “price,” “coupled,” and “validated” sometimes describe different objects in different
sections. Most of the concerns below can be resolved by updating the manuscript after checking the
latest code rather than by changing the architecture itself.

## 1. Comparison with other papers

### 1.1 The most defensible positioning

The best comparison in the draft is:

> IEEM extends the environment downward into a CGE, CLEWs--IO extends the economy sideways into
> employment accounting, and the present framework extends the economy forward in time and across
> cohorts.

This sentence should remain central. It is complementary rather than adversarial, and it states a
structural difference that can be established from the model designs without claiming priority.

The contribution can be made still sharper by organising the comparison around questions:

| Policy question | IEEM | CLEWs--IO | ogclews-link |
|---|:---:|:---:|:---:|
| Physical feasibility under technology and resource constraints | partial | yes | yes |
| Aggregate economic effects | yes | partial | yes |
| Sectoral employment effects | no | yes | not the present strength |
| Ecosystem services and natural-capital wealth | yes | no | roadmap / partial |
| Forward-looking household response | no | no | yes |
| Incidence by cohort and income group | no | no | yes in model structure |
| Demographic health effects inside general equilibrium | no | no | yes |
| Fiscal closure under demographic change | limited | no | yes in model structure |

For publication, the last four rows should be supported by the paper's actual reported outputs or
carefully described as capabilities of the coupled model rather than completed application results.

### 1.2 What the Keppo review establishes

The Keppo et al. review is good evidence that OLG models do not appear among the economic partners
recognised in current model-linking practice. The draft appropriately uses “to our knowledge,” but
the evidence should be described with precision:

- Strong claim: the field's recent review discusses CGE, macroeconometric, and input--output
  partners and does not discuss an OLG partner.
- Reasonable inference: linking to a cohort-resolved OLG economy is outside standard current
  practice and fills an identifiable methodological cell.
- Not yet established by that evidence alone: no ESM--OLG linkage has ever been attempted.

Before submission, retain the planned systematic literature search. Until then, capability should
carry more argumentative weight than priority.

### 1.3 IEEM and CLEWs--IO: retain the differences between their linkages

The current comparison says that neither comparator iterates its two sides to a fixed point. That
is narrowly accurate based on the briefs, but it can obscure an important distinction:

- IEEM uses a sequential five-year process in which land-use and ecosystem-service effects return
  to the economic model. It is iterative over time/modules, although not described as a numerical
  fixed-point solve.
- CLEWs--IO computes employment coefficients offline and passes them one way into CLEWs. It does
  not re-run the IO model against the CLEWs solution.
- In the reviewed ogclews-link snapshot, the return signals and CLEWs re-solve seam exist, while
  the outer convergence controller remains open.

Suggested paper language: distinguish **sequential feedback**, **one-way parameterisation**, and
**fixed-point iteration** rather than treating iteration as a single yes/no property.

### 1.4 The “one coefficient” comparison

The observation that the two nearest comparators use a well-sourced reduced-form coefficient is
useful because it places ogclews-link's own reduced-form mappings within accepted practice. It is
less useful as an implied ranking of rigour.

Recommended use:

- Keep it brief and neutral.
- Use it to justify explicit coefficient provenance, sensitivity analysis, and maturity labels.
- Avoid making it the headline comparison; the cohort, demographic, behavioural, and fiscal
  capabilities are more important and more defensible.
- Describe IEEM's broader spatial and accounting system and CLEWs--IO's broader employment
  accounting before reducing attention to their final feedback coefficients.

### 1.5 The hard-link claim needs conceptual precision

The paper currently argues that a hard link is structurally unavailable because OG-Core exposes no
scalar welfare objective. This clearly rules out folding OG-Core into the particular
single-objective welfare programme used by classic energy--macro models. It may not rule out every
possible simultaneous formulation: equilibrium conditions could, in principle, be combined as a
complementarity or other joint system.

This is principally a literature/theory concern, not something the latest repo can resolve.
Suggested formulation:

> The classic integrated-welfare-program route is not available for the existing OG-Core solution
> concept. A staged soft link preserves both models, accommodates their distinct solution concepts,
> and makes the exchanged quantities inspectable.

That establishes why this implementation uses a soft link without needing the universal claim that
all hard linking is impossible.

## 2. Channel ontology and terminology

### 2.1 “One signal to one wedge” does not describe every deployed channel

In the reviewed manuscript, a channel is defined as a map from one signal to one wedge. The energy
price channel, however, partitions one price signal into an inter-industry cost-push and a household
consumption wedge. The health channel maps an emissions signal into mortality and effective labour.

This is not necessarily a design problem; it is a definition problem. A definition closer to the
implementation would be:

> A channel is a named, guard-railed mapping from a sourced signal or signal bundle to a deliberately
> partitioned set of model adjustments, together with an accounting rule preventing overlap.

The narrower terms can remain useful:

- **Signal:** value or path extracted or externally specified.
- **Adjustment/wedge:** one target parameter or model object.
- **Channel:** economically coherent mechanism, possibly containing several non-overlapping
  adjustments.
- **Experiment:** a runnable configuration that may isolate one adjustment, exercise a channel, or
  compose several channels.

This last distinction is important because the manuscript and code snapshot sometimes use a channel
name for an isolating experiment that is narrower than the full conceptual channel.

### 2.2 Suggested validation vocabulary

Use a maturity ladder rather than the single word “validated”:

1. **Implemented:** the transform exists and produces the intended parameter/output shape.
2. **Guarded:** units, bounds, concordance, missing inputs, and double-counting conditions are
   checked.
3. **Mechanically verified:** the target model object changes as intended and the solve completes.
4. **Economically verified:** direction and attribution agree with model equations or a controlled
   experiment.
5. **Regression-locked:** selected outputs are stored and automatically compared with a committed
   record.
6. **Calibrated:** coefficient values and units are supported for the application country.
7. **Closed-loop validated:** returned signals alter the source model, the outer loop converges, and
   sensitivity/error propagation are assessed.

This vocabulary would let the paper state strong accomplishments without making “validated” carry
all seven meanings at once.

## 3. Channel-by-channel review and questions for the latest repo

The table below records what the manuscript at `ca40cc3` says, the concern raised by the reviewed
snapshot, and the concrete question to answer in the current development repo.

| Channel | Manuscript description | Question to investigate in latest repo | Evidence needed for the paper |
|---|---|---|---|
| `energy_price` | CLEWs electricity price enters through a composite industry cost-push plus recycled household wedge | Is `energy_price` now consistently the full composite, or does the named runnable experiment still apply only the household wedge? Are `energy_full`/composite and `clean_incidence` variants still separate? | One canonical channel definition; a table mapping conceptual channel to runnable experiments; controlled comparison of household, industry, and composite routes |
| `carbon` | One exogenous carbon price is applied once on both sides | In the flagship coupled run, is the OG-side carbon wedge now applied, or is carbon still applied only as a CLEWs emissions penalty? If only one side is used, is that deliberate to avoid overlap with the electricity-price signal? | Exact composition of the flagship run; unit bridge; explanation of revenue treatment and non-overlap |
| `investment` | Public grid/T&D capex raises the public-investment share and public capital | Has the public/private classification or monetary-unit bridge changed? Does the current PHL reform still have a near-zero public-capex delta? | Source classification, unit conversion, financing/closure rule, controlled non-zero test if the PHL application is inert |
| `capital_intensity` | Fleet capital-cost-share ratio changes the energy industry's production exponent | Are the published sectoral numbers (`+12.2%`, `-42.8%`, `+20.9%`, `-22.4%`) reproduced by the current code and stored in the current evidence record? Does the return truly remain fixed for the ratio identity used? | Fresh run; exact FOC reconciliation; current sectoral outputs and tolerance; explanation of why the lever represents factor share rather than physical capex demand |
| `energy_capex` | ITC lowers the energy industry's user cost of capital and draws capital into energy | Is this now included in the battery and golden record? Is the magnitude calibrated or still a controlled policy experiment? Is it part of the flagship coupled run? | Standalone run, expected-sign verification, calibration/status label, non-stacking rule relative to `capital_intensity` |
| `health` | PM2.5 emissions map through a dose-response into mortality and effective labour | Has the morbidity productivity elasticity been calibrated? Is the `M≈0.082` dose-response current? Is the Walras-residual exception still present? Are mortality and morbidity separately decomposed? | Data provenance, coefficient derivation, separate mortality/morbidity runs, solver residuals, cohort/age effects, sensitivity analysis |
| `discount_rate` | OG equilibrium return is written to CLEWs `DiscountRate` | Does the current re-solve actually consume the emitted path? How is the multi-period return converted into the rate and time structure expected by CLEWs? | Round-trip test showing the written rate changes the build mix or objective; units/real-vs-nominal convention |
| `demand` | OG activity or consumption scales CLEWs demand | Is the current signal household electricity demand, sector output, final energy demand, or a configurable choice? Does the `+10% → +4.3% production` re-solve test use the same mapping intended for the closed loop? | Exact demand variable and elasticity; baseline anchoring; round-trip provenance; re-solve result; damping/convergence design |

## 4. Cross-channel concerns to verify

### 4.1 What exactly is in the flagship `coupled` experiment?

At `ca40cc3`, the code snapshot appears to compose:

- the real CLEWs price through the composite energy transmission;
- public investment;
- a carbon penalty on the CLEWs side;
- health;
- post-solve discount-rate and demand emitters.

It does not appear to compose `capital_intensity` or `energy_capex`, and its carbon treatment differs
from the standalone two-sided carbon experiment. Yet the results table labels the coupled row
“all,” and the introduction refers to all eight channels in connection with the full pass.

Questions for the latest repo:

1. What is the current authoritative composition of `coupled`?
2. Which channels are intentionally excluded, and why?
3. Are `capital_intensity` and `energy_capex` alternatives that should never be included together?
4. Is the carbon signal already embodied in the reform LCOE, creating a reason not to add an OG
   carbon wedge in the flagship run?
5. Should the paper distinguish “full application configuration” from “all channel mechanisms”?

The manuscript should list the flagship composition explicitly and avoid “all” unless it literally
means all compatible channels.

### 4.2 Which numbers are in the golden record?

The introduction says every reported number is regression-locked. In the reviewed manuscript, the
capital-pair table says its sectoral decomposition comes from an earlier solve and that the golden
record stores aggregates only.

Questions for the latest repo:

- Are the capital-sector price, output, and capital figures now stored in the golden record?
- Are the LCOE path, health target, emitted signals, unit conversions, and re-solve outputs stored
  with provenance, or only macro aggregates?
- Does “golden” mean exact numerical regression, bounded tolerance, or a manually blessed record?
- Which results are reproducible from committed public inputs, and which depend on external CLEWs
  case data?

Suggested paper practice: qualify each result as regression-locked, freshly reproduced, calibrated,
or illustrative rather than making one global claim.

### 4.3 The non-additive coupled result

The paper reports a coupled steady-state output effect near `-0.138%`, compared with approximately
`-0.02%` from the sum of standalone channel experiments, and attributes the difference to general-
equilibrium interaction.

Questions for the latest repo:

1. Do the standalone experiments use exactly the same channel implementations, recycling rules,
   price paths, carbon treatment, and baseline as the coupled configuration?
2. Does the cumulative `across_steps` run reproduce the current coupled result exactly?
3. At which added step does the large nonlinearity emerge?
4. Is the result invariant to the order in which channels are added?
5. Would an order-averaged or Shapley decomposition be feasible for the paper?

General-equilibrium interaction is plausible, but the magnitude is important enough that the paper
should demonstrate it rather than infer it from the standalone sum.

### 4.4 No-double-counting claims

The accounting principles are a major strength. Their validation should be made concrete. For each
principle, identify:

- the prohibited combination;
- the implemented guard or construction that prevents it;
- the test that intentionally violates the rule and confirms that the guard fires;
- any remaining case controlled only by experiment composition rather than code.

Particular checks:

- household versus intermediate electricity shares;
- electricity self-use;
- carbon cost already embodied in LCOE versus a separate carbon wedge;
- public versus private generation capital;
- `capital_intensity` versus `energy_capex`;
- phantom consumption-tax revenue and the accuracy of recycling.

The paper should avoid saying that every principle is “enforced by a guard” if some are instead
enforced by construction or by the chosen experiment configuration.

## 5. Electricity-price signal and shadow-price hygiene

### 5.1 Preserve the distinction between marginal cost and LCOE

The shadow-price-hygiene protocol is one of the paper's most interesting methodological ideas:

1. compare the dual with solver reporting resolution;
2. test invariance across alternate optima;
3. decompose it against cost parameters that may floor it;
4. trace every component to a sourced input.

The reviewed paper then uses LCOE because the electricity commodity dual fails the first two tests.
The terminology should reflect that outcome consistently:

- The dual is a candidate marginal-value signal.
- In this case it is rejected as unstable/uninformative for the intended long-run transmission.
- LCOE is an average-cost proxy selected for density and robustness.
- A fixed point formed with LCOE is consistency under the selected pricing proxy, not necessarily a
  competitive market equilibrium.

Questions for the latest repo:

- Is the electricity dual still degenerate under the current model version, solve configuration,
  and solver?
- Was degeneracy tested through alternate optimal solutions or only observed as sparse values?
- Is “auto” still allowed to select either a curated cost index or reconstructed LCOE? If so, are
  these economically equivalent enough to share one channel label?
- Is the LCOE construction documented by technology, cost category, generation denominator,
  discounting convention, and treatment of stranded/unused capacity?
- Does the reported `1.05` mean arithmetic mean across years, demand-weighted mean, or another
  statistic?

### 5.2 Status of the land shadow-price evidence

The paper calls the land application preliminary. Keep that status unless the latest work has
reproduced the findings and preserved the evidence. Before presenting the protocol as empirically
validated across commodities, verify:

- the result on a fresh model solve;
- behaviour under at least one alternate solver or degeneracy treatment, if feasible;
- the solver's actual reporting precision;
- the decomposition of the raw dual against the `-10.0` cost parameter;
- provenance and units of that parameter;
- the stated `20–35×` overstatement range.

The general protocol can be presented without all of these results, but numerical claims should be
published only with reproducible evidence.

## 6. Validation design for the channels section

The channels section would benefit from a standard validation template repeated for every channel:

1. **Economic object:** what real-world mechanism the channel represents.
2. **Source signal:** exact file/output, units, time index, and provenance.
3. **Mapping:** equation from signal to target adjustment(s).
4. **Target object:** exact OG-Core or CLEWs parameter/constraint changed.
5. **Expected sign or identity:** analytical prediction, including conditions under which the sign is
   ambiguous.
6. **Guardrails:** bounds, concordance requirements, unit checks, accounting restrictions.
7. **Controlled verification:** isolated experiment and result.
8. **Application calibration:** real, illustrative, provisional, or inert in the PHL case.
9. **Composition rule:** compatible channels and forbidden stacking.
10. **Current maturity:** implemented, mechanically verified, economically verified,
    regression-locked, calibrated, or closed-loop validated.

A compact master table can summarise these items, with the text concentrating on the three channels
that carry the most methodological content: energy price, the capital pair, and health.

## 7. Recommended paper-level revisions after technical verification

These are writing changes to make only after the latest repo answers the questions above:

1. Replace global statements such as “all eight channels are validated” with a channel-by-channel
   maturity table.
2. Distinguish the conceptual channel library, isolated experiments, and the flagship coupled
   configuration.
3. Define a channel broadly enough to contain deliberately partitioned adjustments.
4. Use “LCOE proxy” consistently and reserve “marginal price” or “market-clearing price” for a dual
   that passes the hygiene protocol.
5. Replace “soft-link equilibrium” with “link-consistent fixed point” unless a stronger equilibrium
   interpretation is established.
6. State exactly which side receives the carbon price in the flagship configuration and why.
7. Reproduce or retire the earlier capital-decomposition numbers.
8. Explain the large coupled/standalone gap using matched cumulative experiments.
9. Make every no-double-counting principle point to a specific guard, construction, or experiment-
   composition rule.
10. Lead the literature comparison with capabilities and policy questions; retain the
    single-coefficient observation as a secondary methodological point.

## 8. Investigation checklist for the other assistant

Use the latest technical repo and report `PASS`, `CHANGED`, `STALE`, or `UNVERIFIED` for each item,
with file/commit/run evidence.

- [ ] Identify the current branch and HEAD of the latest link repo, OG model repo, and MUIOGO repo.
- [ ] Confirm the authoritative list of conceptual channels.
- [ ] Confirm the authoritative list and composition of runnable experiments.
- [ ] Record the exact current composition of `coupled`.
- [ ] Determine whether `energy_price` means household-only or composite in code and in the CLI.
- [ ] Determine whether `carbon` is applied on one or both sides in `coupled`.
- [ ] Determine whether `energy_capex` is in the battery and golden record.
- [ ] Reproduce the capital-share identity and all four sectoral percentages used in the paper.
- [ ] Confirm the current source and construction of the PHL electricity price path.
- [ ] Re-test electricity-dual degeneracy and document the test.
- [ ] Confirm the definition of the reported 5% average and 16% peak LCOE change.
- [ ] Confirm the current PM2.5 dose-response, mortality target, morbidity elasticity, and residual
      tolerances.
- [ ] Confirm which emitted discount-rate and demand signals are consumed by a real CLEWs re-solve.
- [ ] Reproduce the `+10% demand → +4.3% production` test and confirm it uses the intended closed-loop
      demand mapping.
- [ ] Match each accounting principle to its guard, construction, or composition rule and test.
- [ ] Confirm which manuscript numbers are in the committed evidence record.
- [ ] Run the cumulative decomposition and locate the source of the `-0.138%` coupled result relative
      to standalone effects.
- [ ] Identify every manuscript statement made stale by subsequent technical development.

## Bottom line

The comparison is already on solid ground when it argues from model capabilities rather than from
priority or breadth. The channel framework is also strong, but the paper should describe three
different things separately: the channel library, the experiments used to validate individual
mechanisms, and the particular channels composed in the Philippine application.

The latest technical repo may already resolve several concerns in this brief. The task is therefore
not to presume defects, but to make the evidence chain explicit: for every published channel claim,
identify the current implementation, the controlled validation, the calibration status, the
composition rule, and the exact result record that supports it.
