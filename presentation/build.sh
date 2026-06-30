#!/usr/bin/env bash
# Build the presentation from source:
#   1. the five coupling diagrams  (coupling-diagrams/*.tex -> .pdf, and .png for the web gallery)
#   2. the Beamer deck             (ogclews-link.tex -> ogclews-link.pdf)
# Requires: TeX Live (pdflatex + latexmk); pdftoppm (poppler) for the PNGs.
# Build outputs (*.pdf) are git-ignored; rerun this to regenerate.
set -euo pipefail
cd "$(dirname "$0")"

FIGURES=(system-map loop energy-fork two-channels worked-example)

echo "==> 1/2  coupling diagrams"
pushd coupling-diagrams >/dev/null
for f in "${FIGURES[@]}"; do
  printf '   - %-16s' "$f"
  latexmk -pdf -interaction=nonstopmode -halt-on-error "$f.tex" >/dev/null 2>&1 \
    && echo "ok" || { echo "FAILED — see coupling-diagrams/$f.log"; exit 1; }
  pdftoppm -png -r 150 "$f.pdf" "$f" >/dev/null 2>&1 && mv -f "$f-1.png" "$f.png" 2>/dev/null || true
done
latexmk -c >/dev/null 2>&1 || true   # drop aux files, keep the PDFs
popd >/dev/null

echo "==> 2/2  deck"
latexmk -pdf -interaction=nonstopmode -halt-on-error ogclews-link.tex >/dev/null 2>&1 \
  && echo "   - ogclews-link.pdf ok" || { echo "   deck FAILED — see ogclews-link.log"; exit 1; }
latexmk -c >/dev/null 2>&1 || true

echo ""
echo "Done."
echo "  diagrams : coupling-diagrams/*.pdf (+ .png, + index.html)"
echo "  deck     : ogclews-link.pdf"
