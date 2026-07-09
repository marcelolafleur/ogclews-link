# ogclews-link

Couples a country's **CLEWS/OSeMOSYS** energy scenarios (run via **MUIOGO**) to its **OG-Core** macro
model and reports the economic results. This page gets you from zero to a solved Philippine example —
about 30 minutes, most of it solver time. You need MUIOGO installed; the setup script handles
everything else, including Python.

## 1) Set your paths

```bash
mkdir -p ~/ogclews-test && cd ~/ogclews-test
export MUIOGO=~/path/to/your/MUIOGO      # <-- edit this once; the steps below reuse it
```

## 2) Get the Philippine CLEWS data

Skip if `$MUIOGO/WebAPP/DataStorage/Philippines_v9` already exists. Otherwise:
```bash
curl -LO https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip
unzip Philippines_v9_250116.zip
mv Philippines_v9 "$MUIOGO/WebAPP/DataStorage/"
```

## 3) Get OG-PHL on the multi-industry calibration

Skip the clone if you already have OG-PHL, but you need the `m8` branch and a built environment:
```bash
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
cd OG-PHL
git fetch origin pull/63/head:m8 && git checkout m8
uv sync
cd ..
```

## 4) Install the ogclews-link

```bash
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link
./scripts/setup.sh --og-path ../OG-PHL
```
If your OG-PHL folder is named anything other than `OG-PHL`, add `--key og-phl`.

**Checkpoint** — this must show a line starting `[x] og-phl` and ending `couplable=1`:
```bash
uv run ogclews-link models list
```

## 5) Optional: enable the health channel

The health channel needs one data file that is not shipped (an IHME GBD extract, ~5 minutes to
download — see [DATA.md](DATA.md)). Without it the run says so up front, skips health, and everything
else works.

## 6) Run

```bash
uv run ogclews-link run coupled \
  --clews-base   "$MUIOGO/WebAPP/DataStorage/Philippines_v9/res/Base_v9/csv" \
  --clews-reform "$MUIOGO/WebAPP/DataStorage/Philippines_v9/res/PEP_v9/csv" \
  --out ./ogclews_runs
```
- About **20 minutes** the first time (baseline + reform); it prints solver iterations throughout.
  Later runs reuse the baseline and take ~8 minutes.
- If it asks for a UN API token, press return — none is needed.

## 7) Check the results

In `./ogclews_runs/coupled/`:
- Open **`index.html`** — the figure deck for this run.
- **`macro_table.csv`** — % change (reform vs baseline) in GDP, consumption, capital, labour, r, and w,
  by year and at the steady state. For this example expect small effects: GDP dipping through the
  transition (deepest ≈ −0.5% in 2030) and roughly flat (≈ −0.1%) at the steady state.
- **`ogclews_manifest.json`** — what ran, channel by channel, including the energy-price source.

---
More detail: [DATA.md](DATA.md) (health data), [VALIDATION.md](VALIDATION.md) (how results are
checked), `docs/` (design notes and the test plan).
