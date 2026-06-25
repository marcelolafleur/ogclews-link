# How OG-Core and CLEWS work together

*A guide to how a model of the economy (OG-Core) and a model of the energy system (CLEWS)
work as one system — what passes between them, and what it means. A separate, more technical
reference covers the equations.*

Diagrams for each channel are in [`channel-diagrams.html`](channel-diagrams.html).

---

## What this system is for

Energy-transition pathways and their economic consequences are usually analysed with separate models
that don't share inputs. A least-cost energy model can say what a pathway costs to build and what it
does to electricity prices and emissions — but not what those changes do to wages, the public budget,
household welfare, or the distribution of gains and losses. A macroeconomic model can say the latter,
but treats energy as a price and a quantity, with no representation of the system that supplies it.

This couples the two, so a change on the energy side carries through to the economy and the economy's
response carries back. It pairs **OG-Core**, a macroeconomic model, with **CLEWS**, a least-cost
energy-system model, by passing a defined set of quantities between them — the channels this guide
describes.

---

## 1. What each model covers

The two models are built to answer different questions, and each leaves out exactly what the other is
about.

**OG-Core** is a macroeconomic model of a country (calibrated here for the Philippines). It represents
households over their life cycle — many overlapping generations at once — along with the government
budget, wages, the interest rate, saving, and investment, and solves for a single consistent outcome
across all of them. Unusually, it resolves that outcome by income group, so it yields distributional
results, not just aggregates. What it does not represent is energy supply: there are no power plants in
it. Energy enters only as a price households pay and the amount they spend on it.

**CLEWS** is a least-cost model of how a country supplies energy — its power plants, fuels, costs, and
emissions — together with the land and water that energy use draws on (the name is climate, land,
energy, and water). It finds the cheapest way to meet a specified energy demand. What it does not
represent is the economy: it takes demand as given, and says nothing about who pays, how the rest of
the economy responds, or what discount rate to use for investments that pay off over decades.

So each supplies what the other lacks. From CLEWS the economy gets an energy price, the cost of
building the energy system, and the change in air pollution. From OG-Core the energy system gets the
energy demand to plan for and the interest rate to discount with. Everything that follows is about that
exchange.

The energy price is the most important of these, and it is not assumed or marked up. It is the marginal
cost of supply in the least-cost solution — the cost of the next unit of energy — which CLEWS produces
directly, as the shadow price on its energy-balance constraint. Marginal rather than average cost is
the right signal: it is what an additional unit actually costs the system, and so what should govern how
much energy the economy chooses to use. That is what reaches households, not the average cost of
everything produced.

---

## 2. What connects them

Several distinct things connect the two models, not one. The energy-system change reaches the economy
through a few concrete links, and the economy reaches back through a couple more.

Most of the links run from the energy system to the economy, since that is where the change starts.
The first and most important is **price**: when the cost of supplying energy changes, households pay a
different price for it. The second is **investment**: changing the power system means building new
public infrastructure — the grid and transmission lines — which the economy has to pay for and then
benefits from. The third is a **change in how the energy industry produces**: a power system built
mostly from clean sources relies more on equipment and less on fuel than one that burns coal and gas,
and that shift in the makeup of the industry's costs has its own effect (as it turns out, mostly on the
price of energy). The fourth is **health**: burning less fuel means cleaner air, and cleaner air means
fewer early deaths and healthier, more productive working-age people.

A couple more links are not produced by either model — they are policies someone chooses to apply: a
carbon price, or a tax credit for clean investment.

The economy sends two things back the other way: how much energy it ends up wanting, which is what the
energy system must plan to supply; and the interest rate it settles on, which is how the energy system
should value an investment that lasts decades.

Each of these links is a *channel*. The next section explains how the two models use them to reach a
single consistent answer; the section after that takes the channels one at a time.

---

## 3. How the two models reach a consistent answer

The economy and the energy system each depend on the other's answer. How much energy the economy wants
decides what the energy system builds, and what that costs decides what the economy does. The two
models are run in turn until they stop disagreeing.

One round goes like this:

1. Begin with the energy system's results for a scenario — its prices, build costs, and pollution.
2. The energy-to-economy channels turn those into changes inside the economy model: the energy price
   becomes a price on the energy good households buy, the grid build becomes public investment, the
   pollution change becomes changes in health, and so on.
3. The economy is worked out a single time — the model computes one consistent outcome for wages,
   prices, saving, and the rest, with all of those changes in place at once.
4. The economy-to-energy channels read that outcome and hand the energy system what it needs for the
   next round: the new energy demand and the interest rate.
5. The energy system re-solves at that demand and rate, its prices shift, and the round begins again.

It ends when nothing moves any more — when the amount of energy the economy chooses, at the price it is
given, equals the amount the energy system built to meet. That is the consistent answer.

You do not always need the full loop. If the question is simply "what does this energy scenario do to
the economy?", a single round is enough: take the scenario as fixed and read off the economy's
response. The full loop matters when the question is "where do the two settle once they have adjusted
to each other?"

### The channels act together, not one after another

The channels feeding the economy all act at the same time. Each changes a different parameter, and the
economy is then solved once with all of them in place. Their interactions — cheaper energy changing
labour supply, say, or a capital subsidy moving the economy-wide interest rate — are resolved inside
that single equilibrium, not summed by hand afterwards. Because each channel changes a different
parameter, the order in which they are applied does not change the result.

---

## 4. The channels in detail

There are eight channels — the carbon price counts once here, as a single lever applied on both sides
(in the code it is two pieces, one per side). The table lists all eight at a glance — what each one
carries, and what it changes in the model that receives it. They are then explained in turn, grouped by direction: first the
four channels from the energy system to the economy, then the two policy levers, then the two channels
from the economy back to the energy system. The table follows that reading order. (Model symbols such
as `τ_c` appear in parentheses; they are names for the settings being changed, secondary to the plain
description.)

| # | Channel | Direction | What it carries | What it changes in the receiving model |
|---|---------|-----------|-----------------|----------------------------------------|
| 1 | Energy price | energy → economy | the cost of supplying one more unit of energy | a price on the energy good households buy (`τ_c`) |
| 2 | Investment | energy → economy | the cost of building the public grid | public investment that builds up public infrastructure (`α_I`, `K_g`) |
| 3 | Capital intensity | energy → economy | how equipment-heavy the power system is | how the energy industry splits its costs between equipment and labour (`γ`) |
| 4 | Health | energy → economy | the change in air pollution (PM2.5) | death rates by age (`ρ`) and how much workers produce by age (`e`) |
| 5 | Carbon price | policy (both models) | a carbon price | the household energy price (`τ_c`) and, inside CLEWS, an added cost on polluting options |
| 6 | Energy capex incentive | policy | a tax credit for clean building | what it costs the energy industry to fund its equipment (cost of capital) |
| 7 | Demand | economy → energy | how much energy the economy wants | the demand CLEWS plans to meet |
| 8 | Discount rate | economy → energy | the economy's interest rate | the rate CLEWS uses to value long-lived investments |

### From the energy system to the economy

**Energy price.** This is the link from what energy costs to supply to what households pay for it. If
the change to the energy system makes energy cheaper or dearer to supply, households see it in their
bills, adjust how much they use, and — because energy is a larger share of a poorer household's
spending — feel it unevenly. The channel takes the cost of supplying energy from CLEWS, compares it to
the starting point, and applies the difference as a price on the energy good (`τ_c`) that enters every
household's spending decision. That gives both the overall demand response — for illustration, a 20%
higher price reduces energy use by roughly 16%, and the reverse for a price fall — and how that
response is distributed: when energy is treated as a necessity, the cost falls hardest on poorer
households, who spend a larger share of their income on it. That split across income groups is
something a model with only one average household cannot produce, and OG-Core tracks many.

**Investment.** The public side of the buildout — the grid, transmission, and distribution lines — is
public infrastructure like any other: it has to be paid for, and once it stands it makes the whole
economy more productive. The channel takes the cost of that public build from CLEWS (the network, not
the power plants), expresses it as a share of GDP, and adds it to public
investment (`α_I`). That investment builds up the stock of public infrastructure (`K_g`), which lifts
productivity across industries. It is treated as a temporary programme that fades once the building is
done, not a permanent change. This is the public network only — the cost of building private power
plants reaches the economy through the energy price, through the next channel, or through the tax
credit further down, not here.

**Capital intensity.** A power system built mostly from clean sources — solar, wind, and plants fitted
with carbon-capture equipment — relies more on equipment and less on fuel than one that burns coal and
gas. More of its cost is the equipment you build once; less is the fuel and labour you pay for
continuously. The channel reflects that by raising how much of the energy industry's costs go to
equipment rather than to fuel and wages (its capital share, `γ`), with the part going to fuel and wages
falling to make room.

The result is counterintuitive. Shifting the cost mix toward equipment lowers the marginal cost of
producing energy, so its price falls. Because energy is a small, price-inelastic share of consumption,
demand barely responds — the industry does not expand, it meets the same demand more cheaply, and ends
up using *less* total equipment than before. The larger cost share and the smaller capital stock are
consistent: a bigger share of a smaller total can be less in absolute terms (if total cost falls
100 → 80 while equipment's share rises 40% → 45%, equipment itself goes 40 → 36). The interest rate
barely moves. In the Philippine case this channel on its own makes energy roughly a quarter cheaper and
leaves the energy industry using more than a tenth less equipment. So it is really about the price of
energy and the split of income between capital and labour — not about drawing capital into the sector.
(That is the energy-capex tax credit below, which pushes the other way.)

**Health.** Cleaner energy means cleaner air, and that reaches the economy in two ways. First, fewer
people die early — but those deaths fall mostly on the elderly, who have largely left the workforce, so
the effect on the economy's output is small. Second, and more important for output, people of working
age are sick less often, and healthier workers produce more.

Mechanically, the channel takes the change in fine-particle pollution (PM2.5) from CLEWS — PM2.5
specifically, because an energy-policy change can move it very differently from CO₂. It scales that
change down by a factor that combines two things: the power sector is only about a tenth of the
ambient PM2.5 people are exposed to, and the exposure-response curve is concave, so a given cut buys
less health at high pollution levels than at low ones. For the Philippines that leaves roughly 8% of
the raw change (a multiplier of about 0.08). The scaled change then moves two things, each by age,
using age profiles from the Global Burden of Disease study: death rates by age (`ρ`), after which the
model recomputes the population; and the productivity of labour by age (`e`), which is the larger
source of the output gain.

### Policy levers

**Carbon price.** A carbon price should mean the same thing wherever it applies, so a single price path
is applied to both models. On the energy side, it adds a cost to emissions, which pushes the system
toward cleaner plants and fuels. On the economy side, it adds to the price households pay for energy
(`τ_c`). Because OG-Core has no energy inside production — energy enters it only as something
households buy — the carbon price on the economy side raises the cost of just that household energy,
which is only about 1.4% of what households spend. The effect of the carbon price on emissions across
the rest of the economy is handled on the energy side, where the power plants and fuels actually are.
The revenue raised can be returned to households as a payment. Running this as one lever is what keeps
both effects of the price in view without charging for the same carbon twice. (Note that this and the
energy-price channel both raise the price of the energy good — one as a cost of supply, one as a policy
charge — so they should not be added together as if they were unrelated.)

**Energy capex incentive.** If the aim is to draw equipment into clean generation, the direct way is to
make it cheaper for the energy industry to fund that equipment — an investment tax credit. The channel
does exactly that, lowering what it costs the energy industry to finance its equipment (its cost of
capital), paid for through the public budget; in response, more equipment moves into energy (around +5%
in the Philippine case). This is the counterpart to the capital-intensity channel above. That one
changes how the industry *splits its costs* between equipment and labour, and ends up making energy
cheaper while using less equipment. This one changes *what it costs to fund* equipment, and draws
equipment in. Because the two move energy-sector equipment in opposite directions and answer different
questions, you would use one or the other, not both.

### From the economy back to the energy system

**Demand.** A larger or differently-shaped economy needs a different amount of energy, and the energy
system should plan for what the economy will actually want. The channel takes the energy-related
activity in the solved economy, compares it to the starting point, and passes the change back to CLEWS
as the amount of energy it must now plan to meet. This is the link that closes the loop — the route by
which a change in the economy reaches the next energy-system solve.

**Discount rate.** Whether an asset that lasts forty years is worth building depends on how much the
future is worth, and the energy system should not pick that number arbitrarily. The channel hands CLEWS
the interest rate the economy settles on (`r_p`) to use when valuing long-lived investments, so both
models weigh the future the same way.

### Two pairs to use with care

Two pairs of channels reach for the same quantity, so they should not be combined carelessly:

- **Energy price and carbon** both raise the price of the energy good households buy — one as the cost
  of supplying energy, one as a policy charge. Do not add the two together as if they were unrelated.
- **Capital intensity and energy capex** both move the amount of equipment the energy industry uses,
  but in *opposite* directions (one makes the industry use less, the other draws more in). They stand
  for different policies, so use one at a time, not both.

---

## 5. Worked example: following the energy price and the demand it produces

The clearest way to see the channels in action is to follow one quantity the whole way around the loop:
the price of energy going out to the economy, and the energy demand it produces coming back. Two
channels carry it — the energy-price channel on the way out, the demand channel on the way back. (The
five-step loop from Section 3 is what drives this; here it is filled in with one concrete number.)

Take a scenario that changes the power system and, in the process, makes electricity cheaper to supply
— say about 4% cheaper than the starting point.

- That 4% lower cost flows through the energy-price channel and eases the price households pay for energy (`τ_c`).
- The economy is worked out with the lower price in place. Households use more energy, and because
  energy is a necessity, the relief is proportionally larger for poorer households — which the model
  reports group by group. The economy's energy demand is now higher.
- The demand channel passes that higher demand back to the energy system as the amount it must now plan to meet.
- The energy system re-solves at the higher demand; its mix of plants and its price shift; the economy
  responds again; and the loop repeats until the demand the economy wants and the supply the energy
  system plans line up.

So the same quantity has gone from the energy system into the economy as a price, come back out as a
demand, and returned to the energy system — one full circuit.

For contrast, the health channel enters the economy at a different point. It does not work through
prices; it works through people. A change in pollution becomes a change in death rates and in the
productivity of working-age people, which changes both the size of the workforce and how much each
worker produces. It is the same overall shape — one quantity from the energy system changing one part
of the economy — but it touches the economy somewhere other than the price.

This distributional and health detail is exactly what the economy model adds that the energy model
alone cannot: who the cheaper energy helps most, and how much cleaner air is worth in lives and in
output.