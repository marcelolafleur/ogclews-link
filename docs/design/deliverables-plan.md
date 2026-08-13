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
| env-accounting / forest-carbon | COMPLETE, read-only consultant. Deliverables absorbed: §13/§14, stickiness menu, patch script | stood down |
| linkage visualization | presentation/diagram assets for the channels | active (identify: og-core-23 or muiogo-55) |

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
   attribution table; visualization session's assets (interface below).
4. **Comparison with IEEM / CLEWs-IO** — a section in both papers + slides.
   Inputs: docs/design/ieem-comparative-assessment.md (existing); env_accounts layer
   (IEEM-parity: land cover, biodiversity index, carbon damage, depletion — DONE, stage 0-1);
   the v16 emissions-coverage upgrade (conversion carbon now booked, ~25% of national CO2e —
   an explicit advantage over energy-only accounting); paper-comparative-assessment.md
   (STALLED workflow, resumable).

## Interface contract for the visualization session

- Channel definitions: `ogclews_link/channels.py` docstrings + `ogclews-link channels`
  (direction clews->og vs og->clews matters; emit-only channels bind nothing in one pass).
- Real numbers: `ogclews_runs/<experiment>/macro_table.csv` (v12 battery, 11 experiments,
  DONE) and `ogclews_runs_v16/` after the run. Attribution table in
  phl-calibration-decisions.md §15 (with the coupled==energy structural identity caveat).
- Figures: `ogclews_runs/coupled/figures/` — reuse or restyle, don't recompute.
- The stack fingerprint (what produced the numbers): og-clews-linked-run skill,
  "Fingerprint the stack" section.

## Status log

- 2026-08-11: file created. v12 battery complete (11/11); v16 case staged (calibration +
  moratorium + land pin + accounting variant); conversion cost sourced, implementation
  deferred; run button ready (experiments/run_v16_coupled.sh), awaiting Marcelo's "run".
