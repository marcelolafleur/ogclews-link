# Deliverables plan — CLEWS↔OG linkage papers and presentation

**The big deliverable** (Marcelo, 2026-08-11): a SHORT paper, a TECHNICAL paper, and a
PRESENTATION showing the linkage channels between CLEWs and OG-Core, including the
comparison with other integrated-tool methods (IEEM, CLEWs-IO). Everything else in this
repo is input to these three artifacts.

**Coordination:** the v16/stack session (owner of this file) coordinates; there is no
master-coordinator session. This file is the shared state — every session reads it before
acting and appends to the status log when it delivers. Cross-session messages for
handoffs; this file for truth.

## Session roster

| session | role | status |
|---|---|---|
| v16/stack (this file's owner) | results producer + coordinator: calibrated stack, CLEWs v16 case, channel battery, coupled runs, comparison assessment | active; run staged, awaiting "run" |
| env-accounting / comparative-methods | owns the COMPARISON CONTENT (deliverable 4) and the forest-carbon findings (§13/§14, stickiness menu, patch script — absorbed). Read-only on the branch and off the MUIOGO server; active on paper content | active (content committed) |
| "Model linkage visualization" (OG-Core structure plots) | OG-SIDE figures only: ogcore/structure_plots.py on OG-Core feature/structure-plots (HEAD 8b358be8, pushed to the fork) -- circular flow of institutional linkages, io_matrix heatmap, calibration-status and fit plots, Mermaid render, worked OG-PHL M=8 example. Explicitly does NOT cover the CLEWS<->OG channel diagrams; has touched nothing in this repo | active |
| (unowned) CLEWS<->OG channel diagram | the presentation's centerpiece figure -- the coupling channels themselves. NOT covered by any session; falls to the coordinator unless Marcelo assigns it | GAP |

## Deliverable tree and inputs

1. **Short paper** — headline result + channel story, plain language.
   Inputs: attribution table (DONE, v12 battery — §15 of phl-calibration-decisions.md);
   v16 coupled headline (PENDING "run"); health channel finding (DONE: ~46 deaths, <0.005% GDP).
2. **Technical paper** — methods: the soft-link architecture, channel specifications,
   calibration record, doctrine (derive-don't-force), falsification results.
   Inputs: phl-calibration-decisions.md (15 sections, DONE through v12);
   phl-testcase-plan.md §12-14 (DONE); land-conversion-cost-sourcing.md (DONE);
   land-stickiness-options.md (DONE); ogcore #1199 finding (FILED);
   v16 migration record (PENDING run + writeup).
3. **Presentation** — the linkage channels, visually.
   Inputs: channel table with directions (ogclews-link `channels`; the emit-only caveat
   in the og-clews-linked-run skill); coupled figure deck (v12 DONE at
   ogclews_runs/coupled/figures/, 19 PNGs; v16 lands in ogclews_runs_v16/coupled/figures/);
   attribution table. OG-side structure figure: REUSE ogcore.structure_plots
   (plot_circular_flow for the institutional linkages, plot_calibration_status for
   own-evidence-vs-US-defaults) from OG-Core branch feature/structure-plots -- render from
   that branch's own environment; NEVER install branch ogcore into OG-PHL's venv (the
   solve stack is fingerprint-pinned). The CLEWS<->OG channel diagram itself is UNOWNED
   (see roster) and is the presentation's centerpiece.
4. **Comparison with IEEM / CLEWs-IO** — a section in both papers + slides.
   OWNER: the env-accounting/comparative-methods session. Its committed content:
   paper-comparative-methods-brief.md (the drafting brief; contribution claims graded by
   evidence strength — strongest: Keppo et al. 2026, the field's own linking review, has
   zero OLG/cohort/intergenerational hits vs seven for CGE; the 'nobody has done it' claim
   is flagged UNVERIFIED pending a systematic search), ieem-comparative-assessment.md
   (IEEM's feedback = one 8% erosion coefficient; genuine-savings terms computable from a
   solved case), clews-io-employment-assessment.md (their 'endogenized employment' is a
   jobs-per-PJ coefficient, no iteration; IO table confidential), method-comparison-brief.md.
   Shadow-price hygiene is a titled contribution (cross-validated three ways: energy-side
   LCOE guardrail, land-side degeneracy, §13 falsification). This session's v16 inputs feed
   it: the emissions-coverage upgrade (~25% of national CO2e) and the moratorium-corrected
   PEP. The earlier stalled paper-comparative-assessment.md workflow is SUPERSEDED by the
   brief; do not resume it.

## Submission blockers (tracked here, with owners)

1. **Unit deflator hardcoded 1.0** (`ogclews_link/contract.py:115`, UnitMap.deflator) —
   carbon/investment magnitudes are illustrative until audited/fixed. OWNER: v16/stack
   session (it is link code). Audit scope: which channels actually flow a currency
   magnitude through UnitMap (percent-of-GDP normalizations are unitless and immune);
   fix or document per channel BEFORE paper numbers are quoted as calibrated.
2. **Keppo item-xiii epistemic map** (least-cost planner vs decentralized equilibrium —
   what linking an LP to an OLG means epistemically) — unwritten. OWNER: comparative-methods
   session (its brief), unless Marcelo reassigns.
3. **'Nobody has linked OSeMOSYS/CLEWs to an OLG' claim** — UNVERIFIED; needs a systematic
   search before any submission. OWNER: comparative-methods session.

## Interface contract for the visualization session

- Channel definitions: `ogclews_link/channels.py` docstrings + `ogclews-link channels`
  (direction clews->og vs og->clews matters; emit-only channels bind nothing in one pass).
- Real numbers: `ogclews_runs/<experiment>/macro_table.csv` (v12 battery, 11 experiments,
  DONE) and `ogclews_runs_v16/` after the run. Attribution table in
  phl-calibration-decisions.md §15 (with the coupled==energy structural identity caveat).
- Figures: `ogclews_runs/coupled/figures/` — reuse or restyle, don't recompute.
- The stack fingerprint (what produced the numbers): og-clews-linked-run skill,
  "Fingerprint the stack" section.
- TERMINOLOGY (hard requirement from the comparative-methods session, learned from its own
  corrected over-claim): the energy-price channel's exchanged signal is the LEVELIZED COST
  ('auto' resolves to the cost-of-electricity workbook or LCOE reconstruction). It is NOT
  the shadow price/dual — the marginal source is opt-in only and degenerate. Any figure
  narrating the channels must say "levelized cost"; "shadow price" in print repeats the
  mistake.

## Status log

- 2026-08-11: file created. v12 battery complete (11/11); v16 case staged (calibration +
  moratorium + land pin + accounting variant); conversion cost sourced, implementation
  deferred; run button ready (experiments/run_v16_coupled.sh), awaiting Marcelo's "run".
