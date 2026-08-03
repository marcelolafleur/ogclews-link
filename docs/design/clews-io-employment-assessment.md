# CLEWs–IO (Bararzadeh Ledari et al. 2026) — assessment

**Status:** research note, **full text now read (2026-08-03)**. Nothing here is built.
**Date:** 2026-08-03
**Companion to:** `ieem-comparative-assessment.md` (IDB's IEEM) and `phl-testcase-plan.md`.

> **Update — the seven questions are answered.** Marcelo supplied the PDF. §7 below now
> records what the method actually is, replacing the speculation this note opened with.
> **Headline: the loop is not iterative, and the adoptable pattern is much cheaper than
> expected — jobs can go into MUIOGO today as an OSeMOSYS emission species, with no code
> change anywhere.** See §7 and §9.

## The paper

> Bararzadeh Ledari, M., Akbarnavasi, H., Khajehpour, H., **Gardumi, F.**, Adel Barkhordar, Z.S.,
> Heredia Fonseca, R., Thakur, J. (2026). *Optimizing resource management for water-smart,
> low-carbon futures: A CLEWs–IO model for job creation and climate resilience.*
> **Journal of Cleaner Production 544**. DOI [10.1016/j.jclepro.2026.147543](https://doi.org/10.1016/j.jclepro.2026.147543)

Affiliations: Sharif University of Technology, Shahid Beheshti University, and **KTH Energy
Systems** — Gardumi and Heredia Fonseca are OSeMOSYS/CLEWs core maintainers.

**Why this matters more than IEEM.** IEEM is a CGE from a different modelling tradition; adopting
from it means translation. This paper uses **the same model family we run** (CLEWs/OSeMOSYS),
**the same architecture we use** (soft-link), and adds the sector-resolved economic layer that the
IEEM note identified as the hole in our stack — via input-output rather than by rewriting
OG-Core's firm side. It is the closest published analogue to what ogclews-link is.

## Access — read this before trusting anything below

**I could not read the full text.** The article is closed access (Unpaywall: `closed`; OpenAlex:
no repository fulltext; KTH DiVA record `diva2:2049903` says no full text). ScienceDirect served a
CAPTCHA, which I will not complete.

So this note is built from **verified metadata, the publisher abstract, the author-supplied
highlights, and an open-access sibling paper by the same lead author** — not from the method
section. Everything method-level in §4 is an *open question*, not a finding. Marcelo has
institutional access; §6 lists exactly what to extract from the PDF.

## What is established

From the abstract (via the KTH DiVA record) and the publisher highlights:

- The framework integrates CLEWs with **input-output modelling**, soft-linked, to assess
  climate resilience and job creation jointly in a **water-scarce region**.
- Replacing flood irrigation with **drip and subsurface systems** cuts water consumption ~30%.
- Expanding renewables to **80% of electricity demand** cuts emissions **66%** and creates
  **~107,000 jobs**.
- Highlight, verbatim in substance: *endogenising employment reshapes the optimal
  water–energy–land pathways*.
- Highlight: soft-linked CLEWs–IO reveals **cross-sector feedbacks** not visible otherwise.

**The load-bearing claim is the first highlight.** If employment is endogenised such that it
*changes the CLEWs optimum*, then this team has closed the loop that ogclews-link has not —
`framework.run` is still one pass, and `clews_driver` is built but unwired (`phl-testcase-plan.md`
§4 and the repo audit). Whether "endogenise" here means a term inside the LP or an iterated
soft-link to convergence is precisely what I could not verify.

## The sibling paper — the team's method, open access

> Khaleghian, A., **Bararzadeh Ledari, M.**, Vahedi, R., Fani, M. (2025). *Transforming arid
> regions: CLEWs–OSeMOSYS pathways for low-carbon jobs and circular resource loops.*
> **Energy Nexus 20**, DOI [10.1016/j.nexus.2025.100552](https://doi.org/10.1016/j.nexus.2025.100552)
> — **gold OA, CC-BY-NC-ND.**

Same lead author, same country (Iran, Khash region), same jobs-from-CLEWs question. Its abstract
gives the shape of the team's approach:

- CLEWs–OSeMOSYS, 2020–2050, three scenarios imposing a 50% groundwater cut and 50–90% cuts to
  traditional agriculture/livestock under carbon caps of 30–90%.
- Base case: agriculture employs ~32,000 (75% of all jobs), 367 MCM water, 0.3 Mt CO₂.
- Most stringent scenario: withdrawals −84%, emissions −90%, farm jobs −90% — yet **total
  employment rises** to ~40,000, recomposed into renewables (28,600), greenhouse farming (8,100)
  and CCUS-based ethylene (5,100).

That recomposition result is the interesting one, and it is the kind of finding a CLEWs model
plus an employment layer can produce and neither MUIOGO nor OG-Core currently can.

**Note the difference between the two papers:** the sibling reports employment *by scenario*,
consistent with employment factors applied to solved activity (post-processing). The 2026 paper
claims employment *reshapes the optimum*. If that distinction is real, the 2026 paper's
contribution is exactly the feedback step — and that is the part worth reading closely.

## Where this lands against our stack

| | CLEWs–IO (2026) | ogclews-link |
|---|---|---|
| Physical core | CLEWs/OSeMOSYS | CLEWs/OSeMOSYS — **same** |
| Economic side | Input-output (sector-resolved, fixed coefficients) | OG-Core (OLG, forward-looking, no intermediates) |
| Architecture | soft-link | soft-link — **same** |
| Loop closed? | claimed yes | **no** — one pass; driver built, unwired |
| Employment | headline output | absent entirely |
| Sector detail | full IO table | 8 industries, but energy not in production |
| Distribution | none | cohorts + income groups |
| Fiscal | none | deep |

The honest read: **they have the layer we lack, we have the layer they lack.** An IO table gives
inter-industry flows and employment cheaply but is fixed-coefficient and has no forward-looking
behaviour, no fiscal side, and no intergenerational welfare. OG-Core has all of those and no
inter-industry structure at all.

An IO layer is also a **much cheaper route to a sector-resolved economy** than the unbuilt
"energy as a production input" spec (`energy-as-production-input-spec.md`), which needs an
OG-Core firm-side rewrite. That is worth taking seriously as an alternative, not a competitor,
to the OG route: employment and inter-industry effects from IO, welfare and fiscal from OG-Core.

## The genuinely actionable find — a model-linking checklist

Hunting the method turned up something more immediately useful, and **it is open access**:

> Keppo, I., Al Khourdajie, A., **Gardumi, F.**, et al. (2026). *Model linking for low-carbon
> transitions: Technical and conceptual challenges and best practices.*
> **Renewable and Sustainable Energy Reviews 226**, 116384.
> DOI [10.1016/j.rser.2025.116384](https://doi.org/10.1016/j.rser.2025.116384) — OA copies at
> [Wuppertal](https://epub.wupperinst.org/files/8979/8979_Keppo.pdf),
> [IIASA](https://pure.iiasa.ac.at/view/iiasa/3435.html),
> [Polimi](https://hdl.handle.net/11311/1301446). Full text read.

Its Table 1 is a 17-point checklist for establishing links between sectoral and integrated
models, grouped under temporal/spatial scales, system boundaries and harmonisation, data-exchange
implementation, and linking as an epistemological problem. Same community, Gardumi co-author.

**ogclews-link audited against it — my assessment, not the paper's:**

| Checklist item | ogclews-link |
|---|---|
| Prefer linking models of similar scale (i) | **Pass.** Both annual, both to mid-century. |
| Attention when foresight assumptions differ (iv) | **Pass, and a real strength.** Both CLEWS and OG-Core are perfect-foresight optimisers. The paper's cautionary example is linking a foresight optimiser to a myopic simulator; we don't have that mismatch. |
| Harmonise variable definitions and units (viii) | **Fail today.** `contract.UnitMap.deflator` is still `1.0` — a hardcoded no-op — so carbon and investment magnitudes remain illustrative. This is the single item the checklist most directly indicts. |
| Detailed model documentation used during linking (ix) | **Partial.** `AGENTS.md` is strong; `STATUS.md` is substantially stale and misdescribes the architecture. |
| Standardised templates, automated exchange (xi) | **Pass.** Registry, manifest, `clews_driver`. |
| Standardised interfaces/APIs (xii) | **Pass.** The subprocess/CLI seam. |
| Map epistemic foundations for conflict before linking (xiii) | **Gap.** CLEWS is a least-cost planner; OG-Core is a decentralised equilibrium of optimising households. Both optimise, but they answer to different rationales, and nothing in the repo maps that explicitly. |
| Assess error propagation, especially with two-way feedback (xv) | **Untested.** The loop is not closed, so propagation has never been exercised. This becomes urgent the moment it is. |
| Separate interpretation stage (xvi) | **Partial.** `docs/design/` does some of this. |
| Minimise inconsistencies a priori, even by altering a model (xvii) | **Open.** "Energy is not in OG-Core's production function" is exactly the kind of a-priori inconsistency this item says to fix at the model level rather than paper over downstream. |

That audit is worth more than the CLEWs–IO paper itself right now: it is a published standard we
can be measured against, from the maintainers of the model we run.

## 7. The method, from the full text

Case: **Sistan region, Iran** (Helmand basin), 2022–2042, SSP2-4.5 and SSP5-8.5. OSeMOSYS,
minimising net present cost. Funded by **UNDP and the Iranian Department of Environment**, Sharif
University with KTH scientific advice.

**1. Is employment inside the LP or outside it? — Inside, but via pre-computed coefficients.**

This is the key structural finding, and it is *not* what the "endogenizing employment" highlight
implies. The workflow is:

1. An IO model is built **once, offline**, and produces net job coefficients per unit of physical
   activity — jobs per PJ generated, per unit of land cultivated, per unit of wastewater treated.
2. Those coefficients are **fed into CLEWs as a parameter.** Table 2's third column is literally
   headed *"Input to the CLEWS model (Thousand Jobs-Net/PJ)"* — e.g. electricity: −343 jobs/PJ
   lost, +1039 gained, **0.70 thousand net jobs/PJ entering the model**.
3. CLEWs then carries employment as an accounting quantity the optimiser can see, and scenarios
   can impose a target on it.

So employment *is* endogenous to the optimisation — but only in the sense that a pre-computed
linear coefficient rides along with technology activity, exactly as an emission factor does.

**2. If iterated — what converges? — It does not iterate. There is no loop.**

The words "iterate", "iteration", "converge" and "convergence" **do not appear anywhere in the
paper.** There is no fixed point, no damping, no convergence criterion. The IO model is not
re-run against CLEWs output. The link is one-way: IO → coefficients → CLEWs.

The prose about "feedbacks reinforcing the uptake of clean technologies" is *interpretive
narrative about what the results imply*, not a modelled mechanism. Where employment genuinely
changes the optimum, it does so because **the modeller imposed a target** — the *Agrarian Oasis*
scenario is defined as "targeting 50% increase in employment by 2040, by incentives for
agricultural activities of the herbal plants."

**This materially changes the earlier reading in §"What is established": they have not closed a
loop we left open.** Their architecture is one-way, like ours. On the price side ogclews-link
arguably goes further, since it carries a genuine LP dual as the signal.

**3. Where do the coefficients come from? — IO multipliers, three tiers.**

Direct + indirect + induced, following Howells et al. (2010) on the Korean electricity system and
extended to food and water. Equations 1–5: a diagonal labour-intensity matrix (jobs per unit
output), Type I Leontief multipliers `L` for indirect effects, and induced effects via a vector
of household expenditure propensities `β_i = Exp_i / ΣExp_i`. For the headline 107,000 jobs the
split is ~70% direct (74,900), ~20% indirect (21,400), ~10% induced (10,700). They cite the ILO's
endorsement of IO multiplier models as validation.

**4. How are CLEWs technologies mapped to IO sectors? — Not disclosed, and not recoverable.**

This was the artefact I most wanted. The concordance is not published, and the data-availability
statement reads: *"The data that has been used is confidential."* The regional IO table is not
available either. The method is reusable; their mapping is not.

**5. Double counting? — Handled by construction, not discussed.**

The three tiers are defined so as not to overlap (direct = the investing sector; indirect =
upstream via the Leontief inverse; induced = household spending of wages). Type I multipliers are
used for the indirect tier, with induced handled separately, which is the standard way to avoid
double counting. But the paper contains no explicit discussion of the risk.

**6. The IO table — regional, and confidential.** Described as a "region-specific IO database"
and an "open-access input-output model" built for the study, but neither the table nor its sector
detail is provided.

**7. Stated limitations — there are none.**

The conclusion has no limitations section and no future-work paragraph. Nothing on the fixed
Leontief coefficients being held constant to 2042, nothing on the one-way linkage, nothing on
transferability of the regional IO table. For a paper whose entire economic side rests on fixed
coefficients over twenty years, that is a real gap — and it is the strongest argument for reading
their headline claims conservatively.

## 8. The reusable methodology is elsewhere, and it is open

The actual method document is the antecedent, and it is a **freely accessible preprint**:

> Howells, M., Necibi, T., Laitner, J.S., **Gardumi, F.**, Bock, F. (2021). *Integrated
> input-output and systems analysis modelling: the case of Tunisia. Part 1 — Energy technology
> Input-Output multipliers.* Research Square,
> DOI [10.21203/rs.3.rs-336989/v2](https://doi.org/10.21203/rs.3.rs-336989/v2) — open.

Plus the original: Howells et al. (2010), *Incorporating macroeconomic feedback into an energy
systems model using an IO approach: evaluating the rebound effect in the Korean electricity
system*, Energy Policy 38, 2700–2728.

If we adopt this, those two are the sources to work from — not the JCLP paper.

## 9. The adoptable pattern — and it costs nothing

Because the job coefficient enters CLEWs as *net jobs per unit of activity*, it is structurally
**identical to an OSeMOSYS emission factor**. MUIOGO already has the whole machinery:

| What jobs need | What OSeMOSYS already has |
|---|---|
| a per-activity coefficient | `EmissionActivityRatio{r,t,e,m,y}` |
| an accounting total per year | `E1`/`E2` annual emission production |
| a target or floor | `AnnualEmissionLimit` / `ModelPeriodEmissionLimit` |
| the shadow price of that target | `E8_AnnualEmissionsLimit` — **already exported** in `Duals.json` |

So employment can be added to a MUIOGO case **as an emission species named `JOBS`**, with net
jobs per unit activity as its activity ratio. No change to the solver, no change to MUIOGO's code,
no change to ogclews-link. It is case data, which is gitignored — the same zero-blast-radius
route as the rest of the PHL work.

And the payoff is more than accounting: because the emission-limit dual is already exported, an
employment *target* immediately yields **the shadow price of a job** — the cost in system NPV of
the marginal job. That is a genuinely policy-relevant number, and neither IEEM nor this paper
reports it.

Caveat to carry: this inherits every weakness of fixed Leontief coefficients. The coefficient is
only as good as the IO table behind it, and it cannot capture the labour-market response. It
is an accounting layer, not a labour model — which is exactly what the JCLP paper's missing
limitations section should have said.

## 10. Recommendation

**Nothing here blocks or changes the PHL work** in `phl-testcase-plan.md`. Stages 0–1 stand.

Three things worth doing, in order of cost:

**(a) Treat the `JOBS`-as-emission-species trick as a first-class option.** It is case data,
costs nothing, and yields the shadow price of a job for free (§9). It would be a genuinely novel
output — and it is a much cheaper way to add a socio-economic dimension than anything in the IEEM
note.

**(b) Do not chase the IO layer yet.** The IEEM note argued for a sector-resolved economic layer,
and this paper is evidence the pattern works. But their table and concordance are confidential,
so we would be building from scratch, and a fixed-coefficient IO table has no forward-looking
behaviour, no fiscal side and no intergenerational welfare — everything OG-Core exists for. The
case for IO as a *second* economic side alongside OG-Core is still open; it is just not urgent,
and the Tunisia preprint (§8) is where it would start.

**(c) Adopt the Keppo checklist now** — independent of all of the above. Items (viii), the
deflator still hardcoded to `1.0`, and (xiii), the epistemic map, are cheap and overdue.

## 11. What this changes about how we talk about the field

Both papers assessed in this repo make a strong-sounding integration claim that turns out, on
reading the method, to be a single reduced-form coefficient:

- **IEEM**: "dynamic endogenous feedbacks between natural capital, ES and the economy" = eroded
  area share × an 8% productivity penalty.
- **CLEWs–IO**: "endogenizing employment reshapes optimal pathways" = a jobs-per-PJ coefficient
  carried alongside activity, with no iteration anywhere.

Neither is dishonest, and both are useful. But the pattern is worth naming: **in this literature,
"integrated" and "endogenous" usually mean a well-sourced linear coefficient, not a converged
fixed point.** We are not behind on rigour. We are behind on publishing — and our repo is more
explicit about its placeholders than either paper is about theirs.

## Provenance of this note

Verified this session: DOI, authors, affiliations, journal/volume via Crossref and OpenAlex;
abstract via KTH DiVA; OA status via Unpaywall for all three papers; sibling abstract via DOAJ;
Keppo et al. full text read from the Polimi repository copy; **the JCLP paper's full text read
from the PDF Marcelo supplied** — §7 cites its Table 1, Table 2, equations 1–5, §2.3, §3.2 and
its conclusion. The comparison table's ogclews-link column is from this repo's own audit, not
from any paper. §9 is my proposal, not the paper's — the paper does not suggest implementing
jobs as an emission species, and does not report a shadow price of a job.
