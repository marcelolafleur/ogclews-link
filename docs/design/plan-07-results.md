# Section plan — paper/ §7 (07-results) rebase and completion

Authoring session (charter v2), 2026-08-13. Propose-then-write: no prose changes until
the coordinator clears this plan. Status of the section today: **fully drafted on the v9
golden** (coupled Y −0.138, morbidity-driven positive transition, "not attributable"
decomposition wording). So the job is a **rebase to the current evidence + one new
subsection**, not a fill.

## What the section argues (frame unchanged, evidence new)

The section stays an illustration of the implemented forward pass — not a policy
evaluation. It demonstrates:

1. the coupled application solves end-to-end on the Philippine calibration and the
   responses are consistent with §5's mechanisms;
2. **new:** the composition of the coupled response is now *identified*, by construction
   and by a matched battery — replacing the drafted "we do not attribute it here";
3. incidence and the capital identity, as before;
4. validation layers and their boundaries.

## Evidence bases, named per number (v18-swap discipline)

| content | base | source of numbers |
|---|---|---|
| coupled headline, transition window, realized channel inputs | CLEWs Philippines v16 (Base_v16 / PEP_v16: 2027 coal moratorium, conversion-carbon accounting), OG-PHL M=8 | the run's own record: manifest (channels + realized magnitudes) and macro table — derived, never retyped |
| matched decomposition / attribution | v12 real-price battery (11 experiments) | the attribution table (§15 of the calibration record) |
| regression lock (Validation) | v9 golden — pending Q(b) below | `results/golden.json` |

Every table and figure names its base on-face (figure-integrity convention). The
decomposition text states its identity was established on v12 and that re-verification
on the final base is queued — never carried forward silently.

## Subsection by subsection

**Framing paragraph** — rewrite. Names both evidence bases; keeps "percent changes from
baseline"; adds the relative-changes-only pointer (deflator unaudited).

**7.1 The coupled application** (rewrites "The flagship coupled run"):
- What is applied, read from the run record: the composite energy-price transmission
  (levelized cost; inter-industry cost-push + recycled household wedge), public grid
  investment, the GBD health mapping; what is emitted and inert in one pass: the
  \$50/tCO2 carbon-price artifact, discount rate, energy demand. The emit-only carbon
  sentence survives verbatim in substance.
- Table (generated): SS + transition-window rows — Y −0.579 / C −0.422 / K −0.550 /
  L +0.015 / r −0.111 / w −0.537; 2025–34 average Y −0.181.
- Narrative: contraction in both the transition window and the steady state; the wage
  carries most of the factor-price adjustment; realized inputs named with magnitudes
  from the record: mean household electricity-price wedge ≈ +5.5%, PM2.5 −7.03% →
  ≈253 avoided deaths and ≈1,950 FTE/yr of working time, with near-zero macro
  contribution from health and investment.
- **Mandatory transmission caveat, adjacent to the headline:** the headline rides on
  the cost-push leg, a reduced-form exogenous-price mapping by its own specification;
  the structural TFP alternative flips the sign (+0.026 on v12). The quote never
  travels without the transmission named.
- **Dropped:** the v9 "positive near-term transition from the morbidity gain"
  narrative. Those health numbers predate the 2026-08-11 mortality-shock fix and the
  v16 transition is negative throughout the window; nothing of that story survives.
- Figure: the macro transition figure from the run's own figure set (regenerates per
  evidence base).

**7.2 Composition of the coupled response** (rewrites "Standalone mechanism
experiments"): the matched real-price battery replaces the "not attributable" close.
- The identity: coupled = energy composite + investment (≈0) + health (≈0), **by
  construction** — carbon enters coupled emit-only — so this is an identity, not a
  zero-interaction finding. Not bit-exact on w (fourth decimal); never "identical"
  unqualified.
- Within the composite: cost-push −0.496 vs household wedge −0.026 of the −0.525
  total (v12).
- The standalone carbon row (−0.032) is an OG consumption-side tax the coupled
  configuration deliberately omits — stated so no reader sums it against the headline.
- Table: the v12 attribution table (Y, C, w), base named, re-verification-queued note.

**7.3 Distributional incidence** — refresh: the coupled run's own incidence figures
(energy spending by income group; consumption by good by group) become the primary
exhibits, base-named; the recycled-wedge point keeps the battery's clean_incidence row
(v12 values replace v9's). The existing mechanism sentence (regressivity a single-agent
core cannot produce) stays.

**7.4 The capital pair** — minimal touch. Keeps its explicit earlier-solve label until
the re-run on the re-blessed baseline (open work #4) lands; table refs updated only.

**7.5 Validation** — layers table stays; the golden-record row is re-scoped per Q(b);
add one row for the matched-battery identity check; the loosened lives-saved RC-gate
paragraph stays.

**Caveat block** — updated: deflator → magnitudes are relative changes only; the price
signal is a levelized cost, never a marginal price (degenerate dual, documented); the
morbidity response is a placeholder calibration; every figure names its base.

## Derive-don't-retype mechanics (what makes the v18 swap mechanical)

A small generator (repo tooling, never named in the manuscript) reads the run's macro
table + manifest and emits a TeX include: number macros (\cplY, \cplC, …, realized
channel magnitudes) plus the two tables. §7 prose references macros only. On v18:
point the generator at the new run directory, recompile; it prints a sign-comparison
table so any sign flip (which would require prose changes) is caught loudly rather
than silently absorbed.

## Questions for the coordinator

(a) **Citation convention:** the register's sole code-name exception is
    `results/golden.json`, but the v16 numbers' authoritative record is the run
    manifest. Extend the exception to the manifest, or cite "the archived run record"
    generically?
(b) **Regression record:** will a golden be regenerated on the final evidence base, so
    Validation keeps the "regression-locked" claim — or does that claim get scoped to
    the v9 record?
(c) Confirm dropping the v9 morbidity-transition narrative entirely (pre-fix health
    numbers; contradicted on v16).
(d) Confirm the mixed-base presentation (headline v16, decomposition v12, bases named,
    re-verification noted) is acceptable until the matched-leg pair runs on the final
    base.
(e) Which figure set is canonical for the methods paper — the coupled deck
    (macro transition, incidence)? The impact deck reads as short-paper/deck material.

## Cross-lane flag (no action by me)

The stale −0.138 headline appears **only inside §7** — grep over paper/ 01–06 and all
of paper-intro finds no other occurrence, so the rebase needs no patches to session A's
sections.
