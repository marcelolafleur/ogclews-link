# ogclews-link

Couples a country's **CLEWS/OSeMOSYS** energy scenarios to its **OG-Core** macro model and reports the
economic results. This page gets you from zero to a solved Philippine example — about 30 minutes, most
of it solver time.

## Quick start — one script

```bash
curl -fsSL https://raw.githubusercontent.com/marcelolafleur/ogclews-link/main/scripts/test-drive.sh -o test-drive.sh
bash test-drive.sh
```
It downloads the solved Philippine CLEWS case, installs OG-PHL and the link (including Python — it
needs nothing pre-installed beyond git/curl/unzip), runs the coupled example, and opens the results
deck. Safe to re-run; a second run takes ~8 minutes. When it mentions the health channel skipping,
that's expected — see [DATA.md](DATA.md) to enable it (~5 minutes).

The manual steps below do the same thing, if you'd rather see each one.

## 1) Make a working folder and get the Philippine CLEWS data

```bash
mkdir ogclews-test
cd ogclews-test
curl -LO https://github.com/marcelolafleur/ogclews-link/releases/download/phl-test-data/Philippines_v9_250116.zip
unzip Philippines_v9_250116.zip
mv WebAPP/DataStorage/Philippines_v9 .
```
This is a solved CLEWS case (baseline `Base_v9` and reform `PEP_v9`) — you don't need MUIOGO to run
this example. (If you have MUIOGO with `Philippines_v9` already installed, you can skip the download
and point step 4 at `<MUIOGO>/WebAPP/DataStorage/Philippines_v9` instead.)

## 2) Get OG-PHL on the multi-industry calibration

```bash
git clone https://github.com/EAPD-DRB/OG-PHL.git OG-PHL
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

**Checkpoint** — this must show a line starting `[x] og-phl` and ending `couplable=1`:
```bash
uv run ogclews-link models list
```

## 4) Run

```bash
uv run ogclews-link run coupled \
  --clews-base   ../Philippines_v9/res/Base_v9/csv \
  --clews-reform ../Philippines_v9/res/PEP_v9/csv \
  --out ./ogclews_runs
```
- About **20 minutes** the first time (baseline + reform); it prints solver iterations throughout.
  Later runs reuse the baseline and take ~8 minutes.
- If it asks for a UN API token, press return — none is needed.
- It will say the health channel is skipping: that channel needs one data file that is not shipped
  (~5 minutes to download — see [DATA.md](DATA.md)). Everything else runs without it.

## 5) Check the results

In `./ogclews_runs/coupled/`:
- Open **`index.html`** — the figure deck for this run.
- **`macro_table.csv`** — % change (reform vs baseline) in GDP, consumption, capital, labour, r, and w,
  by year and at the steady state. For this example expect small effects: GDP dipping through the
  transition (deepest ≈ −0.5% in 2030) and roughly flat (≈ −0.1%) at the steady state.
- **`ogclews_manifest.json`** — what ran, channel by channel, including the energy-price source.

---
More detail: [DATA.md](DATA.md) (health data), [VALIDATION.md](VALIDATION.md) (how results are
checked), `docs/` (design notes and the test plan). To change the energy scenarios themselves you'll
need MUIOGO — this example uses the shipped, already-solved case.
