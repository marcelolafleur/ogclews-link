# OG-Core settable surface: an evidence-grounded inventory

Purpose: enumerate every parameter OG-Core's `Specifications` object exposes (i.e. everything a
coupling channel could set), classify each into an economic surface, and mark which ones the current
`explore/channel-space` channels already touch. Code is truth. All citations are `file:line` into the
**installed** ogcore package (verified below), not a checkout.

## Environment verified

```
$ /Users/mlafleur/Projects/OG-PHL/.venv/bin/python -c "import ogcore, os; print(ogcore.__version__, os.path.dirname(ogcore.__file__))"
0.16.3 /Users/mlafleur/Projects/OG-PHL/.venv/lib/python3.12/site-packages/ogcore
```

All `ogcore/<file>.py:<line>` citations below resolve under that install path. `default_parameters.json`
in the same directory (2.2MB) is the schema of record; it has **130 top-level keys** (129 real parameters
+ 1 `schema` metadata key). Every one of the 130 keys is classified exactly once below (verified
programmatically — no key double-counted or dropped).

Channel source checked: `/Users/mlafleur/Projects/ogclews-link-channels/ogclews_link/channels.py` and
`ogclews_link/policy_levers.py` on branch `explore/channel-space`.

---

## Surface counts (of 130 total keys)

| Surface | Count |
|---|---|
| household | 12 |
| demographics | 13 |
| productivity/ability | 3 |
| production/firm | 8 |
| fiscal-spending | 26 |
| fiscal-tax | 24 |
| open-economy | 8 |
| pensions | 18 |
| closure/solver | 18 |

---

## 1. Household (preferences, labor, subsistence, bequests) — 12 params

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `sigma` | scalar (CRRA) | `household.py:599,604,608,610,614,619,780` — marginal utility of consumption | always active | risk-aversion calibration lever | no |
| `chi_b` | vector, length J (per ability type) | `household.py:496,518` — utility weight on bequests | always active (bequests exist whenever `use_zeta`/BQ logic runs) | bequest-motive strength | no |
| `chi_n` | matrix (S ages × ... ), extrapolated to (T+S,S) in `parameters.py:295-299` | `household.py` labor disutility; `SS.py:102`, `TPI.py:314,403` | always active | labor-supply disutility by age | no |
| `ltilde` | scalar | `household.py:93,99-148` (labor FOC), `SS.py:117,1150,1395,1401`, `TPI.py:455,1574` | always active | time endowment (labor supply ceiling) | no |
| `frisch` | scalar | `parameters.py:114` (derives `b_ellipse`/`upsilon` for the labor disutility function); `parameter_plots.py:284` | always active | Frisch elasticity of labor supply | no |
| `beta_annual` | vector, length J (per ability type; special-cased in `parameters.py:90-133`) | derives `p.beta` → `household.py:497,519` (discount factor in Euler eq.) | always active | household patience / savings | no |
| `c_min` | vector, length I (per consumption good) | `household.py:354,356,359` (min-cons floor in budget constraint); `SS.py:439,1035,1044`, `TPI.py:1123,1135` | always active | subsistence/necessity floor per good — **this is the energy-price channel's regressivity lever** | **yes** — `energy_price` (`channels.py:130-132`) sets `c_min[i_e]` |
| `alpha_c` | vector, length I | `TPI.py:524,804,820,956,1122,1134`; `SS.py:283,439,537,837,1034,1044` — CES/Cobb-Douglas weights on composite consumption good | always active | relative taste weights across consumption goods (food/energy/etc.) | no |
| `tau_bq` | vector (T+S,) or scalar-broadcast | `tax.py:536,540,542,544,548` — linear tax on bequests | always active | bequest taxation | no |
| `use_zeta` | bool | `household.py:176`, `aggregates.py:227`, `SS.py:1393,1404,1479`, `TPI.py:899` | default `False` (see JSON) — when off, bequests are distributed by `lambdas`/`omega` instead of `zeta` | switches bequest-distribution mechanism | no |
| `zeta` | matrix (S,J) | `household.py:179,183,187,193` — bequest distribution process | only load-bearing when `use_zeta=True` | age/type profile of who receives bequests | no |
| `lambdas` | vector, length J | pervasive: `aggregates.py:40-478`, `household.py:179-495`, `tax.py:526,531` — population share by ability type | always active | ability-type population weights | no |

## 2. Demographics (mortality/fertility/immigration/population) — 13 params

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `omega` | (T+S, S) | `aggregates.py:44,84,147,149,204,315,423`; `household.py:184-297` | always active | population-by-age time path | **yes (indirectly)** |
| `omega_SS` | (S,) | `aggregates.py:40,72,137,138,193,306,407`; `household.py:179-291`; `SS.py:519` | always active | steady-state age distribution | **yes (indirectly)** |
| `omega_S_preTP` | (S,) | `aggregates.py:132,133,189,204` | always active | pre-transition age distribution | **yes (indirectly)** |
| `imm_rates` | (T+S, S) | `aggregates.py:73,86,139,151` | always active | immigration-rate path | **yes (indirectly)** |
| `imm_rates_preTP` | (S,) | `aggregates.py:134` | always active | pre-transition immigration rate | **yes (indirectly)** |
| `rho` | (T+S, S) | `aggregates.py:195,207`; `SS.py:80`; `TPI.py:291,404`; `household.py:544` | always active | mortality-rate path by age | **yes (indirectly)** |
| `rho_preTP` | (S,) | `aggregates.py:191,207` | always active | pre-transition mortality | **yes (indirectly)** |
| `g_n` | (T+S,) | `fiscal.py:84,197,201,491`; `aggregates.py:79-337`; `pensions.py:669-722` | always active | population growth path | **yes (indirectly)** |
| `g_n_preTP` | scalar | `fiscal.py:84`; `aggregates.py:135,190,213,222,325,326` | always active | pre-transition pop growth | **yes (indirectly)** |
| `g_n_ss` | scalar | `fiscal.py:253,256,496`; `aggregates.py:79-338` | always active | steady-state pop growth | **yes (indirectly)** |
| `constant_demographics` | bool | `parameters.py:342` (zeroes out `g_n`/`g_n_ss`/`g_n_preTP` when True) | default `False` | flat-demographics toggle | no |
| `starting_age` | int | `parameters.py:114,315` (feeds `retire`, labor-disutility calc) | always active | model's youngest economically-active age | no |
| `ending_age` | int | `parameters.py:135,139,144,335` (feeds `rate_conversion` for delta/g_y/delta_tau) | always active | maximum lifespan | no |

**Used-now note:** the `health` channel (`channels.py:460-575`) does **not** mutate demographic params
directly, but on the mortality branch it stages `ctx.extras["health_shock"]` (`channels.py:548-549`),
which `og_runner.py:417-437` (`_apply_health`) feeds through `health_pop.disease_pop` →
`ogcore.demographics.get_pop_objs` (`demographics.py:1156-1166`, whose `pop_dict` keys are literally
`omega`, `g_n_ss`, `omega_SS`, `rho`, `g_n`, `imm_rates`, `omega_S_preTP`, `imm_rates_preTP`, `rho_preTP`,
`g_n_preTP`) → `p.update_specifications(pop_dict)` (`og_runner.py:435`). So **all 10 of those demographic
params are already load-bearing** through the health channel's mortality path, even though no line in
`channels.py` itself sets `p.omega` etc. `constant_demographics`, `starting_age`, `ending_age` remain
untouched by any channel.

## 3. Productivity/ability (e, Z, g_y) — 3 params

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `e` | (T+S, S, J) effective-labor/ability matrix | pervasive: `aggregates.py:40-202`; `household.py:22-809`; `pensions.py:33-408`; `TPI.py:1060-1478`; `SS.py:140-1082` | always active | ability×age effective-labor profile | **yes** — `health` channel's morbidity branch mutates `p.e` in place (`channels.py:562-571`) |
| `g_y_annual` | scalar | `parameters.py:143-144` derives `p.g_y` → `household.py:377,599,610`; `fiscal.py:84-496`; `aggregates.py:80-274`; `pensions.py:669-722` | always active | exogenous labor-augmenting TFP growth rate | no |
| `J` | int (dimension) | ability-type count, sizes `lambdas`/`chi_b`/`e`'s 3rd axis | always active (dimension, not a shock lever) | number of ability types modeled | no |

Note: `Z` (industry TFP) is classified under production/firm below since it is the firm-side production
function's total factor productivity, not a household ability parameter — despite the surface-category
name "productivity/ability (e, Z, g_y)" grouping them together in the task brief, `Z` is economically a
firm/production-technology object (see `firm.py`), so it's tabulated there for accuracy; it is the single
most channel-relevant parameter in the whole surface (three separate current channels write it).

## 4. Production/firm (gamma, epsilon, delta, io_matrix, TFP) — 8 params

**No energy/water/climate-native input exists in OG-Core's firm code.** `grep -ni
"energy\|water\|climate\|emission\|carbon\|fuel\|electric" ogcore/firm.py` returns **zero matches** (and
zero matches across the whole package outside doc/plotting helper filenames). The production function is
a pure value-added CES over private capital, public capital, and labor per industry (`firm.py`); there is
no intermediate-input / energy-in-production channel. This is why the current channels' own docstrings
say things like *"OG-Core has no inter-industry intermediates"* (`channels.py:152`) and *"OG has no
energy in production, so this is the only door"* (`channels.py:85`).

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `Z` | (T+S, M) industry TFP | pervasive in `firm.py:64-680` (every production/factor-demand function) | always active | industry-level total factor productivity — the GE-consistent way to move an industry's price | **yes** — `energy_price_tfp` (`channels.py:169-176`), `energy_cost_push` (`channels.py:207-222`), `energy_capex`'s underlying `set_investment_incentive` reads `p.Z.shape` (`policy_levers.py:91`) |
| `gamma` | (M,) capital's output share, time-invariant | `firm.py:62-674` | always active | capital vs. labor factor-share by industry | **yes** — `capital_intensity` via `policy_levers.set_capital_intensity` (`policy_levers.py:140-158`) |
| `gamma_g` | (M,) public-capital output share | `firm.py:61-675`; `SS.py:509,869`; `TPI.py:882,1280` | always active | public-capital share in each industry's production | no (read, never mutated, by current channels) |
| `epsilon` | (M,) elasticity of substitution (K,K_g,L) | `firm.py:57-676` | always active | CES vs Cobb-Douglas curvature per industry | no |
| `delta_annual` | scalar | `parameters.py:134-135` derives `p.delta` → `tax.py:225-246`; `aggregates.py:81-105`; `firm.py:223-559`; `SS.py:1331` | always active | private-capital depreciation rate | no |
| `delta_g_annual` | scalar | `parameters.py:138` derives `p.delta_g` → `fiscal.py:493,497` | always active | public-capital depreciation rate | no |
| `io_matrix` | (I, M) Leontief input-output map | `aggregates.py:406,419`; `SS.py:277-1112`; `TPI.py:521-1541` | always active | maps industry output to consumption goods (M→I) | no |
| `M` | int (dimension) | number of industries; sizes `Z`/`gamma`/`epsilon`/`io_matrix` | always active | industry-count dimension | no (dimension, not a shock lever) |

## 5. Fiscal-spending (alpha_G/I/T, baseline-spending variants) — 26 params

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `alpha_G` | (T+S,) share of GDP | `fiscal.py:95,102,296` | **active by default** (`budget_balance=False`) | government consumption spending rule | no (available via `policy_levers.route_revenue(to="government_consumption")`, `policy_levers.py:175`, but no channel calls it) |
| `alpha_I` | (T+S,) share of GDP | `fiscal.py:457,459` | active by default | public (infrastructure) investment → `K_g` | **yes** — `investment` (`channels.py:262-264`) |
| `alpha_T` | (T+S,) share of GDP | `fiscal.py:383,385`; `TPI.py:861`; `SS.py:723-1588` | active by default | government transfers | **yes** — `_recycle_via_transfers` (`channels.py:51`) |
| `alpha_bs_G` | (T+S,) | `fiscal.py:93` | **silent no-op by default** — only read when `baseline_spending=True` (default `False`, `default_parameters.json`) | proportional adjustment to G *relative to the baseline run* | no |
| `alpha_bs_I` | (T+S,) | `fiscal.py:452,454` | **silent no-op by default** (`baseline_spending=False`) | proportional adjustment to I_g relative to baseline | **yes, but guarded** — `investment(..., use_baseline_spending=True)` writes it and prints a guardrail warning that it is inert unless `p.baseline_spending=True` (`channels.py:266-269`) |
| `alpha_bs_T` | (T+S,) | `fiscal.py:380`; `SS.py:721,728,801` | **silent no-op by default** (`baseline_spending=False`) | proportional adjustment to TR relative to baseline | no |
| `baseline_spending` | bool | `fiscal.py:92,379,450`; `TPI.py:176,846,1242,1378`; `SS.py:720-1597` | default `False` | **the closure switch** — flips G/I_g/TR from `alpha_*` rules to `alpha_bs_*` relative-to-baseline rules | no channel flips it; `investment`'s `use_baseline_spending` kwarg assumes the caller has |
| `budget_balance` | bool | `TPI.py:831`; `fiscal.py:100,248,295,366`; `SS.py:722,729,1287` | default `False` | **the master closure switch**: `True` forces `TR=alpha_T*Y` residual/balanced-budget each period; `False` (default) lets debt absorb the gap and G/I/T follow their `alpha_*` rules | no |
| `debt_ratio_ss` | scalar | `fiscal.py:128,139,165,251`; `SS.py:445,496,834` | active whenever debt is not fixed by `budget_balance=True` | long-run debt/GDP anchor | no |
| `eta` | (T+S, S, J) | `household.py:240-297` | active by default | transfer allocation shape (who receives `TR`) | no |
| `infra_investment_leakage_rate` | scalar | `fiscal.py:486` (`phi_g`) | active by default | share of public infra capex that "leaks" (doesn't become usable `K_g`) | no |
| `initial_Kg_ratio` | scalar | `TPI.py:868,1245` | active by default | initial public-capital/GDP ratio | no |
| `initial_debt_ratio` | scalar | `fiscal.py:88` | active by default | initial debt/GDP ratio | no |
| `r_gov_DY` | scalar | `fiscal.py:417,425` | active by default | linear debt→gov-borrowing-rate effect | no |
| `r_gov_DY2` | scalar | `fiscal.py:418,426` | active by default | quadratic debt→gov-borrowing-rate effect | no |
| `r_gov_scale` | (T+S,) or scalar | `fiscal.py:415,423` | active by default | scale on market rate → gov rate | no |
| `r_gov_shift` | (T+S,) or scalar | `fiscal.py:416,424` | active by default | shift on market rate → gov rate | no |
| `rho_G` | scalar | `fiscal.py:128`; `aggregates.py:265-277` (via `tG1`/`tG2`) | active by default | speed of convergence to steady debt/GDP during the closure window | no |
| `tG1` | int | `fiscal.py:125`; `aggregates.py:265-273`; `TPI.py:759` | active by default | period budget-closure rule engages | no |
| `tG2` | int | `fiscal.py:125,137`; `aggregates.py:269-277`; `TPI.py:759` | active by default | period budget-closure rule / remittance ramp ends | no |
| `ubi_growthadj` | bool | `parameters.py:403` | active whenever any `ubi_nom_*` is nonzero | growth-adjust UBI or not | no |
| `ubi_nom_017` | scalar | `parameters.py:390` | active whenever nonzero | UBI amount, ages 0-17 | no |
| `ubi_nom_1864` | scalar | `parameters.py:391` | active whenever nonzero | UBI amount, ages 18-64 | no |
| `ubi_nom_65p` | scalar | `parameters.py:392` | active whenever nonzero | UBI amount, ages 65+ | no |
| `ubi_nom_max` | scalar | `parameters.py:394` | active whenever nonzero | UBI household cap | no |

## 6. Fiscal-tax (tau_c, cit, itc, delta_tau, payroll, wealth, etr/mtr) — 24 params

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `tau_c` | (T+S, I) consumption tax by good | `household.py:545-702`; `tax.py:575,578`; `SS.py:156-1044`; `TPI.py:524-1133` | always active | consumption-tax wedge — **the primary energy-price channel instrument** | **yes** — `energy_price` (`channels.py:111-121`), `carbon_tax` (`channels.py:378-382`) |
| `cit_rate` | (T+S,) statutory CIT rate | `parameters.py:328` derives `p.tau_b` (business income tax); no direct `p.cit_rate` reads elsewhere | always active | statutory corporate tax rate (feeds `tau_b`) | no |
| `adjustment_factor_for_cit_receipts` | (T+S,1) | `parameters.py:330-333` (feeds `tau_b`) | always active | CIT-receipts calibration adjustment | no |
| `c_corp_share_of_assets` | scalar | `parameters.py:329` (feeds `tau_b`) | always active | share of business assets in C-corps (feeds effective business tax) | no |
| `capital_income_tax_noncompliance_rate` | (T+S, J) | `household.py:499-532`; `tax.py:348-375`; `TPI.py:1470` | always active | capital-income tax evasion/noncompliance rate | no |
| `inv_tax_credit` | (T+S, M) | `firm.py:213-556`; `tax.py:223-243` | always active | investment tax credit by industry — **the energy-capex ITC lever** | **yes** — `energy_capex` via `policy_levers.set_investment_incentive` (`policy_levers.py:98-100`) |
| `delta_tau_annual` | (T+S, 1) annual | `parameters.py:334-338` derives `p.delta_tau` → `firm.py:211-555`; `tax.py:221-241` | always active | accelerated tax depreciation by industry — **second `energy_capex` lever** | **yes** — `energy_capex` (accelerated_depreciation kwarg → `policy_levers.py:101-103`) |
| `tau_b` (derived from `cit_rate` etc., not its own JSON key but load-bearing) | (T+S, M) | `firm.py:212-559`; `aggregates.py:491,495`; `tax.py:222-242` | always active | effective per-industry business tax rate — **third `energy_capex` lever** | **yes** — `energy_capex` (cit_rate_multiplier kwarg → `policy_levers.py:104-106`) |
| `tau_payroll` | (T+S,) | `household.py:694-701`; `tax.py:399-414` | always active | linear payroll tax rate | no |
| `frac_tax_payroll` | (T+S,) | `aggregates.py:416,436` | always active | share of IIT+payroll revenue attributable to payroll | no |
| `h_wealth` | (T+S,1) | `household.py:541-552`; `tax.py:457-499` | always active | wealth-tax function numerator | no |
| `m_wealth` | (T+S,1) | `household.py:542-553`; `tax.py:457-499` | always active | wealth-tax function denominator term | no |
| `p_wealth` | (T+S,1) | `household.py:543-554`; `tax.py:457-491` | always active | wealth-tax function scale | no |
| `income_tax_filer` | (T+S, J) | `household.py:500-732`; `tax.py:350-377`; `SS.py:920`; `TPI.py:1475` | always active | income-tax filer indicator (who pays IIT) | no |
| `wealth_tax_filer` | (T+S, J) | `household.py:501-536`; `tax.py:442-452` | always active | wealth-tax filer indicator | no |
| `etr_params` | (T+S, S, n) polynomial coeffs | `SS.py:81-891`; `TPI.py:292-1435` | always active | estimated effective-tax-rate function | no (estimation output, not a natural coupling target) |
| `mtrx_params` | (T+S, S, n) | `SS.py:104-898`; `TPI.py:316-1445` | always active | marginal tax rate on labor income function | no |
| `mtry_params` | (T+S, S, n) | `SS.py:82-905`; `TPI.py:293-1455` | always active | marginal tax rate on capital income function | no |
| `tax_func_type` | str | `tax.py:118-186`; `TPI.py:579-668` | always active | functional form for ETR/MTR (e.g. "DEP", "GS", "mono") | no |
| `analytical_mtrs` | bool | `tax.py:168-188` | default depends on estimation config | analytically-derived vs. estimated MTRs flag | no |
| `age_specific` | bool (**default `True`**) | `txfunc.py:982-1910` **only** (tax-function estimation pipeline, not `SS.py`/`TPI.py`) | active only during offline tax-function estimation, not during a solve | whether IIT functions vary by age — an estimation-time flag | no |
| `constant_rates` | bool | referenced only in `parameter_tables.py:187` (a documentation/reporting table); no `SS.py`/`TPI.py`/`tax.py` runtime read found | effectively inert at solve time | flag intended to force linear tax functions; not wired into the runtime solve in this version | no |
| `zero_taxes` | bool (default `False`) | referenced only in `parameter_tables.py:188`; no runtime read found in `SS.py`/`TPI.py`/`tax.py`/`household.py` | effectively inert at solve time in 0.16.3 | flag intended to zero out all IIT; not wired into the runtime solve in this version | no |
| `labor_income_tax_noncompliance_rate` | (T+S, J) | `household.py:705-729`; `tax.py:345-372`; `TPI.py:1464`; `SS.py:912-916` | always active | labor-income tax noncompliance rate | no |
| `mean_income_data` | scalar | used by the tax-function estimation pipeline (`txfunc.py`), not by `SS.py`/`TPI.py` directly | estimation-time only | mean income scale for tax-function estimation | no |

*(`h_wealth`/`m_wealth`/`p_wealth`/`income_tax_filer`/`wealth_tax_filer` counted once each above — 24
total tax params, cross-checked against the classification script.)*

## 7. Open-economy (world rate, foreign debt, zeta_D/K, remittances) — 8 params

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `world_int_rate_annual` | scalar | `parameters.py:305-309` derives `p.world_int_rate` → `SS.py:455-858`; `TPI.py:828-1275` | active only where `zeta_K==1` (open-economy industries) | exogenous world interest rate | no |
| `zeta_D` | (T+S,) or scalar, share of new debt bought by foreigners | `fiscal.py:193,254` | always active | foreign share of government debt purchases | no |
| `zeta_K` | (T+S,) or scalar, per-industry open-economy switch | `SS.py:480-861`; `TPI.py:805-1285` | always active (determines whether `r` is pinned to `world_int_rate` per industry) | small-open-economy capital-market closure per industry | no |
| `initial_foreign_debt_ratio` | scalar | `fiscal.py:190` | active by default | initial share of debt held by foreigners | no |
| `alpha_RM_1` | scalar | `aggregates.py:264` | active by default | remittances/GDP ratio, period 1 | no |
| `alpha_RM_T` | scalar | `aggregates.py:261,272,277` | active by default | remittances/GDP ratio, long run | no |
| `g_RM` | (T+S,) | `aggregates.py:267,274` | active by default | remittance growth rate between `tG1`/`tG2` | no |
| `eta_RM` | (T+S, S, J) | `household.py:282-297` | active by default | remittance allocation shape across households | no |

## 8. Pensions — 18 params

| param | shape | consumed where | default closure | channel-relevance | used now? |
|---|---|---|---|---|---|
| `pension_system` | str, one of {"US-Style Social Security","Defined Benefits","Notional Defined Contribution","Points System"} | `pensions.py:101-107,475-480` | selects which of the below sub-blocks is live | pension-system regime switch | no |
| `replacement_rate_adjust` | (T+S, J) | `pensions.py:159-199`; `TPI.py:548-641` | active under "US-Style Social Security" | Social Security replacement-rate reform lever | no |
| `retirement_age` | int | `parameters.py:313-317` derives `p.retire` → `pensions.py:45-724` | always active | statutory retirement age | no |
| `AIME_bkt_1` / `AIME_bkt_2` | scalars | `pensions.py:51-61` | active under US-style SS | AIME bend-point brackets | no |
| `PIA_rate_bkt_1/2/3` | scalars | `pensions.py:52-61` | active under US-style SS | PIA replacement rates per bracket | no |
| `PIA_minpayment` / `PIA_maxpayment` | scalars | `pensions.py:64-66` | active under US-style SS | PIA floor/ceiling | no |
| `alpha_db` | scalar | `pensions.py:250-574` | active under "Defined Benefits" | DB replacement-rate parameter | no |
| `avg_earn_num_years` | int | `pensions.py:41-562` | active under DB/NDC/points systems | years averaged for benefit base | no |
| `baseline_theta` | bool | `pensions.py:68` | default `False` | whether reform runs keep the *baseline* replacement rate | no |
| `indR` | scalar | `pensions.py:726` | active under NDC | survivor-benefit adjustment | no |
| `k_ret` | scalar | `pensions.py:726` | active under NDC | payment-frequency adjustment | no |
| `tau_p` | scalar | `pensions.py:334-530` | active under NDC | NDC contribution tax rate | no |
| `vpoint` | scalar | `pensions.py:413-610` | active under Points System | value of one pension point | no |
| `yr_contrib` | int | `pensions.py:227-563` | active under points/DB systems | years of contribution counted | no |

## 9. Closure/solver (dimensions + numerics — not economic levers) — 18 params

`I`, `J` (ability-type count — tabulated under productivity/ability above, not repeated), `M`, `S`, `T`,
`schema`, `FOC_root_method`, `SS_root_method`, `RC_SS`, `RC_TPI`, `mindist_SS`, `mindist_TPI`, `maxiter`,
`nu`, `use_sparse_FOC_jac`, `initial_guess_TR_SS`, `initial_guess_factor_SS`, `initial_guess_r_SS`,
`reform_use_baseline_solution`, `start_year`. These size the model or tune solver convergence; none is an
economic channel target. (Per the task brief, detail skipped.)

---

## OG-PHL industry and goods lists (the concrete M/I a channel indexes into)

Checked in `/Users/mlafleur/Projects/OG-PHL/ogphl/constants.py` (the committed `main` branch) and the
`feature/multi-industry-calibration` worktree at
`/Users/mlafleur/Projects/OG-PHL/.claude/worktrees/m8-compat` (the branch that carries the isolated-
electricity M=8 split referenced in prior session memory).

**Committed `main` (`ogphl/constants.py:349-400`) — M=7, electricity fused with water:**
`PROD_DICT` = Agriculture and Fishing, Mining, **Utilities (`aelec`+`awatr` fused)**, Construction, Trade
and Transport, Services, Manufacturing.

**`feature/multi-industry-calibration` worktree (`ogphl/constants.py:372-400` there) — M=8, electricity
isolated (`constants.py:385-389`: *"Utilities split into Electricity and Water so electricity is its own
industry"*):**

```
PROD_DICT (M=8): Agriculture and Fishing, Mining, Electricity, Water,
                 Construction, Trade and Transport, Services, Manufacturing
CONS_DICT (I=5): Food, Energy and water, Non-durables, Durables, Services
```

Note the asymmetry the channels' docstrings rely on: the **industry** split isolates Electricity as its
own OG production sector (`energy_industry_index`, used by `Z`/`gamma`/`inv_tax_credit`/`delta_tau`/
`tau_b` channels), but the **consumption good** side still fuses electricity with water into "Energy and
water" (`energy_good_index`, used by `tau_c`/`c_min` channels) — there is no isolated household energy
good, only an isolated energy *industry*.

---

## Channel-usage summary (what's already spoken for)

Grepped `p.<param>` / `og_reform.<param>` mutations in `channels.py` + the mutation helpers it calls in
`policy_levers.py`:

- `p.tau_c` — `energy_price`, `carbon_tax`
- `p.c_min` — `energy_price` (subsistence floor)
- `p.alpha_T` — `_recycle_via_transfers` (used by `energy_price`/`carbon_tax` when `recycle_revenue_to_transfers=True`)
- `p.Z` — `energy_price_tfp`, `energy_cost_push`
- `p.alpha_I` / `p.alpha_bs_I` — `investment`
- `p.gamma` — `capital_intensity` (via `policy_levers.set_capital_intensity`)
- `p.inv_tax_credit`, `p.delta_tau`, `p.tau_b` — `energy_capex` (via `policy_levers.set_investment_incentive`)
- `p.e` — `health` (morbidity branch, direct mutation in `channels.py:562-571`)
- `omega`, `omega_SS`, `omega_S_preTP`, `imm_rates`, `imm_rates_preTP`, `rho`, `rho_preTP`, `g_n`,
  `g_n_ss`, `g_n_preTP` — `health` (mortality branch, indirect via `_apply_health` →
  `health_pop.disease_pop` → `ogcore.demographics.get_pop_objs` → `p.update_specifications(...)`)

`policy_levers.route_revenue` (`policy_levers.py:164-186`) can also write `alpha_T`, `alpha_I`, or
`alpha_G` (`"deficit"` is a documented no-op), but **no channel currently calls it** — it is dead code from
a channel-graph standpoint today (per session memory, this function and two siblings were removed from
the `main` trunk and currently live only on `explore/channel-space` / other lanes).

That is **13 distinct parameters directly mutated** + **10 more indirectly mutated via the health
channel's demographic re-solve** = **23 of 130** total default-parameter keys touched by any channel today.

---

## Unused surface: the raw material for new channels

Every param below is economically meaningful, is load-bearing under the model's **default closure**
(`budget_balance=False`, `baseline_spending=False`, unless noted), and is touched by **zero** current
channels or their helpers.

1. **`alpha_G`** — government consumption/GDP. `route_revenue` supports writing it but nothing calls that
   path; a CLEWS-side driver (e.g. energy-subsidy fiscal cost) could route through here.
2. **`gamma_g`** — public capital's output share per industry (`firm.py:61-675`). Distinct from `gamma`
   (private capital share, already used by `capital_intensity`); no channel touches the *public*-capital
   elasticity, even though `investment` already drives `alpha_I → K_g`.
3. **`epsilon`** — CES/Cobb-Douglas substitution elasticity per industry (`firm.py:57-676`). A structural
   "how substitutable is capital-for-labor in electricity generation" lever, never touched.
4. **`delta_g_annual`** — public-capital depreciation rate (`fiscal.py:493,497`). Grid/T&D degradation
   rate is a natural CLEWS-sourced quantity and is currently just the model default.
5. **`world_int_rate_annual` / `zeta_K`** — the open-economy capital-market closure. A CLEWS-driven story
   about capital mobility into/out of the energy sector (distinct from the domestic `capital_intensity`
   and `energy_capex` levers already built) is entirely open.
6. **`zeta_D` / `initial_foreign_debt_ratio`** — who finances public debt (foreign vs. domestic). Relevant
   if a channel ever finances grid investment via foreign borrowing rather than `alpha_I`.
7. **`tau_payroll` / `frac_tax_payroll`** — payroll tax instruments, untouched; a labor-cost channel (e.g.
   payroll tax credits for green-jobs employment) has no current analogue.
8. **`h_wealth` / `m_wealth` / `p_wealth`** — the full wealth-tax function. No channel expresses "carbon
   wealth" or capital-levy ideas through it.
9. **`eta`** — who receives government transfers, by age/type (`household.py:240-297`). The `_recycle_via_transfers`
   helper only bumps the *level* of `alpha_T`; it never touches `eta`'s incidence shape, so revenue
   recycling today is distributionally naive (uniform per the existing `eta` default) even though the
   model supports a targeted rebate.
10. **`ubi_nom_017` / `ubi_nom_1864` / `ubi_nom_65p` / `ubi_nom_max` / `ubi_growthadj`** — a full universal
    basic income block, entirely unused; an alternative (non-`alpha_T`) revenue-recycling design for a
    carbon tax could route through UBI instead of lump-sum transfers.
11. **`pension_system` and its entire sub-block** (`replacement_rate_adjust`, `retirement_age`, AIME/PIA
    brackets, `alpha_db`, `indR`, `k_ret`, `tau_p`, `vpoint`, `yr_contrib`, `avg_earn_num_years`,
    `baseline_theta`) — 18 params, zero touched. An aging-driven labor-supply or fiscal-sustainability
    story for the energy transition (e.g. energy-transition job losses interacting with early retirement)
    has no current channel.
12. **`io_matrix`** — the Leontief map from industries to consumption goods (`aggregates.py:406-419`;
    `SS.py:277-1112`). Every current channel takes the io-matrix as given; none *reweights* it (e.g. to
    model a shift in which goods draw more on the electricity industry as generation mix changes).
13. **`capital_income_tax_noncompliance_rate` / `labor_income_tax_noncompliance_rate`** — tax evasion
    rates, untouched. Relevant to informal-sector energy-transition narratives (e.g. informal generators).
14. **`c_corp_share_of_assets` / `adjustment_factor_for_cit_receipts` / `cit_rate`** — the broader
    corporate-tax base feeding `tau_b`; only the multiplicative `tau_b_mult` knob in `energy_capex` reaches
    this indirectly, and only for one industry — the *economy-wide* CIT rate itself is never a channel
    input (e.g. a green-CIT-surcharge-funded ITC design would need it).
15. **`etr_params` / `mtrx_params` / `mtry_params` / `tax_func_type`** — the household income-tax function
    itself. No channel models a broader fiscal-reform financing mechanism for energy policy through the
    income tax (only `tau_c`, `alpha_T`, and industry-specific business taxes are used today).
16. **`debt_ratio_ss` / `initial_debt_ratio` / `r_gov_DY` / `r_gov_DY2` / `r_gov_scale` / `r_gov_shift` /
    `rho_G` / `tG1` / `tG2`** — the entire debt-financing/closure-timing block. A "how is the energy
    transition's fiscal cost financed over time" channel (debt path, not just the instantaneous
    `alpha_I`/`alpha_T` level) is untouched.
17. **`alpha_RM_1` / `alpha_RM_T` / `g_RM` / `eta_RM`** — remittances. Plausible if energy-transition
    emigration/remittance flows are ever modeled, currently inert.
18. **`chi_b` / `zeta` / `use_zeta`** — the bequest-motive/distribution block, entirely separate from the
    labor-supply and consumption parameters channels already touch.
19. **`infra_investment_leakage_rate` / `initial_Kg_ratio`** — the public-capital accumulation mechanics
    around `alpha_I`; `investment` sets the *flow* but never touches the leakage rate or the initial stock
    ratio that governs how much of that flow becomes usable `K_g`.

---

## Things worth flagging (could not fully resolve or note as caveats)

- `constant_rates` and `zero_taxes` appear in `default_parameters.json` and in `parameter_tables.py`'s
  documentation list, but a full-package grep found **no runtime read** of either in `SS.py`, `TPI.py`,
  `tax.py`, or `household.py` in ogcore 0.16.3 — they look like flags whose original wiring was retired or
  never completed in this version. Flagging rather than asserting a mechanism that isn't there.
- `age_specific` and `mean_income_data` are consumed only in `txfunc.py`, the offline tax-function
  *estimation* pipeline — not in the `SS.py`/`TPI.py` solve loop a coupling channel would run inside. They
  are real parameters but not solve-time coupling surface in the same sense as everything else here.
- The JSON schema's own per-key `"value"` list-shapes (e.g. "list-of-list, n_entries=1") describe the
  *validator's test values*, not necessarily the parameter's runtime array shape after `parameters.py`
  extrapolation/broadcast logic runs (e.g. `chi_n` starts as a 7-value-per-J stub and is extrapolated to
  (T+S, S) at `parameters.py:295-299`). Shapes in the tables above are the runtime shapes inferred from
  actual indexing in `firm.py`/`household.py`/etc., which is the more reliable source; where I was not
  fully certain of an exact axis order I described it qualitatively (e.g. "(T+S, M)") rather than guess.
