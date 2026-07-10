# Research-inbox drop 1 — the MUIOGO Rev-4.2 coupling spec + coupling matrices

**Processed:** 2026-07-10 · **Files:** `Claude v.9.pdf` (22 pp), `OG–CLEWS Coupling Map.docx`,
`OG–CLEWs Annex_Philippines_Generalization_With_Formulas.docx`, `OG–CLEWS Nuclear 1.xlsx`.
All read in full; claims verified against the installed MUIOGO/OG stack where marked ✔.

## What the four documents are

1. **`Claude v.9.pdf` — "MUIOGO: Proposal for an Iterative OSeMOSYS/MUIO ↔ OG-Core Coupling, Rev 4.2
   (Philippines pilot)".** The centerpiece: a complete, operational bridge-layer specification with
   exact file/parameter names. Recipes **A1–A6** (OG→OSeMOSYS: demand rebuild with per-commodity
   elasticities; compound-average discount rate; wage escalation of tech running costs [off by
   default]; carbon price in; shared-WPP checksum; consumption-driven refinement), **B0–B7**
   (OSeMOSYS→OG: unit-cost extraction in *marginal* [dual] or *average* [CRF-annualized] mode;
   supply-cost→energy-Z price-index steering; exponentiated multi-bundle cost-push
   `Z×Π c_x^(−s[x,m])`; capex→α_I with public-financing flags; carbon-revenue-consistent τ_c;
   cap-dual→implied carbon price; import bill as reverse-remittance [Phase 3]; dashboard reporting),
   **C1–C8** (food/water/land legs: same recipes, new rows — rice the flagship; C8 = climate-scenario
   propagation "nothing to code": typhoon/ENSO shocks entered CLEWs-side reach macro through the
   supply-cost recipes). Plus a **residual-based damped iteration loop** (per-commodity λ, defaults
   0.5 energy/water and **0.3 food — the food loop has higher gain than the energy loop** because
   food's budget share is several times energy's), a **failure taxonomy** (LP infeasible / macro
   explosion / genuine non-convergence / multiple equilibria — all first-class *findings*, not
   errors), a validation plan (channel-off bit-equivalence, start-from-both-ends, accounting
   cross-checks vs PSA/FIES), and a 3-phase roadmap.
2. **Coupling Map docx** — the conceptual companion: six core exchange objects (annual demand,
   delivered cost schedules, public capex, private capex, emissions+revenues, financing envelopes +
   legacy capacity), with per-object cautions ("pass wedges, never overwrite equilibrium prices";
   "annual flows, never discounted totals"; "only the publicly financed share feeds I_g").
3. **Annex docx** — the bridge as country-agnostic formulas (D_CLEWs = ΣB·C_i + ΣA·Y_m + a·G + b·I_g;
   POP/GDP elasticity harmonization; unit-cost wedge uc[f,t]; pass-through matrices P_hh/P_firm;
   iteration rule). Priority order from the PHL use case: demand-first; earliest feedbacks = fuel
   imports, extraction, investment; emissions/land/water retained as *reporting* bridges.
4. **Nuclear 1 xlsx** — an exhaustive documentation-level crossing of both models' full surfaces
   (63 OSeMOSYS params + 75 variables × OG params/variables; 143 + 70 rows). Mostly "n/a" with ~30
   real mappings (ResidualCapacity→initial_Kg_ratio; CapitalCost→α_I; Variable/FixedCost→α_G or Z;
   EmissionsPenalty→τ_c or cit_rate; TradeAnnual→debt path...). Zero nuclear content — the filename
   evidently names the intended application: ✔ **v9 PEP adds an SMR buildout** (`PHL_POW_PP_NUSMR` +
   uranium chain `PHL_PRO_UR`, recorded in `lcoe.py`'s per-run discovery notes).

## Verified against the installed stack

- ✔ **E8 emissions-limit dual is available**: `E8_AnnualEmissionsLimit` is one of the 4 duals in
  MUIOGO's `Duals.json` AND `E8_AnnualEmissionsLimit.csv` exists in `Philippines_v9/res/Base_v9/csv/`
  → recipe **B5 is feasible today**.
- ✔ **The link's `lcoe.py` ≈ recipe B0 (average mode) already** — CRF-annualized capex + O&M ÷
  delivered, validated on v9 with flow-allocation/CHP/negative-cost guards. Generalizing B0 to other
  bundles (food, water, liquids) is incremental.
- ✔ `TotalAnnualMaxCapacityInvestment`, `AnnualEmissionLimit`, `Fixed/VariableCost` all writable in
  this MUIOGO's `Parameters.json` (checked earlier for the map).
- ⚠ **Two factual tensions to resolve with the author:** (a) the spec says OG-PHL remittances are
  calibrated at **8.3 %** of GDP; the installed `ogphl_default_parameters.json` has
  `alpha_RM_1 = 0.072` (7.2 %) — version drift, someone's number is stale. (b) The spec assumes the
  **DESA Philippines CLEWs model carries food/crop commodities**; the installed v9 case declares
  crop/grass land techs but they carry **zero activity** (re-verified) — so the food leg (C1/C4)
  is gated on CLEWS-case work exactly as the map already says, and §13.2's "confirm the model
  version and its commodity list" is the operative open decision.
- ⚠ **Architecture tension:** the spec homes the orchestrator *inside MUIOGO* (`muiogo/` backend
  package, two adapters, per-iteration artifacts under `WebAPP/DataStorage/.../coupled_runs/`);
  the existing `ogclews-link` **is** an external orchestrator owning channels/experiments/CLI.
  These overlap ~80 % in function. Who owns the loop is a real decision — not resolvable here.
  Note the link's per-run concordance discovery, registry, and health/demographics machinery have
  no counterpart in the spec, while the spec's residual ledger/failure taxonomy/per-commodity
  damping have no counterpart in the link.

## What this changes in the channel-space map

**New candidates (were absent):**
- **A3 wage escalation of technology costs** (og→clews): w path × labor share θ_L →
  Fixed/VariableCost. New writers; ships off by default. → added as 2.6, grade B.
- **B6 fuel/food import bill as a reverse-remittance wedge** (clews→og, Phase 3): TradeAnnual ×
  border prices → the existing RM pipe with a minus sign. Resurrects the previously-✗ fuel-import
  candidate with a concrete mechanism riding machinery OG-PHL already runs at scale. Needs an
  OG-Core-side extension (bridge-driven RM add-on) → grade B/C boundary; map it B with the
  extension named. → added as 1.9.
- **C8 climate-scenario propagation through CLEWS** (emergent): typhoon/ENSO/hydrology/capacity-factor
  shocks entered as CLEWS *inputs*; the macro side receives them through the existing supply-cost
  recipes. **This is the honest climate channel** — the differential is CLEWS-mediated and
  reform-attributable, unlike the direct e/Z damage route (which stays gated on symmetric
  application). → climate row split in two.

**Upgrades to existing rows:**
- **2.1 demand emit → A1-style demand rebuild**: per-commodity elasticity library (rice η≈0.1–0.3
  Engel; residential elec 0.6–0.8; municipal water 0.2–0.4; ν=1 per-person), drivers = Y/Y_m/C per
  B_D config, autonomous-efficiency term with trend-ownership rule. Still grade A; strictly better
  than ratio-scaling (which is the η=1 special case).
- **2.2 emission cap + B5 cap-dual read-back**: write `AnnualEmissionLimit`, read the E8 dual as the
  implied carbon price, feed it to the τ_c recipe → the cap arm becomes *economically complete in
  one pass* (no loop needed for the OG side to see the cap's cost). Upgraded A with the dual-read.
- **Existing `carbon_tax` → B4 revenue-consistency form**: size τ_c from emission-factor-weighted
  household deliveries (`EmissionActivityRatio` × A1 demands ÷ bundle price) so OG's government
  collects exactly the revenue the energy model charges — replaces the illustrative
  `carbon_per_energy_unit` scalar. Grade A refinement of an existing channel.
- **1.1 water + 1.2 liquid fuels → B2 exponentiated multi-bundle form**: one recipe,
  `Z_new(m)=Z_base(m)×Π_x c_x^(−s[x,m])` over config-declared bundles (energy, water, ...), replacing
  the linear `(1+φ(r−1))` haircut; s[x,m] from PSA I-O tables. First-order, documented as such.
- **§4 loop closure**: adopt the spec's loop design — residual-based convergence (log-gap on demand
  and price indexes), per-commodity damping with a LOWER food default (higher loop gain), oscillation
  auto-halving, ±10 %/iteration caps, hard cap 15 iterations, warm-started OG solves, and the failure
  taxonomy where non-convergence/infeasibility/multiple-equilibria are named, reported findings.
- **Graduation pipeline**: adopt channel-off bit-equivalence and start-from-both-ends as gates.

**Confirmations (map rows that survive contact unchanged):** investment/α_I public-only flags
(=B3, incl. post-EPIRA "generation is private" flag ≈ 0); the "pass wedges, never overwrite prices"
rule; food-leg CLEWS gating; the distributional-teeth point (c_min makes food/carbon-price shocks
regressive with no extra machinery — the spec states it as a design feature, matching the map's
c_min amplifier note); "no land factor in OG-Core — land rents accrue to capital owners, wrong
factor incomes, documented honestly" (carried into map §5).
