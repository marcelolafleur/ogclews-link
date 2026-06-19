# Presentation assets — OG-Core × CLEWS integration framework

Programmatically generated, reusable assets for presenting the OG-Core ⇄ CLEWS/OSeMOSYS
soft-link: five **TikZ diagrams** (vector PDF), six **curated example figures** (from the
matplotlib suite), and a self-contained **Beamer deck** that uses them. Everything shares one
editorial, colorblind-safe palette ([`theme/ogclews-colors.tex`](theme/ogclews-colors.tex),
mirrored from `ogclews_link/style.py`), so diagrams, figures, and slides read as one family.

## Build

```bash
bash build.sh        # diagrams -> PDFs, curate figures, compile slides.pdf
```

Requires TeX Live (`pdflatex` + `latexmk`) and `python3`. The figures step copies from a
completed run under `../ogclews_runs/` — regenerate those first with
`../experiments/run_across_steps.py` (or `regen_figures.py`) in the OG-PHL venv if missing.
Build outputs (`*.pdf`, `figures/*.png`) are git-ignored; rerun `build.sh` to regenerate.

## What's here

```
presentation/
  slides.tex            the demo Beamer deck (16:9) — narrative + diagrams + figures
  build.sh              one-command build of every asset
  theme/
    ogclews-colors.tex  the shared palette (the single source of truth for colour)
  diagrams/             standalone TikZ — each compiles to its own tight-cropped PDF
    _preamble.tex         shared tikz libraries + semantic styles + the icon flow helper
    ch_health.tex         CHANNEL FLOWS — plain-language causal chains (general audience):
    ch_energy.tex           health, energy prices, carbon, investment, cost of capital, demand.
    ch_carbon.tex           Icon-led, no model variables. These are the main channel explanation.
    ch_investment.tex
    ch_discount.tex
    ch_demand.tex
    architecture.tex      the structural seam: what each model solves / takes as given
    channels.tex          the full channel map at the variable level (technical reference)
    loop.tex              the iterated soft-link + convergence (honest about the stub)
    scenarios.tex         the scenario builder: defaults, levers, templates, guardrails
    maturity.tex          per-channel roadmap: proxy -> dual-consistent
  figures/
    curate.py             copies the curated example figures from the run dir
    *.png                 the curated set (generated)
  EXPLANATION.md        prose walkthrough of the framework + how to read each diagram
```

## Reusing the assets

- **Drop a diagram into your own slides / paper:** `\includegraphics{diagrams/architecture.pdf}`.
  Each diagram is a `standalone` document — edit the `.tex` and recompile just that file
  (`cd diagrams && latexmk -pdf architecture.tex`).
- **Match the colours** in new material by `\input{theme/ogclews-colors}` and using
  `ogc` (OG-Core blue), `clews` (teal), `policy` (red), `claret`, `ink`/`sub`/`mute`.
- **Re-skin the deck** by editing the theme block at the top of `slides.tex`.

The diagrams are content-faithful to the code: channel directions, parameter names, theory
status, and the stubbed/placeholder flags all track `ogclews_link/channels.py`, `STATUS.md`,
and `docs/design/`. If the channels change, update the diagrams to match.
