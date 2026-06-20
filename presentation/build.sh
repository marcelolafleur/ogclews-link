#!/usr/bin/env bash
# Build every presentation asset from source:
#   1. the standalone TikZ diagrams  (diagrams/*.tex  -> diagrams/*.pdf)
#   2. the curated example figures   (copied from the run dir by figures/curate.py)
#   3. the demo Beamer deck          (slides.tex      -> slides.pdf)
# Requires: TeX Live (pdflatex + latexmk) and python3. The figures step needs a completed run under
# ogclews_runs/ (regenerate with: python -m ogclews_link.viz --run-dir ogclews_runs/across_steps).
set -euo pipefail
cd "$(dirname "$0")"

DIAGRAMS=(architecture channels loop scenarios maturity \
          ch_health ch_energy ch_carbon ch_investment ch_discount ch_demand)

echo "==> 1/3  diagrams"
pushd diagrams >/dev/null
for f in "${DIAGRAMS[@]}"; do
  printf '   - %-14s' "$f"
  latexmk -pdf -interaction=nonstopmode -halt-on-error "$f.tex" >/dev/null 2>&1 \
    && echo "ok" || { echo "FAILED — see diagrams/$f.log"; exit 1; }
done
latexmk -c >/dev/null 2>&1 || true   # drop aux, keep the PDFs
popd >/dev/null

echo "==> 2/3  figures"
python3 figures/curate.py || echo "   (figures step skipped — run the model first)"

echo "==> 3/3  deck"
latexmk -pdf -interaction=nonstopmode -halt-on-error slides.tex >/dev/null 2>&1 \
  && echo "   - slides.pdf ok" || { echo "   deck FAILED — see slides.log"; exit 1; }
latexmk -c >/dev/null 2>&1 || true

echo ""
echo "Done."
echo "  diagrams : $(printf '%s ' "${DIAGRAMS[@]/%/.pdf}")(in diagrams/)"
echo "  figures  : figures/*.png"
echo "  deck     : slides.pdf"
