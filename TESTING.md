# Try the OG↔CLEWS coupling (temporary dev test)

Copy-paste, **macOS / Linux**. A throwaway developer test to try the coupling **today** — not the final
flow (that will be one-click modules inside MUIOGO). Everything below is public; no GitHub account needed.
**Each block is paste-ready as-is** — what it does is described in the line just above it.

Assumes you already have **git** and **uv** (the Python environment manager) — testers do.

> Don't have `uv`? Install it once — this runs uv's official installer from Astral (the makers of
> `uv`/`ruff`); or use `brew install uv` / `pip install uv`:
> `curl -LsSf https://astral.sh/uv/install.sh | sh`

Make one folder to hold everything:
```
mkdir -p ~/ogclews-test && cd ~/ogclews-test
```

## 1. OG-PHL (the economic model, M=8 multi-industry calibration)
Clones the public OG-PHL repository, switches it to the multi-industry (M=8) calibration branch via its
public pull-request ref (OG-PHL PR #63), and builds OG-PHL's own isolated environment (`uv sync` fetches a
matching Python for you if needed).
```
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
cd OG-PHL
git fetch origin pull/63/head:m8
git checkout m8
uv sync
cd ..
```

## 2. The link + register the model
Clones the coupling tool and runs its installer, which builds the link's own environment, checks the
`ogclews-link` command works, and registers the OG-PHL model from Step 1. You should see a line ending
`[x] og-phl ... couplable=1`.
```
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link
./scripts/setup.sh --og-path ../OG-PHL
```

## 3. The Philippine CLEWS scenario data — only if you don't already have it
The run needs a solved PHL CLEWS case: a baseline (`Base_v9`) and a reform (`PEP_v9`). **If you already
have this case** (e.g. from a MUIOGO install), skip this download and point Step 4 at your existing
`.../Philippines_v9/res/Base_v9/csv` and `.../res/PEP_v9/csv` folders instead. Otherwise download the
pre-solved case (**~76 MB**) and unzip it — the link reads these files directly, so no MUIOGO needed:
```
cd ~/ogclews-test
curl -L -o phl-clews.zip "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip"
unzip -q phl-clews.zip -d muiogo-data
```

## 4. Run the coupled scenario
From inside `ogclews-link`, solve the Philippine economy against the baseline and reform CLEWS scenarios.
The two paths point at the case from Step 3 (or your own copy). The first run solves the baseline (a few
minutes); later runs reuse it.
```
cd ~/ogclews-test/ogclews-link
uv run ogclews-link run coupled \
  --clews-base   ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/Base_v9/csv \
  --clews-reform ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/PEP_v9/csv \
  --out ./ogclews_runs
```

## 5. (optional) Include the health channel — only if you don't already have the GBD file
Without a GBD health file the health channel just prints `[skip]` and the run still completes (energy +
investment + carbon). To include health, put the GBD CSV where the link looks for it, **then re-run Step 4**.
Skip the download if you already have a copy — just place it under `ogclews-link/IHME-GBD_2023_DATA/`.
```
cd ~/ogclews-test/ogclews-link
mkdir -p IHME-GBD_2023_DATA
curl -L -o IHME-GBD_2023_DATA/IHME-GBD_2023_DATA-a20a92ea-1.csv "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/IHME-GBD_2023_DATA-a20a92ea-1.csv"
```

## Where the results are
The run prints a macro summary to the screen at the end, and writes everything under
**`ogclews-link/ogclews_runs/coupled/`**:

- **`macro_table.csv`** — the headline. % change of the reform vs the baseline for GDP (`Y`), consumption
  (`C`), capital (`K`), labour (`L`), interest rate (`r`), wage (`w`) — by year, plus a 10-year point and
  the long-run steady state. Open it in any spreadsheet.
- **`ogclews_manifest.json`** — what actually ran: the country, which channels fired (and which skipped and
  why), the scenarios used, and the model versions. Open in a text editor.
- **`clews_inputs/`** — the values the link would feed back to CLEWS (`EmissionsPenalty.csv`,
  `DiscountRate.csv`, `demand_scaling.csv`).
- **`reform/`** — the raw solved model output (for deeper inspection).

### (optional) A browser page of charts
Turns the run into a self-contained figures page (no re-solve). Runs under OG-PHL's Python; then open the
page in your browser:
```
cd ~/ogclews-test/ogclews-link
PYTHONPATH="$PWD" ../OG-PHL/.venv/bin/python -m ogclews_link.viz --coupled-run ./ogclews_runs/coupled --country phl
```
Then open `ogclews-link/ogclews_runs/coupled/index.html` (double-click it, or `open` on macOS /
`xdg-open` on Linux).

## Did it work?
- Step 2 printed `couplable=1`.
- Step 4 finished without error and wrote `ogclews_runs/coupled/macro_table.csv`.
- If you didn't add the GBD file, the health channel printed `[skip]` — that is expected.

Please send back: the last ~20 lines of Step 4's output, plus `ogclews_runs/coupled/macro_table.csv`.
