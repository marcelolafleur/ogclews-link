"""The soft-link fixed-point driver.

The theoretical-best architecture (de novo analysis, section 4): quantities flow
macro -> energy, prices/duals flow energy -> macro, iterated to the fixed point
where the demand OG chooses at the returned price equals the demand CLEWS met.

This module sketches the loop. The OG-side single pass is real; the CLEWS re-run
step is intentionally a seam -- it belongs to the MUIOGO-orchestrated path that can
actually invoke OSeMOSYS and read its duals. Until then, ``run_once`` drives the
one-directional test (CLEWS file -> OG response) that validates the demand mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LoopState:
    iteration: int
    price_ratio: list      # energy price ratio fed into OG this round
    demand_response: list  # OG energy demand (reform/base) this round
    converged: bool


def run_once(p_reform, *, runner, base_tpi=None):
    """One OG solve under an already-applied energy-price wedge.

    ``p_reform`` is a Specifications object with the wedge set (see ``og_wedge``);
    ``runner`` is ``ogcore.execute.runner``. Returns the reform TPI dict. Kept thin so
    the experiment script owns scenario wiring and so this stays solver-agnostic.
    """
    runner(p_reform, time_path=True)
    return _read_tpi(p_reform.output_base)


def soft_link(*, og_setup, clews_signal, max_iter=10, damping=0.5, tol=1e-3):  # pragma: no cover
    """Full dual-exchanging loop (target architecture).

    Pseudocode of the fixed point:

        demand <- OG baseline activity/consumption
        for k in range(max_iter):
            clews  <- run CLEWS at `demand`              # needs MUIOGO / solver
            price  <- commodity_shadow_price(clews)      # the dual
            p      <- apply energy-price wedge(price)     # og_wedge route A/B/C
            og     <- run OG(p)                           # -> new price-responsive demand
            demand_new <- og energy demand
            if ||demand_new - demand|| < tol: break
            demand <- damping*demand_new + (1-damping)*demand   # relaxation for stability

    The CLEWS re-run and dual extraction are the seam to MUIOGO; raise until wired.
    """
    raise NotImplementedError(
        "Closing the loop needs CLEWS re-run + dual extraction (MUIOGO-orchestrated). "
        "Use run_once() for the one-directional demand-response test first."
    )


def _read_tpi(output_base: str):
    """Load an OG-Core TPI result bundle (TPI_vars.pkl + model_params.pkl)."""
    import os

    from ogcore.utils import safe_read_pickle

    return {
        "tpi": safe_read_pickle(os.path.join(output_base, "TPI", "TPI_vars.pkl")),
        "params": safe_read_pickle(os.path.join(output_base, "model_params.pkl")),
    }
