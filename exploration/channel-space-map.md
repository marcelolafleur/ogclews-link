# The OG ⇄ CLEWS channel possibility space

**Date:** 2026-07-10 · **Branch:** `explore/channel-space` @ main `7bfc992` · **Status:** complete first
pass, evidence-grounded; updates as research-inbox documents arrive.

**Evidence base** (everything below cites these; nothing is assumed):
- [findings/og-core-surface.md](findings/og-core-surface.md) — all 130 ogcore-0.16.3 parameters classified;
  23 already used by channels; consumption sites verified file:line.
- [findings/clews-surface.md](findings/clews-surface.md) — MUIOGO catalogs (49 writable params / 29 result
  variables / 4 duals), Philippines_v9 census (132 techs, 57 commodities, 2020–2053, CO2e+PM2_5);
  3 params written, 9 CSVs + 1 dual read today.
- [findings/2026-06-adversarial-critique.md](findings/2026-06-adversarial-critique.md) — 119 verified
  findings against the v1 prototypes; the ✗/gate column below inherits its P0/P1 lessons.
- Live-system facts verified this session: the link's registry resolves OG-PHL to the **m8-compat
  worktree** (`M=8`, Electricity=industry 2, **Water=industry 3**, Agriculture-and-Fishing=industry 0,
  Trade-and-Transport=industry 5; goods I=5 with "Energy and water" = good 1, electricity share 0.3931);
  OG-PHL *main* is still M=7 (Utilities fused) — **the coupling depends on an unmerged feature worktree**.
  v9 cooking: PEP shifts 40.12 activity units **electric→coal** (wrong sign for clean cooking — the LP
  re-coals cooking when PEP raises electricity cost). v9 water: DEM water techs carry nonzero
  AnnualVariableOperatingCost; PEP surface cooling water 698→5311 (~7.6×).

**Grades.** **A** = buildable now with existing idioms (function channel + `signals.*` sourcing +
transform test). **B** = feasible with a *minor* change, named per candidate (a link-side reader/writer,
a concordance-discovery extension, a framework option, a CLEWS scenario authored in MUIOGO). **C** =
blocked on a *large* change (OG-Core production rewrite, CLEWS structural additions, sectoral labor) —
mapped for completeness, out of scope now. **✗** = economically or honestly unsound for this coupling
(reason given). Grades are about *feasibility and honesty*, not priority.

---

## 0 · What is already taken (don't re-propose)

11 channel functions + 1 composite on main: electricity price ×3 transmissions (`energy_price` τ_c wedge /
`energy_price_tfp` own-Z / `energy_cost_push` φ_j-weighted Z haircut) + `energy_full` composite (cost-push
with self-use zeroed + recycled diluted wedge — the `coupled` flagship, at the real `'auto'` LCOE price);
`investment` (public T&D capex → α_I→K_g); `capital_intensity` (γ[electricity]); `energy_capex` (ITC);
`carbon_tax` (τ_c + deflator guard); `health` (PM2.5 ratio × dose-response M → mortality via disease_pop +
morbidity on e); `emit_carbon_penalty`, `emit_discount_rate`, `emit_energy_demand`. Levers available in
`policy_levers.py`: `set_investment_incentive`, `set_capital_intensity`, `route_revenue` (α_T/α_I/α_G/
deficit), `industry_registry`/`resolve_industry`.

---

## 1 · CLEWS → OG candidates (read the energy system, mutate the economy)

| # | Candidate | CLEWS signal (verified) | OG entry | Grade | Gate |
|---|---|---|---|---|---|
| 1.1 | **Water cost/scarcity** | DEM/WTR tech variable costs + activity (nonzero in v9; PEP water 7.6×) | `Z[:,3]` (Water industry, M=8) or τ_c on "Energy and water" good diluted by 1−0.3931 | **B** | water-port discovery + water-cost reader |
| 1.2 | **Liquid-fuels cost-push** | PHL_PRO_LIQ/OIL supply costs (cost CSVs, unread) | `energy_cost_push` machinery with an oil φ_j vector from the SAM | **B** | oil input-intensity vector + liquid-fuel price reader |
| 1.3 | **Disaggregated activity→demand feedback** | — (this is og→clews; see 2.1) | | | |
| 1.4 | **Cooking HAP → health** | HOU_COOK activity by fuel (live) — but PEP moves cooking electric→**coal** | existing `health` machinery + bimodal HAP h(s) | **B**, blocked on scenario | needs a clean-cooking CLEWS scenario; current pair is wrong-signed (would show PEP *adding* HAP deaths — report it only as exactly that) |
| 1.5 | **Crop/food from CLEWS land** | ✗ none: PHL_LND_CRP/GRS declared, **zero activity** in v9 (re-verified) | — | **✗ (CLEWS side)** | crop module unpopulated; see 3.2 for the external-data food channel |
| 1.6 | **Reliability/outage costs** | not observable: the LP meets demand by construction; no unserved-energy slack in this MUIOGO (no ReserveMargin param either) | Z haircut × VoLL | **C** | needs CLEWS-side unmet-demand slack (structural) |
| 1.7 | **Sectoral labor reallocation (coal→renewables jobs)** | tech-mix shift is readable | none — OG-Core labor is homogeneous/mobile; no sectoral labor market | **C** | large OG change |
| 1.8 | **Emissions → agriculture productivity** (pollution damage to crops) | PM2.5 readable | `Z[:,0]` (AgriFish) | **✗ for now** | no defensible dose-response at this aggregation; double-counts health morbidity (critique lesson) |

**1.1 Water cost/scarcity — the strongest genuinely-new clews→og candidate.** M=8 isolates Water as its
own industry (index 3) — the v1 blocker (water fused) is gone. Two honest transmissions, mirroring the
electricity pair: (a) *cost route*: reform/base ratio of water provision cost per unit (DEM/WTR variable
costs ÷ activity, both in the cost CSVs — verified nonzero) → `Z[:,3]` haircut so OG produces the higher
water price endogenously (exactly `energy_price_tfp`'s idiom); (b) *demand-side wedge*: τ_c on the
"Energy and water" good diluted by water's complement share (1−0.3931 = 0.607 — water is the *bigger*
half of that good). Minor changes needed: extend the og-runner concordance discovery to emit a
`water_industry_index` port (same PROD_DICT scan that finds Electricity), and add a
`signals.water_cost_ratio` reader (same shape as the LCOE reconstruction). Economics: the PEP scenario's
7.6× cooling-water pull is a real resource claim; pricing it into the water utility's cost is the
transition's water footprint made economic. Caveat inherited from critique: don't stack the Z route with
an energy-price cost-push on the same industry without separating components.

**1.2 Liquid-fuels cost-push.** Today every price channel is electricity-only, but transport is the
*largest* CLEWS sector (37 techs) and runs on liquids; households and industry buy oil products directly.
CLEWS carries liquid-fuel supply costs (PRO_LIQ/OIL tech costs, currently unread). Route the reform/base
liquid-fuel cost ratio through the existing `energy_cost_push` machinery with an *oil* input-intensity
vector φ_j^oil from the same SAM used for electricity φ_j (`aggregation.input_intensity` generalizes; the
SAM has petroleum activity codes). Minor changes: the φ^oil extraction + a liquid-fuel price reader.
Honesty note: same "illustrative reduced-form" label as the electricity cost-push — calibrated weights,
not a use-matrix equation.

---

## 2 · OG → CLEWS candidates (read the solved economy, write OSeMOSYS inputs)

46 of 49 writable parameters are unused; these are the pairings that make economic sense.

| # | Candidate | OG output | CLEWS write | Grade | Gate |
|---|---|---|---|---|---|
| 2.1 | **Disaggregated sectoral demand** | Y_m ratios for all 8 industries | SpecifiedAnnualDemand per demand commodity (AGR_*, INDU_*, SER_*, HOU_*, TRA_*) | **A** | an industry→demand-commodity concordance table (link-side data) |
| 2.2 | **Emission cap (quantity twin of the carbon price)** | policy scalar / OG-derived budget | AnnualEmissionLimit | **A** | new artifact type in `clews_io` (mechanically identical to EmissionsPenalty) |
| 2.3 | **Financed-capacity coherence** | α_I-affordable public capex path | TotalAnnualMaxCapacityInvestment on T&D techs | **B** | capex→capacity conversion via CapitalCost; new writer |
| 2.4 | **Capital-cost scaling from OG's r** | r path | CapitalCost | **✗** | double-counts DiscountRate (the LP already discounts with the emitted rate) |
| 2.5 | **Fuel price / labor cost to CLEWS** | — | VariableCost | **✗** | OG produces no fuel prices (no energy in production) and OSeMOSYS has no labor |

**2.1 Disaggregated sectoral demand — the highest-value og→clews upgrade.** `emit_energy_demand` today
scales ONE fuel by ONE activity ratio; with M=8 the OG solve gives 8 sectoral output paths, and the v9
case has sector-specific demand commodities (PHL_AGR_ELE, PHL_INDU_ELE/OTH*, PHL_SER_ELE, PHL_HOU_ELE,
PHL_TRA_PKM*/FKM* — 57 commodities censused). Mapping each OG industry's Y_m ratio to *its* CLEWS demand
commodities makes the forward leg economically meaningful instead of a uniform scalar — and it is what
makes the iteration loop (§4) worth closing: structural change in the economy then *reshapes* energy
demand, not just rescales it. Pure grade A: the SpecifiedAnnualDemand writer exists; the work is a
declarative concordance table (OG industry → CLEWS demand commodities) plus a small loop in the emitter.
Transport demand maps from "Trade and Transport" (industry 5) with a passenger/freight split assumption —
label it.

**2.2 Emission cap.** A carbon *budget* (AnnualEmissionLimit) instead of a carbon *price* — the standard
quantity-vs-price instrument pair. Mechanically a sibling of `emit_carbon_penalty` (same region/species
validation, different parameter name). Enables the classic comparison: same emissions outcome, tax vs cap,
who bears it — with the OG side unchanged (`carbon_tax` for the price arm, nothing for the cap arm since
the cap's economic cost arrives via the next-pass electricity price). Honest framing requires the loop
(§4) or at least a re-run CLEWS scenario; as a one-pass artifact it's still useful as a scenario-authoring
lever.

---

## 3 · Policy / shared-lever candidates (one lever, applied consistently)

| # | Candidate | OG side | CLEWS side | Grade | Gate |
|---|---|---|---|---|---|
| 3.1 | **Electricity affordability / lifeline tariff** | negative τ_c wedge on energy good + `energy_subsistence_floor`; funded via `route_revenue` | none (or demand feedback in-loop) | **A** | none — existing machinery, sign flipped; α_T floor guard already handles funding sign |
| 3.2 | **Food price / subsistence (external climate-crop scenario)** | τ_c[Food good 0] or `Z[:,0]` (AgriFish — now cleanly isolable at M=8) + `c_min[Food]` | none (CLEWS crop empty) | **B** | honest labeling as EXTERNAL-scenario channel (IRRI/IFPRI yield data); the v1 critique's aggregation objection is *reduced* (AgriFish no longer contains mining/utilities) but food-processing still sits in Manufacturing |
| 3.3 | **Carbon revenue → UBI** | the unused `ubi_nom_*` block (017/1864/65p, growthadj) instead of the α_T lump-sum bump | same carbon price via `emit_carbon_penalty` | **A** | none mechanically; distributional story is the point (age-differentiated rebate vs flat transfer) |
| 3.4 | **Transfer-incidence targeting** | the unused `eta` matrix (WHO receives transfers) alongside α_T levels | — | **B** | critique lesson applies verbatim: per-period sum-to-1 must be preserved (the eta_RM P0); needs a shape-safe helper |
| 3.5 | **Fossil-subsidy removal** | positive τ_c restoration on energy good(s) | VariableCost lift on subsidized supply techs | **B** | subsidy magnitude data + a VariableCost writer |
| 3.6 | **Renewable mandate (RPS)** | — (effects arrive via next-pass price/capex) | TotalAnnualMinCapacity on renewables | **B** | writer + loop for the OG side to see it |
| 3.7 | **Diaspora/remittance financing of transition capex** | α_RM/η_RM native (PHL baseline 7.2% GDP); bond arm = α_I path + `zeta_D` | thematic tie to capex only | **B** | fix the critique P0s first: `*_annual` params are inert post-build (set derived arrays or rebuild); η tilts must preserve per-period sums; label as macro-financing lever, not a biophysical coupling |
| 3.8 | **Just-transition pensions (coal-worker early retirement)** | pension block (18 unused params) | — | **C** | OG pensions are economy-wide; no sectoral tagging without large change |
| 3.9 | **LDC graduation** | — | — | **✗ for PHL** | not an LDC, never was; keep only as a framework capability note for an actual graduating country |
| 3.10 | **Climate damages (heat-labor e, crop Z)** | e / Z[AgriFish] from external damage functions | climate exogenous in CLEWS | **B** | the critique P0 stands: reform-only application misattributes damages to PEP. Gate = a framework option to apply designated channels to the BASELINE too (link-side, moderate); until then ✗ to run it |

---

## 4 · Loop closure (the bidirectional fixed point)

Not a channel but the multiplier on channels 2.1–2.3: today the `emit_*` artifacts are produced and the
Runner's multi-pass loop exists but "honestly degrades to one pass" without a CLEWS re-solve driver. The
design for closing it exists (link-emitted patch → MUIOGO's own `/updateData` → `/createCaseRun` → `run()`
— see docs/design + the MUIOGO seam notes): **grade B**, MUIOGO-side endpoints already exist; the work is
the patch-apply hook + re-adding an iterate driver. Every og→clews candidate above is sized on the
assumption this eventually closes; none *requires* it to be individually useful (they are also
scenario-authoring tools).

## 5 · Explicitly out of scope (large changes — recorded so the map is complete)

- **Energy as a production input in OG-Core (Option B CES rewrite)** — the structurally right fix that
  would retire the cost-push proxy; tracked in docs/design/energy-as-production-input-spec.md. **C.**
- **Sectoral labor markets / frictions in OG-Core** (just-transition employment stories). **C.**
- **CLEWS crop/land module population** (turns 1.5/3.2 into real couplings) — a CLEWS modelling project,
  not a link change. **C** from the link's perspective.
- **Unserved-energy slack in OSeMOSYS/MUIOGO** (reliability channel 1.6). **C.**

## 6 · Shortlist — where the next build effort should go

Ranked by (value × feasibility), all consistent with "minor changes only":

1. **2.1 Disaggregated sectoral demand** (A) — makes the forward leg real; pure link-side table + emitter loop.
2. **3.3 Carbon→UBI recycling** (A) — distributional upgrade of the existing recycle; params already exist.
3. **3.1 Lifeline tariff / affordability** (A) — PHL-relevant, existing machinery, completes the incidence story.
4. **1.1 Water cost/scarcity** (B) — the strongest new biophysical signal; two minor link-side extensions.
5. **2.2 Emission cap** (A) — cheap twin of the carbon penalty; enables tax-vs-cap.
6. **1.2 Liquid-fuels cost-push** (B) — extends the price coupling beyond electricity to the biggest CLEWS sector.

Graduation pipeline for any candidate: verify the signal on the live v9 pair → function channel + transform
test (no solve) → experiment wiring → adversarial critique gate (the 2026-06 findings set the bar) → solve
comparison → merge proposal to trunk.

## 7 · Standing fragilities this exploration must respect

- The live coupling imports ogphl from the **unmerged m8-compat worktree**; if that worktree moves or
  OG-PHL main merges differently, ports shift (registry re-discovery handles it, but goldens won't).
- `*_annual` OG parameters are **inert if set after Specifications build** (critique P0; the
  world_int_rate lesson) — any candidate touching them must set the derived arrays or rebuild.
- The v9 scenario pair optimizes cooking the wrong way for clean-cooking stories (electric→coal under
  PEP); never present 1.4 on this pair as a co-benefit.
- Absolute/external shocks (3.2, 3.10) must be applied symmetrically or clearly labeled — the framework
  currently applies channels to the reform only.
