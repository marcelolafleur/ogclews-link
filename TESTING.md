# Try the OG↔CLEWS coupling (temporary dev test)

Copy-paste for **macOS / Linux**. ~15 min of setup + one solve (a few minutes). This is a throwaway
developer test to try the coupling **today** — not the final flow (that will be one-click modules inside
MUIOGO). No GitHub account needed; every source below is public.

You install three things side by side under one folder, then run one command. **Each block is
paste-ready as-is** — what it does is described in the line just above it.

## 1. One-time tools
Installs **uv**, the Python environment manager the projects use. The first command downloads and runs
uv's **official installer from Astral** (the makers of `uv`/`ruff`) at `astral.sh/uv/install.sh` — the
standard uv install, the same one MUIOGO and OG-Core use; it just adds `uv` to your PATH. (Prefer not to
pipe to a shell? `brew install uv` or `pip install uv` are equivalent.) The second command makes a working
folder to keep everything in.
```
curl -LsSf https://astral.sh/uv/install.sh | sh
mkdir -p ~/ogclews-test && cd ~/ogclews-test
```

## 2. The Philippine CLEWS scenario data
Downloads MUIOGO's Philippine CLEWS case — already solved (a baseline `Base_v9` and a reform `PEP_v9`) —
and unzips it into `muiogo-data/`. The link reads these files directly, so you do **not** need to install
or run MUIOGO.

> ⚠️ **This is a ~76 MB download.** If you already have the `Philippines_v9` case (from an earlier test or
> a MUIOGO install), **skip this step** and instead point Step 6's `--clews-base` / `--clews-reform` at your
> existing `.../Philippines_v9/res/Base_v9/csv` and `.../res/PEP_v9/csv` folders.

```
curl -L -o phl-clews.zip "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip"
unzip -q phl-clews.zip -d muiogo-data
```

## 3. OG-PHL (the economic model, M=8 multi-industry calibration)
Clones the public OG-PHL repository, switches it to the multi-industry (M=8) calibration branch via its
public pull-request ref (OG-PHL PR #63), and builds OG-PHL's own isolated environment. `uv sync` downloads
a matching Python for you if needed.
```
cd ~/ogclews-test
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
cd OG-PHL
git fetch origin pull/63/head:m8
git checkout m8
uv sync
cd ..
```

## 4. The link + register the model
Clones the coupling tool and runs its installer, which builds the link's own environment, checks the
`ogclews-link` command works, and registers the OG-PHL model you built in Step 3. You should see a line
ending `[x] og-phl ... couplable=1`.
```
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link
./scripts/setup.sh --og-path ../OG-PHL
```

## 5. (optional) Add the health data
Downloads the GBD health dataset (1.4 MB) so the health channel runs. **Skip this** and the health channel
simply prints `[skip]` — energy + investment + carbon still run. Run these from inside `ogclews-link`; it
places the file in the folder the link looks in.
```
mkdir -p IHME-GBD_2023_DATA
curl -L -o IHME-GBD_2023_DATA/IHME-GBD_2023_DATA-a20a92ea-1.csv "https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/IHME-GBD_2023_DATA-a20a92ea-1.csv"
```

## 6. Run the coupled scenario
Runs the coupling: it solves the Philippine economy against the baseline and reform CLEWS scenarios and
writes the results. Run from inside `ogclews-link`. The first run solves the baseline (a few minutes).
Results land in `./ogclews_runs/coupled/`; the headline table is `macro_table.csv`.
```
uv run ogclews-link run coupled \
  --clews-base   ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/Base_v9/csv \
  --clews-reform ../muiogo-data/WebAPP/DataStorage/Philippines_v9/res/PEP_v9/csv \
  --out ./ogclews_runs
```

## Did it work?
- Step 4 printed `couplable=1`.
- Step 6 finished without error and wrote `ogclews_runs/coupled/macro_table.csv`.
- If you skipped Step 5, the health channel prints `[skip]` — that is expected.

Please send back: the last ~20 lines of Step 6's output, plus `ogclews_runs/coupled/macro_table.csv`.
