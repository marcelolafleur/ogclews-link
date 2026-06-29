# The energy-price transmission: `tau_c` / own-`Z` / cost-push / composite

**Goal.** Carry a CLEWS electricity-price change into OG-Core honestly. OG-Core has no energy in
production, so there is no single "right" door — this doc compares the transmissions the link can build,
shows *why they disagree on the sign of GDP*, and lands on the composite (`energy_full`) as the best
representation achievable without an OG-Core change.

**Status:** built + run (PHL M=8, cross-env). **Audience:** OG-Core ⇄ ogclews-link maintainers.
**Cross-refs:** [energy-as-production-input-spec.md](energy-as-production-input-spec.md) (the Phase-2
"route C" rigor endpoint — a genuine OG-Core production-function PR; **deferred** by decision), and
[capital-intensity-gamma-lever.md](capital-intensity-gamma-lever.md) (a sibling lever that also mutates a
production parameter). This is the realized, **country-generic, cross-env** form of that spec's
"route-B family" plus a composite that adds the household half.

## 1. The problem — one price, two halves, no production home

A CLEWS electricity price is a *resource cost*. It has no **production-side** home in OG-Core: shipped
production is a value-added CES `Y_m = Z[t,m]·CES(K, K_g, L)` (`firm.py:22` `get_Y`) with no energy
input and **no inter-industry intermediates**; `io_matrix` is a final-demand bridge
(`p_i = io_matrix·p_m`, `SS.py:277`), not a Leontief use matrix. So the price cannot natively raise any
firm's marginal cost.

But in the real economy electricity is used **two ways**, and the PHL SAM (`celec` row) splits them:

| use of electricity | share of total | the channel it should drive |
|---|---|---|
| **intermediate** input to industry | **73%** (473) | a supply-side **cost-push** (every using sector's cost rises) |
| **final** household consumption | 25% (163) | a demand-side **cost-of-living** wedge |
| government | 2% (13) | — |

The "true" macro response therefore has **both** halves — a cost-push that contracts output *and* a
regressive household price hit — and, because intermediate use dominates ~3:1, it is **net
contractionary**. Each single transmission below captures only part of this; the composite captures both.

## 2. The four transmissions

| mode | experiment / channel | what it perturbs | half it carries |
|---|---|---|---|
| `tau_c` | `energy_price` | consumption-tax wedge on the energy good | final (demand) |
| own-`Z` (A) | `energy_price_tfp` | `Z[:,e] /= ratio` (electricity's own TFP) | final, endogenous price |
| cost-push (A′) | `energy_cost_push` | `Z[:,j] /= (1 + φⱼ(ratio−1))` per industry | intermediate (supply) |
| **composite** | **`energy_full`** | A′ (self-use zeroed) **+** recycled final-good wedge | **both** |

The mechanics rest on one identity: with value-added production, the producer price is `p_m = w/MPL` and
`MPL ∝ Z`, so **`p_m ∝ 1/Z`** ([firm.py `get_pm`/`get_MPx`]). A `Z` haircut therefore raises a producer
price; `tau_c` instead raises the consumer price as a wedge `(1+τ_c)·p_i`. Both `Z` modes propagate to
households through the **same** Leontief consumption bridge `p_i = io_matrix·p_m`.

## 3. Verified result — the 4-way (PHL M=8, controlled +20%, first-decade-mean % vs baseline)

One solved baseline, four reforms (`experiments/run_energy_price_comparison.py`):

| transmission | Y | C | K | L | r | w | elec output | energy `pᵢ` | energy consumption |
|---|---|---|---|---|---|---|---|---|---|
| `tau_c` | +0.22 | +0.03 | +0.22 | +0.23 | −0.03 | +0.02 | −9.7 | −0.4 | −16.1 |
| own-`Z` (A) | +0.24 | −0.01 | +0.25 | +0.23 | +0.03 | −0.03 | −6.5 | **+12.3** | −10.7 |
| cost-push (A′) | **−0.34** | −0.06 | −0.30 | +0.21 | −0.10 | **−0.53** | −1.1 | +1.7 | −1.7 |
| **composite** (`energy_full`) | **−0.40** | −0.06 | −0.37 | +0.17 | −0.12 | **−0.50** | **−7.6** | −0.3 | **−12.5** |

## 4. Why the GDP signs disagree (the economics)

This is the crux, and it is a **structural** consequence of value-added-only production, not a
calibration slip:

- **`tau_c` (+0.22) and own-`Z` (+0.24) are artifacts.** A `Z` cut on electricity is a negative TFP shock
  to **one small sector**. There is no inter-industry use matrix, so the cost never reaches the other
  seven sectors' marginal cost; the freed `K`/`L` reallocate into those unshocked sectors, and the OLG
  household *factor-supply* response to the higher cost-of-living (work more, save more → `K +0.25`,
  `L +0.23`) dominates the tiny own-sector efficiency loss. Measured GDP rises **even though welfare
  falls** (`C`, `w` down). The "+" is a household-supply/reallocation artifact — the **wrong macro sign**
  for a world where electricity is an intermediate.
- **Cost-push (A′, −0.34) has the right sign.** A broad, `φⱼ`-weighted productivity loss is a genuine
  economy-wide negative supply shock: output falls and the **immobile factor (labor) bears it**
  (`w −0.53`; capital is cushioned by the partially-open closure, `r −0.10`). This is the textbook
  cost-push incidence — and the channel OG-Core structurally lacks, restored as a reduced-form proxy.
- **The SAM settles it.** Electricity is 73% intermediate, so the true response is cost-push-dominated →
  **negative**. A′ is directionally right; A/`tau_c` are faithful only to the 25% consumption piece.

The composite makes both visible at once (§5). *(Adversarially verified — 6-agent theory pass + the
PHL run; the `Z ∝ 1/p` mechanics, the factor-supply decomposition, and the SAM split were each checked
against the equations.)*

## 5. The composite — `energy_full` (the recommended default)

`energy_full` injects the same +20% through **both** uses, decomposed by the SAM:

```
                 CLEWS: electricity price +20%
                          │
        ┌─────────────────┴───────────────────┐
        ▼ intermediate (73%)                   ▼ final (25%)
   each industry j cost  +φⱼ·20%          households pay +20% on the
        │                                  electricity in the energy good
        ▼                                       │
   energy_cost_push (φⱼ haircut,                 ▼
   electricity self-use ZEROED)            recycled energy_price wedge
        │   GDP↓, wages bear it             │   regressive cost-of-living
        └─────────────────┬───────────────────┘
                          ▼
            energy_full = cost-push sign  +  household incidence
```

Reading the composite row against the singles: GDP **−0.40%** with `w −0.50%` (the A′ cost-push, in fact
slightly *deeper* — the wedge does **not** flip the sign positive), **and** the household channel
restored — electricity output **−7.6%**, energy consumption **−12.5%** — which A′ alone almost entirely
missed (−1.1 / −1.7).

Two construction choices make it consistent:

- **Electricity's own self-use is zeroed** in the cost-push (`φ_e ← 0`), so electricity's price is not
  raised twice — once through its own `Z` (cost-push self-use) and again through the final wedge.
  Precisely: zeroing drops electricity's *own-use* cost-push on its producer price (which would
  double-count against the household wedge), at the cost of the *second-round propagation* of that
  own-use cost to other industries — which the final wedge does **not** capture and which only a true
  use matrix (Option B) would. So the zeroing is conservative and keeps the "lower bound" claim honest.
- **The final wedge is recycled.** A CLEWS price is a *resource cost*, not a levy, so the wedge revenue
  is rebated lump-sum (`recycle_revenue_to_transfers=True`). This removes the phantom government revenue
  that inflates `tau_c`-alone: the recycled wedge contributes only **~−0.06** to GDP (full −0.40 vs A′
  −0.34), versus `tau_c`-alone's **+0.22** — direct confirmation that `tau_c`'s positive sign was an
  unrebated-revenue artifact, not a price effect.

The final wedge is sized `price_ratio = 1 + share·0.20`, where `share = io_matrix[energy_good,
energy_industry]` is electricity's **io_matrix (Leontief) weight in the energy consumption good** — for
PHL, **0.737** (a +14.7% wedge on the energy good). Note this is *not* the SAM's 25% final-demand share
from §1: the two measure different things — `io_matrix[good,industry]` is *what fraction of the energy
good's composition is electricity*; the 25% is *what fraction of all electricity goes to households*. The
wedge dilutes by the former because that is the model-consistent weight at which electricity's price
enters the energy good's price `p_i = io_matrix·p_m`.

A **couplability gate** opens the composite: it needs the country to isolate electricity as its own
industry *and* good (both `ctx.concordance` ports). When it can't — single-industry `M=1`, or electricity
fused with water — the composite skips both legs cleanly (records a skip, mutates nothing). The standalone
`energy_cost_push` experiment stays SAM-driven / concordance-independent by design.

## 6. Country-generality — nothing is hardcoded to PHL

*(Reconciled against the pre-merge audit — see §9.)* The transmission is country-agnostic by
construction: every country-varying quantity is **discovered per run**, **derived from shapes**, or
**passed in** — none is a PHL literal in the channel code.

| quantity | source | not hardcoded because |
|---|---|---|
| electricity industry index | `ctx.concordance.energy_industry_index` | discovered per run from the country package's `PROD_DICT`/`CONS_DICT`, exported in `baseline_meta.json` |
| energy good index | `ctx.concordance.energy_good_index` | same |
| `M` (industry count) | `Z.shape[1]` | derived from the solved baseline |
| `φⱼ` intensity vector | `aggregation.input_intensity(sam, prod_dict)` | read link-side from *the installed country's* SAM (`discovery._read_sam(source_dir)`), aligned to `PROD_DICT` order |
| `share` (final-wedge dilution) | `io_matrix[energy_good, energy_industry]` | a cell of the country's own calibrated `io_matrix` |
| the SAM path / package | `registry.lookup(ctx.country)` → `source_dir` | from the registry, whatever the user installed |

**Degrade paths (empirically verified, all four non-PHL cases):** `energy_full`'s couplability gate
skips the whole composite when `ctx.concordance` can't isolate electricity (single-industry `M=1`, or
electricity fused with water) — clean no-op, no SAM read, no mutation. A couplable country that ships no
SAM yields `_electricity_intensity → None`, so the cost-push leg skips while the concordance-resolved
final wedge still fires. The standalone single-channel experiments skip via `_skip_if_unavailable` on a
`None` port. The transform tests run at **M=4, electricity index 1** *and* explicitly at **index 2** — so
a green suite is direct evidence the Z-haircut / self-use-zeroing / wedge are index-driven, not fixed to a
PHL-specific position.

## 7. Honest limits, and the ladder to the rigorous version

`energy_full` is the **best link-side** representation, not the exact one:

1. **It is a reduced-form composite** — two stacked `Z`/`tau_c` proxies for a channel OG-Core lacks. A
   `Z` haircut conflates "costlier input" with "less productive" and has **no factor substitution** away
   from dear electricity, and no intermediate *quantity* to reconcile with CLEWS supply.
2. **`−0.40%` is a lower bound.** The first-order `φⱼ` haircut omits the Leontief-inverse `(I−B′)⁻¹`
   upstream amplification (a sector also buys electricity-intensive inputs from other sectors), so the
   true contraction is somewhat larger.

The improvement ladder (only the last needs OG-Core):

| tier | what | where | gains | still missing |
|---|---|---|---|---|
| `energy_full` (now) | first-order `φⱼ` + wedge | link | correct sign, both halves | amplification; substitution; quantities |
| **B-lite** | `(I−B′)⁻¹`-amplified haircut | link | full cost incidence + amplification | substitution; quantities |
| **Option B** | gross-output + use matrix | OG-Core engine, per-country `B` | everything, endogenously | — |

B-lite is a drop-in upgrade to `energy_cost_push` (build `B` from the SAM use block already parsed by
`ogphl/input_output.py`, apply the Leontief-amplified vector). Option B is the
[energy-as-production-input-spec.md](energy-as-production-input-spec.md) endpoint — a shared OG-Core PR
(per-country `B` data is already in each SAM), deferred by decision.

## 8. Double-counting discipline

`tau_c`, own-`Z` (A), and cost-push (A′) are **alternative transmissions of the same shock** — never
stack them as if they were separate effects. `energy_full` *composes* A′ + a final-good wedge
deliberately, by **use** (intermediate vs final), with electricity's self-use zeroed so the two halves
do not both move electricity's own price. This is the same discipline as the sibling levers
([capital-intensity-gamma-lever.md](capital-intensity-gamma-lever.md) §"Double-counting"): `γ`, a `Z`
haircut, and the ITC act on different objects and are not interchangeable.

## 9. Verification

- **Transform level (no solve, `tests/test_channels.py`):** `energy_price_tfp` lowers only the energy
  industry's `Z` (others untouched), skips with no `energy_industry_index`, and rejects a non-positive
  ratio; `energy_cost_push` haircuts each industry by `φⱼ`, skips on a `None` intensity, guards the
  vector shape (`(M,)`), and rejects both a non-positive ratio and a price-drop large enough to collapse
  the push factor; `input_intensity` recovers the right `φⱼ` from a synthetic SAM (scalar, list-of-codes,
  and the no-commodity-row / zero-output branches); `_electricity_intensity` reads a stubbed
  registry→SAM→`input_intensity` chain and degrades a wrong-length vector to `None`; `Z` is in the
  override diff only when changed; `energy_full` cost-pushes using-industries, **zeroes** electricity's
  self-use, applies the diluted final wedge, **routes at a non-unit index (2)**, and **skips when not
  couplable** (wedge-only when no SAM); the three modes touch **disjoint state** (Z modes leave `tau_c`,
  the wedge leaves `Z`). All green (suite 126 pass / 1 skip).
- **Cross-env SS+TPI run (`experiments/run_energy_price_comparison.py`):** the 4-way table in §3, on the
  live PHL M=8 multisector baseline (reused from cache), all four reforms converged (exit 0).
- **Economics:** the sign decomposition, the `Z ∝ 1/p` mechanics, the SAM 73/25 split, and the
  recycled-wedge consistency check were adversarially verified (6-agent theory pass + a pre-merge
  generality/economics/test audit).
