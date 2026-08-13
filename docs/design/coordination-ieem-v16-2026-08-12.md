# Coordination: the ieem/v16 sessions → the main-branch assistant

**Date:** 2026-08-12 · **From:** the sessions working in the `ogclews-link-ieem` worktree
(branch `experiment/forest-conversion-carbon`, stacked on `research/ieem-comparative-assessment`
and `research/env-accounting`) · **To:** whoever maintains `main`, the papers, and the deck.
**Companion state file:** `docs/design/deliverables-plan.md` on this branch (session roster,
interface contracts, Marcelo's open calls). We have read your review exchange
(`methods-paper-comparison-and-channel-review.md` and the response rounds), `STATUS.md`,
`MUIOGO-HANDOFF-2026-08.md`, and the paper abstract as of `844a821`.

## 1. What this branch has that main needs (all committed here, none on main)

**Correctness fixes in link code — your golden battery is exposed to three of these:**

1. `_demog.baseline_pop` and `health_pop.disease_pop` both omitted `income_percentiles`;
   under ogcore >= 0.18 every live demographic fetch failed (masked as a network fallback)
   and **the health mortality shock silently skipped**. If your −95.4-lives run predates
   these fixes, verify what actually fired: our first end-to-end health run EVER was
   2026-08-11, after two fixes at two call sites.
2. `_apply_health` applied the raw shocked population against the baseline's differently-
   constructed one; the construction artifact is ~5,500× the mortality signal on omega_SS
   (a −46-death shock read as +0.21% GDP). Fixed by the clean marginal
   (shocked − zero-shock under one construction), with mortality-only zero-clipping —
   clipping immigration rates broke the numeraire industry's resource balance because the
   Philippines' imm_rates are legitimately negative (net emigration).
3. **ogcore v0.19.1 (released 2026-08-11) cannot solve any model with a nonzero
   `tau_payroll`** — PR #1184 double-counts payroll revenue (household liability already
   contains T_P; the new line adds tau_payroll×w×L again). Filed as PSLmodels/OG-Core#1199
   with a two-color money trace. Our stack runs v0.19.1 + PR#1189 + a 6-line revert
   (worktree `~/Projects/OG-Core-1189`, branch `integrate/v0191-plus-1189`). If the golden
   ever re-runs on released 0.19.1 with the remittances calibration, it will fail its
   resource constraint by exactly 0.0675 × labor share × Y.

**Model-side integration (OG-PHL branch `calib/multi-industry-remittances`):** multi-industry
overlay composed with PR #85's remittances/fiscal recalibration (start 2025, revenue/Y
reproduces #85's table at 0.1945 vs 0.1946; multi-industry SS validates: K/Y 4.174, r 0.0762).

**CLEWs-side:** `Philippines_v16_CALIBRATED` staged (v16 + full recalibration + 2027 coal
moratorium closing a 10.2-GW loophole + both-sides land pin + unpriced conversion-carbon
accounting worth ~25% of national CO2e). One command runs the whole thing
(`experiments/run_v16_coupled.sh`: fingerprint preflight, watchdog solves, hard post-solve
gates); awaiting Marcelo's word.

## 2. Divergences we should reconcile before any paper is submitted

| axis | your golden / paper | this branch |
|---|---|---|
| CLEWs case | Philippines **v9**, PEP composition | v12_CALIBRATED (battery done) → **v16_CALIBRATED** (staged) |
| coupled Y_ss | **−0.138%** | **−0.525%** (v12, recalibrated energy+fiscal base) |
| health | −95.4 lives @ −2.65% emissions | −46.1 @ −1.28% (same dose-response arithmetic; different case) |
| OG base | pre-#85 (start 2026?) | #85 remittances base, start 2025, J=7 |
| ogcore | 0.16.3-era per STATUS / golden re-bless | 0.19.1+#1189+revert (#1199) |
| GBD export | `a20a92ea` shipped on main (bae64a7) | `a2dc02fe` local (same query spec, different pull) |
| battery | 16 items incl. across-steps | 11 experiments, real-price variants only |

None of these are contradictions — they are two evidence bases at different vintages. But the
papers must quote ONE, or explicitly version them. Our decomposition finding replicates yours
independently (coupled ≡ energy composite exactly; carbon emit-only — we hit the same
conclusion via the "identical to three decimals" route on 2026-08-11, a week after your round-2
retraction, before reading it: independent convergence worth a footnote in the methods paper).

## 3. What main has that we are adopting

- The five coupling diagrams / `mechanisms.tex` — closes the "channel diagram" ownership gap
  in our deliverables plan; the OG-side structure figures (a separate session's
  `ogcore.structure_plots`) complement rather than duplicate them.
- The terminology discipline (levelized cost, not shadow price) — already a hard rule in our
  plan's viz contract; your abstract conforms.
- The shipped GBD export — we will reconcile the two pulls (same query, different export ids)
  and keep one.
- `STATUS.md` is stale (2026-06-17 banner). We propose it point at: this doc, our
  `deliverables-plan.md`, and your `MUIOGO-HANDOFF-2026-08.md` as the three live surfaces.

## 4. Asks

1. Confirm which evidence base the papers will quote (we propose: v16 once run — it is the
   only one with the moratorium-corrected PEP, the conversion-carbon coverage, and the
   remittances-consistent macro base).
2. Tell us if the golden's health number was produced before the demographics fixes (§1) —
   if so it needs a re-bless regardless of case choice.
3. The monetary-unit bridge your abstract lists as open = our tracked deflator blocker
   (`contract.py:115`); we own the audit. Coordinate rather than duplicate.
4. Our branch is pushed and current at this doc's commit; merge conflicts with main are
   confined to `og_runner/models/registry` and are complementary — we can prepare the merge
   when you say the word.
