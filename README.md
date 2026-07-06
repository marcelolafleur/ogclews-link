# ogclews-link

A coupling layer between **OG-Core** (an overlapping-generations macro model; e.g. OG-PHL) and
**CLEWS/OSeMOSYS** (a least-cost energy–land–water model, run via **MUIOGO**). It reads a country's CLEWS
energy scenarios, applies them to that country's OG model through guard-railed **channels** (energy prices,
public investment, a carbon penalty, health), solves the economy, and reports the results.

The link is its own environment and imports no OG-Core: to solve, it drives the country's OG model in *its*
environment as a subprocess, so the link, MUIOGO, and each OG model stay independently installed.

## Before you start
1) Assumes you already have **MUIOGO** installed.

2) Pick a working folder (here its `ogclews-test`) to keep OG-PHL and the ogclews-link. The results 
land here too; the CLEWS data stays in your MUIOGO install):
```bash
mkdir -p ~/ogclews-test && cd ~/ogclews-test
```

3) **The Philippine CLEWS data** must sit in `MUIOGO/WebAPP/DataStorage/` — the `Philippines_v9` case with a
solved baseline (`Base_v9`) and reform (`PEP_v9`). If you don't have it, download it here:
[**Philippines_v9_250116.zip**](https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip)
— then unzip it and move the resulting `Philippines_v9` folder into your MUIOGO's `WebAPP/DataStorage/`.

4) **OG-PHL on the M=8 (multi-industry) calibration.** If you don't already have OG-PHL, clone it in the working folder (`ogclews-test`):
```bash
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
```
5) Then, from inside it, switch to the M=8 calibration this test uses and build its environment:
```bash
cd OG-PHL
git fetch origin pull/63/head:m8 && git checkout m8
uv sync
cd ..
```

6) ## Install the link
```bash
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link
./scripts/setup.sh --og-path ../OG-PHL
```
Builds the link's own environment, checks the CLI, and registers OG-PHL. Look for a line ending
`[x] og-phl … couplable=1`.

7) ## Run the example
Point it at your CLEWS baseline and reform:
```bash
uv run ogclews-link run coupled \
  --clews-base   <MUIOGO>/WebAPP/DataStorage/Philippines_v9/res/Base_v9/csv \
  --clews-reform <MUIOGO>/WebAPP/DataStorage/Philippines_v9/res/PEP_v9/csv \
  --out ./ogclews_runs
```
The first run solves the baseline (a few minutes), then applies the channels and solves the reform.

8) ## Results
Under `./ogclews_runs/coupled/`:
- **`macro_table.csv`** — the headline: % change (reform vs baseline) in GDP, consumption, capital, labour,
  interest rate, and wage — by year and at the steady state.
- **`ogclews_manifest.json`** — what ran, channel by channel.
- `clews_inputs/`, `reform/` — the feedback files sent back toward CLEWS, and the raw solved output.

## What to expect
The run prints a **per-channel log**, then the macro table. Each channel reports or skips with a reason —
`energy_price`, `investment`, `emit_carbon_penalty`, `health` (skips unless a GBD file is present), and the
`emit_*` feedback to CLEWS. Effects are small: for PHL, GDP is roughly flat at the steady state with a
modest positive transition. The energy price uses the real CLEWS signal; the carbon→tax conversion is still
illustrative. Missing data makes a channel skip cleanly rather than fail, so the run still completes.

---
Detailed docs — architecture, the channels, and onboarding a new country — will live under `docs/`.
