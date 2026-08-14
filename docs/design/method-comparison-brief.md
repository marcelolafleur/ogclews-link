# How our method compares — a brief

**Status:** briefing note. Standalone; assumes no knowledge of this repo.
**Date:** 2026-08-03
**Compares:** our CLEWs environmental-accounting work against IDB's IEEM platform and the
KTH/Sharif CLEWs–IO employment model.
**Sources:** `ieem-comparative-assessment.md`, `clews-io-employment-assessment.md`,
`phl-testcase-plan.md` — all in this directory, all with the underlying evidence.

## The one-paragraph version

Two recent frameworks add socio-economic and environmental dimensions to resource models, and
both are worth learning from. Neither is more rigorous than what we are building. Both rest their
headline integration claim on a single linear coefficient, and neither reports whether the numbers
they publish are real model signals or solver artefacts. **Our distinguishing contribution is not
a new model — it is verification discipline: we check that the accounts close, and we check that
a price is a price before we quote it.** That has already caught things in our own model that
neither published method would have surfaced.

## The three at a glance

| | **IEEM** (IDB) | **CLEWs–IO** (KTH/Sharif) | **Ours** |
|---|---|---|---|
| Physical core | none — CGE with satellite accounts | CLEWs/OSeMOSYS | CLEWs/OSeMOSYS |
| Economic side | recursive-dynamic CGE | input-output, fixed coefficients | OG-Core (OLG) — separate track |
| Adds | ecosystem services, natural-capital wealth | employment | land accounts, biodiversity index, depletion |
| Coupling | CGE → land-cover → ecosystem services → shock back | IO → coefficients → CLEWs | reads a solved case |
| Iterative? | yes, 5-year steps | **no** | no |
| Spatial | 300 m raster | none | none |
| Software | GAMS (commercial) | OSeMOSYS (open) | OSeMOSYS + Python, Apache-2.0 |
| Data available? | ecosystem geodata yes, model no | **confidential** | fully open |
| Published? | extensively | yes | not yet |

## What each actually does

**IEEM** is an environmentally-extended CGE with SEEA physical accounts attached to the industry
accounts, covering 20+ Latin American countries. Its land-cover module feeds ecosystem-service
models, and it reports comprehensive wealth — genuine savings, netting natural-capital depletion
off national saving. That wealth framing is its real contribution and we have adopted it.

**CLEWs–IO** runs an input-output model once, offline, to derive net jobs per unit of physical
activity, then feeds those coefficients into CLEWs as a parameter. Employment becomes something
the optimiser can see and be constrained on. Applied to the Sistan region of Iran; ~107,000 jobs
under its best-case package, split roughly 70% direct, 20% indirect, 10% induced.

**Ours** reads a solved CLEWs case and computes a land-cover state vector, an area-weighted
biodiversity-style index, a carbon-damage term, and the present value of natural-capital
depletion. It is post-processing: no change to OSeMOSYS, to MUIOGO, or to the case it reads.

## The pattern in both published methods

Each makes a strong-sounding integration claim that, read at the method level, is one coefficient.

**IEEM** — "dynamic endogenous feedbacks between natural capital, ecosystem services and the
economy" is, in full, eroded agricultural area as a share of total, times an 8% productivity
penalty from one literature estimate, applied as a productivity haircut on agriculture.

**CLEWs–IO** — "endogenizing employment reshapes optimal water–energy–land pathways" means a
jobs-per-PJ coefficient travels alongside technology activity. The words *iterate* and *converge*
appear nowhere in the paper. Employment changes the optimum only where the modeller imposes a
target.

Neither is dishonest and both are useful. But the vocabulary runs ahead of the machinery: in this
literature, *integrated* and *endogenous* usually mean a well-sourced linear coefficient, not a
converged fixed point. Two consequences for us. We are not behind on rigour — our equivalent
coefficients are labelled as provisional in code, which is more than either paper does. And a
reduced-form coefficient is a legitimate way to add a dimension, so we should feel free to use one
where it earns its place, and say so plainly.

## Where our method is genuinely different

Neither published method verifies its own numbers in the way described below. This is the part
worth defending.

**1. The accounts must close.** Land-use areas are asserted to sum to the land resource, or the
read is refused. On the Philippine model this holds at 0.00e+00 at both endpoints and within 1e-4
across all 34 years. This is not decoration: the obvious way to read land from a CLEWs model
silently drops forest entirely and mixes water volumes into an area total. We hit that bug, and
the closure check is what caught it. A test deliberately deletes a land class to prove the guard
fires.

**2. A price is not a price until it survives scrutiny.** When we read the land shadow price out
of the Philippine model, it came back at 1.0e-4. We did not report that as a low land value. We
established that it is exactly the token variable cost on the land resource, that it sits an order
of magnitude below the solver's own shadow-price reporting resolution, and — decisively — that two
runs at the *same optimum with identical land in every year* report it in **different years**. A
price that moves between alternate optima while nothing physical changes is degeneracy, not
information. The tooling now warns whenever every non-zero rent is at or below solver resolution,
so it cannot be mistaken for a result later.

**3. Decomposing a shadow price before believing it.** The constraints that genuinely bind on
Philippine land carry shadow prices of order 10. Taken at face value, that is the marginal value
of land. It is not: about 97% of it is a `-10.0` variable-cost reward that puts an opportunity-cost
floor under every cluster. Net it out and only three of eight clusters carry any genuine scarcity
premium — 0.28 to 0.51, over 23.5% of national land. **Quoting the raw shadow price would overstate
the marginal scarcity value of land by 20× to 35×.**

**4. Tracing a number to its origin.** Following that `-10.0` back through the model-generation
code found a hardcoded constant with no source, no units, and no documentation anywhere in the
build's assumption register. It is the model's *entire* representation of the economic value of
standing forest — necessary, because forest produces no commodity and a cost-minimiser would
otherwise convert every free hectare to cropland at zero cost. A whole environmental valuation
resting on one undocumented integer is exactly the kind of thing that stays invisible unless
someone checks. Neither published method's workflow would have surfaced it.

**5. Calibration stated honestly.** The Philippine land block puts 61% of national area under
forest against roughly 24% observed, and built-up an order of magnitude low. We label its outputs
mechanism checks, never Philippine results. IEEM's applications and the CLEWs–IO paper both report
country findings; the CLEWs–IO paper has **no limitations section at all**.

## Where we are genuinely behind

Stated plainly, because a brief that only flatters is not useful.

- **No published applications.** Both others have peer-reviewed country studies. We have a repo.
- **No ecosystem-service valuation.** IEEM has spatially explicit services and a decade of
  applications; we have a biodiversity-style index awaiting real coefficients.
- **No employment layer yet** — though this is the cheapest gap to close (below).
- **No sector-resolved economy.** IEEM has a CGE, CLEWs–IO has an input-output table. We have
  neither: OG-Core has industries but no intermediate inputs, so nothing in our stack can currently
  answer "which sectors shrink when water gets scarce."
- **No spatial dimension.**
- **The loop is not closed** — though it now appears neither of theirs is either.

## What we take from each

**From IEEM:** the wealth framing. Genuine savings — netting natural-capital depletion off
national saving — is an accounting identity over model outputs, not a modelling capability. Its
terms are already computable from a solved case.

**From CLEWs–IO:** the cheapest available win. Because their job coefficient is *net jobs per unit
of activity*, it is structurally identical to an OSeMOSYS emission factor. Employment can be added
to a case as an emission species with no code change anywhere — and because the emission-limit
shadow price is already exported, an employment target immediately yields **the shadow price of a
job**, the system cost of the marginal job. Neither paper reports that number.

**From neither:** their data. IEEM's model is GAMS and its ecosystem geodata is Latin America
only; the CLEWs–IO table and its sector concordance are confidential. The reusable method behind
the employment work is an open preprint, not the paper.

## Bottom line

We occupy a defensible position that neither of the others does: **the same physical model as the
best CLEWs work, fully open, with verification discipline neither published method applies to its
own results.** Every number we have produced so far has been checked for whether it is real, and
in two cases the answer was no — which is the point.

What we lack is breadth and publication, not rigour. The gaps that matter are employment (cheap),
ecosystem services (real work), and a sector-resolved economy (open question). None of them
require adopting anyone else's model.

The claim worth making in public, when the work is ready, is not that we have integrated more
systems than anyone else. It is that we can say which of our numbers mean something.
