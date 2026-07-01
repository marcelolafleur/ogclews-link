# OG-Core × CLEWS integration paper

Academic write-up of the `ogclews-link` integration: the theory of the coupling, the
economics, the eight channels and their mechanisms, the calibration, and the validation
results.

## Build

```sh
latexmk -pdf main.tex      # runs pdflatex + bibtex passes
# or
make                       # if a Makefile is added later
```

Clean aux files with `latexmk -c`.

## Figures

The paper reuses the presentation's diagram PDFs and figure PNGs via `\graphicspath`
(`../presentation/diagrams/`, `../presentation/figures/`). Build those first:

```sh
cd ../presentation && ./build.sh
```

Paper-specific figures go in `figures/` (takes precedence).

## Layout

- `main.tex` — document root; `\input`s the preamble and each section.
- `preamble.tex` — packages, the shared color palette, theorem environments, notation macros.
- `sections/` — one file per section; each currently holds an outline (`% TODO`) grounded
  in the codebase, ready to draft into prose.
- `references.bib` — seed bibliography (verify all fields before submission).

## Source of truth

Substance is drawn from the repo: `docs/design/`, `ogclews_link/channels.py`,
`results/golden.json`, `STATUS.md`, `VALIDATION.md`, and the `presentation/` deck.
