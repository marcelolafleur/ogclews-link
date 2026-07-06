# ogclews-link

A coupling layer between **OG-Core** (an overlapping-generations macro model; e.g. OG-PHL) and
**CLEWS/OSeMOSYS** (a least-cost energy–land–water model, run via **MUIOGO**). It reads a country's CLEWS
energy scenarios, applies them to that country's OG model through a set of guard-railed **channels**
(energy prices, public investment, a carbon penalty, health), solves the economy, and emits results back
toward CLEWS.

The link is its **own environment** and imports no OG-Core: to solve, it drives the country's OG model in
*its* environment as a subprocess, so the link, MUIOGO, and each OG model stay independently installed. It
**discovers** what each OG model ships (its calibration, its demographics) and uses it, or cleanly
**skips** the channels it can't support.

## Install
Needs `git`, [`uv`](https://docs.astral.sh/uv/), and an **OG country model already installed** — its own
repo cloned and built with its own `uv sync` (so it has a `.venv`), e.g. OG-PHL on its multi-industry
(M=8) calibration. Then:
```bash
git clone https://github.com/marcelolafleur/ogclews-link.git
cd ogclews-link
./scripts/setup.sh --og-path <path-to-that-OG-model>
```
`setup.sh` builds the link's own environment, verifies the CLI, and registers the OG model. For the full
Philippine setup — which OG-PHL branch to use, and the CLEWS data — see [TESTING.md](TESTING.md).

## Run
Point it at a CLEWS baseline + reform scenario and solve the coupled result:
```bash
uv run ogclews-link run coupled --clews-base <base>/csv --clews-reform <reform>/csv --out ./ogclews_runs
```
Results land in `./ogclews_runs/coupled/` — `macro_table.csv` is the headline; `ogclews_manifest.json`
records what ran. `uv run ogclews-link --help` lists the other commands.

## Try it
[**TESTING.md**](TESTING.md) — a copy-paste walkthrough that runs the Philippine reference case end to end.

## Tests
```bash
uv run pytest tests/
```
Transform, boundary, discovery, and registry tests run numpy-only in seconds; country-integration tests
skip without the OG packages installed.

## Status
The cross-environment solve runs end to end; the PHL M=8 coupled stack is validated through the
install → register → run flow. The `coupled` energy price uses the real CLEWS signal, and config
mismatches fail loudly rather than producing silent zeros. Open items: the carbon→OG deflator is
uncalibrated (illustrative), and loop-closure back into MUIOGO is the next piece.

---

Detailed documentation — architecture, the individual channels, and onboarding a new country / CLEWS
case — will live under `docs/`.
