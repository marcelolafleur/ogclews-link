# OG-Core ⇄ CLEWS — channel mechanisms

A mechanism-level explainer for the six integration channels: the triggering signal, the **specific
OG-Core object** each one moves or reads, how it propagates, the resulting effect, and the
scope/condition caveats that keep it honest.

**One structural distinction.** CLEWS→OG and policy channels **move** an OG-Core parameter (a real
input changed before the reform solve). OG→CLEWS channels **read** an OG-Core output and pass it to
CLEWS — *nothing in OG changes*, so their macro effect on the economy returns only through the
iterated loop.

## Summary

| # | Channel | Direction | OG-Core object | moves / reads | One-line effect |
|---|---------|-----------|----------------|:---:|-----------------|
| 1 | `energy_price` | CLEWS→OG | `τ_c` — consumption-tax/price wedge on the energy good | **moves** | energy demand ↓; distributional incidence (regressive *only if* `c_min`>0) |
| 2 | `investment` | CLEWS→OG | `α_I` → `K_g` — public-investment share → public capital | **moves** | productive public capital (output↑) vs debt/tax financing (crowds out). **Public infrastructure only** |
| 3 | `carbon` | policy → both | `τ_c` on **household** energy (+ `α_T` recycle); CLEWS `EmissionsPenalty` | **moves** | household demand ↓ + revenue (≈neutral *if* recycled); CLEWS emissions ↓ |
| 4 | `discount_rate` | OG→CLEWS | `r_p` — equilibrium cost of capital | *reads* | shifts CLEWS least-cost build mix; macro effect via the loop |
| 5 | `health` | CLEWS→OG | `ρ` (mortality by age) **and** `e` (effective labour by age) | **moves** | mortality→demographics (≈0, elderly); morbidity→productivity (the main gain) |
| 6 | `demand` | OG→CLEWS | `Y_m` / `C_i` — activity & consumption | *reads* | more CLEWS capacity (cost & emissions); macro effect via the loop |

---

## 1 · `energy_price` — CLEWS→OG (structural)

- **Trigger.** The OSeMOSYS electricity commodity-balance **dual** (the marginal price of electricity),
  as a reform/base ratio, share-diluted into the OG energy consumption good.
- **OG object moved.** `τ_c` — the **consumption-tax / price wedge** on the energy good (optionally also
  `c_min`, the Stone-Geary subsistence floor).
- **Mechanism.** The wedge enters the household demand FOC,
  `c_i = α_i·((1+τ_c)p_i / p̃)^{-1}·c + c_min_i`, and the composite price `p̃` — raising the effective
  consumer price of energy.
- **Effect.** Households cut energy demand (substitution), with a distributional incidence across the
  `J` lifetime-income groups.
- **Scope / conditions.**
  1. **Regressivity is not automatic** — it comes from the *necessity floor*. The bare `τ_c` wedge is
     ~homothetic (uniform budget shares → roughly proportional incidence). Regressive incidence appears
     only when energy is set as a necessity (`c_min` > 0).
  2. **It is a tax wedge, not a pure resource cost.** The revenue accrues to government; recycling it
     (lump-sum via `α_T`) isolates the pure price/substitution + distributional effect. Left
     un-recycled it is a tax-transfer, so the welfare/GDP read depends on the fiscal closure.

## 2 · `investment` — CLEWS→OG (structural)

- **Trigger.** The increment in CLEWS **public-infrastructure** (grid / transmission & distribution)
  capital cost, as a share of GDP (via `units.deflator`), as a finite transition flow.
- **OG object moved.** `α_I` — the public-investment share of GDP (`I_g = α_I·Y`) → public capital `K_g`.
- **Mechanism.** `K_g` enters the CES production function as economy-wide public capital (productive via
  `γ_g`, lifting every industry's output); the spending lands on the government budget (debt) and
  competes in the capital market.
- **Effect.** Two-sided — productive public capital raises output; the debt/tax financing crowds out
  other spending (and can raise the interest rate). The net depends on the fiscal closure (no clean sign).
- **Scope / conditions.** **Public infrastructure only.** The transition's *private generation capex* —
  typically the bulk of the capital — is a **separate mechanism** not captured here: it enters as the
  energy **cost-push** (the `energy_price` channel) or a capital-intensity (`γ`) shift on the energy
  industry. Do not equate "investment channel" with "the transition's total capital effect." (Magnitude
  illustrative until `units.deflator` is calibrated.)

## 3 · `carbon` — policy → OG and CLEWS (structural)

- **Trigger.** A single carbon price (USD/tCO₂), set once and fed to both models.
- **OG object moved.** `τ_c` on the energy good — a carbon tax on **household** energy — booking
  consumption-tax revenue, optionally recycled via `α_T` (transfers). **CLEWS object:** `EmissionsPenalty`
  (same price path).
- **Mechanism.** On the OG side, identical to the energy-price wedge (household energy price ↑ → demand ↓)
  plus the revenue is collected and, if recycled, rebated. On the CLEWS side, the price shifts the
  least-cost mix.
- **Effect.** Household energy demand ↓ + government revenue; if recycled, roughly revenue-neutral with a
  distribution that depends on the rebate. CLEWS: emissions ↓.
- **Scope / conditions.**
  1. **The OG-side carbon tax prices household energy only.** OG-Core has no energy in production, so
     industrial / economy-wide carbon is unpriced on the OG side — the economy-wide carbon price is the
     **CLEWS `EmissionsPenalty`**. This is a fundamental scope limit of the mechanism, not a scenario detail.
  2. **Recycling is optional** (a switch), not automatic.

## 4 · `discount_rate` — OG→CLEWS (structural, post-solve)

- **Trigger.** The OG reform equilibrium.
- **OG object read.** `r_p` — the household equilibrium portfolio return (the real market **cost of
  capital**). *An OG output, not a mutated input.*
- **Mechanism.** `r_p` → CLEWS `DiscountRate` → the LP's intertemporal weighting → which technologies are
  least-cost.
- **Effect.** Shifts the energy system's least-cost build mix (low rate favours capital-heavy clean; high
  rate favours cheap-now fossil) and cost trajectory.
- **Scope / conditions.** One-way; nothing in OG changes — the macro effect returns only through the loop.
  Confirm real-vs-nominal and annualization conventions.

## 5 · `health` — CLEWS→OG (reduced-form)

- **Trigger.** The CLEWS **PM2.5** emissions reform/base ratio (not CO₂e — decarbonization moves PM2.5 and
  CO₂e by different ratios), scaling an **external GBD dose-response**.
- **OG objects moved (two).**
  - **Mortality:** `ρ` — mortality rates by age — shifted by `shock_scale·g_t·h(s)` (`h(s)` = GBD by-age
    deaths shape); the population is then recomputed (`get_pop_objs`) → demographics (`ω`, `g_n`).
  - **Morbidity:** `e` — effective labour units by age — scaled by `(1 + benefit·g(s))` (`g(s)` = GBD
    working-age YLD shape) → labour productivity.
- **Mechanism.** `ρ` → population/demographics → labour-force composition; `e` → effective labour in CES
  production → output per worker.
- **Effect.** Mortality → demographics, but PM2.5 deaths skew **elderly** → added survivors are retirees →
  ~0 output effect. Morbidity → **productivity** (`e`) → output ↑ (the dominant effect).
- **Scope / conditions.** Dose-response magnitudes are placeholders pending GBD calibration (the real PHL
  PM2.5 export is still a stand-in).

## 6 · `demand` — OG→CLEWS (structural, post-solve)

- **Trigger.** The OG reform equilibrium.
- **OG object read.** `Y_m` (industry output) or `C_i` (consumption of the good) — ratio-scales CLEWS
  demand. *An OG output.*
- **Mechanism.** Reform/base activity ratio → CLEWS `SpecifiedAnnualDemand` → the LP must meet higher
  demand → more capacity / build / emissions.
- **Effect.** The energy system builds more capacity (cost & emissions ↑).
- **Scope / conditions.** One-way; **inert in a single pass** (ratio ≈ 1 without iteration); real only
  inside the loop.

---

## Cross-cutting notes

- **`energy_price` and `carbon` move the same lever** (`τ_c` on the energy good) but mean different things:
  `energy_price` is a resource-cost passthrough (recycle to avoid a phantom-revenue artifact); `carbon`
  is a tax (revenue is the point, recycled via `α_T`). Don't apply both to the same cost — they double-count.
- **Magnitudes are illustrative** until `units.deflator` (CLEWS-money ↔ GDP basis) is calibrated — this
  affects `carbon` and `investment` levels in particular.
- **Direction families:** CLEWS→OG = `energy_price`, `investment`, `health`; policy = `carbon`;
  OG→CLEWS = `discount_rate`, `demand`.
