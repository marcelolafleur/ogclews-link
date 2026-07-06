# Try the OG↔CLEWS coupling (dev test)

Copy-paste, macOS/Linux — a quick way to run the coupling now (throwaway dev test, not the final flow).
Assumes you have `git` and `uv`. Everything below is public; paste each block as-is.

```
mkdir -p ~/ogclews-test && cd ~/ogclews-test
```

**1. OG-PHL — M=8 calibration** (public repo, the PR #63 branch):
```
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
cd OG-PHL && git fetch origin pull/63/head:m8 && git checkout m8 && uv sync && cd ..
```

**2. The link** — builds its env and registers OG-PHL (expect a line ending `couplable=1`):
```
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link && ./scripts/setup.sh --og-path ../OG-PHL
```

**3. The PHL CLEWS case** — *skip if you already have it* (then use your own `res/…/csv` paths in step 4).
Otherwise download the pre-solved case (**~76 MB**):
```
cd ~/ogclews-test
curl -L -o phl.zip "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip"
unzip -q phl.zip -d muiogo-data
```

**4. Run** (from `ogclews-link`; the first run solves the baseline — a few minutes):
```
cd ~/ogclews-test/ogclews-link
uv run ogclews-link run coupled \
  --clews-base   ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/Base_v9/csv \
  --clews-reform ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/PEP_v9/csv \
  --out ./ogclews_runs
```

**5. Health channel (optional)** — without it, health just skips. To include it, add the GBD file
*(skip the download if you already have it)* and re-run step 4:
```
cd ~/ogclews-test/ogclews-link && mkdir -p IHME-GBD_2023_DATA
curl -L -o IHME-GBD_2023_DATA/IHME-GBD_2023_DATA-a20a92ea-1.csv "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/IHME-GBD_2023_DATA-a20a92ea-1.csv"
```

## Results
In `ogclews-link/ogclews_runs/coupled/`:
- **`macro_table.csv`** — the headline: % change (reform vs baseline) in GDP, consumption, capital, labour, interest rate, and wage, by year and at the steady state. Open in any spreadsheet.
- **`ogclews_manifest.json`** — what ran (which channels fired or skipped, the scenarios, versions).
- `clews_inputs/` and `reform/` — the CLEWS feedback files and the raw solved output.

Optional charts: `PYTHONPATH="$PWD" ../OG-PHL/.venv/bin/python -m ogclews_link.viz --coupled-run ./ogclews_runs/coupled --country phl`, then open `ogclews_runs/coupled/index.html`.

**Worked if** step 2 showed `couplable=1` and step 4 wrote `macro_table.csv`. Please send back the last
~20 lines of step 4's output and that CSV.
