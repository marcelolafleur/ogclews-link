# Results-visualization lane — handover

**Your job:** improve the **visual presentation of results** for the OG-PHL ⇄ CLEWS coupled model —
turn the current figure set into a clean, standard, presentation-grade default. You are one of three
parallel lanes; stay in yours.

## Lanes (do not cross)
| lane | worktree | branch | owner |
|---|---|---|---|
| health | `~/Projects/ogclews-link` (shared) | `health-channel-hardening` | another agent (active) |
| energy | `~/Projects/ogclews-link-energy` | `energy-production-input-design` | another agent |
| **viz (you)** | `~/Projects/ogclews-link-viz` | `results-visualization` | you |

**You edit only the figure/report layer:** `ogclews_link/figures.py`, `ogclews_link/report_html.py`,
`ogclews_link/style.py`, `experiments/regen_figures.py`, and any new `ogclews_link/viz_*.py` you add.
**Do NOT touch** `health_pop.py`, `channels.py`, `runtime.py`, `health_profile.py`, `country.py`,
`framework.py`, `experiments.py` — those belong to the health/energy lanes (merge conflicts). Commit to
`results-visualization`. Don't run the full model solve (that's the health lane); see "iterate" below.

## How to iterate — NO model solve (seconds, not an hour)
The full 4-step suite is already solved on **real GBD data**; the pickles live in the shared tree at
`/Users/mlafleur/Projects/ogclews-link/ogclews_runs/across_steps/` (`layered_results.json`, `baseline/`,
and per-step `+ <step>/{SS,TPI}/*.pkl`). `experiments/regen_figures.py` rebuilds **every figure from
those pickles without solving**. So the loop is: edit `figures.py`/`style.py` → run regen → view.

**First task — isolate the I/O so you don't stomp the shared session's figures:** `regen_figures.py`
currently hardcodes `OUT = "/Users/mlafleur/Projects/ogclews-link/ogclews_runs/across_steps"` (absolute,
shared). Parameterize it: read pickles from that shared dir, but write your figures to a viz-local dir
(e.g. `~/Projects/ogclews-link-viz/figs/`). Then regen is fully isolated.

```bash
cd ~/Projects/ogclews-link-viz
PYTHONPATH=$PWD /Users/mlafleur/Projects/OG-PHL/.venv/bin/python experiments/regen_figures.py
```

## What exists now (the current default)
- Top-level (`figures.py`): `across_steps_waterfall` → **waterfall_gdp** (channel→GDP, health split into
  mortality/morbidity), `macro_honest` (Y/C/K/L fixed-axis), `energy_physical` → **emissions_path**
  (baseline vs reform), `across_steps_table` → CSV, plus the poorest-group waterfall and `report.html`.
- Per-step: `incidence_hero` → **incidence.png**, `og_default_outputs` → `og_macro_table.csv`
  (and OG-Core's full plot suite if called with `plots=True` — currently OFF).
- **Stale/orphaned** (from an older approach, no longer regenerated): `energy_by_income.png`,
  `headline_by_step.png`, `macro_by_step.png`, `welfare_by_income.png` — curate (revive or delete).

## What to add for a standard, presentation-grade default
1. **Turn on + curate OG-Core's own default suite** (`og_default_outputs(..., plots=True)`): SS lifecycle
   profiles (consumption / labor / savings / ETR / MTR by age, baseline vs reform), macro transition
   %-change paths (Y, C, K, L, r, w over time), Debt/GDP, Revenue/GDP, Spend/GDP, interest & wage rates.
   These are the canonical OG-Core results plots and are essentially free.
2. **Macro transition paths** — the *time series* of Y/C/K/L deviations across the transition (not just
   the 10-yr-mean snapshot the waterfall/macro_honest use). The dynamics are the story.
3. **Welfare** — consumption-equivalent variation (CEV) by lifetime-income group (the proper welfare
   metric; `consumption_by_J` is only a proxy), and ideally by age (lifecycle).
4. **Health-specific visuals** (this is the newest channel, worth showcasing):
   - Plot the GBD age profiles themselves: mortality `h(s)` (deaths-by-age, elderly-skewed) and morbidity
     `g(s)` (YLD-by-age, rising into working ages) — they tell the "why mortality≈0, morbidity carries it"
     story at a glance. (`health_profile.build_profile_from_gbd` / `build_morbidity_profile_from_gbd`.)
   - The demographic change: survival/population by age, baseline vs reform; deaths & YLDs avoided by age.
   - The mortality-vs-morbidity GDP split (already in the waterfall — make it a clean standalone too).
5. **Distributional richness** — consumption/welfare by income group AND by age; energy-demand response by
   income group (revive `energy_by_income` properly).
6. **Fiscal paths** — Debt/GDP, Revenue/GDP, and the carbon-tax revenue over the transition.
7. **A one-page headline dashboard / summary** tying the channels together.
8. **Unify the editorial theme** (`style.py`): consistent palette, kicker+claim titles, direct labels,
   honest captions. Everything should look like one deck.

## Honesty constraints (keep in captions — these results are ILLUSTRATIVE)
The `NOTE` in regen says it: +20% energy-price wedge is a **cost-index proxy, not the CLEWS dual**;
investment/carbon magnitudes are **uncalibrated** (no deflator bridge); **carbon revenue is not recycled**;
the health channel scales deaths/YLDs by the **CO2e** emissions change (proxy for PM2.5) under a **linear
dose-response**, anchored on the **first-10-year** emissions gap — and that gap is **back-loaded** (the
reform's emissions cut is ~1% early but ~45% by the 2050s), so the health effect shown is a near-term
*understate*. Don't oversell magnitudes; the figures are about mechanism and composition.

## Data notes
- Incidence metric is `consumption_by_J` (welfare→consumption was renamed). CEV is a proper-welfare add.
- Figure PNGs are gitignored — **commit the CODE, not the images.**
- Income groups J=7 (lowest→highest lifetime income); M=4 industries, I=5 consumption goods (good 1 =
  "Energy and water"); S active ages. PHL is the worked country.

## When done
The user merges `results-visualization` → `health-channel-hardening`. Figure code is mostly disjoint from
the health/energy code, so it should merge cleanly. If you need *fresh* solved results (not just restyled
figures), ask the user — the health lane produces them; don't solve here.
