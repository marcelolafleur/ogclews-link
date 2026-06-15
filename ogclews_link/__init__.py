"""ogclews-link: a standalone orchestration layer coupling OG-Core (OLG macro) and
CLEWS/OSeMOSYS (least-cost energy-land-water LP).

Design principle (de novo analysis): keep both models independently runnable; the
coupling is a separate layer that exchanges quantities forward and prices/duals back,
iterated to a fixed point.

Import-light by design: submodules are NOT imported here, so the pure-numpy wedge math
(``og_wedge``) and the dataclass contract (``contract``) stay usable without pandas or
ogcore. Import what you need, e.g. ``from ogclews_link import og_wedge``. The
``clews_signal`` (pandas) and ``iterate`` (ogcore) modules pull heavier deps on demand.
"""
__all__ = ["contract", "clews_signal", "og_wedge", "iterate"]
__version__ = "0.0.1"
