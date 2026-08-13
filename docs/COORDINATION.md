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

## Claims — say what you are working on, to avoid collisions

| Since | Who / where | Working on | Touching |
|---|---|---|---|
| 2026-08-04 | this machine (session A) | channel-by-channel rebuild of the explanations | `paper/linkages-intro`: `docs/design/channel-notes/`, `paper/sections/04–05`, `presentation/mechanisms.tex` |

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

1. Matched cumulative decomposition reproducing the current coupled run.
2. Channel-by-channel explanation rebuild (channel 2 = the capital pair, next).
3. Regression tests for the emitted artifacts (demand, discount rate, carbon paths).
4. Capital-intensity re-run on the re-blessed baseline; store sectoral evidence.
5. Document the dual-degeneracy test; LCOE construction documentation for §6.
6. §8 discussion, §9 conclusion, appendix.
7. Before any submission: systematic ESM↔OLG literature search; calibrate the unit bridge.

## Log

- **2026-08-04 (session A)** — Reconnected the research worktree after the branch rename;
  rebased the two reference-library commits onto `research/env-accounting`. Added
  `docs/references/` (was `docs/design/pdfs/`) with the PDF index. Created this file
  (first committed on the research branch, then moved here to `main` so every branch
  sees it). On the writing branch: paper de-inflation passes, companion-paper mentions
  removed, channel 1 rewritten across paper/deck/notes.
