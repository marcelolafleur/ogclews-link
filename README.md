# ogclews-link

A coupling layer between **OG-Core** (an overlapping-generations macro model; e.g. OG-PHL) and
**CLEWS/OSeMOSYS** (a least-cost energy–land–water model, run via **MUIOGO**). It reads a country's CLEWS
energy scenarios, applies them to that country's OG model through guard-railed **channels** (energy prices,
public investment, a carbon penalty, health), solves the economy, and reports the results.

The link is its own environment and imports no OG-Core: to solve, it drives the country's OG model in *its*
environment as a subprocess, so the link, MUIOGO, and each OG model stay independently installed.

## Before you start

You need **MUIOGO** installed (the CLEWS side). The setup script below handles everything else,
including Python.

Pick a working folder (here it's `ogclews-test`) to hold OG-PHL and the ogclews-link — the CLEWS data
stays in your MUIOGO install:
```bash
mkdir -p ~/ogclews-test && cd ~/ogclews-test
```

## 1) The Philippine CLEWS data

The `Philippines_v9` case, with a solved baseline (`Base_v9`) and reform (`PEP_v9`), must sit in
`MUIOGO/WebAPP/DataStorage/`. If you don't have it, download
[**Philippines_v9_250116.zip**](https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip),
unzip it, and move the resulting `Philippines_v9` folder into your MUIOGO's `WebAPP/DataStorage/`.

## 2) OG-PHL on the M=8 (multi-industry) calibration

If you don't already have OG-PHL, clone it in the working folder:
```bash
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
```
Then, from inside it, switch to the M=8 calibration this test uses and build its environment:
```bash
cd OG-PHL
git fetch origin pull/63/head:m8 && git checkout m8
uv sync
cd ..
```

## 3) Install the ogclews-link

```bash
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link
./scripts/setup.sh --og-path ../OG-PHL
```
This builds the link's own environment, checks the CLI, and registers OG-PHL.

**Check the registration**: run `uv run ogclews-link models list` and confirm the line starts
`[x] og-phl` and ends `couplable=1`. The registry key must be exactly `og-phl`, and by default it's taken
from the folder's name — so if your OG-PHL checkout lives in a directory *not* literally named `OG-PHL`
(a git worktree, a renamed folder), pass the key explicitly:
```bash
./scripts/setup.sh --og-path <your-OG-PHL-dir> --key og-phl
```

## 4) Run the example

Point it at your CLEWS baseline and reform:
```bash
uv run ogclews-link run coupled \
  --clews-base   <MUIOGO>/WebAPP/DataStorage/Philippines_v9/res/Base_v9/csv \
  --clews-reform <MUIOGO>/WebAPP/DataStorage/Philippines_v9/res/PEP_v9/csv \
  --out ./ogclews_runs
```
The first run solves the baseline (**~10–12 minutes**) and then the reform (**~8 minutes**) — about
20 minutes total, printing solver iterations throughout (it's working, not stuck). Later runs reuse the
cached baseline and only solve the reform. If it asks for a UN API token, press return — none is needed.

## 5) Results

Under `ogclews-link/ogclews_runs/coupled/` (wherever `--out` points):
- **`index.html`** — a self-contained figure deck, built automatically at the end of the run (open it in a
  browser); the figures live in `figures/`. It shows only *this* run's results — no hardcoded scenario, so
  it works for any model or country. Pass `--no-figures` to skip it (it can be rebuilt later, no re-solve).
- **`macro_table.csv`** — the headline: % change (reform vs baseline) in GDP, consumption, capital, labour,
  interest rate, and wage — by year and at the steady state.
- **`ogclews_manifest.json`** — what ran, channel by channel, including which energy-price source was used.
- `clews_inputs/`, `reform/` — the feedback files sent back toward CLEWS, and the raw solved output.
- `clews_source/` — the CLEWS export slices the deck used, copied in so the figures rebuild without the
  original MUIOGO case.

## What to expect

Before the solve, the run prints a checklist of the CLEWS export files and which price source it resolved
(for a raw MUIOGO case: the levelized cost of electricity, computed from the export itself). Then a
per-channel log, then the macro table. Each channel reports or skips with a reason.

**The health channel needs a data file that is never shipped with the repo** (an IHME GBD extract; it's
machine-local and git-ignored). On a fresh install the run tells you before the solve that health will
skip, and everything else proceeds. Downloading the extract takes ~5 minutes — see [DATA.md](DATA.md).

Effects are small and the sign depends on which channels run. For PHL with health skipped: GDP dips
through the transition (deepest around −0.5% in 2030, where the reform's electricity-price premium
peaks) and lands roughly flat (about −0.1%) at the steady state. With the health data present, avoided
pollution deaths lift the early transition to slightly positive. The energy price uses the real CLEWS
signal; the carbon→tax conversion is still illustrative. Missing data makes a channel skip cleanly
rather than fail, so the run always completes.

---
More detail: [DATA.md](DATA.md) (the health data and how to get it), [VALIDATION.md](VALIDATION.md)
(how the results are checked), and `docs/` (design notes and the test plan). A guide to onboarding a
new country is planned under `docs/`.
