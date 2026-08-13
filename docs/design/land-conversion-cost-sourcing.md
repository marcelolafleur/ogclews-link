# Land-conversion cost for PHL CLEWs — sourcing record and implementation verdict

**Date:** 2026-08-11 · **Status:** sourced (triangulated); implementation DEFERRED — see verdict.
**Task:** §14 item 3 of `phl-testcase-plan.md` — a sourced cost of clearing forest for
agriculture, "the discipline the `-10` skipped."

## The number

**USD 500–1,500 per hectare (2020s prices), central value USD 800/ha**, for complete
forest-to-plantation/cropland land preparation (felling, stacking/windrowing, residue
disposal, initial field preparation) at plantation scale in maritime Southeast Asia.

In model units (case currency MUSD, land unit 10^3 km²): USD/ha × 0.1 = MUSD per 10^3 km²,
so the central value is **80 MUSD per 10^3 km² converted**, range 50–150.

## Sources, strongest first

1. **IUCN/WWF Project FireFight South East Asia**, *Land Clearing on Degraded Lands for
   Plantation Development* (Kuching workshop report, Oct 2002, ISBN 979-3260-05-X) —
   the only itemized primary costing found:
   - Table 4 (Golden Hope Plantations, Sarawak, oil palm on peat, RM/ha, 2002): complete
     land preparation **RM 1,920/ha clean-clearing / RM 1,790 zero-burning** (felling 450,
     stacking 450, burning+restacking 110, lining 43, holing/planting 442, compaction 425).
     At 2002's ~RM 3.8/USD: **≈ USD 505/ha complete; the clearing-proper components
     (felling + stacking + residue) ≈ USD 240–270/ha.** ≈ USD 880/ha in 2024 dollars.
   - Table 7 (Samling, Sabah, timber plantation): mechanical spreading costs
     **+RM 400/ha (~USD 105)** over burning; nutrient loss from burning valued
     > RM 2,000/ha — evidence the cash clearing cost understates the economic cost.
2. **Oil-palm industry establishment guides** (SEA, 2020s): land preparation
   **USD 500–1,500/ha** depending on vegetation density and mechanization — brackets (1)
   inflated forward.
3. **DENR reforestation** (the reverse flow): heavy capital cost of reforestation
   **≈ USD 1,000/ha** (DENR's own estimate, cited in the NGP context via World
   Agroforestry); NGP audit (COA PAO-2019-01) documents the ₱47.2bn/2011–2019 program.
   Regrowth is not cheaper than clearing — relevant if a reversion technology is ever built.
4. **Not used:** US land-clearing rates (USD 3,500–14,000/ha) — machinery-cost structure
   not transferable; Philippine PSA/PhilRice production-cost surveys — their "land
   preparation" is annual tillage of existing cropland, not conversion. **No direct
   Philippine forest-conversion costing exists in the public domain that we could find**;
   the Sarawak plantation costing is the nearest observed analogue (same climate,
   comparable labor markets, 2002 wage levels inflated forward).

## Scale context

At the case's 10% discount rate, a one-time 80 MUSD/10^3 km² conversion cost annualizes
to ≈ 8 MUSD/10^3 km²·yr — the same order as the existing `-10` forest reward
(10 MUSD/10^3 km²·yr). A sourced conversion cost is therefore not a rounding refinement:
it is the same magnitude as the unsourced parameter it would discipline.

## Implementation verdict — why this is NOT in the case yet

OSeMOSYS case data cannot express a one-way cost on *change*: `VariableCost` prices
activity LEVELS, and the only change-machinery available (`EmissionToActivityChangeRatio`
+ a penalty) is symmetric — the exact configuration the §13 falsification broke (the LP
"planted" 300 Philippines and collected the credits). Both this session and the
env-accounting session reached the same conclusion independently.

The doctrine-safe implementations are:
- **Tier-2f split-variable adjustment costs** (GMPL edit to `model.v.5.4.txt`, mirrors
  E10/E11): `Up/Down ≥ 0` change variables, each with its own cost — and its own emission
  ratio, which also structurally fixes the credit-farming exploit. Propose both upstream
  together (see `land-stickiness-options.md`).
- **Land-as-stock restructuring** (conversion technologies with CapitalCost/OperationalLife)
  — larger redesign of the land block.

Until one of those exists, the run proceeds WITHOUT conversion costs. This record is the
assumption-register entry so that the moment the machinery lands, the number and its
derivation are waiting.
