# Follow-up on the methods-paper review response

**Date:** 2026-08-04  
**Responding to:** `methods-paper-review-response.md`  
**Scope:** remaining substantive questions after commit `5bdbf2e`

## Overall response

I agree with most of the response and with the manuscript changes made in `5bdbf2e`. The response
is careful, evidence-oriented, and usefully distinguishes matters already established from work
that requires fresh runs. The revised comparison among IEEM, CLEWs--IO, and ogclews-link is clearer;
the channel-versus-experiment distinction is helpful; and the more precise treatment of hard links,
the re-solve seam, and enforcement by guards versus composition rules improves the paper.

I also agree with retaining “soft-link equilibrium” for now. The added sentence makes clear that,
with LCOE as the price signal, the object is consistency under a pricing proxy rather than a
competitive-equilibrium price. Reader feedback can determine whether the defined term itself causes
confusion.

The cumulative decomposition is correctly identified as the highest-priority verification run. The
response is also right to queue a fresh capital-intensity run, documentation of the dual-degeneracy
test, fuller LCOE provenance, and a principle-by-principle enforcement map.

## Terminology point withdrawn

I withdraw the recommendation to introduce a direction-neutral three-part terminology of “signal,”
“target adjustment,” and “channel.” Although formally comprehensive, it would add vocabulary for a
relationship readers understand intuitively: one model or a policy supplies a quantity, and that
quantity changes an input in the other model.

The revised channel definition is sufficient for the paper's purposes. The paper does not need a
formal ontology covering every direction and policy case. It needs only to identify each channel,
show what crosses the boundary, show where it enters, and explain how overlap is prevented. The
existing prose and channel table can do that without another conceptual layer.

Any remaining one-signal/one-wedge wording elsewhere in the paper is therefore a minor consistency
edit, not a theoretical issue.

## Remaining substantive questions

### 1. Carbon provenance in the flagship application

This is the most important unresolved issue.

In the reviewed implementation, `coupled` reads an already-solved reform electricity-price path and
also writes a new `$50/tCO2` `EmissionsPenalty` artifact for CLEWs. The outer controller does not yet
feed that emitted artifact into a new CLEWs solve. Therefore, the emitted `$50` path does not itself
affect the macroeconomic results currently reported for `coupled`.

The response gives a plausible reason for omitting the direct OG-side carbon wedge: the reform LCOE
already embodies the penalty-induced system cost, so applying the same cost again through OG would
double count it. That rationale is correct only if the pre-solved reform scenario actually contains
the same carbon-price policy.

Please verify from the CLEWs case and its solve provenance:

1. whether the pre-solved reform contains an `EmissionsPenalty` on the relevant CO2 species;
2. its exact value, time path, units, and years;
3. whether it is the same `$50/tCO2` policy emitted by `coupled`;
4. whether the LCOE path used by the macro solve was calculated from that penalised CLEWs solution.

If all four checks pass, the paper can state that the reform LCOE already transmits the resource-cost
effect of the carbon policy, while `coupled` emits the matching policy artifact for the future
round-trip. If they do not pass, the current paper should say that the experiment **emits** a proposed
carbon-price input rather than saying that the reported coupled result **applies** a `$50/tCO2`
carbon price.

This should be resolved in the application description itself, not deferred solely to the general
discussion, because it determines what generated the reported numbers.

### 2. The non-additivity claim should await the matched run

The response correctly establishes that the old `across_steps` record was not regenerated after the
LCOE re-bless. There is an additional reason the current comparison cannot yet establish a general-
equilibrium interaction: the standalone `energy_price` experiment applies the household wedge alone,
whereas `coupled` applies the composite household-plus-industry transmission. The simple sum and the
application configuration are therefore not matched treatments.

Until the new cumulative run exists, the manuscript should avoid attributing the gap to channel
interaction. A neutral temporary statement would be:

> The coupled result is not reproduced by summing these isolating experiments, whose configurations
> do not collectively duplicate the application treatment. A matched cumulative decomposition is
> required to attribute the difference.

Once the new cumulative run is available, the paper can identify the step at which the large effect
appears and then determine whether the source is genuine nonlinearity, a particular channel
combination, or a configuration difference. Order-averaged or Shapley attribution is optional; the
first requirement is simply a matched sequence whose final step reproduces `coupled`.

### 3. Scope of the golden record

The response usefully confirms that the committed golden record contains macroeconomic aggregates
and sectoral output, while several other reported quantities live elsewhere. The manuscript should
reflect that narrower scope.

In particular, `golden.json` does not by itself regression-test:

- the emitted demand path;
- the emitted discount-rate path;
- the emitted carbon-penalty path;
- the LCOE input path and its provenance;
- the health target;
- the sectoral price and capital values in the capital-pair decomposition.

Executing the `demand` or `discount_rate` experiment and locking its macro aggregates confirms that
the experiment still solves. It does not establish that the emitted artifact is numerically correct
or unchanged.

Accordingly, two revisions are recommended:

1. Narrow global statements such as “every reported number is regression-locked” to specify exactly
   which outputs the golden record covers.
2. Add small artifact-level regression tests or committed evidence records for the returned demand,
   discount-rate, and carbon paths.

This is not a criticism of the present golden record; it is a request that the paper distinguish
macro-result regression from interface-artifact verification.

### 4. Discount-rate interpretation

The discount-rate channel needs economic validation in addition to unit and time-convention checks.
The draft currently moves from the Stern--Nordhaus disagreement over social discounting to the claim
that OG-Core can supply an equilibrium return to the energy planner. These are not automatically the
same object.

The paper should establish what the CLEWs/OSeMOSYS `DiscountRate` represents in this application:

- a social rate used to discount system costs;
- a financing cost or required return;
- a public-sector hurdle rate; or
- another country-model convention.

It should then explain why the selected OG-Core return is the appropriate counterpart, including any
real/nominal conversion, annualisation, risk premium, tax treatment, or public/private financing
adjustment. If the mapping is a harmonisation convention rather than a structural equality, label it
accordingly.

This does not block the channel as an implemented return path. It determines the strength of the
economic interpretation the paper can attach to it.

## Minor manuscript consistency edits

These do not require further conceptual discussion or technical investigation:

1. The results text now correctly explains that the table contains isolating experiments, but the
   text and captions still call them “per-channel” results. Rename them “standalone mechanism
   experiments” or similar.
2. The `-0.006%` result belongs to the household-wedge `energy_price` experiment, not to the full
   composite energy-price channel. Describe it accordingly.
3. The framework now limits the hard-link claim to the classic integrated-welfare-program route, but
   the background still says that “the hard-link route is structurally unavailable.” Propagate the
   narrower wording.
4. The introduction still says every accounting principle is enforced by a code guard, while the
   framework now correctly says that some are enforced by experiment composition. Make the
   introduction match.
5. In the nearest-neighbour paragraph, CLEWs--IO is correctly described as one-way. Replace the
   preceding phrase “economy--resource feedback” with “economy--resource linkage” so the sentence
   does not call a one-way mapping feedback.

## Agreed next-step order

1. Verify whether the source reform LCOE contains the same `$50/tCO2` carbon policy described in the
   paper.
2. Regenerate the matched cumulative decomposition and require its final step to reproduce the
   current `coupled` run.
3. Correct the global golden-record wording and add artifact-level checks for the reverse channels.
4. Re-run the capital-intensity experiment under the re-blessed baseline and preserve the sectoral
   evidence.
5. Document and reproduce the electricity-dual degeneracy test.
6. Establish the economic interpretation of the discount-rate mapping.
7. Complete the principle/enforcement/maturity table and the LCOE construction documentation.
8. Apply the small manuscript consistency edits listed above.

## Bottom line

The response and commit `5bdbf2e` resolve most of the original review constructively. There is no
need to spend more paper space formalising intuitive terminology. The remaining work is empirical
and interpretive: prove what carbon policy is already present in the reform price, reproduce the
coupled result through matched cumulative steps, distinguish macro-output regression from emitted-
artifact validation, and justify the economic meaning of the discount-rate mapping.

Once those points are settled, the channel description and comparison will be on much firmer ground
without adding conceptual machinery the reader does not need.
