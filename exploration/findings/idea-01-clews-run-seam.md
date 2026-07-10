# Idea #01 — the CLEWS re-run seam (write-back → solve → re-read)

**Assessed:** 2026-07-10 · **Origin:** our own loop-closure design (docs/design + the map §4); the
Rev-4.2 spec's OSeMOSYS-adapter is the same idea homed differently. Assessed on its own merits below.
**Build branch:** `channel/clews-run-seam` · **Status:** assessment PASSED → building.

## What it is

A link-side driver that (1) writes a set of OSeMOSYS parameter changes into a **copy** of a MUIOGO
case, (2) triggers MUIOGO's own datafile-generation + solve for a named caserun, (3) re-reads the
result CSVs with the link's existing readers. It is the missing consumer of everything the `emit_*`
channels produce, and the prerequisite for empirically testing ANY og→clews idea.

## Merit assessment (ours)

**Value to the tool — decisive.** Today `emit_energy_demand` / `emit_carbon_penalty` /
`emit_discount_rate` write artifacts nobody consumes; the Runner's multi-pass loop "honestly degrades
to one pass." Every og→clews candidate in the map (§2) and the whole loop program (§4) is untestable
without this seam. It also unlocks one-shot empirical questions that need no loop at all ("write the
cap, read the E8 dual").

**Technical sense — yes, with the house idiom.** Verified mechanics (read from MUIOGO source, not the
spec): the solve path is `DataFile(casename).generateDatafile(caserunname)` +
`DataFile.run(solver, caserunname)` (`API/Classes/Case/DataFileClass.py:625,2070`) — plain Python,
no Flask session dependence (the `/run` route takes casename in the body), results land under
`DataStorage/<case>/res/<caserunname>/csv/` (the exact layout `muiogo_run`/`country.clews_scenario_dir`
already read). MUIOGO's env exists at `~/.venvs/muiogo` (verified importable). Design: **subprocess
MUIOGO's own interpreter** with a small driver script (JSON-in/paths-out), mirroring `og_runner` —
the link's established cross-env idiom; no MUIOGO deps enter the link env.

**Economic sense — n/a (infrastructure).** No economic content of its own; it transports whatever
economics the channels encode. The honesty requirement is provenance: every patched parameter and the
solver/caserun identity must land in the run manifest.

**Feasibility — verified, with one real risk.** The write side must edit the case's input JSONs,
which key technologies/commodities by **opaque per-case IDs** (e.g. `COM_*`, `EMI_0`), not by code
names — the driver must translate via the case's own registry (`genData.json`, which we've parsed).
Scope control for v1: support the parameters the emit channels actually produce
(`SpecifiedAnnualDemand`-style demand scaling, `EmissionsPenalty`, `AnnualEmissionLimit`,
`DiscountRate`) rather than a general patcher. **Never mutate the live case: operate on a copy.**

**Empirical test (PHL, defined before building):** copy `Philippines_v9`; scale one demand commodity
(household electricity) by a known factor in a new caserun; solve with CBC via the driver; re-read
production/cost CSVs; assert the change propagated with the right sign and rough magnitude (more
demand → more generation, higher total cost). Then the negative control: an untouched caserun
reproduces the original results (bit-comparable CSVs where the solver is deterministic).

**Died-if:** the case-copy solve had failed to reproduce baseline results (would mean MUIOGO runs are
not reproducible from the case store alone), or datafile generation had required live-session state.
Neither is the case per the code read; the empirical test will confirm.

## Verdict

**Worth building — highest-leverage item in the program.** Not because the spec says so: because our
own map has three og→clews channels and a loop that are unfalsifiable without it. Risks are scoped
(ID translation, case-copy discipline); the empirical test is crisp.

## Empirical log (2026-07-10, PHL Philippines_v9, CBC)

The seam works — the driver ran MUIOGO's own pipeline headlessly on case copies from the first
attempt. Every iteration below was a REAL discovery, not a code bug hunt:

1. **Result-CSV naming:** the Rev-4.2 spec says `ProductionByTechnologyAnnual`; this MUIOGO exports
   `ProductionByTechnologyByMode`. First verdict pass crashed by trusting the spec — fixed against
   the actual export (the discipline holds: never believe the spec).
2. **Silent zero-row no-op (now a loud error):** `PHL_HOU_ELE`'s SAD rows are all zero — household
   load rides **`PHL_HOU_ELEF`** (9,978 PJ over 34 yrs, SC_0). The patcher initially "succeeded"
   scaling zeros; it now raises on all-zero rows and names the commodities that actually carry
   demand. General lesson for every demand-side channel: **the `*F` final-demand code is the
   coupling surface**, not the delivered-commodity code.
3. **Old-MUIO case under today's MUIOGO (the user's caution, tested):** the Jan-2026 case
   regenerates **functionally identically** — all 54 datafile param blocks value-identical
   (differences: block order, CRLF, comments). The small orig-vs-today result gap
   (production −0.12%, var-op-cost −0.53%) is **alternative optima**: var-op-cost is ~0.03% of the
   investment-dominated objective, and `AnnualizedInvestmentCost` matches to +0.0001%. So no
   data-structure misreading detected for Base_v9 — but structures Base_v9 doesn't exercise
   (storage, UDCs, PEP's SMR chain) remain untested; the caveat stands.
4. **Historical years are load-bearing:** scaling demand ×1.1 in ALL years (including calibrated
   2020–2024 history pinned to actual generation) made the LP pathological — CBC ground >1 h vs
   ~4 min healthy. **Patch the exchange window only (2026+)**, exactly what the coupling does
   anyway. Also caught: `subprocess.run`'s timeout kill orphaned the CBC grandchild at 100 % CPU —
   the driver now owns the process group and kills it on timeout.
5. Determinism (same store + same MUIOGO solved twice) and the window-patched treatment: verdicts
   from round-trip v3 — recorded below when complete.
