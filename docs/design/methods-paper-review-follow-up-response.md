# Response to the follow-up (round 2)

**Date:** 2026-08-04
**Responding to:** `methods-paper-review-follow-up.md`
**Manuscript state after this response:** `paper/linkages-intro`, the commit carrying this
document. Both papers and the deck compile clean.

## 1. Carbon provenance — checked, your checks FAIL, and I retract my earlier rationale

This was your most important question, and it was checkable rather than debatable. Evidence,
gathered directly from the case data the coupled run's own manifest points to:

- **Provenance chain:** `ogclews_runs/battery/coupled/coupled/ogclews_manifest.json` records
  `scenario.base_dir = …/Philippines_v9/res/Base_v9/csv` and
  `scenario.reform_dir = …/Philippines_v9/res/PEP_v9/csv` — so the LCOE the macro solve used
  was computed from the `PEP_v9` caserun's outputs.
- **The solver's own record:** in both `res/Base_v9/data.txt` and `res/PEP_v9/data.txt` the
  compiled parameter block reads `param EmissionsPenalty default 0 := ;` — **empty**. Neither
  the baseline nor the reform CLEWs solve carries any carbon price on any species.
- **What the reform actually is:** the case's scenario codebook (`genData.json`,
  `osy-scenarios`) lists BASE / COALPHASEOUT / RE / EV — the reform is a
  policy-composition scenario, not a carbon-priced one.

So, against your four checks: (1) no `EmissionsPenalty` in the pre-solved reform; (2) n/a;
(3) not the same policy — there is none; (4) the LCOE derives from an **unpenalised** solve.

**Retraction:** my round-1 response (§5) offered the rationale that "the reform LCOE already
embodies the penalty-induced system cost." That is wrong for this application and is hereby
withdrawn. The correct statement is the one your conditional prescribed: the flagship
`coupled` **emits** a proposed $50/tCO2 carbon-price input for the future round trip, and
**no carbon-price effect enters the reported coupled numbers**.

**Manuscript changes made accordingly (not deferred to the discussion):**

- §7 flagship description rewritten: the run "emits, alongside the equilibrium return and
  activity, a \$50/tCO2 carbon-price input for the energy model. The emitted signals are
  inert in a single pass, so no carbon-price effect enters the numbers reported here — the
  underlying CLEWs reform is a policy-composition scenario whose solve carries no emissions
  penalty…"
- §5 carbon channel: added that in the one-pass validation the CLEWs-side path is *emitted*
  and shapes the build mix only when the energy model is re-solved on it.
- The companion paper's introduction (`paper-intro/sections/01-introduction.tex`) had the
  same overstatement ("transmits … a carbon price") — fixed to "emits a carbon-price input
  for the energy model's next solve."
- The mechanisms deck's coupled-anatomy slide had it too ("in the energy model") — fixed to
  "emitted for the energy model's next solve," with a bullet stating plainly that no carbon
  price acts in the reported numbers.

The count-once principle survives as design logic for any future two-sided run; it just was
not the operative fact here. Good catch — this is the kind of thing the paper's own
"auditable interface" claim obliges us to get exactly right.

## 2. Non-additivity — your additional mismatch accepted; wording neutralised

You are right that the isolating `energy_price` run (household wedge only) and `coupled`
(composite) are not matched treatments even before the staleness of `across_steps` is
considered. §7 now says the coupled result "is not reproduced by summing these isolating
experiments — nor should it be," names the wedge/composite mismatch explicitly, and states
that a matched cumulative decomposition whose final step reproduces `coupled` "is the
instrument for attributing the difference; we do not attribute it here." The deck's
corresponding bullet was aligned. Attribution language returns only when the matched run
exists.

## 3. Golden-record scope — narrowed

The introduction now says "each experiment's macroeconomic aggregates regression-locked in a
committed record (sectoral and interface quantities are reproduced from the solved outputs
and qualified where they appear)." §7's validation subsection already made the narrower
claim. Your recommendation of artifact-level regression tests for the emitted demand,
discount-rate, and carbon paths is accepted and added to the queue as a code task (it
belongs next to `tests/test_golden.py`; small, well-scoped).

## 4. Discount-rate interpretation — labelled as a harmonisation convention

§5's discount-rate subsection now states the mapping is a harmonisation convention, not a
structural equality: `DiscountRate` is the planner's system-cost discount rate, $r_p$ the
economy's equilibrium portfolio return; equating them asserts planning at the economy's
opportunity cost of capital, with risk premia, tax treatment, and the real/nominal
convention named as open harmonisation choices. The §2 sentence (the discount rate as an
equilibrium object the economy *can supply*) stands as a capability claim and now reads
against a §5 that says precisely what "supply" means.

## 5. Minor consistency edits — all five applied

1. §7 retitled "Standalone mechanism experiments"; table and figure captions no longer say
   "per-channel" (the committed figure PNG's own title still says "by channel" — noted in
   the caption; regenerating the figure is queued as cosmetic).
2. The −0.006% is now attributed to "the household-wedge `energy_price` experiment."
3. §2 now says "the classic integrated-welfare-program route of the hard links is
   unavailable," matching §4.
4. The introduction's guards sentence now matches §4 (guards in code + composition rules).
5. "economy–resource feedback" → "economy–resource linkage" in the neighbours paragraph.

## 6. Updated queue (supersedes round 1's §3)

1. ~~Verify the reform's carbon policy~~ — **done this round; result above.**
2. Matched cumulative decomposition reproducing the current `coupled` (top priority run).
3. Artifact-level regression tests for emitted demand / discount-rate / carbon paths (new,
   from your §3).
4. Capital-intensity re-run on the re-blessed baseline; store sectoral evidence.
5. Dual-degeneracy test documentation (electricity; land alongside).
6. LCOE construction documentation in §6 (technology costs, denominator, discounting, mean
   definition, the two "auto" providers and their interchangeability conditions).
7. Principle-by-principle enforcement map + per-channel maturity table (§5).
8. Standing: systematic ESM↔OLG search; deflator calibration.

## 7. Status of the conversation

Round 1's disagreements are settled on your terms or withdrawn by you (ontology). Nothing in
this round is contested: every item was either verified and adopted, or verified and found
to cut *against* my earlier position, in which case the manuscript now says what the
evidence says. The remaining open items are runs and documentation, not interpretation.
