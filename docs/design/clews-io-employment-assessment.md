# CLEWs–IO (Bararzadeh Ledari et al. 2026) — assessment

**Status:** research note, **incomplete pending full text**. Nothing here is built.
**Date:** 2026-08-03
**Companion to:** `ieem-comparative-assessment.md` (IDB's IEEM) and `phl-testcase-plan.md`.

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

## What to extract from the PDF

Marcelo has access. These are the questions that decide whether we adapt anything:

1. **Is employment inside the LP or outside it?** Does the CLEWs objective or constraint set carry
   an employment term, or is employment computed from solved activity and then fed back by
   re-solving? The first is a model change; the second is our existing `clews_driver` pattern.
2. **If iterated — what converges, and how?** Convergence criterion, damping, number of
   iterations, and whether convergence was actually achieved. Keppo et al. are explicit that
   convergence is not guaranteed.
3. **Where do employment coefficients come from?** Jobs per unit of activity/capacity by
   technology, or IO employment multipliers per unit of final demand? Which data source, which
   year, and are they direct-only or direct+indirect+induced?
4. **How are CLEWs technologies mapped to IO sectors?** This is the concordance problem we hit in
   `contract.Concordance`. Their mapping is the reusable artefact.
5. **How is double counting avoided** between direct jobs in CLEWs technologies and indirect jobs
   from the IO multipliers?
6. **Is the IO table national, regional, or constructed?** For Iran, and at what sector detail.
7. **Stated limitations** — particularly on fixed coefficients over a 2050 horizon, which is the
   obvious weakness of any IO-based projection.

## Recommendation

**Do not act on this yet.** Two reasons: the method is unverified, and the current PHL work
(stages 0–1 of `phl-testcase-plan.md`) is unaffected by anything here.

When the PDF is in hand, the decision worth making is whether an **IO layer becomes the second
economic side of ogclews-link**, sitting alongside OG-Core rather than replacing it — cheap
sector and employment detail from IO, welfare and fiscal from OG-Core. That would answer the
"which sectors shrink when water gets scarce" question that the IEEM note flagged we cannot
currently answer, without the OG-Core firm-side rewrite.

Separately and independently of all of the above: **the Keppo checklist should be adopted now.**
Items (viii) — the deflator — and (xiii) — the epistemic map — are concrete, cheap, and overdue.

## Provenance of this note

Verified this session: DOI, authors, affiliations, journal/volume via Crossref and OpenAlex;
abstract via KTH DiVA; OA status via Unpaywall for all three papers; sibling abstract via DOAJ;
Keppo et al. full text read from the Polimi repository copy. **Not** verified: any method detail
of the 2026 CLEWs–IO paper. The comparison table's ogclews-link column is from this repo's own
audit, not from the paper.
