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
| authoring session | CONFIRMED: worktree ~/Projects/ogclews-link-writing, branch writing/results-and-closing off paper/linkages-intro. Correction absorbed: paper 07-results is DRAFTED on the v9 golden, so the work is a REBASE + new composition subsection, per its committed plan (docs/design/plan-07-results.md on its branch). Green-lit lanes: 07-rebase per plan, paper-intro 07-conclusion, the TeX number-macro generator (derive-don-t-retype with a sign-flip check) | active |
| "Model linkage visualization" (OG-Core structure plots) | OG-SIDE figures only: ogcore/structure_plots.py on OG-Core feature/structure-plots (HEAD 8b358be8, pushed to the fork) -- circular flow of institutional linkages, io_matrix heatmap, calibration-status and fit plots, Mermaid render, worked OG-PHL M=8 example. Explicitly does NOT cover the CLEWS<->OG channel diagrams; has touched nothing in this repo | active |
| CLEWS<->OG channel visualization ("Graphics for ogclews-link") | CONFIRMED 2026-08-13: worktree ~/Projects/ogclews-link-viz, branch viz/channel-diagrams off main, nothing pushed. First sketch delivered (fixed-layout ledger, AST-derived channels -- no imports, no hand lists; symlog effect axis; baseline block on-figure). Its review found: the upstream channels.tex carries the forbidden "dual/marginal price" wording, symmetric carbon arrows, 7-of-11 channels, 3 stale names (routed to session A via COORDINATION.md); the Option A vs A-prime sign flip (+0.026 vs -0.496) is now on the figure; per-row numbers captioned as ATTRIBUTION not decomposition (matched-pair runs queued on the v16 base); "identical" overclaim on coupled==energy corrected in section 15. Decision taken: ledger prints Y only, C/K/w in a companion heatmap | active |

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
   attribution table. OG-side structure figure: UNBLOCKED via option (d), verified by the
   structure-plots session end to end -- structure_plots.py loaded by file path from its
   worktree, ogcore resolving to the pinned 1189 build, nothing installed; it read today's
   OG-PHL parameters (M=8, I=5, initial_wealth_ratio=2.783) and produced the full set.
   Its ogcore surface is a single lazy `from ogcore.parameters import Specifications`.
   THE FINDING THAT MAKES (d) CORRECTNESS, NOT CONVENIENCE: calibration_status judges
   "calibrated" against Specifications() defaults, so the verdict is BASELINE-RELATIVE --
   under the 1189 defaults PHL's government block is 10/12 calibrated; under the 0.18.1
   baseline the committed figure says 7/12, understating the fiscal calibration by three
   parameters (h/m/p_wealth). The meaningful baseline is the build the country model runs
   on, so the deck figure MUST be generated per (d); the synthetic example (c) remains the
   right upstream artifact -- complements, not alternatives. Known gap, owner
   structure-plots session: PARAM_BLOCKS is hand-maintained and omits initial_wealth_ratio
   entirely, so a demonstrably calibrated parameter is invisible; will drift as ogcore
   moves. Corrected figures exist in that session's scratch pending Marcelo's confirmation.
   REUSE ogcore.structure_plots
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
4. **Baseline-identity claims: build-family granularity only** until a content digest exists
   (the version+param-count footer cannot separate builds — two local OG-Core builds share
   "0.19.1, 140 parameters"). In the brief's §8 as item 6. OWNER: comparative-methods
   session (claim scoping); digest itself is on Marcelo's queue (og-core-23).

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

## Onboarding brief for the incoming channel-visualization session

Read first: docs/COORDINATION.md on main (protocol + writing register), this file's
interface contract above, then coordination-ieem-v16-2026-08-12.md. Prior art: the five
coupling diagrams in presentation/ on main -- reconcile, don't duplicate.

Hard-won lessons from the OG-structure-plots session (each cost real rework there):

1. NAME THE BASELINE ON THE FIGURE. "Calibrated/changed/differs" is relative to whatever
   supplied the comparison; unstated, the error is silent (its 7/12-vs-10/12 miss reached
   committed artifacts). For channel work: state build, case, and scenario for EACH side
   of any coupled-vs-uncoupled or tool-vs-tool comparison, on the figure itself.
2. VERSION STRINGS DO NOT IDENTIFY BUILDS. Two local ogcore builds both say "0.19.1";
   two of them also share a 140-parameter count. Fingerprint by content where identity
   matters. This session spans ogclews_link + ogcore + a country package + MUIOGO case
   data, each independently pinned -- the hazard compounds.
3. NEVER INSTALL INTO A PINNED ENVIRONMENT. Ride on top: import your module by file path
   so its ogcore import resolves to the pinned build (the verified "option (d)" pattern;
   writes nothing anywhere).
4. DERIVE WHAT YOU DRAW; never hand-list it. Read channels from channels.py
   programmatically. Direction is semantic: emit-only channels bind nothing in a one-pass
   run -- a diagram with symmetric arrows everywhere is WRONG, not loose.
5. NO MIXED STOCKS/FLOWS OR UNITS in one diagram. PJ, GW, prices, and shares of GDP are
   different kinds; a Sankey spanning them means nothing. Normalize and print the unit.
   (Capital enters magnitude figures as the rental payment (r+delta)K, not the stock.)
6. DEVIATION AXES NEED SYMMETRIC LOG -- cross-model comparisons are heavy-tailed; one
   1600% outlier flattens everything else onto the centre line.
7. MERMAID SPECIFICS: arrowhead size is not controllable from source (several documented
   failures, one erases arrowheads); ELK routing needs a plugin GitHub won't load -- so
   render PNG via the Mermaid CLI (mmdc 11.16.0, installed globally on the ieem machine);
   collapse whole-group fan-outs onto the group node or automatic layout is destroyed.
8. MARCELO'S EVIDENCED TASTE: kept -- composed fixed-layout diagrams, heatmaps, tile
   grids, dot plots with the numbers beside the geometry. Rejected -- ribbon bundles,
   chord diagrams, Graphviz output, two-parameterization diffs, any single encoding that
   visually dominates (a coverage bar was replaced by per-parameter chips). Numbers stay
   visible; auto-laid-out node-edge graphs get rejected.
9. PROCESS: use your OWN git worktree (a shared checkout was branch-switched under a
   session here), and treat result directories as regenerable-underneath-you while
   rendering. TERMINOLOGY: the energy channel exchanges a LEVELIZED COST, never "shadow
   price" (see interface contract above).
10. Do NOT use ogcore.structure_plots' committed files as reference yet -- its example
    gallery still carries a known-wrong figure (7/12); wait for Marcelo to clear that
    session's queue.

## Status log

- 2026-08-11: file created. v12 battery complete (11/11); v16 case staged (calibration +
  moratorium + land pin + accounting variant); conversion cost sourced, implementation
  deferred; run button ready (experiments/run_v16_coupled.sh), awaiting Marcelo's "run".
- 2026-08-11 (later): OG-side figure blocker recorded (version mismatch, options a-d
  above). Unattributed actor note: something switched the shared ~/Projects/OG-Core
  checkout to pension-replacement-rate-adjust and committed d03f6ac2 (unpushed gallery
  fix) to feature/structure-plots -- neither this session nor structure-plots did it;
  candidates are the unidentified peers (og-core-23 / muiogo-55). Sessions working in
  OG-Core should use their OWN worktrees, not the shared checkout.
- 2026-08-11 (later still): baseline footer shipped by the structure-plots session
  (local 85457d6e, unpushed): "Judged against OG-Core <version>, <N> parameters" -- the
  parameter COUNT discriminates BUILD FAMILIES, NOT BUILDS -- the peer's own correction,
  measured on this machine: OG-Core-1189 and OG-Core-pr1189 both count 140 keys (identical
  footers for different builds); the 0.18.1 base counts 134. The footer separates the
  0.18.1-vs-1189-family confusion that bit the PHL figure, and no further. The technical
  paper must not claim more. Exact fix (proposed, deliberately NOT built pending Marcelo:
  the peer is holding on peer suggestions until he weighs in): a short content digest of
  default_parameters.json next to the version -- identity, not proxy. Complementary to
  this session's source-grep preflight (grep = known threat, digest = identity).
  PARAM_BLOCKS coverage drift remains open (theirs).
  MARCELO'S OPEN CALLS, consolidated: (1) "run" for the v16 coupled run; (2) confirm
  (d)+(c) for the OG-side figures; (3) authorize pushes on feature/structure-plots
  (d03f6ac2 gallery fix + 85457d6e footer); (4) push of this branch's local commits;
  (5) assign the CLEWS<->OG channel diagram (gap); (6) upstream package (parked).
- 2026-08-12: upstream surveyed (origin/main 844a821). The other assistant has: the
  methods paper (paper/) + intro paper (paper-intro/), the deck with five coupling
  diagrams, a 16-item golden on CLEWs v9 (coupled -0.138%, health -95.4 -- PRE our
  demographics fixes, needs verification), a review exchange that independently reached
  the emit-only-carbon conclusion, a shipped GBD export (different pull id than ours),
  and MUIOGO-integration briefs. STATUS.md is the cross-session coordination file
  (stale). Our side written up in coordination-ieem-v16-2026-08-12.md with the
  divergence table and four asks. Local main fast-forwarded to 844a821.
- 2026-08-13: upstream now carries docs/COORDINATION.md on main (the formal
  cross-assistant protocol; our entries appended at a2fdb58 and pushed). BINDING for all
  paper-bound content from any session: the writing-register rules (methodology only, no
  contribution-claiming, no definitional scaffolding, no code-file names except
  golden.json, mechanism-traced explanations per channel-notes/01-energy-price.md).
  The comparative brief's claims must be register-checked before its text enters the
  manuscript. The env-accounting session's socket is gone (work all committed); the
  branch rename (research/ieem-comparative-assessment -> research/env-accounting) is
  official; the shared worktree branch stays un-rebased, reconcile at merge.
- 2026-08-13 (from the comparative session, quiescent): the different-solver half of brief
  §8 item 4 is one flag away — muiogoai ships glpk alongside cbc, so re-solving a staged
  case with --solver glpk tests whether the 20-35x dual overstatement and year-placement
  degeneracy reproduce (magnitude reproducing while years move would STRENGTHEN the
  degeneracy finding). Queue after the v16 run. Paper rule: report which solver produced
  every dual quoted.
- 2026-08-13 (viz session confirmed): see roster. QUEUED after the v16 run: the MATCHED
  composite-leg pair on the v16 base (the composite's cost-push leg with self-use zeroed
  at composite phi, and the diluted+recycled wedge alone) -- quantifies the
  attribution-vs-decomposition gap the ledger currently captions (also answers upstream
  open-work #1 with matched treatments). PAPER-GRADE CAVEAT now on the figure and to be
  in both papers: 94% of the headline rides on the cost-push leg (Option A-prime), a
  reduced-form proxy by channels.py's own docstring; the structural alternative (Option A,
  TFP route) flips the sign (+0.026). Any headline quote names the transmission.
- 2026-08-13 THE V16 COUPLED RUN IS DONE, end to end, gates green. Steady state:
  Y -0.579, C -0.422, K -0.550, L +0.015, r -0.111, w -0.537 (transition-window
  2025-34 avg Y -0.181). vs v12: Y -0.525 -- the moratorium binds (7.94 GW pipeline
  then zero new coal; system loses its cheapest expansion option) and the headline
  deepens ~10%, as predicted when the moratorium was added. Health on v16:
  PM2.5 -7.03% (v13's calibrated emissions layer) -> -253.2 deaths (GBD-anchored),
  5.5x the v12 signal. Conversion carbon booked: 1,474 Mt (2022-53). Offshore cap
  binds exactly (823.0). Investment still ~0 (0.0097% GDP cumulative). Results:
  ogclews_runs_v16/coupled/ (macro_table, manifest, deck, clews_inputs for the
  future loop closure). Evidence-base recommendation to upstream stands: v16.
  Interface-contract upgrade (from the viz session): ogclews_manifest.json is the
  AUTHORITATIVE record of applied channels (channels[]) and realized magnitudes
  (provenance[]); figures derive from it, never from experiments.py readings.
  Known non-derivable: the ogcore build and OG-PHL branch@commit appear in NO run
  artifact (the link env has no ogcore by design) -- figures label them
  "SUPPLIED, not derived" until a content digest exists.
- 2026-08-13 (viz): v16 ledger + heatmap rendered, all magnitudes derived from the
  manifest (its own hand-typed "46 deaths" literal self-caught when the derivation
  replaced it -- lesson 4 landing on its preacher, their words). FIGURE-INTEGRITY
  CONVENTION adopted for every session: a check that cannot be evaluated on the current
  case prints "MISSING, NOT RESOLVED" in red and names the absent experiments; prior-
  case conclusions are never carried forward silently. OPEN VERIFICATIONS on v16 (held
  on v12, treated as unknown until run): (a) coupled == energy composite; (b) the
  Option A vs A-prime sign disagreement. Both need energy_full_real,
  energy_cost_push_real, energy_price_tfp_real on v16 -- same runs as the queued
  matched-leg pair; one decision covers all.
- 2026-08-13 PAUSED (Marcelo): CLEWs-PHL v18 is coming soon and includes land changes.
  Consequences until it lands: the evidence-base decision (v16 proposed) is REOPENED;
  the queued v16 component runs / matched-leg pair are ON HOLD (run them on whichever
  base the papers will quote); v16 results stand as current-best and all v16 figures
  carry their baseline on-face, so nothing needs retraction if v18 supersedes. When
  v18 arrives, the migration path is the proven one: checksum-verify, install copy,
  one-pass calibration (verify the land block digest FIRST -- v18 changes land, so the
  byte-identical shortcut that justified water factor 14.4128 and the crop factors MUST
  be re-checked, not assumed), moratorium script, land pin + EACR only if v18 does not
  already carry them, run button gates.
- 2026-08-13 (during pause) DELIVERABLE REORIENTATION (Marcelo): the run output shows THE
  SCENARIO'S IMPACT AND THE COUNTRY'S TRENDS -- CO2e, health, power system, land (CLEWs
  side) and economic trends (OG side). NO calibration-version comparisons in the
  deliverable. Built and proven on v16: experiments/scenario_impact_charts.py generates
  the impact deck from any (base, reform, coupled) triple -- 1 generation-mix
  transformation, 2 national CO2e vs no-policy path (incl. land conversion, cumulative
  avoided annotated), 3 PM2.5-and-lives, 4 what-gets-built capacity bins, 5 macro
  GDP/C/w transition. Incidence, cohort, and fiscal figures reuse the coupled deck.
  Regenerates on v18 with one command once its runs exist.
- 2026-08-13 AUTHORING SESSION CHARTER v2 (corrected: there is SUBSTANTIAL existing
  authoring in the repo -- the session ADVANCES it, never restarts). The corpus, all on
  paper/linkages-intro: paper-intro/ IS the short paper, drafted end to end (only the
  conclusion is a 9-line stub); paper/ IS the technical paper (sections 1-7 drafted,
  8-9 + appendix stubs); presentation/mechanisms.tex IS the deck (18 frames, session A
  mid-rebuild of the channel explanations). LANES, non-colliding with session A's claim
  (channel sections 04-05, channel notes, deck channel frames):
    1. paper-intro/: refresh 05-illustration and 06-policy with the final-evidence-base
       results (derive-don't-retype; v18-swap discipline); write 07-conclusion.
    2. paper/: fill 07-results from the attribution table + impact deck; draft
       08-discussion, 09-conclusion, 10-appendix. Sections 01-06 are session A's --
       patches to those route through the coordinator.
    3. Deck: results/impact frames (the scenario story: sankey, mix, CO2e-by-source,
       lives+working-time, macro) proposed as a block to session A via COORDINATION.md,
       since mechanisms.tex is their artifact -- they integrate or delegate the block.
  WORKSPACE: own worktree (~/Projects/ogclews-link-writing), branch
  writing/results-and-closing off paper/linkages-intro. BINDING: COORDINATION.md
  register; figure-integrity conventions; emit-only carbon + levelized-cost wording;
  comparative-brief section 8 blockers (deflator: magnitudes as relative changes until
  audited); every quoted magnitude names its evidence base and derives from run
  artifacts where possible. INPUTS READY: impact deck scripts (+.venv-viz sankey),
  coupled deck, attribution + caveats (section 15), comparative brief, channel notes,
  both papers' TeX, the review exchange (register exemplars).
- 2026-08-13 authoring Q&A (decisions): (1) v16+ evidence citations stay GENERIC in prose
  ("the archived run record"); exact filenames live in the appendix (authoring lane) --
  no unilateral extension of the golden.json code-name exception; proposed to session A
  via the log if they prefer a named exception. (2) A GOLDEN RE-BLESS on the final
  evidence base is QUEUED (stack session runs it after the v18 decision); until then the
  papers scope "regression-locked" to v9 explicitly. (3) The v9 morbidity-transition
  narrative is DROPPED -- it predates the 2026-08-11 demographics fixes and describes an
  artifact. (4) Mixed-base presentation confirmed: headline v16, decomposition v12,
  bases named on-face, re-verification note; until the matched legs run on the final
  base. (5) Figure split: methods paper = the coupled deck (mechanism figures); impact
  deck (sankey, CO2e-by-source, lives+working-time) = short paper + presentation.
- 2026-08-13 authoring milestone: paper/ 07-results REBASED to v16 and compiled clean
  (22pp, zero undefined refs) on writing/results-and-closing (b033c6c generator with
  missing-not-resolved TeX flags + sign-flip check; 9bccb32 the section). Two manuscript
  defects found and routed to session A via COORDINATION.md (stale 95-lives figures at
  file:line; regressivity result-claims unsupported on v16 -- incidence is NON-monotone
  there). QUEUED ANALYSIS (stack session): why is the v16 coupled incidence non-monotone
  (middle groups +2.9% consumption, 90-99% -1.6%, poorest ~0; energy budget shares ~1.4%
  flat)? Report-not-explain until investigated. Investment-figure semantics confirmed:
  channel_inputs shows RAW pre-scoping CLEWs signals (gross power investment ~30% GDP
  cumulative); the channel transmits only the public-infrastructure delta (0.0097%).
