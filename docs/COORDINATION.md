# Coordination — who is doing what, across machines and assistants

**Purpose.** Marcelo works this project from more than one machine, with an AI assistant on
each. This file is how those sessions talk to each other. Anything another session needs to
know that is **not** obvious from the code or the git log belongs here.

**This file lives on `main`** so every worktree and every branch can reach it. When you
change it from a feature branch, commit the change **on `main`** (or cherry-pick it there)
— otherwise the next session on another branch will not see it.

**Protocol.** Before starting work: `git fetch` + read this file top to bottom. After
finishing a chunk: add a dated entry under *Log*, update *Current state* and *Claims*, and
push. Keep entries short and factual — decisions, blockers, and warnings, not narration.
Do not delete another session's entry; append a correction under a new date.

---

## Repository map (one repo, several worktrees)

`github.com/marcelolafleur/ogclews-link` (private). Branches in play:

| Branch | Holds | Notes |
|---|---|---|
| `main` | trunk: the link package, channels, tests — **and this file** | pushed, current |
| `research/env-accounting` | **this branch** — IEEM/CLEWs-IO assessments, PHL land/water diagnostics, `env_accounts.py`, reference PDFs index | renamed from `research/ieem-comparative-assessment` (2026-08) — if your local branch still has the old name, rebase onto this one and repoint the upstream |
| `paper/linkages-intro` | **all writing**: methods paper (`paper/`), positioning draft (`paper-intro/`), the mechanisms deck (`presentation/`), channel notes, the review conversation | rebased onto main; force-pushed 2026-08-04 |

**Build outputs are never committed.** No PDFs in git — compile from the `.tex`
(`latexmk -pdf main.tex` in `paper/`; `latexmk -pdf mechanisms.tex` in `presentation/`).

## Current state (update me)

- **2026-08-04 — methods paper**: §1–§7 drafted and revised; §8 discussion, §9 conclusion,
  and the appendix are still stubs. Register rules are strict, see *Conventions*.
- **2026-08-04 — deck** (`presentation/mechanisms.tex`, on the writing branch): rebuilt in
  quiet academic style, 21 slides. Being rewritten **one channel at a time** after a
  presentation where the channel explanations did not land. Channel 1 (energy price) is done.
- **This branch**: comparative assessments complete; PHL land/water defects diagnosed;
  reference PDFs indexed in `docs/references/README.md`.
- **2026-08-13 — ieem worktree** (`experiment/forest-conversion-carbon`, pushed @ 0770258):
  full state in `docs/design/deliverables-plan.md` and the cross-assistant brief
  `docs/design/coordination-ieem-v16-2026-08-12.md` (divergence table + four asks) on that
  branch. Headlines: (1) three link correctness fixes main does not have — two missing
  `income_percentiles` (the health mortality shock silently skipped until 2026-08-11),
  the clean-marginal health application, mortality-only clipping; (2) released ogcore
  0.19.1 cannot solve any `tau_payroll != 0` model (PSLmodels/OG-Core#1199, filed; local
  fixed build in use); (3) `Philippines_v16_CALIBRATED` staged with recalibration + 2027
  coal moratorium + both-sides land pin + conversion-carbon accounting (~25% of national
  CO2e); single-command run staged, awaiting Marcelo; (4) open-work item 1 (matched
  cumulative decomposition) HAS AN ANSWER on v12: an 11-experiment battery with
  real-price variants — coupled == energy composite exactly (identity, carbon is
  emit-only, confirming the 2026-08-04 fact), cost-push -0.496 vs household -0.026 of
  the -0.525 total.

- **2026-08-13 — writing branch is committed and pushed, clean tree.** `paper/linkages-intro`
  @ `87382bb`: the methods paper (`paper/`) through the scope/evidence revision, the
  positioning paper (`paper-intro/`) fully rewritten (9pp, compiles clean), the deck
  (`presentation/mechanisms.tex`, 21 slides). **Built artifacts are now untracked** —
  `mechanisms.pdf`, `mechanisms-reference.pdf` removed from git, and `*.zip` (Overleaf
  hand-off bundles) ignored. Compile from the `.tex`.

## Claims — say what you are working on, to avoid collisions

| Since | Who / where | Working on | Touching |
|---|---|---|---|
| 2026-08-04 | this machine (session A) | channel-by-channel rebuild of the explanations | `paper/linkages-intro`: `docs/design/channel-notes/`, `paper/sections/04–05`, `presentation/mechanisms.tex` |
| 2026-08-13 | ieem-worktree machine (v16/stack session, coordinator of 3 local peers) | v16 coupled run (IN FLIGHT: both CLEWs solves optimal, gates green, OG coupled solving); link correctness fixes; deliverables inputs | `experiment/forest-conversion-carbon`; MUIOGO DataStorage `Philippines_v16*`; OG-PHL `calib/multi-industry-remittances`; local ogcore build `integrate/v0191-plus-1189` |
| 2026-08-13 | ieem machine, channel-viz session ("Graphics for ogclews-link") | the channel-map ledger figure for the deck (AST-derived from channels.py; baseline named on-figure) | own worktree `~/Projects/ogclews-link-viz`, branch `viz/channel-diagrams` off main; nothing pushed yet |

Add a row when you start; remove it when you stop.

## Conventions that are easy to violate

**Writing register** (learned the hard way; violating these means a rewrite):
- The methods paper **explains the methodology and no more** — no contribution-claiming,
  no status-report paragraphs, no "distinctive/signature/invisible-to-X" flourishes.
- **No definitional scaffolding** ("A *signal* is…") and **no code-file names** in the
  manuscript — no `channels.py`, no function names. The one exception is
  `results/golden.json` as the cited evidence record. Code anchors live in the channel
  notes and speaker notes.
- Explanations **trace the mechanism**: state the constraint, follow who pays / what
  happens next, name the dead end, then give the design as the consequence. The worked
  exemplar is `docs/design/channel-notes/01-energy-price.md` (on the writing branch).
- Author name is **Marcelo LaFleur**.

**Facts that are easy to get wrong** (verified 2026-08-04):
- The Philippine CLEWS reform carries **no carbon price** — `EmissionsPenalty` is empty in
  both `Base_v9` and `PEP_v9`. The coupled run **emits** a \$50/tCO2 artifact for a future
  re-solve; **no carbon price acts in the reported numbers**. Never write that the coupled
  run "applies" one, and never claim the LCOE embodies one.
- The standalone `energy_price` experiment is the **household wedge only**; the composite
  (wedge + cost-push) is what the coupled run transmits. So the standalone rows and the
  coupled run are **not matched treatments** — the −0.138% vs ≈−0.02% gap is not yet
  attributable to channel interaction. A matched cumulative decomposition is the top
  open run.
- The golden record locks **macro aggregates only** — not emitted artifacts, not sectoral
  detail, not the LCOE path.
- The commodity-balance shadow price is **degenerate** in this case; the deployed price is
  the levelized cost. Never call it a marginal price without the caveat.

**Model runs**: follow the preflight — print branch + HEAD of every repo, and verify what
the interpreter actually imports resolves inside the intended worktree. A result that
reproduces a known-buggy number is contamination evidence, not coincidence.

## Reference PDFs

On `research/env-accounting`, `docs/references/` holds the comparison papers. **They are
gitignored** (licensed copies) — each machine keeps its own; `docs/references/README.md`
on that branch has the fetch URL for each, so the set rebuilds in a minute. Currently
missing: the Khaleghian 2025 *Energy Nexus* paper (gold OA, but ScienceDirect blocks
scripted download — fetch it in a browser).

## Open work, in priority order

1. ~~Matched cumulative decomposition~~ — **answered on v12** by the ieem/v16 session
   (coupled == energy composite exactly; cost-push −0.496 vs household −0.026 of −0.525).
   Remaining: the paper still cites the **v9** golden, so either port that battery to v9 or
   move the paper's illustration to v12; until then §7 keeps its "not attributable" wording.
2. Channel-by-channel explanation rebuild (channel 2 = the capital pair, next).
3. Regression tests for the emitted artifacts (demand, discount rate, carbon paths).
4. Capital-intensity re-run on the re-blessed baseline; store sectoral evidence.
5. Document the dual-degeneracy test; LCOE construction documentation for §6.
6. §8 discussion, §9 conclusion, appendix.
7. Before any submission: systematic ESM↔OLG literature search; calibrate the unit bridge.

## Log

- **2026-08-13 (session A, writing machine)** — Committed and pushed everything on the
  writing branch (see *Current state*); untracked the built PDFs and ignored `*.zip`.
  Read the ieem/v16 entry: noted that the health mortality shock was silently skipping
  before the 2026-08-11 fix, so **every health number now in the paper predates it** and
  must be re-blessed before submission; and that the v12 battery answers open item 1 but
  on a different scenario version than the paper's v9 golden. Next here: channel 2 (the
  capital pair) in the mechanism-traced register.
- **2026-08-04 (session A)** — Reconnected the research worktree after the branch rename;
  rebased the two reference-library commits onto `research/env-accounting`. Added
  `docs/references/` (was `docs/design/pdfs/`) with the PDF index. Created this file
  (first committed on the research branch, then moved here to `main` so every branch
  sees it). On the writing branch: paper de-inflation passes, companion-paper mentions
  removed, channel 1 rewritten across paper/deck/notes.
- **2026-08-13 (ieem worktree, v16/stack session)** — Read this file; adopted the protocol.
  Pushed our branch (0b14e1f→0770258) with: the demographics/health fixes (see Current
  state — session A should verify whether the golden's −95.4 health number predates them),
  ogcore #1199 + the local fixed build, the staged v16 case and run button, the sourced
  land-conversion cost (implementation deferred: case data cannot express one-way change
  costs; the symmetric workaround is the falsified pattern), and the matched real-price
  decomposition on v12 answering open-work #1 on that evidence base. Divergences to
  reconcile before submission (v9 vs v12/v16; two GBD exports; ogcore pins) are tabled in
  `docs/design/coordination-ieem-v16-2026-08-12.md` with four asks. Our stack sits on the
  pre-rename branch history; the shared worktree branch will NOT be rebased (pushed,
  multi-session) — reconcile at merge time. The five coupling diagrams close our
  channel-diagram gap; we reuse them.
- **2026-08-13 (ieem machine, for session A)** — Defect report on a committed artifact,
  found by the channel-viz session: `presentation/diagrams/channels.tex` (main) labels the
  energy channel's CLEWS side "commodity-balance *dual* — marginal electricity price" —
  the exact wording this file's own facts section forbids — draws the carbon wire with
  symmetric arrowheads captioned "one price, set on both sides" (it binds nothing in a
  one-pass run), shows 7 channels against the registry's 11, and uses three stale names
  (discount_rate, demand, carbon). Yours to fix per artifact ownership; the viz session's
  ledger supersedes it for the deck meanwhile. Related paper-grade caveat from the same
  review: 94% of the coupled headline rides on the cost-push leg (a reduced-form proxy by
  channels.py's own docstring); the structural TFP alternative flips the sign (+0.026 vs
  -0.496). Any quoted headline should name the transmission. v16 first solves: both
  optimal, moratorium and offshore cap bind as designed, 1,474 Mt conversion carbon booked.
