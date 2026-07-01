# Adversarial validation — findings and resolutions

Three independent challengers reviewed the channels against (1) economics, (2) OG-Core/CLEWS
model theory and code, (3) the implementation. Below: what they found, and what changed.
All transform tests pass after the fixes. Since this review the model has been solved end-to-end: the
full coupled PHL M=8 run converges on ogcore 0.16.3, and the results are captured in the committed golden
regression baseline (`results/golden.json`). Follow the README walkthrough to reproduce.

## Fixed

| # | Severity | Finding | Resolution |
|---|---|---|---|
| W1 | wrong-result | Carbon `tau_c` and the recycle `alpha_T` bump only wrote `[:T]`, so a *permanent* policy vanished in the SS tail (T:T+S) that anchors TPI's terminal condition. | Carbon + recycle now fill the tail. Investment deliberately keeps `[:T]` (transition capex is *temporary* → tapers to baseline SS) with an explicit `persist` flag. Added a tail-persistence test. |
| B1 | economic | `recycle_via_transfers` overclaimed "revenue-neutral"; it estimates revenue on *baseline* quantities (the wedge shrinks its own base → overstates) and the closure interacts. | Docstring corrected to "first-order, approximately neutral"; recipe for the exact post-solve version documented. Carbon `recycle` now defaults **off**. |
| B2 | economic | Investment defaulted to routing *all* power capex (incl. private generation) into *public* `K_g` → a wrong-signed productivity boost; CLEWS-MUSD ÷ real GDP assumes unit parity. | `public_only=True` by default; magnitude guardrail prints when the peak `alpha_I` increment exceeds baseline; unit-parity assumption documented (deflator still TODO). |
| Maj5 | economic | Health applied the productivity benefit to **both** `e` and `chi_n` (same magnitude) = within-channel double count. | Default `affects=("e","mortality")`; `chi_n` is opt-in with a warning. |
| M1 | theory | OG-Core memoizes `e` in `_e_long_cache`; a serial-fallback baseline solve could leave it stale so the reform `e` edit is silently ignored. | Cache dropped after the reform deepcopy and in `apply_mortality`. |
| M2 | theory | A too-large energy `c_min` silently drives consumption negative (broken solve, not a clean error). | Guardrail compares `energy_cmin` to the minimum baseline per-household energy consumption and warns. |
| C1 | crash | `_fit`/`_align_to_start` crash (`IndexError`) on an empty signal or `start_year > max(year)`. | Empty → zeros; `_align_to_start` short-circuits. Test added. |
| S1/m3 | bug | `apply_mortality` hardcoded UN code "608" (a dead walrus); non-PHL countries got Philippine demographics. | `p._un_code` set from `country.un_code`; walrus removed. |
| W2 | wrong-result | `emissions_ratio` divided base (ByMode-summed) by reform (plain-summed) — mismatched aggregation. | `emissions_by_year` prefers the ByMode variant present in both scenarios, so both sides aggregate identically. |
| W3 | provenance | Investment reported cumulative %GDP from the unaligned series (overstated vs what entered the model). | Reports from the aligned path. |
| S2/S3 | robustness | Long-format reader could sum CO2e+PM2.5; demand-response divide-by-zero unguarded. | Long reader filters to one emission; demand response guards the denominator. |

## Flagged / deferred (guardrails fire, but the deeper fix is a design choice)

- **Unit/deflator bridge.** Both `investment` (MUSD÷GDP) and `carbon` (USD/tCO2 vs OG numéraire)
  assume CLEWS monetary ≈ real-USD. The carbon guardrail fires (a 50/0.5 default implies a 25×
  `tau_c` add-on — clearly wrong units). The real fix is the `factor`/deflator bridge the contract
  promises; until then, treat the magnitudes of these two channels as illustrative.
- **Carbon's OG base is structural-only.** OG has no energy in production, so the OG carbon tax
  prices ~1.4% of consumption (household energy); industrial carbon is unpriced. CLEWS prices it
  system-wide. This is a known limitation of the pair, documented in provenance, not a bug.
- **Exact revenue-neutral recycling** needs a post-solve read of reform `cons_tax_revenue` + a
  re-solve (a one-step iteration). First-order is implemented; the exact loop is future work.
- **`energy_cmin` calibration.** The necessity-incidence experiment needs `c_min` calibrated below
  every income group's baseline energy consumption; the guardrail catches gross violations only.

## Confirmed sound (survived all three reviews)

The `tau_c` energy-price wedge (enters the demand FOC, the budget, the composite price, and books
`cons_tax_revenue` correctly); the index concordance (energy industry 1 / good 1); the carbon
one-price *setting* (same exogenous price to both sides, not re-inferred from a dual); the
investment lever mechanics (`alpha_I → I_g → K_g →` CES); the health sign conventions and the
`e`/`chi_n`/mortality application matching `PEP_simulation.py`; the discount-rate real/period
conventions for PHL (S=80 → one period = one year); all parameter shapes and TPI keys.
