# Channel-space exploration lane

**Branch:** `explore/channel-space` (off `main`) · **Worktree:** `~/Projects/ogclews-link-channels` ·
**Started:** 2026-07-10

## Charter

Map the **entire space of feasible coupling channels** between OG-Core and CLEWS/OSeMOSYS — both
directions (clews→og and og→clews), plus shared policy levers and loop-closure variants. A candidate
channel qualifies only if it is:

1. **Economically sensical** — a defensible mechanism and sign, entering the OG model where its
   equations actually carry the effect (verified against ogcore source, not assumed);
2. **Technically sensical** — a real signal exists on the sending side (a reform-differential CLEWS
   output, a solved OG output, or an honest external dataset labeled as such) and a consuming
   parameter exists on the receiving side;
3. **Feasible today** — implementable with the models as they are. *Minor* model changes may be
   flagged as such (grade B); *large* changes (e.g. energy-as-production-input CES in OG-Core,
   endogenous climate in CLEWS) are mapped for completeness but explicitly out of scope (grade C).

## Isolation rule

This lane stays independent of all other ongoing work (writing worktree, scenario lane, narrative
lane, trunk). Nothing here edits trunk code until a channel graduates via its own reviewed merge.
The previous exploration lane (`channel-exploration`, class-based prototypes + adversarial critique)
is **archived as pushed** — its knowledge is carried forward in `findings/`, its code idiom is
superseded by the trunk's function-based rewrite.

## Layout

```
exploration/
  README.md                          this charter
  channel-space-map.md               THE deliverable: the graded possibility map
  findings/
    2026-06-feasibility-v1.md        first exploration round (5 ideas + 2 discovered), pre-rewrite
    2026-06-adversarial-critique.md  distilled 119-finding critique of the v1 prototypes
    og-core-surface.md               evidence: every settable OG-Core parameter, classified
    clews-surface.md                 evidence: every readable/writable CLEWS/MUIOGO surface
  research-inbox/                    DROP RESEARCH DOCUMENTS HERE (see its README)
```

## Working discipline (decided 2026-07-10)

**Architecture decision:** `ogclews-link` owns the coupling loop (separate orchestrator); MUIOGO stays
the energy-model server, driven through its own endpoints/classes. The Rev-4.2 spec is a source of
HYPOTHESES, not truths.

**Per-idea pipeline — one idea at a time, each surviving on its own merits:**
1. **Assess** (here, `findings/idea-NN-<name>.md`): does it add value to OUR tool? technically sound?
   economically sound? feasible with the models today? What is the empirical test? Independent
   judgment — never "the spec says so".
2. **Build** on its own branch `channel/<idea>` off `origin/main`, in the single build worktree
   (`~/Projects/ogclews-link-build`); transform tests without solving, per the house idiom.
3. **Test empirically** on the PHL models (v9 case copies — never mutate the live case; CLEWS LP solves
   are minutes and run freely; OG solves are asked-first).
4. **Decide**: merge proposal to trunk, or record why it died. Branch deleted either way; worktree
   moves to the next idea.

Idea ledger: #01 CLEWS re-run seam (in progress) · #02 residual loop controller (blocked on #01) ·
then the map §6 shortlist, re-assessed one by one.

## Method

The space is constructed as a cross-product, then graded:

- **clews→og candidates** = {reform-differential CLEWS outputs} × {OG-Core settable parameters},
  each pairing requiring a coherent transmission story.
- **og→clews candidates** = {solved OG outputs} × {OSeMOSYS input parameters MUIOGO manages}.
- **policy candidates** = one exogenous lever applied consistently to both sides.
- Grades: **A** = buildable now · **B** = minor change needed (named) · **C** = blocked on a large
  change (out of scope, recorded so the map is complete) · **✗** = economically or honestly unsound
  (with the reason — several v1 ideas landed here after critique).
