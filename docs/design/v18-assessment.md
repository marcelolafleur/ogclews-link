# CLEWs-PHL v18 — assessment against our register, before any run

**Date:** 2026-08-13 · **Archive:** `Philippines_v18_v18.0.0_MUIO.zip`, checksum verified
against the repo's SHA256SUMS (ae9cb6fc…). Every claim below read from the case JSONs or
the build README, not assumed.

## 1. What v18 absorbed (convergence with our register — no PR needed)

| item | v18 | our register | verdict |
|---|---|---|---|
| coal capital cost | 1,604.789 | 1,605 (BNEF) | same |
| nuclear SMR capital | 8,000 | 8,000 (NREL ATB) | same |
| large-hydro life | 60 y | 60 y | same |
| coal calorific check | ~22.1 GJ/t | 22.1 (DOE) | same |
| LNG chronology | zero through 2022 | "no LNG before Apr 2023" | same point |
| onshore wind ceiling | 663.84 PJ | 664 (NREL Restricted) | same screen |
| land endowment | TAL = TAU = 295.8131 | both-sides pin (§14 item 1) | same |
| the `-10` forest reward | **PRESENT AND INTACT** — all 8 cluster techs (LNDAGRPHLC01-08), forest mode 27, -10.0 every year 2020-2053, identical across v12/v16/v18 | flagged unsourced | **MY EARLIER "REMOVED" CLAIM WAS FALSE** (2026-08-13, retracted same day): I probed LNDFORTOT, the aggregate accounting terminal, which never carried the reward in any version. Marcelo's suspicion of an error was correct — the error was in my assessment, not in v18. The -10 remains the live (still unsourced) forest value; our benchmark and sourcing work applies to v18 unchanged |
| deployment envelopes | TAMaxCI realism bounds from 2026 | (new, theirs) | good addition |
| irrigated rice water | corrected (IAR total ×8 vs source) | national ×14.4 to AQUASTAT | partial overlap |

## 2. What v18 still lacks — PR candidates, ranked by justification strength

**A. Offshore wind — the strongest item, and v18's own energy pass missed it.**
`PHL_POW_PP_WOF` TAU is still the **3,949.31 PJ placeholder** (4.8× the World Bank/ESMAP
screened resource of 823 PJ = 58 GW @ 45%), and its CF profile means **29.3%** against
ESMAP's 45–47% for the screened sites — not in the v18 update list, so inherited, not
evidence-based. Consequence demonstrated on v12: the wind build lands on the wrong
resource and the LCOE ordering flips. Sourced fix ready: cap 823, CF to the ESMAP mean.

**B. The coal-moratorium loophole persists.** The COAL_PHASEOUT layer still bans
investment only from **2031**, and the new SC_0 envelope explicitly allows 2–2.5 GW/yr
of new coal through 2030 — up to ~10–12 GW in the policy scenario's window, the same
order as the 10.2 GW our v12 solve exploited. The DOE moratorium (Oct 2020, committed
pipeline exempt) dates the ban to ~2027. One-parameter fix, demonstrated consequence.

**C. Conversion-carbon accounting (EACR).** Absent in v18. Ours is proven exact and
behavior-neutral (allocation identical to the cent; 1,474 Mt = ~25% of national CO2e on
v16), with the falsification doctrine attached (unpriced only; one-way pricing spec;
never symmetric-price-plus-penalty). Doctrine-consistent PR with the patch script ready.

**D. Discount rate.** v18 keeps 0.05; NEDA/ICC mandates 10% real for Philippine public
investment appraisal. Sourced, but behaviorally large — propose as a documented option,
their call.

**E–G (discussion, not PRs yet):** water national total (their rice fix reaches ~×8 of
source; AQUASTAT's 67.9 km³ needs ~×14 — reconcile targets); geothermal AF 0.70 vs our
DOE-derived 0.629 (compare sources); SMR 60-y life retained vs our FOAK-40 argument.

## 3. Migration warnings (for the eventual v18 run — all breaking)

1. **Tech renames**: `PHL_POW_PP_WON_T1/WOF_T1/SPV_T1` → `..._WON/WOF/SPV`. The v12↔v16
   id-stability assumption is DEAD for v18. Affects: calibrate_phl_case.py constants,
   forest_carbon_patch.py (`TEC_hjgww`), gates, mix/sankey chart tech lists.
2. **The land block is restructured** (v17 "safeguarded land account"): crop OAR differs
   from the v12 source, so our yield factors DO NOT transplant; forest TAMLL/TAMUL carry
   99999 placeholders. The -10 forest reward IS present (cluster techs, mode 27) and,
   combined with the v17 account, produces a far more plausible base forest path than
   v12's (72.3 -> peak ~97 -> 78.4 by 2053, vs v12's jump to 161): READ THE v17 LEDGER
   before porting any land item or re-deriving yields.
3. **Water base differs** (their rice correction), so our 14.4128 factor is INVALID on
   v18 — a fresh two-pass against AQUASTAT is required if we recalibrate water at all.
4. Scenario names unchanged (BASE/COAL_PHASEOUT/RE/EV); envelope machinery now occupies
   TAMaxCI SC_0, so our moratorium script must UPDATE the policy layer without clobbering
   the envelopes.

## 4. Recommendation

Offer A+B+C upstream as one well-evidenced PR (offshore wind sourcing, moratorium date,
conversion-carbon accounting), D as a documented option, E-G as issues/discussion.
Migrate and run only after Marcelo decides the PR question — if upstream takes A-C, we
run on clean v18(+PR) rather than maintaining another local calibration layer.
