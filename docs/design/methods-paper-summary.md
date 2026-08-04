# Methods-paper summary

The paper develops an auditable soft link between CLEWS/OSeMOSYS and OG-Core. CLEWS supplies
technology-resolved resource planning, investment requirements, emissions, and electricity-cost
paths; OG-Core supplies forward-looking household behaviour, general-equilibrium adjustment,
fiscal closure, demography, and incidence across ages and income groups.

The contribution is the design and validation of the interface. Eight channels transmit
electricity costs, public and private investment effects, carbon policy, pollution-related health
effects, equilibrium returns, and economic activity. Each channel identifies the source quantity,
its economic interpretation, its destination in the receiving model, and the accounting rules
needed to prevent overlapping representations of the same cost.

Electricity-price transmission is the central mechanism. Because the commodity-balance dual is
unstable in the Philippine CLEWS case, the application uses levelized electricity cost as a dense
price proxy. The price change is divided between household electricity consumption and industrial
electricity use. The household component changes the cost of living and permits distributional
analysis; the industrial component enters through an input--output-calibrated cost adjustment
because energy is not yet represented as a structural production input in OG-Core.

The health channel maps changes in particulate emissions into age-specific mortality and effective
labour using Global Burden of Disease profiles and an external dose-response calibration. Embedding
these effects in an OLG economy allows the model to distinguish near-term productivity effects from
longer-run changes in population age structure.

Relative to neighbouring approaches, the framework adds a different economic dimension. IEEM
connects economic activity to land use, ecosystem services, and natural-capital accounts.
CLEWs--IO introduces sectoral employment coefficients into resource-system optimisation. The
present framework introduces forward-looking cohorts, income heterogeneity, demography, and fiscal
closure. Its comparative advantage is therefore intertemporal and distributional analysis rather
than spatial environmental accounting or employment estimation.

The Philippine application validates the principal mechanisms and illustrates their joint
operation. The transition produces modest near-term output gains associated with improved
working-age health and a small negative long-run output effect associated with higher electricity
costs and demographic composition. Electricity-price incidence is regressive under the present
calibration. These results are presented as mechanism validation rather than a definitive
Philippine policy assessment.

The current implementation supports the CLEWS-to-OG-Core application pass and a controlled CLEWS
re-solve seam. The outer fixed-point controller remains open, as do parts of the monetary-unit
calibration and several application-specific coefficients. The paper therefore distinguishes
implemented mechanisms, calibrated inputs, controlled experiments, and components that remain to
be completed.

In short, the paper's contribution is a transparent and testable way to connect detailed resource
planning with an economy that represents households, generations, government, and distribution.
It shows how to trace each effect across the model boundary, test whether the mechanism behaves as
intended, and state clearly which parts are operational, provisional, or still under development.

