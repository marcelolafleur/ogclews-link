# How a user creates a scenario — UX design note

**Status:** design exploration (no code yet). **Branch:** `scenario-builder-ux`.
**Builds on:** `scenario-builder-and-policy-levers.md` (the *backend* seam — generic levers, the
declarative choice catalog, guardrails). That note answered "what primitives does a scenario reduce to."
This note answers the question it deferred: **how does a human actually build one, and what do we copy
from the tools that already do this well.** **Cross-refs:** `og-clews-denovo-analysis.md` (channels),
the viz lane (results comparison is the back half of the loop).

## The question

A scenario in this model is already a small object: `Experiment(name, [(channel, options)…], description)`
— a list of channel activations with options, diffed against a baseline (see `framework.py`). The hard
part is not representing it; it's letting a non-author *explore the space* of scenarios without writing
Python. That space is combinatorial: {6 channels} × {options each} × {target industry/resource} ×
{revenue use} × {baseline} × {time profile} × {single-run vs compare-set vs sweep}. The design job is to
make that space **approachable, hard to get wrong, and reproducible** — and to do it for users who range
from "show me a clean-air health story" to "I want a carbon tax recycled three different ways."

## What the best analogs actually do

I looked at four tools that solve a version of this problem, picked for how directly they map to us.

**En-ROADS (Climate Interactive + MIT Sloan)** — *the closest analog*: an integrated energy/climate
(and now land/health) model, exactly our shape, exposed to the public. Lessons:
- **Curate the levers; never expose raw model parameters.** A huge integrated-assessment model is
  distilled to **~19 sliders** in ~6–7 groups (energy supply, carbon pricing & standards, transport,
  buildings & industry, growth, land/agriculture, carbon removal). The user never touches the thousands
  of underlying parameters.
- **Two-level progressive disclosure.** Quick mode = drag a slider, graphs move. Detailed mode = click
  the title → description, **numeric input with units, valid range, related graphs, and help**. Simple by
  default, full control one click deeper.
- **Always start from a live baseline**, never a blank page. The default scenario is on screen before you
  touch anything.
- **Immediate feedback** (100+ output graphs update as you drag) and a *"replay last change"* that
  re-runs your last move so you can *see* the causal effect.
- **Scenarios are shareable URLs** that preserve every setting and the graphs you were viewing.

**PolicyEngine** — *the domain twin*: a tax/benefit **reform** builder (reform = a diff from current law,
exactly our baseline-vs-reform). Lessons:
- A reform is a **stack of provisions** (parameter changes); you add them one at a time and they compose.
- **Searchable parameter metadata** — every parameter carries a label, the legal-code reference, type and
  range (their "API explorer"). The metadata *is* the UI.
- **Baseline vs reform is the spine**: it computes the reform, computes current law, and reports the
  *difference* at two altitudes — **population** (budget, poverty, inequality) and **a single household**.
- Explicitly **multi-tiered**: the same product serves "policy novice" and "researcher running
  multi-scenario analyses" — different doors, one engine.

**The Fiscal Ship (Brookings/Wilson Center)** — *the engagement lesson*: a budget game.
- **Goal-first, not parameter-first.** It asks you to pick your *goals/values* first, *then* choose among
  100+ policy options to hit a target (stabilize debt/GDP). Scenarios are framed as **questions with a win
  condition**, not as forms to fill. This is why it's sticky where a parameter sheet is not.

**Anaplan / Causal (enterprise scenario planning)** — *the comparison lesson*:
- Scenarios are **first-class, named, forkable objects**: "build a new one with one click," duplicate and
  tweak, then **compare side-by-side**. The unit of work is a *set* of scenarios, not one.

The convergence across all four is striking, and it's the spec:

| Pattern | En-ROADS | PolicyEngine | Fiscal Ship | Anaplan |
|---|---|---|---|---|
| Start from a working baseline, never blank | ✅ | ✅ (current law) | ✅ | ✅ |
| Curated levers, not raw parameters | ✅ (19) | ✅ (provisions) | ✅ (~100 options) | ✅ |
| Progressive disclosure (simple → expert) | ✅ | ✅ (tiers) | — | ✅ |
| Defaults that make a sound scenario | ✅ | ✅ | ✅ | ✅ |
| Edit a *diff* from baseline | ✅ | ✅ | ✅ | ✅ |
| Goal/question framing | — | partial | ✅ | partial |
| Scenarios are saved/named/shareable/forkable | ✅ | ✅ (URL) | ✅ | ✅ |
| Compare scenarios side-by-side | ✅ | ✅ | — | ✅ |
| Live feedback while editing | ✅ | ✅ | ✅ | ✅ |

## Where we differ — the one constraint that changes the design

En-ROADS and Anaplan recompute in **milliseconds**; that's what makes drag-a-slider-watch-graphs-move
magical. **We can't.** A full TPI solve is minutes × parallel workers. We cannot copy live-drag feedback
for the full model, and pretending otherwise would be the central design mistake. Two honest adaptations:

1. **Split "build" from "run."** *Building* a scenario (assembling channels/options, validating the combo)
   must be instant and guardrailed. *Running* it is explicitly asynchronous — a queue, a progress
   indicator, and the provenance manifest we already emit (`ogclews_manifest.json`). It's a *render*, not
   a *preview*.
2. **Buy back fast feedback elsewhere.** Three cheap proxies for En-ROADS's live graphs:
   - **Steady-state preview.** The lever validation already runs in SS ("a 20% energy ITC → +5.0% energy
     capital, GDP ≈ 0"; see `scenario-builder-and-policy-levers.md`). SS is fast and gives a *directional*
     read before you commit to a TPI run.
   - **Precomputed template gallery.** Ship the named scenarios with results already cached, so the common
     80% is *instant to view* — the user only pays solve cost when they fork and change something.
   - **Marginal-contribution layering.** `ACROSS_STEPS` already shows each channel's incremental effect;
     surface that as the "what does adding this channel do" feedback.

Counterintuitively, we have a **head start** on the hardest part. En-ROADS spent years distilling an IAM
down to 19 levers; PolicyEngine's whole UX problem is taming thousands of parameters. **Our curation is
already done** — the 6 channels + the two generic policy levers *are* the slider set. We should never
expose raw OG-Core parameters. We're closer to a good UX than either tool was at the start.

## Recommendation: three doors, one representation

Not "UI options *or* templates" — both, plus a config door, as **three views over the same object**. The
single underlying representation is the existing `Experiment` JSON. Each door emits it; each door can
re-open what another produced (this is exactly how PolicyEngine makes a clicked reform and an API reform
the same object). Pick your door by how much control you want:

**Door 1 — Template gallery (the front door, ~80% of users).** Named, pre-assembled scenarios framed as
**questions**, Fiscal-Ship style, not as parameter sets:
- *"Revenue-neutral carbon tax — who pays?"* · *"Clean-air health dividend"* · *"Energy transition
  (structural): capex + operating cost + carbon tax"* · *"Carbon tax: transfers vs infrastructure vs
  deficit"* (a 3-run **compare-set**, not one run).
- One click → **view precomputed results instantly**, or **"fork & tweak"** → drops you into Door 2 with
  everything pre-filled. The existing `EXPERIMENTS` / `ACROSS_STEPS` are the seed gallery.

**Door 2 — Guided builder (the workbench, intermediate users).** En-ROADS quick-mode + PolicyEngine
provisions:
- Toggle **channel cards** on/off. Each enabled channel shows its **1–3 key options** with defaults
  pre-filled and plain-language labels; everything else is collapsed behind **"Advanced."**
- Selectors that don't apply are **disabled with a reason** (target industry greyed out on a
  single-industry model; agriculture/water greyed until calibration supports it — the separability
  guardrail).
- **Live guardrails** as you assemble (no double-counting a cost through investment *and* Z *and* tau_c;
  "recycle or it's a tax"; magnitude flags) — see the guardrail list in the backend note.
- A **"diff from baseline"** panel always shows what you've changed. Output is the `(channel, options)`
  list.

**Door 3 — Expert / config (researchers, reproducibility, automation).** The raw `Experiment` JSON / an
`experiments.py` entry / `python -m ogclews_link run <name>`. Full access including the generic
`policy_levers` by industry index. Hand-edited JSON re-opens cleanly in Door 2. This door already exists —
it's today's CLI.

**Above all three, a goal-first overlay (optional, Fiscal-Ship).** Let a user start from an *objective*
("minimize the bottom-decile burden of a carbon tax") that maps to a template + the **metric to watch**.
Even with no auto-optimization, framing scenarios as questions beats framing them as forms.

**Scenarios are first-class objects (Anaplan).** Saved, named, **duplicated/forked**, queued to run, and
**compared side-by-side** once results exist — the comparison view is the hand-off to the viz lane. The
manifest is the reproducibility backbone.

## The variation taxonomy — every axis the UI must cover

So we design for the real space, not a happy path. Each axis maps to a control and a door:

| # | Axis of variation | Control | Door |
|---|---|---|---|
| 1 | Which channels (of 6+) | channel toggle cards | 2 |
| 2 | Options per channel (shock size, price source, recycle…) | key options inline; rest under Advanced | 2 |
| 3 | Target industry / resource (energy now; ag/water later) | selector, **separability-gated** | 2 (advanced) |
| 4 | Revenue use (transfers / public-investment / govt-consumption / deficit) | dropdown | 2 |
| 5 | Magnitude source (CLEWS dual vs manual %) | toggle, dual = default | 2 (advanced) |
| 6 | Time profile (phase-in years, persist, smoothing) | numeric, defaulted | 2 (advanced) |
| 7 | Baseline (current calibration; later alt baseline / alt country) | baseline picker | 1/3 |
| 8 | **Run mode** (single / cumulative-layering / **compare-set** / sweep) | top-level mode switch | 1/2 |
| 9 | Country / onboarded model (PHL today; registry generalizes) | model picker | 1/3 |

Axis 8 is the one most teams forget: the common research output is a *comparison*, so "build a set of
scenarios that vary one knob" (the carbon-tax-three-ways template, a sweep over shock size) should be a
first-class mode, not three manual runs.

## What this implies we should build first (smallest useful slice)

1. **A declarative catalog with human metadata.** Today the channel options live only in `apply()`
   signatures (the backend note's choice-catalog table is prose, not machine-readable). Promote it to a
   JSON/YAML: per channel → per option → `{label, description, type, default, domain/range, units,
   depends_on, conflicts_with, why_it_matters}`. **Every door reads this.** It's the single highest-
   leverage artifact and it's mostly transcription of what already exists. *(Built on this branch:
`ogclews_link/scenario_catalog.json` + the `scenario_catalog.py` loader/validator + a sync test; see
`scenario-catalog.md`.)*
2. **A template library** that emits `Experiment` JSON (formalize `EXPERIMENTS`/`ACROSS_STEPS` as the
   gallery, add the question-framed titles and the compare-sets).
3. **The build/validate layer**: assemble `(channel, options)`, run the guardrails as pure validation,
   show the baseline diff — *no solve*. This is Door 2's engine and it's all cheap.
4. **Defer live feedback to SS-preview + precomputed templates**, and treat the full run as an async job.

MUIOGO (the GSoC UI) renders Doors 1–2 from the catalog + template library and shells out to the CLI for
the run (the seam in the backend note, §4). Door 3 is the CLI we already have. Nothing here needs new
solve machinery — it's a declarative layer plus an honest async-run UX over the channels and levers that
already exist.

## Open questions to validate next

- **Slow-solve UX**: is an SS-preview trustworthy enough to gate a TPI run, or do users always want the
  full path? (Decides how much we lean on SS vs precompute.)
- **Precompute budget**: how big a template gallery can we afford to keep results cached for, and refreshed
  when calibration changes?
- **Tier priority**: build Door 1 (gallery) or Door 2 (builder) first? Gallery ships value sooner and
  needs only the template library + cached results; the builder needs the full catalog + guardrail layer.
- **Compare-set ergonomics**: how does a user express "vary this one knob over these values" without it
  becoming a combinatorial footgun (and how do we cap/queue it)? Ties directly to the viz comparison view.
