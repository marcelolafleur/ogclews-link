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
- Higher `γ_energy` raises energy's marginal product of capital (`firm.get_r → get_MPx(Y,K,γ[m])`,
  line 220), so energy demands more capital. The economy-wide `r` is pinned by the **last** industry's
  FOC (`SS.py:493`, `firm.get_r(..., -1)`); capital is mobile across industries. The result — capital
  flows into energy, the cost of capital rises, and the other industries' investment/output are
  **crowded out** — is endogenous.

**The one guard OG-Core does not provide.** The `gamma` validator only checks `0 ≤ γ ≤ 1` *per
element*; it does **not** enforce `γ + γ_g ≤ 1`. Set `γ_energy` too high and the labor exponent
`1 − γ − γ_g` goes ≤ 0 — a broken production function — silently. The lever therefore hard-blocks any
shift that leaves the residual labor share below a floor (default 0.05). This is a real model-invariant
guard, not analyst-nannying.

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

`γ` (structural capital intensity), a per-industry `Z` haircut (the I-O cost-push route,
`io_energy_passthrough`), and an energy ITC (`set_investment_incentive`) are **three views of the same
buildout**. The channel's `validate()` warns against stacking them — pick one by the question. It also
notes that `capital_intensity` (private) and `investment` (public grid → `K_g`) are *complementary*,
not double-counting.

## Verification

- **Transform level (no solve, in `tests/test_channels.py`):** lever scale/target, the
  `γ+γ_g+labor≡1` identity, the labor-floor hard-block, the exactly-one guard; the CLEWS calibration
  readers against real files; the channel explicit + CLEWS-calibrated paths and its guardrail messages.
  All green.
- **Crowding-out (needs an SS solve; `experiments/run_capital_intensity.py`):** expected signature —
  energy `K_m` ↑, every other industry's `K_m` ↓, economy-wide `r` ↑. SS-only (fast), isolated `/tmp`
  output. Run with the OG venv (see the script header).
