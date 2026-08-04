# Channel 1: the electricity price — the definitive explanation

**Date:** 2026-08-04
**Purpose:** the first of the fresh channel-by-channel explanations, rebuilt after the
2026-08 presentation to Rick and Jason. Written to answer, head-on, the four questions
that failed in the room. Every claim carries its code anchor (link code in this repo;
`ogcore` cites from the solving package, ogcore 0.16.3).
**Sources:** `ogclews_link/channels.py:80–226`, `ogclews_link/experiments.py:60–81`,
`ogclews_link/channels.py:23–54` (`_recycle_via_transfers`); ogcore `SS.py:277`,
`aggregates.py:392,599–619,310–436`, `household.py:343–397`, `firm.py:566`,
`fiscal.py:383–385`; the presentation transcript.

---

## 0. What the channel must accomplish

CLEWS says the reform makes a delivered unit of electricity ~5% more expensive on
average (peaking ~16% around 2030 — the LCOE ratio). That one fact has to reach the
economy on **two margins**:

1. **Industries' costs** — in the Philippine SAM, roughly **three quarters** of
   electricity is bought by industries as an input.
2. **Households' cost of living** — the remaining quarter is final consumption.

Getting both margins, without counting any peso twice, is the whole design problem.

## 1. The constraint that shapes everything: OG-Core has no intermediates

Two structural facts about OG-Core, stated exactly:

- **Production is value-added only.** Each industry produces
  `Y_m = Z_m · CES(K_m, K_g, L_m)`. Firms buy *nothing* from each other — there is no
  input-output block on the production side. An electricity price has **no native door
  into any other industry's cost function.**
- **Consumption goods are a fixed bridge over industry outputs.** Goods prices are
  `p_i = io_matrix · p_m` (ogcore `SS.py:277`, `aggregates.py:392`), and quantities go
  back `Y_m = io_matrixᵀ · C_i` (`SS.py:464`). The `io_matrix` is **I×M, fixed
  coefficients** — it maps industry outputs into consumption goods with *no
  substitution across industries* (Jason said this himself in the room: "you've got
  this fixed coefficient matrix anyway, there's no substitution across those
  outputs"). Note what this matrix is NOT: it is a *consumption* bridge, not an
  intermediate-use matrix.

So electricity's price can reach households through the goods bridge, but the
three-quarters of it that is an *industry input* has no structural path. Everything
below is the consequence of that.

## 2. The three routes in code — and the answer to "why is changing Z not enough?"

The link implements **three** transmissions of the same price ratio `r_t`
(reform/baseline). Each is a real function; each answers a different part of the
problem; none suffices alone.

### (a) `energy_price` — the household wedge (`channels.py:80`)

Sets the consumption-tax rate on the energy good so the gross price inherits the
ratio: `1 + τ^c,new = r · (1 + τ^c,base)`. This enters OG-Core exactly where OG-Core
puts consumption taxes:

- the cost-of-living index `p̃ = ∏((1+τ^c_i)p_i / α_i)^{α_i}` (`aggregates.py:616`),
- subsistence spending `Σ(1+τ^c)p_i·c_min` (`household.py:343`),
- the sub-good demand `c_i(c, p_i, p̃, τ^c, c_min)` (`household.py:373`).

It delivers demand response and **incidence** (with `c_min[energy] > 0`, poorer
households spend a larger share → regressive). It does **not** touch production, and
it mechanically books government revenue (§4).

### (b) `energy_price_tfp` — the firm-side route (`channels.py:142`). This IS Jason's suggestion.

Jason asked: *"why not put it on the firm side — since there's already a p_m, maybe
they get p_m minus something?"* — a producer-side representation instead of a
consumer tax. We can't do literally that: OG-Core has no parameter that drives a gap
between what a firm's output sells for and what the firm receives. Prices in OG-Core
aren't set by a dial — they're an *outcome*: every industry prices at cost (zero
profit), so `p_m` is whatever it costs to produce one unit.

But because price = unit cost, there *is* a dial that moves `p_m`: productivity. If
electricity's `Z` falls 5%, producing a unit takes ~5% more inputs, so its unit cost
— and therefore its price — rises ~5% (`firm.py:566`, `get_pm`; `p_m ∝ 1/Z` holding
factor prices). That's `Z[:, e] /= r`: we change one deep parameter, and the higher
price *emerges from the model's own equilibrium* — which is exactly what Jason wanted.
And because it emerges in equilibrium, everything responds: wages, the interest rate,
electricity's own K and L. That's the GE response the τ^c wedge doesn't have.

**Why it's still not enough — trace who actually pays.** In reality, two kinds of
buyers pay a higher electricity price: households (their bills) and **industries
(the electricity they use in production — three quarters of all use).** In OG-Core,
only the first group exists: no firm buys anything from any other firm, so there is
no line in manufacturing's cost function where electricity appears — at any price.
Trace the Z route through: electricity's Z falls → `p_m` rises → the energy
*consumption good* gets dearer → **households pay. Full stop.** Manufacturing's
costs, prices, and decisions: unchanged. The three quarters of the shock that
industrial buyers should pay vanishes, because those buyers don't exist in the model.
The route is not wrong — it is *incomplete by construction*: it can deliver the shock
only to the quarter of its real-world destination the model represents.

A second, subtler liability: it encodes a **system**-cost change as an
electricity-**technology** change, so the sector's own K/L/Y reorganise in response
to a productivity event that did not occur in the scenario (compare the
capital-share lesson, channel note 3, forthcoming).

### (c) `energy_cost_push` — the missing-intermediates proxy (`channels.py:185`)

For the three-quarters that is an industry input, the link does the only thing the
structure allows: a calibrated per-industry cost shock. From the country SAM,
`φ_j` = electricity's share of industry j's input costs (`aggregation.input_intensity`);
then `Z[:, j] /= (1 + φ_j (r−1))`, which raises each industry's price by ≈ `φ_j(r−1)`
— the first-order cost pass-through an intermediate-input structure would deliver.
The code labels this **illustrative**: `φ_j` is a calibrated weight, not a structural
equation. This is the honest version of "we're shocking industry somehow": the *size*
comes from data (the SAM), the *mechanism* is imposed because the structural door
does not exist.

## 3. What actually runs: the composite (`experiments.py:60`, used by `coupled`)

`_apply_energy_composite` applies **both margins at once, partitioned by use**:

1. `energy_cost_push` with `φ` from the SAM — and **electricity's own self-use zeroed
   out** of φ (`experiments.py:75`), so the sector's own consumption isn't in both legs;
2. `energy_price` on the household share, with the ratio **diluted to electricity's
   value-share of the energy good** (`wedge = 1 + share·(r−1)`; share ≈ 0.39 for PHL,
   because the "energy good" bundle is not all electricity), and with
   `recycle_revenue_to_transfers=True`.

Accounting: every peso of the price rise enters exactly once — intermediate exposure
through φ, final exposure through the diluted wedge, the overlap (self-use) removed.

## 4. The revenue question — the precise answer Jason asked for

**What the wedge does mechanically.** τ^c revenue is real inside OG-Core: it flows
through `cons_tax_liab` into `total_tax_revenue` (`aggregates.py:399–431`) and the
government budget. If we set the wedge and did nothing else, the government would
"collect" the electricity price increase; under the debt-rule closure that is an
accidental **fiscal consolidation** riding along with the price shock. That would be
wrong, because the price rise is **not a tax** — it is a real resource cost: the
economy genuinely uses more resources to get the same electricity, and no government
gets that money.

**What the code does** (`_recycle_via_transfers`, `channels.py:23`): the wedge's
revenue is returned to households **lump-sum** through the transfer share
(`TR = α_T · Y`, `fiscal.py:383`): the α_T path is bumped by
`Δτ^c · p_i · C_i / Y` (estimated on baseline quantities, floored at α_T ≥ 0). The
wedge is therefore **revenue-neutral by construction**: households face the higher
*relative* price of energy — the substitution and incidence effects — while the
income the wedge would have extracted is handed back. No phantom government windfall,
and no phantom stimulus either.

**Then where does the real cost live?** In the cost-push leg. The Z haircuts destroy
real productive capacity — which is exactly what "the economy pays more real
resources for the same electricity" means at this level of structure. So the division
of labour is: **the wedge carries relative prices and incidence (neutralized
fiscally); the cost-push carries the real resource loss.** The transcript's instinct
("it's a dead weight captured by the electricity producer — you can't recycle that")
is honored: nothing is spent as if the government got richer, and the resource cost
is not erased by the rebate because it enters through production, not through the
wedge.

**Honest caveats, so they're said before a reviewer says them:** the recycle is
first-order (baseline quantities, slightly overstating reform revenue); and the
*split* of the real cost between "productivity loss" (a resource cost) and "transfer
to the energy sector's factors" (a redistribution) is a modeling choice that only the
structural form (§5) can resolve properly.

## 5. What Option B changes, and why this design is the interim

The structural fix is a real intermediate-input block: an M×M use matrix and energy
in the firm's technology (`docs/design/energy-as-production-input-spec.md`). Then the
cost-push becomes an equation instead of a calibration, the composite collapses into
one mechanism, firms substitute away from expensive electricity, and the loop can
close on quantities. Two facts make it nearer than it looks: the IFPRI SAM already in
OG-PHL contains the intermediate-use block (the data exists; the barrier is OG-Core's
firm side), and — as discussed in the room — the multi-industry investment work heads
in the same structural direction.

## 6. The numbers this channel produces (current golden record)

- Real PHL price path: LCOE ratio ≈ 1.05 mean, 1.16 by 2030 (the marginal/shadow
  price is degenerate and never auto-selected — `experiments.py:84`).
- Household wedge alone on the real price: `Y_ss = −0.006%` — honestly transmitted,
  a 5% electricity price moves aggregate output little.
- Recycled variant (`clean_incidence`): aggregate `C_ss = −0.092%` **even with full
  recycling**, concentrated on lower-income households — the regressivity is a real
  relative-price result, not a fiscal artifact.
- The composite is what `coupled` transmits (electricity output −2.0% there).

## 7. One-slide version (for the rebuilt deck)

> **The electricity price enters twice, because electricity is used twice.**
> Households (¼ of use): a consumption wedge, `1+τ^c ← r·(1+τ^c)`, revenue rebated
> lump-sum — relative price and incidence, no fiscal side-effect.
> Industries (¾ of use): a calibrated cost-push, `Z_j ÷= 1+φ_j(r−1)` — the real
> resource cost, sized by the SAM because OG-Core has no intermediate inputs.
> Self-use is netted out; each peso enters once. The firm-side alternative (lower
> electricity's Z, let p_m rise endogenously) exists in code and still reaches only
> consumption — that is the structural gap, and the M×M use matrix is the fix.
