#!/usr/bin/env python3
"""Curate the example figures for the presentation.

The matplotlib figures are already produced programmatically by ogclews_link's viz
modules (editorial style.py theme) into a run directory; this script copies a curated
subset into presentation/figures/ so the deck is self-contained and portable, and so
the "example figures" selection is documented in one place. Stdlib only — no solve,
no matplotlib needed. Re-run after regenerating figures (experiments/regen_figures.py).

    python3 presentation/figures/curate.py [--run-dir DIR]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_RUN = REPO / "ogclews_runs" / "across_steps" / "figures"

# the curated set: (source filename, what it illustrates in the deck)
CURATED = [
    ("waterfall_gdp.png",       "channel decomposition — what each policy step adds to output"),
    ("energy_by_income.png",    "distributional incidence — energy demand change by income group"),
    ("welfare_cev_by_group.png","welfare (CEV) by income group"),
    ("health_gdp_split.png",    "health channel — mortality vs morbidity split"),
    ("macro_transition.png",    "macro transition paths"),
    ("headline_dashboard.png",  "headline dashboard — coupled-run overview"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, default=DEFAULT_RUN,
                    help=f"source figures dir (default: {DEFAULT_RUN.relative_to(REPO)})")
    args = ap.parse_args()
    src_dir: Path = args.run_dir

    if not src_dir.is_dir():
        print(f"[curate] source dir not found: {src_dir}", file=sys.stderr)
        print("[curate] run experiments/run_across_steps.py (or regen_figures.py) first.",
              file=sys.stderr)
        return 1

    copied, missing = 0, []
    for name, desc in CURATED:
        src = src_dir / name
        if not src.exists():
            missing.append(name)
            print(f"[curate]  MISSING  {name:28s} ({desc})")
            continue
        shutil.copy2(src, HERE / name)
        copied += 1
        print(f"[curate]  ok       {name:28s} -> figures/{name}")

    print(f"\n[curate] copied {copied}/{len(CURATED)} figures from {src_dir}")
    if missing:
        print(f"[curate] {len(missing)} missing — regenerate the run or adjust CURATED.")
    return 0 if copied else 1


if __name__ == "__main__":
    raise SystemExit(main())
