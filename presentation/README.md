# Presentation — OG-Core × CLEWS (`ogclews-link`)

A technical introduction to the OG-Core ⇄ CLEWS/OSeMOSYS soft link: a **Beamer deck**
(`ogclews-link.tex`) built on five **standalone TikZ figures** (`coupling-diagrams/`). Everything
shares one editorial, colour-blind-safe palette
([`theme/ogclews-colors.tex`](theme/ogclews-colors.tex), mirrored from `ogclews_link/style.py`).

The deck runs: intro → overview → the channels → the channels in detail → the software →
use in MUIOGO. The software and MUIOGO sections are content-faithful to the code
(`ogclews_link/channels.py` and the rest of the package), and honest about what is built today
(the single CLEWS→OG pass) versus the next step (closing the loop back into MUIOGO).

## Build

```bash
bash build.sh        # figures -> PDF/PNG, then the deck -> ogclews-link.pdf
```

Requires TeX Live (`pdflatex` + `latexmk`) and `pdftoppm` (poppler) for the web PNGs. Build
outputs (`*.pdf`) are git-ignored; rerun `build.sh` to regenerate them.

## What's here

```
presentation/
  ogclews-link.tex      the deck (16:9)
  build.sh              one-command build (figures + deck)
  theme/
    ogclews-colors.tex  the shared palette (single source of truth for colour)
  coupling-diagrams/    the five self-titled figures — each a standalone .tex -> .pdf/.png
    system-map.tex        the connections: two models bookending the channel bands
    loop.tex              how the two models run in turn
    energy-fork.tex       one electricity price reaching the economy two ways
    two-channels.tex      the two transmission channels the live link uses
    worked-example.tex    one change, traced step by step
    _preamble.tex         shared styles (the figure look) + colour
    index.html            a web gallery of the five figures
```

## Reusing the assets

- **Drop a figure into your own slides / paper:** `\includegraphics{coupling-diagrams/system-map.pdf}`.
  Each figure is a `standalone` document — edit the `.tex` and recompile just that file
  (`cd coupling-diagrams && latexmk -pdf system-map.tex`).
- **Match the colours** with `\input{theme/ogclews-colors}` and `ogc` (OG-Core blue),
  `clews` (teal), `policy` (red), `claret`, plus `ink`/`sub`/`mute`.
- **Re-skin the deck** by editing the theme block at the top of `ogclews-link.tex`.
