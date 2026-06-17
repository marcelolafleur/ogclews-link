# Energy as a production input — the structurally-correct energy-cost representation

**Status:** design spec (no code yet). **Audience:** OG-Core + ogclews-link maintainers.
**Cross-refs:** `og-clews-denovo-analysis.md` (Thread 1 "theoretical best" / Thread 2 "practical
frontier"; the three routes A/B/C), `ogcore-clews-integration-synthesis-report.md` (demand-led forward
+ targeted feedback), `ogcore-clews-integration-worklog.md` (Channel C = Z proxy, guardrailed).

## 1. Problem

An energy-price/-cost shock has no **production-side** home in OG-Core. Shipped production is a 3-factor
CES `Y_m = Z[t,m]·CES(K, K_g, L)` (firm.py:22–183) — no energy input, no inter-industry intermediates;
`io_matrix` is a final-demand bridge (`p_i = io_matrix·p_m`), not a Leontief use matrix; `Y` is gross
output and the resource constraint nets only final demand. The two available proxies are each wrong or
incomplete for a *resource* cost:

- **`tau_c` (route A, demand-side):** correct for household energy *incidence*, but it is a **tax**
  (phantom revenue → must be recycled), touches no firm, and double-counts if stacked with B or carbon.
- **`Z` haircut (route B, supply-side; `og_wedge.set_energy_industry_tfp`):** "smuggling energy through
  the one door that doesn't represent it" (denovo §1). Gets the energy industry's relative-price rise
  roughly right, but: no inter-industry pass-through (no other industry buys energy), **no factor
  substitution** (no energy factor), GDP falls via lost TFP rather than a higher input bill
  (gross-vs-value-added mislabeled), and the energy "market" is fake — so the CLEWS dual has nothing
  structural to attach to.

The **correct price object** is the OSeMOSYS **commodity-balance dual** (the marginal energy price), and
the **correct representation** is energy as a **priced production input** — denovo route **C**, the
"rigor endpoint": energy cost passes through endogenously, firms substitute, the dual prices a real
quantity, and OG↔CLEWS reconcile energy demand vs supply at a fixed point.

## 2. What PHL already provides (this is the enabling finding)

OG-Core can't do route C natively, but PHL's calibration already supplies **three of the four pieces**:

1. **An energy industry (the supplier) exists.** The **target platform is the CLEWS M=4 calibration**
   — `[NaturalResources, Electricity, ConsTradeServices, Manufacturing]`, with **"Electricity" at
   index 1** (`_calibration.py` / `contract.py` `energy_industry_index=1`). It is the proven runnable
   multi-industry baseline (full TPI converges: baseline + the 4-step across-steps reforms) and its
   energy industry maps `Electricity → ["aelec"]` (electricity *only*), which is the clean match to the
   per-fuel CLEWS commodity dual. The energy supplier is a real industry with its own price `p_m[m_e]`,
   `K`, `L`, `Z`. **Not M=7:** canonical OG-PHL also ships an energy industry — `M=7` "Utilities"
   (`aelec`+`awatr`; `ogphl/constants.py`) — but it is *not* a validated/runnable config (OG-PHL defaults
   to `M=1`; its only multi-industry example is a toy `M=2`), it bundles water into the energy price, and
   it would need its **own calibration assessment** (param vectors, SS initial-guess tuning, convergence
   check) before use. Defer M=7 until that assessment is done; build route C on M=4.
2. **The energy price object exists:** `p_m[m_e]` (industry-M numeraire price system, SS.py:535,
   TPI.py:797/813), to be anchored to the CLEWS commodity dual (`signals.commodity_shadow_price`).
3. **The θ_m calibration data already ships, and the extractor is BUILT.** `ogphl/data/
   002_IFPRI_SAM_PHL_2018_SAM.csv` contains the full inter-industry intermediate-use block;
   `get_io_matrix` reads only the household-final-demand slice and **discards** the
   activities×commodities block, which gives energy cost share by destination industry directly.
   `ogclews_link/energy_calibration.py::get_energy_use_shares()` (built, read-only on the SAM) computes
   it. **Computed M=4 θ_m (this de-risks Phase 2 — real numbers, no new data):**

   | industry | electricity only (`celec`) | + fuels & water (`celec,cmine,cwatr`) |
   |---|---|---|
   | Natural Resources | 0.39% | 0.42% |
   | Electricity (own use) | 6.59% | 10.98% |
   | Construction/Trade/Services | 0.54% | 0.99% |
   | Manufacturing | 0.59% | 3.23% |

   **Carrier choice dominates the result, and it's the key economic finding.** *Electricity* is a small
   input share in PHL (~0.4–0.7% outside the power sector), so an electricity-only route-C channel is
   structurally correct but quantitatively small. The material energy cost is *fuels* (`cmine` =
   petroleum/extraction): it lifts Manufacturing's share to 3.23%, and the fine activities show
   **chemicals 14.8%, basic metals 11.4%, non-metallic minerals 5.5%**. So price the carrier the shock is
   actually about (fuels for a fuel-price shock; electricity for a power-price shock) against the matching
   CLEWS commodity dual — don't assume "energy" ≈ electricity.

**The only missing piece is OG-Core production-side machinery (code, not data):** firms don't demand the
energy industry's output, there's no energy FOC, no inter-industry delivery in the resource constraint,
and no value-added netting.

**Granularity note (M=4 is enough; escape hatch if not).** M=4 captures the mechanism — a supplier and
three energy-buying industries — but it (like M=7) bundles the *energy-intensive* sub-sectors into one
"Manufacturing" `θ_m`: the energy+fuels share averages to **3.23%** while the fine activities are
**chemicals 14.8%, basic metals 11.4%, non-metallic minerals 5.5%** — the heavy-industry intensity is
averaged away. M=7 does **not** fix this (it splits only low-intensity sectors — Mining, Construction,
Trade, Services, Agriculture). If that heterogeneity becomes central to a result, the right move is a
**purpose-built aggregation** that breaks energy-intensive manufacturing (`achem`, `ametl`, … are
separate SAM activities) into its own industry — a deliberate calibration choice, not the canonical M=7.

## 3. The design (minimal theory-correct version)

Reuse the existing energy industry `m_e` as the energy supplier. For each energy-buying industry `m`,
nest the existing value-added CES inside an outer CES with an energy aggregate `E_m` bought from `m_e`:

```
Y_gross_m = CES_outer( VA_m , E_m ; sigma_E,m )        VA_m = Z[t,m]·CES(K, K_g, L)   (unchanged inner nest)
```

- **Energy share θ_m, elasticity σ_E,m:** `θ_m` from the SAM (§2.3); `σ_E` from the energy-CGE literature
  (KL–E substitution, ~0.3–0.8). `m_e` itself has `θ=0` (no self-input, or a small own-use term).
- **Firm energy-demand FOC** (cost minimization): `∂Y_gross_m/∂E_m = p_m[m_e] / p_m[m]` ⇒
  `E_m = θ_m · (p_m[m_e]/MC_m)^(-σ_E) · Y_gross_m`. This is the margin every proxy misses.
- **Inter-industry delivery in the energy market:** the energy industry's output clears against final
  demand **plus** intermediate use: `Y_{m_e} = (final demand for energy) + Σ_{m≠m_e} E_m`. (New term in
  the resource constraint for `m_e`.)
- **Value-added netting:** with intermediates, gross ≠ value added. GDP must be measured as factor
  income (Σ value added), and the business-tax base (`tax.py` `tau_b·(p·Y − w·L)`) must net the energy
  bill out, else both double-count. (firm.py `get_Y` GDP sum SS.py:487 and the RC SS.py:649–651.)
- **Dual anchoring + fixed point:** set `p_m[m_e]` to the CLEWS commodity-balance dual (reform/base
  ratio), and iterate OG (firm + household) energy demand against CLEWS supply via the existing
  multi-pass `Runner` (framework.py:106–147) until the demand/price fixed point holds. This is denovo
  Thread 1's consistency condition (marginal value = marginal cost; cost subtracted from the RC with the
  accounting identity intact).

This minimal version (one elastic energy nest in energy-buying industries, single `σ_E`, energy bought
only from `m_e`) captures the four things the proxies miss — inter-industry cost pass-through, factor
substitution, a real energy market, and a structurally-meaningful dual — while deferring full KLEM
(separate K–E vs L–M nests, multiple energy carriers, energy in `K_g` formation).

## 4. Files touched

- **OG-Core** (the real PR): `firm.py` `get_Y`/`get_r`/`get_w`/`get_pm`/`get_MPx`/`get_KY_ratio`
  (outer nest + energy FOC); `aggregates.py` resource_constraint + GDP as value added; `SS.py`/`TPI.py`
  price fixed point now solves jointly for energy price **and** quantity; `parameters.py` +
  `default_parameters.json` new `theta`/`sigma_E` (T+S, M); `tax.py` value-added base nets the energy bill.
- **OG-PHL**: upstream `get_energy_use_shares(prod_dict)` into `ogphl/input_output.py` (reuses
  `read_SAM()`). **Prototyped + computed already** in `ogclews_link/energy_calibration.py` (read-only;
  not yet upstreamed, to avoid touching the shared `ogphl` install while runs are live).
- **ogclews-link**: a channel that anchors `p_m[m_e]` to `signals.commodity_shadow_price` and drives the
  `Runner` fixed point; deprecate the Z route to a clearly-labeled fallback.

## 5. Prerequisite (Thread 2's first job)

The **OSeMOSYS commodity-balance dual** must be reliably extracted — it is not in CLEWS default output;
the solver must export marginals (`signals.commodity_shadow_price` reads it where present). Until then
the energy price is the average-cost index proxy. Dual extraction + unit/time mapping is the foundation
everything rigorous depends on; build it first.

## 6. Phasing & honest cost

- **Phase 0 (now, no core change):** route the transition's *capex* through the structural channel OG
  already has — energy-system investment → `K_g`/`alpha_bs_I` + capital-market crowding-out (the denovo
  "default", correct sign); use a **recycled** `tau_c` (or a small non-tax consumer-price-wedge param)
  for household energy incidence, driven by the **dual**, not the cost index. Never stack `tau_c` + `Z`.
- **Phase 1:** θ_m extractor **DONE** (`ogclews_link/energy_calibration.py`; M=4 shares computed for both
  carriers above). Remaining Phase 1 = **dual extraction** (the binding prerequisite). Data-only.
- **Phase 2 (the rigor endpoint):** the §3 energy-as-CES-input PR + the dual-anchored fixed point, built
  and validated on the **M=4** platform (the proven-runnable multi-industry baseline). M=7 stays out of
  scope pending its own calibration assessment (§2.1).

**Cost:** Phase 2 is a genuine OG-Core production-function PR with a joint price/quantity SS+TPI fixed
point and GDP/tax-accounting changes — non-trivial and needs recalibration of the affected industries.
But it is the only representation that makes the CLEWS dual structurally meaningful rather than a
relabeled consumer tax or TFP haircut, and PHL already supplies the supplier, the price object, and the
θ_m calibration data.
