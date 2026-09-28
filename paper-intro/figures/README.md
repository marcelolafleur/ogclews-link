# Sources and adversarial selection of the short-paper illustrations

Updated 26 September 2026. This is an editorial/evidence record, not paper text.

## Current selection: the same outcome chart across channels

The latest revision supersedes the earlier mixed figure/table selection below.
It follows the user's preference for a repeated result chart so readers can compare
channels without learning a new encoding in each section.

The six charts used in the paper are `channel-macro-energy_price.pdf`,
`channel-macro-investment.pdf`, `channel-macro-capital_intensity.pdf`,
`channel-macro-health.pdf`, `channel-macro-carbon.pdf`, and
`channel-macro-coupled.pdf`. Every chart has:

- GDP, consumption, capital and labour, with fixed colours and line styles;
- 2026–2075 on the horizontal axis and -0.4% to +1.4% on the vertical axis;
- the saved unperturbed reform (`discount_rate`) as the comparison case;
- explicit finite-data and bounds checks, so no outcome is clipped;
- a short input explanation and interpretation next to the chart.

The demand and discount-rate experiments have bitwise-identical saved TPI/SS
outcomes. They solve the unperturbed reform and only emit return signals, making
them a useful common control. Their difference from the original baseline is not
assigned to channel effects. The cause of that offset remains undiagnosed; this
revision changes the comparison transparently rather than silently retaining it.

Public investment stays nearly flat on the common scale; its maximum absolute GDP
response (0.0018%) and public-spending/public-capital changes are stated, not visually
magnified. Capital intensity's large within-electricity responses remain in prose.
The capital run also has different solver settings (`nu`, `maxiter`); minute aggregate
GDP differences are not treated as validation of a specific economic sign.

The remembered standalone-versus-combined comparison is now provided by six
identically encoded charts beside the corresponding explanations. A second GDP
ranking or six-panel recap would duplicate them. The matched cumulative runs support
the combined-section account (-0.19% first-decade GDP with electricity/public
investment, +0.02% after adding health), without another chart. These are sequential,
conditional comparisons, not an additive decomposition of the standalone experiments.

Private incentives retain illustrative credit arithmetic: the older M4 ITC result
was documented but its native `/tmp` outputs were not recovered. The rate table uses
the combined manifest's first-decade mean portfolio return (8.156559%), alongside
an explicitly hypothetical 4% comparison. The demand table reconstructs the original
baseline-relative electricity-output ratios for 2026, 2030 and 2040. The first-decade
mean matches the manifest exactly. No July CSV export was recovered, and no returned
CLEWS outcome is claimed.

`figure-values.json` records the common-control results, true steady-state values,
selected demand ratios and plotting scale. `source-manifest.json` hashes the native
inputs, including the matched cumulative runs. The builder retains alternative
mechanism/age-profile/distribution figures for reference, but those files are not
included in the current paper. It does not change original gallery or model files.

The full supporting audit is in the model repository at
`docs/design/channel-figure-review-2026-09-26.md`. No model solves were run.

## Earlier selection (superseded; retained as decision history)

Follow the original gallery's explanation of how the linked case is built, but
do not assume a gallery chart isolates the channel suggested by its subject.
Put each selected visual at the first explanation of that channel; show the
combined outcome only after all eight channels.

The revised paper uses four numerical channel figures, four mechanism tables,
and two combined-outcome figures. This replaces the earlier four-panel snapshot
bars and three-horizon combined bars. Those two earlier PDF assets are unused.

## Selected visuals and rejected alternatives

| Channel / outcome | Selection | Why this is the defensible choice |
|---|---|---|
| Electricity cost | electricity-paths.pdf: saved applied household price adjustment alongside household energy consumption, from the standalone energy_price experiment | Source-to-response sequence, actual paths. The experiment does not recycle its notional revenue; text discloses this. Reject the old clews_signal_vs_applied plot: it reads a cost workbook rather than this run's reconstructed LCOE, averages a varying wedge into a flat line, and depends on mutable external inputs. The plotted good combines energy and water. |
| Public infrastructure | Mechanism table: construction adds public capital; taxes/debt finance it | The isolated example has negligible additional grid expenditure. Reject the coupled public-capital chart as isolated-channel evidence, and reject all-power capital expenditure as public infrastructure. No invented estimated benefit. |
| Generation capital intensity | capital-intensity-sectors.pdf: gallery's sectoral dot-plot function applied to the standalone experiment, focused on electricity | Capital-share parameter changes 0.781643 to 0.802438. Electricity output rises about 4.36%, capital use falls 4.76%, labour input falls 18.70%. This explains why a changed production structure is not an investment amount. Reject technology capex as a measure of factor intensity. Labour input is not headcount jobs. |
| Health | health-age-distributions.pdf: applied age profiles from standalone health parameters | Same normalized transformations as gallery mortality/morbidity figures. Show two distinct mechanisms; do not equate the heights, read them as risk levels, or infer death counts. Survival uses long-run rates weighted by baseline population; working capacity uses the first affected transition row, weighted over income groups. No claim all older-age capacity gains enter production. |
| Carbon price | carbon-transition.pdf: gallery macro transition for the standalone household-energy tax with transfers | Actual tax policy response, unlike the coupled run's emitted-but-unapplied carbon penalty. Does not estimate economy-wide carbon coverage or identify recycling's causal effect against a no-transfer counterfactual. Reject gallery revenue charts with hardcoded carbon labels and CO2e emissions as evidence of an imposed OG tax. |
| Private incentive | Fully usable 20% credit on an eligible investment costing 100: government support20, investor cost80 | Transparent accounting illustration, not a solved investment response. No isolated incentive run was found in this retained result set. Do not substitute capital-intensity results. |
| Planning discount rate | Present-value table:100 paid now vs in20years at4% and8% | Explains the intertemporal choice without inventing a technology response. Values45.6 and21.5 are arithmetic, not run results. Gallery rates_transition uses r rather than the emitted portfolio return r_p; it is not the right channel series. |
| Demand | Household/industry response → revised user demand → CLEWS re-optimisation table | Explains the intended mechanism. Text explicitly distinguishes the retained run's sector-output proxy and lack of completed return solve. Household energy_by_income is not the demand quantity that run exported. |
| Combined timing | combined-transition.pdf: gallery macro_transition function, frozen coupled output | True annual paths2026–2075, not snapshot interpolation. GDP peak+0.413636579% in2042. The2075 endpoint is not SS. The fiscal-rule marker is2046. |
| Combined distribution | combined-consumption-age.pdf: gallery consumption_by_age from frozen SS | Income-group-weighted average percentage changes at each age, with income-group range. A steady-state cross-section, not one cohort's path, confidence band, or welfare valuation. Prefer this to CEV charts whose interpretation includes excluded cells, age caps, and omitted bequest utility. |

The comparison section has been shortened and placed before the channel walkthrough,
so literature positioning no longer interrupts mechanisms → combined outcome.

## Data provenance and checks

- Case: Philippines, PEP_vs_Base, archived July11 battery.
- Local archive:
  /Users/mlafleur/Projects/ogclews-link/ogclews_runs/battery
- Baseline:
  _og_baseline_cache/og-phl-0.1.0-ogphl_multisector_default_parameters
- Reforms:
  energy_price/energy_price, capital_intensity/capital_intensity,
  health/health, carbon/carbon, coupled/coupled.
- Inputs: retained model_params.pkl, TPI/TPI_vars.pkl, SS/SS_vars.pkl and
  ogclews_manifest.json. These are trusted local model outputs.
- Baseline metadata records M=8, I=5, start2026, OG-Core0.16.3; electricity
  industry2 and energy/water good1. Names are loaded from baseline_meta.json.
- The generator checks Y,C,K,L at t0,t10 and final transition against the
  committed July golden record; the electricity run has tiny numerical drift.
- The source-manifest.json file records SHA256 hashes of every loaded archived
  file, the plotting-module hash, the run timestamp, and the illustrative arithmetic.
- Health profiles each normalize to100% (absolute shares for working capacity).
- Native TPI and NPZ combined Y,C,K,L paths were independently checked bitwise
  over the first50 observations.
- No model solves were launched. No external current CLEWS CSVs were read.
- These are not the later August GOLD replication or current MUIOGO results.

The July run's original external PEP_v9 CSV directory now carries August12 files.
Consequently, do not regenerate its emissions, capex, or source-signal plots from
that directory and label the result July evidence. Frozen applied parameters and
model results are the numerical source for this paper.

## Figure generation

Use the existing OG-PHL environment; do not install dependencies globally:

    MPLCONFIGDIR=/tmp/ogclews-short-mpl /Users/mlafleur/Projects/OG-PHL.m8fix/.venv/bin/python paper-intro/build_figures.py --plot-repo /Users/mlafleur/Projects/ogclews-link --archive-root /Users/mlafleur/Projects/ogclews-link/ogclews_runs/battery

Then compile from paper-intro with latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex.

The script pins and checks the plotting-repo import. It uses the gallery functions
for capital-sector, carbon transition, combined transition and age-consumption
charts. It reproduces the frozen electricity and health transformations explicitly.
Presentation headers are simplified, and misleading inherited jobs/spending labels
are corrected locally. The redundant carbon GDP annotation is removed to avoid
overlap; the combined GDP annotation is identified and repositioned. The age-chart
mean is labelled as a mean at each age. The model plotting module and original
gallery are untouched.

Two supplementary output PDFs, combined-sectors and demand-proxy, are generated
for source checking but are not included in the paper. The latter is an emitted
proxy, not completed demand feedback.

## Adversarial review outcome

Independent read-only selection and data checks rejected plausible but mismatched
figures before authoring. A second review checked the selected variables against
the captions and caught the inherited jobs/spending titles, which were corrected.
The capital narrative now states the observed sectoral result directly. Health timing,
normalisation, carbon coverage, household-price fiscal treatment, and outcome horizon
are identified where they affect interpretation; implementation diagnostics remain here.

No new claim that the complete eight-channel loop has been empirically validated is made.
