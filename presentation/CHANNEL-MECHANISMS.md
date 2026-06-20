# OG-Core ⇄ CLEWS — channel mechanisms

Each channel gets two passes: **What happens** — a plain account of the real-world story — and
**In the model** — how OG-Core (and CLEWS) actually carry it, naming the parts. CLEWS→OG and policy
channels *change* an OG input; OG→CLEWS channels *read* an OG output and hand it to CLEWS, so their
effect on the economy only returns once the two models are run together in a loop.

## Summary

| # | Channel | Direction | OG-Core object | moves / reads | One-line effect |
|---|---------|-----------|----------------|:---:|-----------------|
| 1 | Energy price | CLEWS→OG | `τ_c` — price wedge on the energy good | **moves** | demand ↓; incidence (regressive *if* energy is a necessity, `c_min`>0) |
| 2 | Investment | CLEWS→OG | `α_I` → `K_g` — public investment → public capital | **moves** | productive public capital (output↑) vs debt/tax financing (crowds out). **Public infrastructure only** |
| 2b | Capital intensity | CLEWS→OG | `γ[m]` — energy industry's capital share | **moves** | capex-heavy generation → pulls in capital, ↑`r`, crowds out, ↓labour share (private twin of investment) |
| 3 | Carbon price | policy → both | `τ_c` on **household** energy (+`α_T` recycle); CLEWS `EmissionsPenalty` | **moves** | household demand ↓ + revenue; CLEWS emissions ↓ |
| 4 | Cost of capital | OG→CLEWS | `r_p` — equilibrium return | *reads* | shifts CLEWS build mix; effect via the loop |
| 5 | Health | CLEWS→OG | `ρ` (mortality) **and** `e` (effective labour) | **moves** | mortality→demographics (≈0, elderly); morbidity→productivity (the main gain) |
| 6 | Demand | OG→CLEWS | `Y_m` / `C_i` — activity | *reads* | more CLEWS capacity; effect via the loop |

---

## 1 · Energy price
*CLEWS → OG · the cost of energy reaches households*

**What happens**
When the energy system gets more expensive to run, that cost lands on household energy bills. People
respond to the higher price by using less. But the burden isn't shared evenly: energy is a basic
necessity, and lower-income families spend a bigger share of their budget on it, so the same increase
hits them hardest. So the channel does two things at once — it lowers energy use, and it shows who
carries the cost. A higher price here also works like a tax, so the extra money goes to the government,
and **the user decides what happens to it** — by default it's kept (leaving families poorer), or it can
be returned to households, which offsets most of the loss.

**In the model**
OG-Core doesn't treat energy as an input to production, so the price can only act through households —
it enters as a mark-up on the price of the energy good they buy (a consumption-tax wedge, `τ_c`). From
there it works through a few connected parts:
- energy becomes costlier relative to everything else, so households buy less of it — the demand
  response (their demand for the energy good, `c_i`);
- their overall cost of living edges up too (the composite price, `p̃`), trimming all spending a little;
- the model can treat energy as a necessity with a *subsistence floor* (`c_min`) — an amount families
  need whatever the price. That floor is what makes the burden regressive: poorer households can't cut
  below it, so the rise costs them a larger share. Without it, everyone cuts back in the same proportion.

Because the model follows households separately by income and age (`J` income groups × `S` ages), this
one price change yields a full map of who loses how much — the incidence. The mark-up also raises
consumption-tax revenue (`cons_tax_revenue`), and **the user decides what's done with it** — by default
it stays in the government budget; returned as transfers (`α_T`) it isolates the pure price effect,
otherwise the channel is a net tax whose effect depends on how the budget is balanced.

---

## 2 · Investment
*CLEWS → OG · paying for the public build-out*

**What happens**
Building out the power system takes a lot of money up front. When that spending is *public* — the
transmission and distribution grid — it adds to the country's public infrastructure, which makes the
whole economy a little more productive. But it has to be paid for, by borrowing or taxes, and that money
competes with everything else, crowding out other spending. Whether the economy comes out ahead depends
on how the bill is financed. One thing to be clear about: this channel is only about the *public*
infrastructure. The far larger sum — private companies building power plants — works through a different
channel (it shows up as the cost of energy), not here.

**In the model**
On the CLEWS side, the public-infrastructure (grid / T&D) build appears as a stream of capital spending,
converted to a share of GDP. That feeds OG-Core's public-investment lever (`α_I`), which adds to the
stock of public capital (`K_g`). Public capital is productive in the model — it lifts output across every
industry (its strength set by `γ_g`). At the same time the spending lands on the government's budget
(financed by debt or taxes) and competes for savings, which crowds out other investment. The net sign
isn't fixed — it depends on how the budget is closed. **Scope:** only genuinely public infrastructure
routes here. Private generation capex is a *separate* mechanism with its **own channel — capital
intensity (#2b below)**, the structural `γ` route; or the **energy cost-push** (`Z`); or a **capex
incentive** (`set_investment_incentive`, an ITC). Those are three views of the same capex — use one;
none is this (public) channel. Magnitudes are illustrative until the CLEWS-money↔GDP conversion
(`units.deflator`) is calibrated.

---

## 2b · Capital intensity
*CLEWS → OG · the clean buildout is capital-heavy*

**What happens**
A clean-energy buildout — wind, solar, CCS — is capital-heavy: expensive to build, cheap to run, the
mirror image of fuel-burning plants. So the energy sector becomes structurally more about capital and
less about fuel and labour. That pulls the nation's investment toward energy, nudges up the cost of
borrowing for everyone, and leaves a little less capital for other industries. It's the private-sector
twin of the public grid build-out (the **investment** channel): same story — building the clean system
soaks up capital — but for the plants companies own, not the public grid.

**In the model**
OG-Core has no "inject private capital" dial — private capital is endogenous (households save, firms rent
it). So a capex-heavy mix is represented *structurally*: raise the energy industry's **capital share
`γ[m]`** in its production function. A higher `γ` lifts energy's marginal product of capital, pulling
capital in; the rise in the economy-wide interest rate and the crowding-out of other industries then
emerge **endogenously** from OG's multi-industry capital market. Labour's share is the residual
`1 − γ − γ_g`, so raising `γ` automatically lowers energy's labour share (hard-blocked below a floor).
Calibrated from CLEWS as the reform/base ratio of the power fleet's capital-cost share
(`signals.capital_intensity_ratio`); permanent/structural. **Complementary** to the public `investment`
channel (`α_I → K_g`) — different capital, different lever — and **one of three views** of generation
capex (`γ` here / `Z` cost-push / ITC); use only one.

---

## 3 · Carbon price
*policy → OG and CLEWS · one price, set once, applied both sides*

**What happens**
A carbon price is a single policy lever, set once and applied to both models, and it does two jobs. In
the energy system it makes dirtier options more expensive, so the least-cost plan shifts toward cleaner
ones and emissions fall. For households it raises the price of the energy they buy — so, exactly like the
energy-price channel, they use less, and it raises revenue, with **the user deciding what happens to that
revenue** (by default kept; it can be returned to households). One limit worth stating plainly: on the
economy side the price only reaches the energy households buy directly. It can't price the carbon used by
industry, because the economy model has no energy in production — the economy-wide carbon price lives on
the energy-system side.

**In the model**
One carbon price (USD/tCO₂) is set once and fed both ways. On the energy-system side it enters as an
emissions penalty (`EmissionsPenalty`), shifting the least-cost mix. On the economy side it enters
exactly like the energy-price channel — a mark-up (`τ_c`) on the household energy good — so the same
demand response and incidence apply, and it books consumption-tax revenue (`cons_tax_revenue`) that the
user can recycle as transfers (`α_T`). The scope limit is structural: OG-Core has no energy in
production, so the `τ_c` tax reaches only household energy (a small share of consumption); industrial and
economy-wide carbon is priced only on the CLEWS side. (Magnitudes illustrative until `units.deflator` is
calibrated.)

---

## 4 · Cost of capital
*OG → CLEWS · the economy's interest rate guides the energy plan*

**What happens**
How much a country values the future — captured in its interest rate — ought to be the same whether
you're looking at the economy or planning the energy system. This channel carries the economy's interest
rate over to the energy planner. A patient economy (a low rate) makes options that cost more now but pay
off for decades — clean, capital-heavy plants — look worthwhile; an impatient one (a high rate) favours
whatever is cheapest today, often fossil. So the economy's interest rate shapes what the energy system
chooses to build. This runs one way: it changes the energy plan, and that change only feeds back to the
economy when the two models are run together in a loop.

**In the model**
This channel *reads* an output of the solved economy rather than changing an input. After the reform
solve, it takes OG-Core's equilibrium return on capital (`r_p`) and passes it to the energy model as its
discount rate (`DiscountRate`). That rate sets how the least-cost optimiser weighs up-front cost against
long-run savings, which tilts the chosen technology mix. Nothing in the economy model changes here — the
effect on output and welfare appears only once the loop sends the energy system's new prices and costs
back. (Confirm the rate is on a consistent real, annual basis.)

---

## 5 · Health
*CLEWS → OG · cleaner air, through health, into the economy*

**What happens**
Cleaner energy means less air pollution, and less pollution means better health — which reaches the
economy in two ways. First, fewer people die early. But the deaths air pollution causes fall mostly on
the elderly, who are largely retired, so saving those lives changes the population more than the
workforce — the effect on output is small. Second, and more important, people get sick less; healthier
working-age people are more productive, and that lifts output. So the economic gain from cleaner air comes
mainly from a healthier workforce, not from the lives saved. (The size of both effects is still a
placeholder until the health data is calibrated.)

**In the model**
The trigger is the change in fine-particulate (PM2.5) pollution from the energy system — not CO₂, since
cutting CO₂ and cutting PM2.5 aren't the same thing — scaled by an external dose-response from the Global
Burden of Disease (GBD). It moves two parts of the model, each using a by-age profile from GBD. Mortality
shifts age-specific death rates (`ρ`); the model then recomputes the population, changing its size and age
structure (demographics). Because pollution deaths skew old, the extra survivors are mostly past working
age, so output barely moves. Morbidity shifts effective labour by age (`e`) — healthier workers supply
more productive labour to production — and this is where the output gain comes from. The dose-response
magnitudes are placeholders pending the real Philippine PM2.5 data.

---

## 6 · Demand
*OG → CLEWS · a growing economy needs more energy*

**What happens**
A bigger, richer economy needs more energy — for homes, transport, and industry. This channel carries the
economy's growth over to the energy system as higher demand for energy services, so the system plans to
build and supply more, raising its costs and emissions. Like the interest-rate channel, it runs one way:
it changes the energy plan, and that only matters for the economy once the two models are run back and
forth together. On a single pass, with the economy barely moved from its baseline, this link does almost
nothing — it comes alive inside the loop.

**In the model**
This channel also *reads* a solved-economy output rather than changing an input. It takes the economy's
activity — industry output (`Y_m`) or household consumption of the good (`C_i`) — as a reform-vs-baseline
ratio and scales the energy model's demand (`SpecifiedAnnualDemand`) by it. Higher demand forces the
least-cost model to build more capacity, raising cost and emissions. Because it is a ratio against
baseline, a single pass where the economy is essentially unchanged leaves it near 1 — inert — so it bites
only once the loop iterates.

---

## Cross-cutting notes

- **Energy price and carbon move the same lever** (`τ_c` on the energy good) but mean different things:
  energy price is a resource-cost passthrough; carbon is a tax (revenue is the point). Don't apply both
  to the same cost — they double-count.
- **The resource cost-push is a general prototype, not a registered channel.** A rise in any *input
  commodity's* price raises every industry's cost — directly, and via that input embodied in the
  intermediates it buys — computed with an input-output (Leontief) model from the PHL SAM
  (`io_energy_passthrough`), delivered as a per-industry TFP (`Z`) haircut (OG-Core has no inputs in
  production to carry it natively); a companion calibration (`energy_calibration`, the per-industry cost
  share `θ_m`) feeds the fuller energy-as-CES-input extension. It is **commodity-agnostic**: the SAM carries
  electricity (`celec`), fuels (`cmine`), and **water** (`cwatr`) separately, so the *same code* can price
  energy **or water** — a CLEWS water shadow price → costlier water → the agricultural-productivity channel.
  "Energy" is only the current use case. Not a registered channel of its own. (On `main`, `e429777` fixed
  a SAM aggregate-row double-count, so its magnitudes are ~2× their pre-fix values.)
- **Three views of generation capex — use one.** A capex-heavy generation buildout can enter OG three
  ways: **capital intensity** (`γ`, the structural channel #2b), the **cost-push** (`Z`, the prototype),
  or a **capex incentive** (an ITC via `set_investment_incentive`). They represent the *same* private
  capital — applying more than one double-counts. The public `investment` channel (`α_I → K_g`) is a
  *different* capital (the public grid) and is complementary, not a fourth view.
- **Magnitudes are illustrative** until `units.deflator` (CLEWS-money ↔ GDP basis) is calibrated — this
  most affects carbon and investment levels.
- **Direction families:** CLEWS→OG = energy price, investment, capital intensity, health;
  policy = carbon; OG→CLEWS = cost of capital, demand.
