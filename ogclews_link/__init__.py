"""ogclews-link: a standalone orchestration layer coupling OG-Core (OLG macro) and
CLEWS/OSeMOSYS (least-cost energy-land-water LP).

Design principle (de novo analysis): keep both models independently runnable; the
coupling is a separate layer that exchanges quantities forward and prices/duals back,
iterated to a fixed point. This package is import-light at the edges (numpy/pandas)
and only depends on ogcore where it actually drives a solve.
"""
from . import clews_signal, contract, iterate, og_wedge

__all__ = ["contract", "clews_signal", "og_wedge", "iterate"]
__version__ = "0.0.1"
