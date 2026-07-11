# Idea #02 — the residual loop controller (iterate OG ⇄ CLEWS to a fixed point)

**Opened:** 2026-07-10 · **Origin:** our own loop-closure design (map §4) + the Rev-4.2 spec's §10
loop mechanics, each element to be adopted or rejected on merit. **Build branch:**
`channel/loop-controller` (STACKED on `channel/clews-run-seam` — depends on the proven driver;
merges only after/with it). **Status: ASSESSING.**

## What it is

Upgrade `framework.run`'s existing-but-inert multi-pass skeleton into a real iteration controller:
wire the `clews_runner` hook to `clews_driver` (idea #01), measure per-exchange **residuals** (raw
model disagreement, in logs), apply **per-commodity damping**, and treat every non-converged ending
as a **named, reported finding** (LP infeasible / macro explosion / gain>1 / multiple equilibria)
rather than an error.

## Merit questions to answer before building (our judgment, not the spec's)

1. **Value:** what question does iteration answer that one-pass cannot, for OUR channels TODAY?
   Candidate: the `coupled` run's energy price is currently taken from a CLEWS solve that never saw
   OG's demand response — one loop pass quantifies how wrong that is (the spec claims 3–10 iterations
   matter; MESSAGE-MACRO lore agrees; verify on PHL, don't assume).
2. **Technical:** which exchanged quantities actually MOVE in our current channel set? If the only
   live og→clews artifact is a near-inert demand ratio (`emit_energy_demand` mean ratio ≈ 1), the
   loop converges trivially and adds nothing until the A1-style demand rebuild (map 2.1) exists —
   possibly idea #02 should be REORDERED after 2.1, or scoped as "controller + minimal A1 slice".
   ⇠ this is the load-bearing unknown; measure the live ratio first.
3. **Feasibility facts already in hand (from idea #01):** per-iteration CLEWS solve ≈ 3.5 min
   (window-patched); reproducibility is economic (0.002 %), NOT bit-level — so convergence tolerance
   must sit well above vertex wobble (≥1e-3) or the loop chases solver noise; historical years must
   never be patched; MUIOGO subprocesses need process-group ownership. OG side: a reform solve is
   the cost driver (~minutes to hours) — warm-starting (`og_runner` continuation) is the critical
   optimization; iteration count budget matters.
4. **Economic:** damping and convergence-on-residuals have identical fixed points to the undamped
   loop (spec's argument — verify the algebra ourselves); per-commodity λ with lower food default is
   moot until a food leg exists — start with the single energy exchange.
5. **Empirical test (design before building):** on PHL v9 — run the loop with the energy exchange
   (OG demand path → CLEWS SAD → CLEWS LCOE → OG price channel → …): (a) does it converge, in how
   many passes, at what residuals; (b) does the converged coupled answer DIFFER measurably from the
   one-pass answer (the value question); (c) does a deliberately pathological setup (gain>1) get
   REPORTED as non-convergence rather than looping forever. NB: involves repeated OG solves — ask
   before launching the full empirical run.

## Prior decisions that bind this idea

Link owns the loop (architecture decision 2026-07-10); one idea at a time; assessment must pass
before code; the seam's empirical facts (above) are constraints, not suggestions.
