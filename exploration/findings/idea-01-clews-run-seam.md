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
