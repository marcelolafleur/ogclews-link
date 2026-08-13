# Channel 2: the capital pair — why raising the capital share sheds capital

**Date:** 2026-08-13
**Purpose:** the second fresh channel explanation, in the mechanism-traced register
established by note 01. This is the channel that failed hardest in the 2026-08
presentation ("I'm not doing a very good job of explaining this"), so it is written to
be followed step by step by a hostile listener.
**Code anchors:** `ogclews_link/channels.py` (`capital_intensity`, `energy_capex`),
`ogclews_link/signals.py` (`capital_intensity_ratio`), `ogclews_link/policy_levers.py`
(`set_capital_intensity`, `set_investment_incentive`); ogcore `firm.py`
(`get_KLratio` :316, `get_cost_of_capital`), `SS.py`.
**Evidence status:** the measured numbers below come from an archived M=8 steady-state
solve, recomputed directly from the stored steady states on 2026-08-04. A re-run under
the re-blessed baseline is queued. Also note the health-shock fix of 2026-08-11 does not
touch this channel.

---

## 0. The question this channel has to answer

A clean power system is capital-heavy: solar and wind are almost entirely up-front
capital with little fuel, where a coal or gas plant is cheaper to build and then buys
fuel forever. CLEWS knows this — it reports the power fleet's capital-cost share, and
the reform's share is higher than the baseline's.

So the modelling question is: **how do you represent "the energy transition is
capital-intensive" in the economy?** The intuitive answer — make the electricity
industry's production more capital-weighted — turns out to do the opposite of what
people expect, and the model's own equations are what reveal it. That is the whole
content of this channel, and it is worth getting exactly right because it is the
clearest case where coupling to a structural model catches a mislabeling that a
spreadsheet mapping would have shipped silently.

## 1. Where capital comes from in OG-Core

Two equations do all the work. Both are in the shipped firm block.

**How much capital an industry holds.** Under the calibration's Cobb–Douglas technology
(ε = 1), the firm's first-order condition rearranges to

```
K_m = γ_m · p_m · Y_m / ρ_m
```

In words: **an industry holds capital in proportion to its revenue** (`p_m·Y_m`),
scaled by capital's share of that revenue (`γ_m`), and discounted by what a unit of
capital costs it (`ρ_m`). (In the general CES form this is `K/L =
(γ/(1−γ−γ_g))·(w/ρ)^ε` — ogcore `firm.py:316` — which is the same statement.)

**What a unit of capital costs.** From ogcore's `get_cost_of_capital`:

```
ρ_m = ( r + δ − τ^b_m·δ^τ_m − τ^inv_m·δ ) / (1 − τ^b_m)
```

The thing to notice, and the hinge of this entire channel: **γ appears in the first
equation and not in the second; the tax instruments appear in the second and not in the
first.** The capital *share* moves factor demand through the production exponent. The
*cost of capital* is moved by taxes and credits. They are different equations. This is
structural, not a calibration artifact.

## 2. The lever the intuition reaches for — and what it actually does

`capital_intensity` takes the CLEWS reform/base ratio of the power fleet's
capital-cost share and scales the energy industry's capital exponent γ_E by it
(labour's exponent is the residual, so it falls). Nothing else is touched.

Because nothing else is touched, the user cost ρ_E and the tax terms are *identical*
between the baseline and reform solves and cancel in the ratio, leaving an exact
identity:

```
K̂_E = γ̂_E · p̂_E · Ŷ_E
```

(hats = reform/baseline). Now follow the chain, with the measured numbers from the M=8
Philippine solve:

| # | What happens | Measured |
|---|---|---|
| 1 | the lever raises the energy industry's capital exponent | γ_E **+12.2%** |
| 2 | a more capital-weighted technology is *more efficient*, so unit cost falls; under zero-profit pricing the price follows | p_E **−42.8%** |
| 3 | cheaper electricity raises the quantity demanded | Y_E **+20.9%** |
| 4 | but revenue `p_E·Y_E` **falls** — the price collapse outweighs the output gain | — |
| 5 | capital is a share of revenue, so capital **falls** | K_E **−22.4%** |

Identity check: 1.122 × 0.572 × 1.209 = 0.776, i.e. **−22.4%** — matching the observed
capital response to **0.023 percentage points**. The attribution is exact arithmetic,
not a narrative.

**So: raising the capital share sheds capital.** The lever is a factor-share and
electricity-price instrument. It is *not* capital attraction, and calling it that would
have been wrong in a way no amount of careful prose would have caught — only the FOC
catches it.

Why the sign is not obvious a priori: it depends on how demand responds. If electricity
demand were elastic enough, the output gain in step 3 could outweigh the price fall and
revenue could rise. For a small, relatively demand-inelastic energy good — which is what
the PHL calibration has — it does not. The channel's own docstring says this: *"for a
small, demand-inelastic energy good a higher capital share lowers electricity's unit
cost, so energy CAPITAL need not rise."*

## 3. The lever that actually attracts capital

`energy_capex` is the capital-**demand** instrument: an investment tax credit on the
energy industry. Look again at where it lands:

```
ρ_m = ( r + δ − τ^b·δ^τ − τ^inv·δ ) / (1 − τ^b)
                          ^^^^^^^
```

The credit enters the **denominator of the capital-demand equation**, lowering the cost
of capital — so at the prevailing interest rate the industry wants more capital. γ is
absent here, exactly as τ^inv is absent from the production exponent. Capital
reallocates *into* energy (at electricity's small scale this is reallocation, not
economy-wide crowding-out), funded through the public budget.

This is the modelling answer to the scenario question you actually want to ask — *"we
are ramping up solar; simulate attracting investment into it"*: **use the credit, not
the share.**

## 4. Why both exist, and the rule that keeps them apart

They represent two different real-world facts about a capex-heavy build-out:

- the technology genuinely is more capital-weighted → `capital_intensity` (a
  *technology* statement, whose macro consequence is a cheaper electricity price and a
  factor-mix shift away from labour);
- policy genuinely is pulling investment in → `energy_capex` (a *cost-of-capital*
  statement).

They act on different equations and can move energy capital in **opposite directions**.
The accounting discipline therefore forbids treating them as interchangeable views of
one build-out, and forbids stacking them on the same capex: *the capital cost of a
generation build-out is represented once — through a cost-push or an investment
incentive, not both; and the capital-share lever is not a third interchangeable view.*
Note this is enforced by experiment composition (which channels a run applies), not by
a runtime guard inside either channel.

Separately, and not double counting: **public** grid capital reaches the economy through
the public-investment share (`investment`, channel note 3), while these two touch
**private** capital. Different objects; coupling both is complementary.

## 5. What is fragile here, stated plainly

- **Window sensitivity.** γ is time-invariant in OG-Core, so the signal freezes a single
  window (default 2026–2035) of the fleet's capital-cost share into a permanent shift.
  The signal's own note flags this: *"this share is window-sensitive (verify)."*
- **Fuel is excluded** from the share (fuel costs sit on upstream technologies), which
  makes the measured ratio conservative.
- **The solve needs continuation.** On PHL's M=8 calibration electricity's capital share
  is already high, so this reform is solved by continuation from the baseline steady
  state; a cold solve diverges. Worth knowing before anyone re-runs it.
- **The numbers are pre-re-bless** (see the evidence-status header).
- **`energy_capex` has never been run standalone** in the battery — it is defined,
  guarded, and reasoned from the FOC, but there is no measured result for it. Say so
  wherever its direction is asserted.

## 6. One-slide version

> **Raising the capital share sheds capital; the tax credit draws it in.**
> Capital is held in proportion to revenue: `K = γ·p·Y/ρ`. Raise γ by 12.2% and the
> technology gets cheaper, so the electricity price collapses 42.8%; output rises 20.9%,
> but revenue falls by more, so capital falls 22.4% — and `K̂ = γ̂·p̂·Ŷ` reproduces it to
> 0.023pp. The instrument that actually attracts capital is the investment credit: it
> enters the cost of capital ρ, where γ does not appear. Two levers, two equations,
> opposite signs — never stack them.
