# Response to the methods-paper comparison and channel review

**Date:** 2026-08-04
**Responding to:** `methods-paper-comparison-and-channel-review.md` (same directory)
**Manuscript state after this response:** `paper/linkages-intro`, commits through the one
carrying this document (edits listed in §2 below applied and compiled).
**Author of this response:** the session that drafted the intro/background and folded in the
comparative briefs (manuscript commits `f700e6d`, `268c620`, `ca40cc3`). Evidence cited below
was gathered first-hand from the repo, the solved runs on disk, and external sources — the
provenance of each claim is stated inline.

## 0. Overall verdict

The review is high quality and most of its recommendations are accepted. Its two best catches
are (a) the channel definition ("one signal to one wedge") not matching the deployed channels,
and (b) the non-additivity claim (−0.138% coupled vs ≈−0.02% standalone sum) currently resting
on inference rather than a matched cumulative experiment, because `across_steps` was dropped
at the July 9 re-bless and never regenerated. The first is fixed in the manuscript now; the
second is queued as the top verification run.

Where the review is wrong or already answered, it is because it could not see evidence outside
the `ca40cc3` snapshot. Those items are answered below with the evidence, so they can be
closed rather than re-investigated.

## 1. Answers to the investigation checklist (§8 of the review)

Status vocabulary as requested: PASS / CHANGED / STALE / UNVERIFIED, with evidence.

| Item | Status | Evidence |
|---|---|---|
| Branch/HEAD of latest repos | PASS | link trunk `main` @c24eb7a (2026-07-28); writing branch `paper/linkages-intro` (this worktree); OG-PHL live env = `m8-compat` worktree (M=8, electricity industry 2); MUIOGO case `Philippines_v9`. Surveyed against live git 2026-08-04. |
| Authoritative channel list | PASS | 11 functions in `ogclews_link/channels.py` grouped into the paper's 8-channel taxonomy: route variants (`energy_price_tfp`, `energy_cost_push`) are alternative transmissions of the one energy signal; `carbon_tax`+`emit_carbon_penalty` are the two halves of the carbon channel. Verified by code read (2026-07-06) and unchanged by main's later commits (diff reviewed: robustness/docs/viz only). |
| Experiment list & composition | PASS | 14 named experiments in `experiments.py`. `coupled` composes: `_apply_energy_composite` (real price: cost-push with self-use zeroed + recycled household wedge) → `investment` → `emit_carbon_penalty` ($50, CLEWS side) → `health` → solve → `emit_discount_rate` → `emit_energy_demand`. Verified from `experiments.py:211–223`. |
| Composition of `coupled` | PASS — review's reading confirmed | As above. `capital_intensity` and `energy_capex` are **not** composed; carbon is CLEWS-side only. The manuscript's §7 prose already states this composition; the table row said "(all)" — **fixed** to "(application config.)". |
| `energy_price`: household-only or composite? | PASS — review's reading confirmed | The runnable `energy_price` experiment is the household wedge alone on the real price; the composite is what `coupled` transmits (and `energy_full` exercises at +20%). §7 now says this explicitly. |
| `carbon` one or both sides in `coupled`? | PASS | CLEWS side only in `coupled`; both sides in the standalone `carbon` experiment. The rationale for the flagship choice is the count-once discipline: the reform LCOE already carries the penalty-induced system cost into the economy through the energy channel, so an OG-side wedge in the same run would represent a second entry of the same cost. This rationale should be (and now is being) stated in the paper rather than left implicit — accepted. |
| `energy_capex` in battery/golden? | PASS — absent, and the paper says so | Golden keys (re-blessed record, this worktree): baseline, capital_intensity(+_ss), carbon, clean_incidence, coupled, demand, discount_rate, energy_price(+_ss), health, investment(+_ss). **No energy_capex.** §5 already says "not exercised as a standalone run in the present battery"; the intro's "all eight channels, exercised by a continuable battery" was imprecise — **fixed**. |
| Reproduce the capital-pair percentages | PASS — independently recomputed 2026-08-04 | From the solved steady states on disk (main worktree battery output): `SS_vars.pkl` is a plain dict (no ogcore needed); γ from `reform_overrides.json` (0.7816→0.8772 = +12.2%), p_m[2] −42.8%, Y_m[2] +20.9% (npz), K_m[2] −22.4%; identity gap 0.023pp. Caveats that stand: this is the pre-re-bless battery's solve (the paper's "earlier steady-state solve" qualifier is correct and stays); regeneration under the re-blessed baseline is queued (§3). |
| PHL electricity price source/construction | PASS with a doc task | "auto" = curated cost-of-electricity workbook if present, else LCOE reconstructed from CLEWS per-technology cost/production CSVs; the commodity-balance shadow price is degenerate and reserved for scarcity. Ratio ≈1.05 mean, 1.16 by 2030. The review's asks (mean definition — it is an arithmetic mean over years; LCOE construction by technology/denominator/discounting) are fair documentation tasks for §6 — queued. |
| Re-test electricity-dual degeneracy | UNVERIFIED (queued) | The degeneracy was established on the current model version when the LCOE switch was made (scattered-year binding). Whether it was probed across alternate optima, vs observed as sparse values, needs the run record — queued with the land re-test. |
| 5% mean / 16% peak definition | PASS | Reform/base LCOE ratio: mean 1.0539 across years, max 1.1625 in 2030. §6 states "averages about 1.05 (rising to 1.16 by 2030)". |
| Health: dose-response, target, residuals | PASS | M=0.082 (energy mass-share 9.8% × CRF elasticity 0.84, `ogclews_link/data/pm25_health.json`); −2.7% emissions → −95.4 lives (re-blessed target); morbidity elasticity **uncalibrated** — the paper says so and never attributes the GDP gain to lives saved; Walras exception (1e-5 SS gate, lives-saved direction only) documented in §7. |
| Emitted signals consumed by a real re-solve? | PASS — review's suspicion confirmed, manuscript adjusted | The +10% → +4.28% test (`docs/design/INTEGRATION-HANDOFF.md:89`) is a **controlled demand patch** through `clews_driver.scale_annual_demand` → MUIOGO re-solve → read-back. It validates the seam (patch → re-solve → read), targeting the same case object (`SAD`) the demand emitter is designed to write. It does **not** consume an emitted OG artifact end to end; that is the outer controller's job. §4 wording **fixed**: "the re-solve seam they are designed to feed … validated with a controlled perturbation". |
| Principles → guard/construction/composition map | PARTIALLY ANSWERED | Guards verified in code for: concordance/couplability skips, carbon species validation, price-source fail-fast, demand-target checks. The capital-pair non-stacking and the one-cost-per-flow rule are enforced by experiment composition, not by a runtime guard. §4's blanket "each enforced by a guard" **softened** accordingly. The full principle-by-principle map (including a test that violates each rule) is a good §5/appendix task — queued. |
| Which manuscript numbers are in the golden record | PASS | Macro aggregates (SS + t0/t10) per experiment are regression-locked (`tests/test_golden.py`). Sectoral capital-pair figures are **not** in the record (recomputed from solved outputs, as above). The LCOE path and health target live in inputs/config, not the golden. The review's suggested practice — qualify each number as regression-locked / reproduced / calibrated / illustrative — is accepted for the results section. |
| Cumulative decomposition of −0.138% | **STALE — the review's best catch** | `across_steps` was built for the pre-LCOE golden (its top layer reproduced the then-coupled run by construction) and was **dropped as stale at the July 9 re-bless, not regenerated**. The current −0.138%-vs-−0.02% interaction claim therefore has no matched cumulative run behind it. Queued as the top verification item; until it runs, §7's hedge ("a diagnostic reading, not an additive accounting") stands and no stronger claim is made. |
| Manuscript statements made stale by later development | PASS | The manuscript was drafted against the current code state (2026-08-04 survey), not the other way round; the stale items found ran the other direction and are fixed by this response. |

## 2. Manuscript edits made in response (compiled clean, 21pp)

1. **Channel definition** (intro + §4): a channel now maps a signal to a *deliberately
   partitioned set of wedges that never overlap* — one in the simplest channels, several when
   split by use (energy) or demographic object (health). This adopts the review's §2.1.
2. **Channel vs experiment** (§7): the results table is now introduced as *runnable
   experiments isolating one mechanism*, with `energy_price` identified as the household
   wedge alone and the composite located in `coupled`/`energy_full`. Adopts §2.1's last point.
3. **"coupled (all)" → "coupled (application config.)"** in the table. Adopts §4.1.
4. **Battery coverage** (intro): "the channel library … all but the investment-tax-credit
   lever, which is defined but not yet run standalone". Fixes an overstatement the review's
   §3 row on `energy_capex` correctly probed.
5. **Iteration taxonomy** (§2): sequential feedback (IEEM) vs one-way parameterisation
   (CLEWs–IO) vs fixed-point iteration (nobody, including us). Adopts §1.3.
6. **Hard-link precision** (§4): the assumption now explicitly forecloses the
   integrated-welfare-program route; a joint complementarity formulation is acknowledged as
   conceivable in principle but a research programme of its own. Adopts §1.5.
7. **Fixed-point interpretation** (§4): with LCOE as the deployed price, the fixed point is
   consistency under the pricing proxy, not a competitive-equilibrium price. Adopts §5.1's
   third bullet. (The defined term "soft-link equilibrium" is retained — see §4 below.)
8. **Re-solve seam wording** (§4): "designed to feed … validated with a controlled
   perturbation; feeding the *emitted* signals end to end belongs to the outer controller."
9. **Guards sentence** (§4): enforcement is by guard within a channel, by composition rules
   across channels.

## 3. Queued verification work (accepted, requires runs — in priority order)

1. **Regenerate the cumulative decomposition** on the current `coupled` recipe (re-blessed
   baseline, LCOE price) and locate where the −0.138% emerges relative to standalone effects.
   Until then the manuscript keeps its hedged wording. Order-invariance / Shapley is a
   nice-to-have after the basic cumulative run exists.
2. **Re-run the capital-intensity lever** on the re-blessed baseline so the sectoral
   percentages either update or are confirmed; store the sectoral outputs in the evidence
   record so the "earlier solve" qualifier can be retired.
3. **Document the dual-degeneracy test** (and, with the land work, alternate-optima and
   solver-resolution probes) so §4's hygiene remark cites a recorded test rather than an
   observation.
4. **§6 documentation adds**: LCOE construction (technology costs, generation denominator,
   discounting), mean definition, and the "auto" source's two providers with a statement of
   when they are and are not interchangeable.
5. **Principle-by-principle enforcement map** with deliberate-violation tests (for §5 or an
   appendix).
6. Standing pre-submission items (unchanged from the comparative brief): systematic ESM↔OLG
   literature search; deflator calibration; land shadow-price re-verification before any
   numeric land claim.

## 4. Where I push back or qualify

1. **"Soft-link equilibrium" → "link-consistent fixed point".** Partially declined. The term
   is introduced by a formal definition whose content *is* the fixed point of the two maps;
   the risk the review worries about (reading it as a competitive equilibrium) is now
   addressed head-on by the added proxy-consistency sentence. Renaming would cost the
   definition's readability without adding precision the caveat doesn't already supply. If
   colleagues stumble on it in the feedback round, rename then.
2. **Validation maturity ladder (7 levels).** Accepted in substance, but the paper will carry
   it as a per-channel maturity *table* (§5) rather than adopting all seven terms in prose —
   seven-way vocabulary in running text would fight the paper's register. The distinctions
   the review wants (mechanically vs economically verified vs regression-locked vs
   calibrated) are exactly the table's columns.
3. **"Describe the comparators' full systems before the coefficient point."** Already the
   structure of §2's neighbours paragraph (IEEM's accounts/modules and wealth contribution
   precede the coefficient observation), and the one-coefficient point is already subordinate
   to the capability positioning. No further change made; flagging so it isn't re-litigated.
4. **The Keppo absence evidence.** The review treats it as needing confirmation. It has been
   independently verified (2026-08-04): `pdftotext` over the open-access Wuppertal copy,
   full-text search — zero occurrences of "overlapping generation(s)" / "OLG" / "cohort" /
   "intergenerational"; CGE ×4, macroeconometric ×1, input–output ×1. A comment recording
   this sits in `02-background.tex`; re-confirmation against the publisher's version remains
   flagged for submission. The manuscript keeps "to our knowledge" for the priority claim and
   argues capability first, exactly as the review recommends.
5. **"The introduction refers to all eight channels in connection with the full pass."**
   Correct as of `ca40cc3` and now fixed — but note the direction of the error was the
   introduction's wording, not the validation claims themselves: seven of eight channels are
   battery-exercised and golden-locked; the ITC lever is defined, guarded, and unexercised,
   and the paper now says precisely that.

## 5. One item the review did not raise

The §7 carbon rationale (why the flagship run carries the carbon price on the CLEWS side
only) deserves a stated sentence in §7, not just the count-once principle in §4: the reform
LCOE already embodies the penalty-induced system cost, so an OG-side wedge in the same run
would enter the same cost twice through different doors. This will go in with the §8
discussion drafting, where the composition choice is naturally discussed.
