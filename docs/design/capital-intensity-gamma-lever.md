# Private-generation capital intensity: the `gamma_energy` lever

**Goal.** Make OG-Core reflect the energy transition's *private* generation investment — the
capital-intensive renewables/CCS buildout — using OG-Core's existing levers, with no new mechanism.

**Why this is separate from the investment channel.** The `investment` channel is, by settled design
(commit 448c458), **public-infrastructure-only**: it routes genuine public infra (grid/T&D, via
`country.is_public`) into `alpha_I -> K_g`, OG-Core's government public-capital lever. Private
generation capex must *not* go through `alpha_I` — that would mischaracterize private spending as
productivity-enhancing public capital, and for PHL/PEP the grid-capex delta is ~0 anyway. So the
private side needs a different home. This is it.

## The mechanism (verified against ogcore 0.16.1 `firm.py`)

OG-Core has **no exogenous "inject private capital" dial** — private capital is endogenous (households
save → firms rent capital). But it has a real **multi-industry capital market**. So we reflect the
buildout by making the **energy industry more capital-intensive** and let everything else emerge:

- Production is CES/Cobb-Douglas in `(K, K_g, L)`:
  `Y_m = Z_m · K^{γ_m} · K_g^{γ_g,m} · L^{1−γ_m−γ_g,m}` (`firm.get_Y`).
- `γ` (`p.gamma`) is the **per-industry capital share** — a length-`M`, **time-invariant** vector
  (`p.gamma[m]` is a scalar exponent). So this lever is inherently a **permanent, steady-state**
  structural change, not a transition-flow knob.
- **Labor's share is the pure residual `1 − γ − γ_g`** (`firm.get_w`, line 257) — there is *no*
  separate labor-share parameter. Raising `γ_m` lowers labor's share automatically; nothing else to set.
- Higher `γ_energy` raises capital's *marginal product per unit output* (`get_MPx`), so per unit of
  output energy uses more capital. **But the LEVEL of energy capital is `K = γ·p·Y/ρ` (capital's
  revenue share = γ), and in GE the industry's scale and price are not free.** The economy-wide `r`
  (hence the cost of capital `ρ`) is pinned by the **last** industry's FOC (`SS.py:493`,
  `firm.get_r(..., -1)`), and the energy good is small and demand-inelastic. The naive "capital flows
  in, `r` rises, others crowded out" intuition does **not** survive GE — see the verified result below.

**The one guard OG-Core does not provide.** The `gamma` validator only checks `0 ≤ γ ≤ 1` *per
element*; it does **not** enforce `γ + γ_g ≤ 1`. Set `γ_energy` too high and the labor exponent
`1 − γ − γ_g` goes ≤ 0 — a broken production function — silently. The lever therefore hard-blocks any
shift that leaves the residual labor share below a floor (default 0.05). This is a real model-invariant
guard, not analyst-nannying.

## Verified result — γ is a factor-share/price lever, NOT crowding-out

A PHL M=4 SS solve (`experiments/run_capital_intensity.py`, both sides converged, RC error ~1e-14; raw
`SS_vars.pkl` inspected directly) for the calibrated shift γ_energy 0.538 → 0.604 (×1.122):

| Electricity | base | reform | Δ |
|---|---|---|---|
| output price `p_m` | 0.7217 | 0.5484 | **−24.0%** |
| capital `K_m` | 0.0274 | 0.0235 | **−14.0%** |
| output `Y_m` | 0.00729 | 0.00735 | +0.8% |

with `r`, `w`, and aggregate `K`/`L`/`Y` all flat (≤0.02%) and the other industries' `K` +0.03–0.07%.

**Energy capital FALLS — the opposite of the naive expectation — and it is correct GE behavior.** The
firm identity closes to 0.02%: `K̂ = γ̂·p̂·Ŷ = 1.122 × 0.760 × 1.008 = 0.860` (observed 0.860; implied
cost-of-capital ratio 0.9998). The driver is a **price collapse**: raising the capital exponent (ε=1,
`Z` fixed) re-weights the sector toward its abundant factor, cutting unit cost; under zero profit the
energy price falls ~24%; demand is inelastic so output barely moves (+0.8%); and capital — γ's share of
a *shrunken* revenue `p·Y` — falls. So `capital_intensity` is a **factor-income / energy-price /
distributional** lever, not an investment surge.

**The capital-DEMAND story (energy draws in capital) belongs to the ITC, not γ** — and even there it is capital *reallocating into* energy, not economy-wide crowding-out (at PHL's small electricity scale `r` stays flat and the other industries' `K` edge up). `set_investment_incentive`
lowers the energy industry's *cost of capital* `ρ` (γ is absent from `firm.get_cost_of_capital`;
`inv_tax_credit` enters it directly), shifting capital demand out at the going `r`: energy `K` **+5%**,
financed through the government budget (a small debt cost). γ, a per-industry `Z` haircut, and the ITC
act on **different objects** (factor exponent vs TFP vs cost of capital) — γ and the ITC give **opposite
signs** on energy `K`, so they are not interchangeable.

## The lever — `policy_levers.set_capital_intensity`

```python
set_capital_intensity(p, industry_index, *, gamma_target=None, gamma_scale=None,
                      labor_share_floor=0.05)
```

Generic (by index, duck-typed `p`, like `set_investment_incentive`). Pass exactly one of an absolute
`gamma_target` or a multiplicative `gamma_scale`. Mutates `p.gamma[m]`, hard-blocks `γ>1` and the
labor-floor violation, returns provenance (`gamma_old/new`, `gamma_g`, `labor_share_old/new`, `mode`).

## Calibration — from CLEWS, relative shift

We keep the **baseline** `γ_energy` as solved (the M=4 build broadcasts the economy-wide capital share
uniformly: `gamma=[0.53785]*4`, `gamma_g=0.05`, `ε=1`, so baseline labor share = 0.412 for every
industry) and apply only the CLEWS reform/base **change** — mirroring every other channel, which all
use reform/base ratios and so cancel the (uncalibrated) money units:

> `γ_energy^reform = γ_energy^base × (s_K^reform / s_K^base)`

where `s_K` is **capital's share of the power fleet's annualized own cost** over a window
(`signals.capital_cost_share`):

> `s_K = Σ AnnualizedInvestmentCost / Σ (AnnualizedInvestment + FixedO&M + VariableO&M)`,
> summed over `PHL_POW*` techs.

Renewables/CCS are nearly all capital recovery (no fuel), so a cleaner mix raises `s_K`.
`signals.capital_intensity_ratio` returns the ratio + provenance; the `capital_intensity` channel reads
it (window defaults to the scenario's first decade, `og_start_year .. +9`).

**Empirical (v6-Base vs v6-PEP, 2026–2035 window):**

| | base `s_K` | reform `s_K` | ratio | `γ_energy` | labor share |
|---|---|---|---|---|---|
| First decade 2026–35 | 0.521 | 0.584 | **1.122** | 0.538 → **0.604** | 0.412 → 0.346 |
| Whole horizon 2020–53 | 0.621 | 0.633 | 1.019 | 0.538 → 0.548 | 0.412 → 0.402 |

The first decade (the active build-out) is the chosen anchor: it matches the `[:10]` window the other
channels use, and gives a clear, feasible shift. `window` is a parameter, so the others are one-line
sensitivity checks.

**Caveats (documented, not hidden):**
1. **Fuel is excluded.** In this CLEWS build fuel sits on upstream supply techs, not the `PHL_POW`
   plants (their VariableOperatingCost ≈ 0). So `s_K` is capital's share of the plants' *own* cost — a
   **conservative** proxy (including fossil fuel OPEX would widen the base-vs-reform gap, not shrink it).
2. **Window-sensitive.** `s_K` drifts 0.12 → ~0.70 over 2020–53 and the ratio is non-monotonic (>1
   near-term, <1 by 2053, as the baseline fleet also turns over). A single window is frozen into the
   permanent `γ`; the choice is a calibration decision, surfaced in the provenance `note`.
3. **Relative, not absolute.** The baseline `γ_energy` (0.538) is the economy-wide average, not
   electricity's true factor share. We deliberately scale only the *change*. Re-baselining energy's γ to
   electricity's own level is a separate (out-of-scope) baseline re-calibration.

## Double-counting discipline

`γ` (factor-share/price), a per-industry `Z` haircut (the I-O cost-push route, `io_energy_passthrough`),
and an energy ITC (`set_investment_incentive`, cost of capital) act on **different objects** and are
**not** interchangeable "views of the same capex" — γ and the ITC even move energy `K` in *opposite*
directions (see the verified result). Don't stack them for the same buildout (double-count), and don't
substitute one for another's question. Separately, `capital_intensity` and `investment` (public grid →
`K_g`) are *complementary* (different capital, different lever), not double-counting.

## Verification

- **Transform level (no solve, in `tests/test_channels.py`):** lever scale/target, the
  `γ+γ_g+labor≡1` identity, the labor-floor hard-block, the exactly-one guard; the CLEWS calibration
  readers against real files; the channel explicit + CLEWS-calibrated paths and its guardrail messages.
  All green.
- **SS solve (`experiments/run_capital_intensity.py`):** done and verified (see "Verified result"
  above) — energy `K` −14% via the −24% price collapse, `r` flat, the `K = γ·p·Y/ρ` identity closes to
  0.02%. The script prints the price and the identity decomposition; it does **not** assert a
  capital-draw-in signature (that is the ITC lever's — `run_energy_itc.py`, energy `K` +5%, capital reallocating into energy with no macro crowd-out at this scale).
