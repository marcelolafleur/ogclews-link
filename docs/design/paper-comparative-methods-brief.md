# Comparative methods — analytical brief for the ogclews-link paper

**Status:** drafting aid for the paper's positioning / related-work / methods-comparison section.
Not a paper draft; the argument, the evidence, and the places where the argument is not yet safe.
**Date:** 2026-08-03
**Underlying notes:** `ieem-comparative-assessment.md`, `clews-io-employment-assessment.md`,
`phl-testcase-plan.md`, `method-comparison-brief.md` (internal version of this).

---

## 1. The contribution claim, stated precisely

Draft wording, then the evidence for each clause.

> Bottom-up energy–land–water optimisation models are routinely soft-linked to economy-wide
> models, but the economic partners in current practice — computable general equilibrium,
> macroeconometric, and input–output frameworks — represent households as a representative agent
> or as fixed expenditure shares. None carries a forward-looking, cohort-resolved household
> sector. As a result, the literature can report what a resource transition costs an economy, but
> not **which birth cohorts bear that cost over their lifetimes, nor how it interacts with fiscal
> sustainability under demographic change**. We link a technology-explicit CLEWs/OSeMOSYS model
> to an overlapping-generations macroeconomic model to address that gap.

Three separable claims. They are not equally strong, and the paper should not lean on them equally.

**Claim A — the gap exists in current practice. STRONG, and directly evidenceable.**
The field's own 2026 state-of-the-art review of model linking (Keppo et al., *RSER* 226, 116384 —
~20 authors across Aalto, Imperial, IIASA, KTH, E3M, CICERO, BC3, Polimi, and co-authored by
Gardumi, a CLEWs/OSeMOSYS maintainer) does not mention overlapping-generations models at all.
Verified by search of the full text: **"overlapping generations", "OLG", "cohort", and
"intergenerational" occur zero times.** The economic partners it names are CGE (7 mentions),
macroeconometric (1), input–output (1). Its concrete ESM↔economy examples are TIMES-Sweden↔EMEC,
PRIMES↔GEM-E3, and EU-TIMES↔NEMESIS — all representative-agent frameworks.

This is the cleanest way to make the claim: *cite the field's own review and show the absence*.
It is far safer than asserting nobody has ever done it.

**Claim B — nobody has done it. UNVERIFIED. Do not assert.**
My searches (OpenAlex, web) surfaced no prior ESM↔OLG linkage, but full-text bibliographic search
was too noisy to be decisive, and absence of results is not evidence of absence. **A systematic
search is required before submission** (§8). Until then, phrase as "to our knowledge" or, better,
rely on Claim A, which does not require it.

**Claim C — the questions we can answer are new. STRONG, and the better framing.**
Independent of priority: a representative agent cannot produce lifetime-welfare incidence by
cohort, and a fixed-coefficient IO table cannot produce behaviour at all. This is a structural
property of those models, not a gap in their implementations. Argue capability, not novelty —
capability is provable from the models' own equations.

---

## 2. Positioning: where each method sits

Use the Keppo et al. taxonomy — it is the community's own, which makes the positioning hard to
dispute. It distinguishes **soft-linking** (results passed between models, under user control)
from **hard-linking** (models run in parallel, constantly exchanging), and organises the
challenges under temporal/spatial scale, system boundaries and harmonisation, data-exchange
implementation, and linking as an epistemological problem.

| | **IEEM+ESM** (IDB) | **CLEWs–IO** (KTH/Sharif) | **ogclews-link** |
|---|---|---|---|
| Physical core | none — CGE with SEEA satellite accounts | CLEWs/OSeMOSYS | CLEWs/OSeMOSYS |
| Economic core | recursive-dynamic CGE, representative agent, **myopic** | input–output, fixed Leontief coefficients, no behaviour | OLG, **forward-looking**, cohorts × income groups |
| Linkage | soft, **iterative** (5-yr steps) | soft, **one-way** | soft, one-way (loop designed, not closed) |
| Signal exchanged | land demand → LULC → ES → productivity shock | jobs/unit activity → CLEWs parameter | **LP commodity-balance dual** → household price wedge |
| Feedback mechanism | one coefficient (8% erosion penalty) | one coefficient (jobs/PJ) | channel-specific; several labelled provisional |
| Distributional | none | none | cohort + income-group incidence |
| Fiscal | limited | none | debt, closure rules, demographics |
| Spatial | 300 m raster | none | none |
| Openness | GAMS; geodata open, model not | OSeMOSYS; **IO table confidential** | fully open, free solvers |

**The positioning sentence:** IEEM extends the environment downward into a CGE; CLEWs–IO extends
the economy sideways into employment accounting; ogclews-link extends the economy **forward in
time and across cohorts**. The three are complementary, not competing, and they answer different
questions.

---

## 3. Question-led comparison — the strongest form of the argument

Feature tables invite "so what". Questions do not. Recommend leading the section with this.

| Policy question | IEEM | CLEWs–IO | ogclews-link |
|---|:--:|:--:|:--:|
| Is this decarbonisation path physically feasible given plant stock and water? | ✗ | ✓ | ✓ |
| What does it cost the economy in aggregate? | ✓ | partial | ✓ |
| Which *sectors* contract? | ✓ | ✓ | ✗ |
| How many *jobs*, and where? | ✗ | ✓ | ✗ |
| What happens to ecosystem services and natural capital? | ✓ | ✗ | partial |
| Is the national balance sheet being drawn down? | ✓ | ✗ | partial |
| **Who bears the cost — which cohort, over which lifetime?** | ✗ | ✗ | **✓** |
| **Is the fiscal path sustainable under ageing while this happens?** | ✗ | ✗ | **✓** |
| **Do households anticipate the transition and re-optimise?** | ✗ | ✗ | **✓** |

The bottom three rows are the paper. They are not reachable by a representative agent, by
construction. That is the argument.

---

## 4. What the comparators actually do — for honest related-work prose

Both make integration claims that reduce, at the method level, to a single linear coefficient.
State this **neutrally and without point-scoring** — it is a fair characterisation of standard
practice, and it also licenses our own reduced-form channels.

**IEEM+ESM.** Environmentally-extended SAM; CGE → land demand → Dyna-CLUE spatial allocation →
InVEST ecosystem services → economic shock → back into the CGE, in 5-year steps to 2040. Genuinely
iterative. But the economy↔ecosystem feedback is, in full, land productivity loss = (severely
eroded agricultural area ÷ total agricultural area) × 0.08, the 8% from a single literature
estimate. Reports comprehensive wealth via genuine savings — its real and adoptable contribution.

**CLEWs–IO.** An IO model is run once, offline, producing net jobs per unit of physical activity
(direct + indirect + induced, Leontief Type I plus household expenditure propensities). Those
coefficients are then fed **into** CLEWs as a parameter — their Table 2's third column is headed
"Input to the CLEWS model". The words *iterate* and *converge* appear nowhere in the paper.
Employment shifts the optimum only where the modeller imposes a target. Sistan region, Iran;
~107,000 jobs, split ~70/20/10 direct/indirect/induced. **No limitations section.**

**Implication for our framing:** neither has closed an economy↔resource fixed point. Our loop is
also not closed. So *loop closure is not the axis on which to claim contribution* — the axis is
what the economic side can represent.

---

## 5. What is genuinely ours — three defensible claims

**(i) The economic side represents things the alternatives structurally cannot.** Forward-looking
heterogeneous households, lifetime welfare by cohort, income-group incidence, fiscal closure,
demographic transition. Provable from the models' equations; no priority claim needed.

**(ii) ~~The exchanged signal is a genuine shadow price, not a proxy.~~ CORRECTED 2026-08-11 —
do not make this claim. It is false about our own code.**

The commodity-balance dual was renamed `'marginal'` and **demoted to an explicit opt-in**; the
default price source is `'lcoe'`, a levelized cost reconstructed from the CLEWS cost/production
CSVs. The reason is on record in `signals.py` on `main`: the dual is *"degenerate in OSeMOSYS
(it binds in scattered, scenario-specific years)"*. A guardrail (commit `f8eff19`) now **refuses**
a dual with fewer than three overlapping base/reform years, because on PHL a single 2029 overlap
point was being broadcast into a spurious permanent **+32%** economy-wide price shock.

The correct claim is the opposite and stronger one: **we established that the naive choice —
driving the coupling from the LP dual — is unsafe in OSeMOSYS, and we say so.** That belongs in
(iii), not here.

**(iii) Shadow-price hygiene as method.** This is the most original and least expected
contribution, and it should be a titled subsection, not a footnote. Duals from an LP are only
meaningful under conditions practitioners rarely check.

**Independently cross-validated on two commodities, by two workstreams that did not consult each
other — which is what makes it a finding rather than an anecdote.**

*Electricity* (the coupled-model workstream, `feature/lcoe-price`, June–July 2026): the EBb4 dual
binds in scattered years that differ between base and reform, so the base/reform overlap
collapsed to a single 2029 point, which was then broadcast into a permanent **+32%** price shock.
Response: a guardrail refusing fewer than three overlapping years, the dual demoted to opt-in,
and a levelized cost made the default.

*Land* (this workstream, August 2026): nonzero in 1 of 16 demo years and 6 of 34 PHL years; the
PHL value is the token variable cost, below solver reporting resolution; and two runs at the
**same optimum with identical land in every year** report it in *different years*.

Same pathology, different commodity, different investigators. On the Philippine model we found:

- The land shadow price is **1.0e-4** — exactly the token variable cost on the land resource, an
  order of magnitude below the solver's own shadow-price reporting resolution.
- It is **degenerate**: two runs at the same optimum, with identical land in every year, report it
  in *different years*. A price that moves between alternate optima while nothing physical changes
  carries no information.
- Where land genuinely binds, ~**97%** of the reported shadow price is a `-10.0` variable-cost
  reward, not scarcity. Netting it out, only three of eight land clusters carry a real premium
  (0.28–0.51) over 23.5% of national area. **Taking the raw dual at face value overstates the
  marginal scarcity value of land by 20–35×.**
- That `-10.0` traces to a hardcoded constant in the model-generation code with no source, no
  units, and no entry in the build's assumption register — and it is the model's *entire*
  representation of the economic value of standing forest, needed because forest produces no
  commodity and a cost-minimiser would otherwise clear it for free.

Generalise it into a stated protocol — check against solver resolution; test invariance across
alternate optima; decompose against cost parameters that floor the dual; trace to source — and
it becomes transferable method, which is what makes it publishable rather than anecdote.

**(iv) Accounting closure as a correctness gate.** Land-use areas must sum to the land resource or
the read is refused (0.00e+00 at endpoints, ≤1e-4 across 34 years). Small, but it caught a real
error: the natural way to read land from a CLEWs model drops forest entirely and mixes water
volumes into an area total.

---

## 6. Limitations — write these before a reviewer does

Every one of these is real and in the repo. A methods paper that discloses them is stronger than
one that gets caught.

**The big one: energy does not enter OG-Core's production function.** Output is a CES over private
capital, public capital and labour, with no intermediate inputs. Coupling therefore runs through
the household energy-price wedge, fiscal closure and demographics — *not* through firms' energy
costs. **This is the first thing a reviewer will attack.** Options, in order of honesty:

1. **Scope the claims to the channel.** Argue household-side incidence, which is exactly where our
   comparative advantage lies anyway, and state the firm-side limitation explicitly.
2. Implement the intermediate-input structure (`energy-as-production-input-spec.md`; design exists,
   no code). A firm-side rewrite — likely beyond this paper.
3. Report the reduced-form cost-push channel and label it as such (it is already labelled
   illustrative in code).

Recommend (1) with a clear statement, and (2) as further work.

**The loop is not closed.** One pass. The CLEWs re-solve mechanism is built and validated
standalone but not wired into the orchestrator. Mitigant: neither comparator closes one either
(§4), so this is standard practice, not a deficiency — but say so rather than leaving it implicit.

**The unit/deflator bridge is a placeholder** (`contract.UnitMap.deflator = 1.0`). Carbon and
investment *magnitudes* are illustrative until calibrated. This is Keppo et al.'s harmonisation
item (viii) and is the one checklist item we currently fail. **Fix before submission** — a
methods paper cannot ship with an uncalibrated unit bridge.

**The health channel's morbidity multiplier is uncalibrated**, and the mortality effect is ≈0 for
the Philippines because PM2.5 deaths skew elderly (saved lives add retirees, not workers). Do not
report the health GDP gain as a lives-saved effect; it is the morbidity placeholder.

**The Philippine land block is not calibrated** — 61% forest against ~24% observed, built-up an
order of magnitude low. Every PHL land number is a mechanism check, never a country result. If the
paper shows PHL land figures, this must be stated at every figure, not once in a footnote.

**No sectoral economy, no ecosystem services, no spatial dimension, no employment.** Name these as
the complementarities that motivate future linkage rather than as absences.

---

## 7. Suggested section structure

1. **Framing** — resource-system models answer feasibility; economy-wide models answer cost;
   neither answers *who bears it, when*.
2. **Related work**, organised by economic partner: CGE (IEEM, GEM-E3, EMEC), macroeconometric
   (NEMESIS), input–output (CLEWs–IO). Common property: representative or no agent.
3. **The gap**, evidenced from Keppo et al. — cite the review's own coverage (Claim A, §1).
4. **Our approach** — architecture, the dual as the exchanged signal, the channels.
5. **Verification method** — closure gates and shadow-price hygiene (§5 iii–iv). *Make this a
   contribution, not an appendix.*
6. **Application** — PHL, with calibration caveats stated.
7. **Limitations** (§6), disclosed not buried.
8. **Complementarity** — IEEM's wealth accounting, CLEWs–IO's employment coefficients, both
   adoptable; position as a research programme rather than a rival.

---

## 8. Must be verified before submission

1. **A systematic literature search for prior ESM↔OLG linkage.** Scopus/WoS with a documented
   query string, not the ad-hoc searches behind this note. This decides whether Claim B can appear
   at all. **Highest priority.**
2. **Fix the deflator**, or scope every magnitude claim to relative changes.
3. **Confirm the Keppo absence result** by reading the review yourself — my claim rests on a
   full-text search of a repository copy, and a reviewer with the published version will check.
4. **Re-verify the shadow-price findings on a fresh solve** before publishing the 20–35× figure.
   It rests on one case and one solver; test whether it reproduces under a different solver, since
   degeneracy behaviour is solver-specific.
5. **Decide the PHL question** — a mechanism demonstration on an uncalibrated model is publishable
   *if framed as such*, but it cannot carry country policy conclusions.
6. **Baseline-identity claims at build-family granularity only, until a content digest exists**
   (og-core-23's version+param-count figure footer does not separate builds: two different
   OG-Core builds on this machine both report 0.19.1 with 140 parameters). If the paper claims
   baseline-naming/provenance discipline as method, scope the claim accordingly or wait on the
   digest — deliberately unbuilt pending Marcelo. *(Added 2026-08-13 by the v16/stack session,
   routed from the comparative-methods session with og-core-23's attribution.)*

---

## 9. One caution on tone

The two comparator papers are by groups we work alongside — the CLEWs–IO authors include the
OSeMOSYS maintainers, and IEEM is an IDB flagship. The observation in §4, that both reduce to a
single coefficient, is accurate and worth making, but it should read as *characterising the state
of practice, including our own*, not as criticism. Our channels contain reduced-form coefficients
too. The defensible high ground is that ours are labelled as provisional in the source code — and
that is a statement about transparency, which is friendly, rather than about rigour, which is not.
