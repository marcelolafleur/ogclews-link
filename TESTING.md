# Try the OG↔CLEWS coupling (temporary dev test)

Copy-paste for **macOS / Linux**. ~15 min of setup + one solve (a few minutes). This is a throwaway
developer test to try the coupling **today** — not the final flow (that will be one-click modules inside
MUIOGO). No GitHub account needed; every source below is public.

You install three things side by side under one folder, then run one command.

## 1. One-time tools
```
curl -LsSf https://astral.sh/uv/install.sh | sh
mkdir -p ~/ogclews-test && cd ~/ogclews-test
```

## 2. The Philippine CLEWS scenario data
MUIOGO's Philippine CLEWS case, already solved (a baseline `Base_v9` and a reform `PEP_v9`):
```
curl -L -o phl-clews.zip "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip"
unzip -q phl-clews.zip -d muiogo-data
```
You don't need to install or run MUIOGO — the link reads these files directly.

## 3. OG-PHL (the economic model, M=8 multi-industry calibration)
```
cd ~/ogclews-test
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
cd OG-PHL
git fetch origin pull/63/head:m8 && git checkout m8      # the M=8 calibration (OG-PHL PR #63)
uv sync                                                  # builds OG-PHL's own venv (uv fetches Python too)
cd ..
```

## 4. The link + register the model
```
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link
./scripts/setup.sh --og-path ../OG-PHL
```
Expect a line ending `[x] og-phl ... couplable=1`.

## 5. (optional) Add the health data
Skip this and the health channel simply prints `[skip]` — energy + investment + carbon still run. To
include the health effect, drop the GBD file in (run from inside `ogclews-link`):
```
mkdir -p IHME-GBD_2023_DATA
curl -L -o IHME-GBD_2023_DATA/IHME-GBD_2023_DATA-a20a92ea-1.csv "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/IHME-GBD_2023_DATA-a20a92ea-1.csv"
```

## 6. Run the coupled scenario
Still inside `ogclews-link`:
```
uv run ogclews-link run coupled \
  --clews-base   ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/Base_v9/csv \
  --clews-reform ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/PEP_v9/csv \
  --out ./ogclews_runs
```
The first run solves the baseline (a few minutes). Results land in `./ogclews_runs/coupled/` — the
headline table is `macro_table.csv`.

## Did it work?
- Step 4 printed `couplable=1`.
- Step 6 finished without error and wrote `ogclews_runs/coupled/macro_table.csv`.
- If you skipped Step 5, the health channel prints `[skip]` — expected.

Please send back: the last ~20 lines of Step 6's output, plus `ogclews_runs/coupled/macro_table.csv`.
