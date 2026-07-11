# Idea #03 — the demand rebuild (OG drivers → per-commodity CLEWS demand paths)

**Opened:** 2026-07-10 · **Origin:** map §2.1 (our #1 shortlist item); the Rev-4.2 spec's recipe A1
is the same idea — adopted element-by-element on merit only. **Build branch:**
`channel/demand-rebuild` (stacked on `channel/clews-run-seam`: the emitter is link-side, but its
EMPIRICAL test needs the proven driver). **Status: ASSESSING → building.**
**Pulled forward past idea #02:** the loop controller failed its value test with today's exchange
content; this idea CREATES the feedback content (see idea-02's assessment outcome).

## What it is

Replace the single near-inert activity ratio (`emit_energy_demand`, mean ≈ 1.002) with a rebuild of
each CLEWS demand commodity's annual path from OG outputs: for commodity f,
`D_new(f,y) = D(f,y₀) × IDX(driver_pc,y)^η_f × IDX(pop,y)^ν_f × (1−a_f)^(y−y₀)`, driver per
commodity (Y, an industry's Y_m column, or C), with a per-commodity elasticity config (B_D table).
Base-year levels stay exactly as the country team calibrated them; only trajectories are steered.
Output = SpecifiedAnnualDemand patches over the exchange window (2026+), applied via the idea-01
driver to a case copy.

## Merit assessment (ours)

**Value — measured, decisive.** The CLEWS case's authored demand growth (PHL_HOU_ELEF 4.35 %/yr,
PHL_SER_ELEF 5.34 %/yr, 2026–53) vs the OG-implied path (≈3.8 %/yr residential) differ by
0.5–1.5 pp/yr compounding — tens of percent by 2053. Reconciling the two macro stories is the
single largest untapped coupling content, matters one-pass (scenario harmonization — no loop
required), and is what makes idea #02's loop worth having later.

**Technical.** All ports verified: OG side, `Y`/`Y_m`/`C` in the solved TPI arrays with the per-run
concordance naming industries; CLEWS side, SAD rows per commodity per scenario (idea-01's patcher
is the writer — extend from scale-factor to absolute-path form). The **`*F` final-demand codes are
the coupling surface** (idea-01 lesson). Timeslice profiles are untouched (SpecifiedDemandProfile
stays the case's own — annual totals only).

**Economic.** Engel/income elasticities are standard demand theory; the elasticity values are
CONFIG with mandatory country review, not code (grade the defaults as illustrative). One genuine
judgment call to surface, not bury: **whose baseline wins?** Rebuilding demands overrides the
country team's official projections with OG's macro story. That is a run-time CHOICE (harmonize vs
respect-official), must be explicit in provenance, and deserves the user's/country team's call on
the default. The anchor discipline (levels y₀ fixed, trajectories steered) limits the damage either
way. Trend double-count risk (OG's g vs a_f efficiency term): one config table owns each trend.

**Feasibility.** Everything exists: seam driver (proven), TPI arrays + concordance (main), SAD
patch mechanics (idea-01), CLEWS solve ≈3.5 min (window-patched). New work: the emitter math, the
B_D config schema, an absolute-path variant of the patcher, transform tests. No OG solve needed to
BUILD; the empirical test needs one existing baseline TPI (on disk from the golden runs) or, if
none is readable, one OG baseline solve (ask first).

**Empirical test (design before building):**
1. *Transform level (no solve):* fixture TPI + fixture case → rebuilt paths match hand-computed
   `D₀·IDX^η·IDX_pop^ν`; y₀ never touched; unknown commodity/driver fails loudly; zero-demand rows
   respected (idea-01 guard).
2. *PHL live:* rebuild PHL_HOU_ELEF + PHL_SER_ELEF (+ industrial via Y_m if isolable) from the
   latest CLEAN baseline TPI; report the rebuilt-vs-authored gap by 2053 (expect tens of %);
   write to a case copy via the driver; solve; verify the LP responds sanely (capacity build-out
   and costs move with demand, no pathology, solve time ~minutes).
3. *Negative control:* η=0, ν=0, a=0 → rebuilt path == authored path → LP results reproduce
   control within the vertex-wobble tolerance.

**Died-if:** no clean baseline TPI is readable link-side (then one OG solve, asked-first, unblocks);
or the rebuilt paths make the LP pathological even window-limited (would mean demand levels far
outside the case's capacity envelope — itself a reportable harmonization finding, not a code bug).

## Population-basis check (2026-07-11, the "two growth paths" worry — resolved)

The user's concern: is it a problem to run two models on two different growth paths? Checked, no solve:
- **CLEWS v9 carries NO population or GDP series.** genData.json has no pop/gdp/driver fields; demand
  is authored directly as absolute PJ paths in RYC.json (the only `population|gdp` grep hit was
  "capital costs" in the case description). So there is **no hidden second population/GDP dataset**
  that could silently conflict with OG field-by-field. The only divergence is the demand *trajectory*
  itself — precisely what this channel harmonizes.
- OG-PHL uses UN-608 population (declining, ~1%/yr per WPP) and g\_y=3.71%/yr; the authored CLEWS
  household-elec growth (4.35%/yr) sits in a plausible income-elasticity range against OG's GDP path.

**Design consequence (the resolution):** consistency = shared *drivers*, not identical demand paths.
Two divergent paths is the STATUS QUO today (channel off), silent; turning the channel on collapses
them to one story (OG's). The real trap is *partial* harmonization — so the design guards are:
(1) a whole-run **stance toggle** (OG-consistent [default, user's choice] vs official-outlook), never
silent half-and-half; (2) loud provenance recording the mode + every rebuilt commodity; (3) harmonize
the demand vector as a set (or state exactly which commodities); (4) full reconciliation is the loop
(idea #02), where the two paths *converge* rather than one overwriting the other. This channel is the
necessary first step; the loop is the closure.

## Verdict

**Worth building — proceeds.** Highest-value item on our own map (§6 #1), measured-large content,
all machinery verified present, empirical test crisp and mostly solve-free. User decision recorded:
default to OG-consistent growth, expose an on/off stance toggle.
