"""The coupling orchestrator. A channel is a plain function (see channels.py) that reads/mutates the
coupling state and records provenance. An EXPERIMENT is a function ``exp(ctx, solve)`` that calls
channels in order and calls ``solve(ctx)`` at the point the reform is solved -- pre-solve channels
(clews->og, policy) before it, og->clews ``emit_`` channels after. ``run`` builds the OG baseline (or
reuses a prebuilt one), threads a fresh reform through the experiment, and returns the context.

The ogcore-touching callables (build_baseline, solve, apply_health) are INJECTED so this module and the
channels import only numpy and stay unit-testable without ogcore.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

CLEWS_TO_OG = "clews->og"
OG_TO_CLEWS = "og->clews"
POLICY = "policy"


@dataclass
class ExperimentContext:
    """Everything a channel reads or writes during a run (the mutable analogue of OG-Core's ``p``)."""
    country: Any                              # CountryConfig
    og_reform: Any = None                     # Specifications the pre-solve channels mutate
    base_tpi: dict | None = None              # baseline OG outputs (always solved before any channel)
    reform_tpi: dict | None = None            # reform OG outputs (for og->clews channels)
    clews: dict = field(default_factory=dict)
    clews_inputs: dict = field(default_factory=dict)  # OG->CLEWS artifacts to write
    extras: dict = field(default_factory=dict)        # e.g. the mortality shock for the runtime
    provenance: list = field(default_factory=list)

    def log(self, channel: str, **info) -> dict:
        rec = {"channel": channel, **info}
        self.provenance.append(rec)
        return rec


# --- orchestration --------------------------------------------------------------

def _fresh_reform(p, base_dir, reform_dir):
    import copy
    r = copy.deepcopy(p)
    r.baseline = False
    r.baseline_dir = base_dir
    r.output_base = reform_dir
    r.__dict__.pop("_e_long_cache", None)     # ogcore memoizes e; reform edits must take
    return r


def _solve_step(solve, apply_health):
    """Build the solve callable an experiment invokes as ``solve(ctx)``: fire the mortality
    re-solve hook if a health channel staged one, then solve the reform into ctx.reform_tpi."""
    def solve_step(ctx):
        if apply_health and ctx.extras.get("health_shock") is not None:
            ctx.og_reform = apply_health(ctx.og_reform, ctx.extras["health_shock"])
        ctx.reform_tpi = solve(ctx.og_reform)
        return ctx.reform_tpi
    return solve_step


def run(experiment_fn, country, *, build_baseline, solve, apply_health=None,
        out_root="./ogclews_runs", prebuilt=None) -> ExperimentContext:
    """Run one experiment. ``experiment_fn(ctx, solve)`` calls channels and calls solve(ctx) once.
    A ``prebuilt`` tuple (p, base_tpi, base_dir) reuses an already-solved baseline (the battery reuses
    one across reforms instead of re-solving the identical baseline)."""
    name = getattr(experiment_fn, "__name__", "experiment")
    ctx = ExperimentContext(country=country)
    base_dir = os.path.join(out_root, name, "baseline")
    reform_dir = os.path.join(out_root, name, "reform")
    if prebuilt is not None:
        p, ctx.base_tpi, base_dir = prebuilt
    else:
        p, _aux = build_baseline(country, base_dir)
        ctx.base_tpi = solve(p)
    ctx.og_reform = _fresh_reform(p, base_dir, reform_dir)
    experiment_fn(ctx, _solve_step(solve, apply_health))
    return ctx


def run_across_steps(step_fns, country, *, build_baseline, solve, apply_health=None,
                     out_root="./ogclews_runs") -> list:
    """Solve the baseline ONCE, then one reform per CUMULATIVE step. ``step_fns`` is a list of
    (label, step_fn(ctx, solve)); each shares the baseline -- the layered 'what does each added channel
    do' view. A non-converging step is recorded and skipped, not fatal to the batch."""
    base_dir = os.path.join(out_root, "across_steps", "baseline")
    p, _aux = build_baseline(country, base_dir)
    base_tpi = solve(p)
    solve_step = _solve_step(solve, apply_health)
    results = []
    for label, step_fn in step_fns:
        ctx = ExperimentContext(country=country, base_tpi=base_tpi)
        ctx.og_reform = _fresh_reform(p, base_dir, os.path.join(out_root, "across_steps", label))
        try:
            step_fn(ctx, solve_step)
        except Exception as e:  # one non-converging step must not kill the whole batch
            print(f"[across_steps] step '{label}' did NOT solve: {type(e).__name__}: {e}")
            ctx.extras["error"] = f"{type(e).__name__}: {e}"
        results.append((label, ctx))
    return results


def preflight(active: list[str]) -> list[str]:
    """Advisory cross-channel guardrails for a set of active channel names (no solving). Surfaces
    double-counting and 'don't stack these' cautions; the orchestrator/CLI can print them before a run."""
    a = set(active)
    msgs: list[str] = []
    if "energy_price" in a and "carbon_tax" in a:
        msgs.append("energy_price + carbon_tax both wedge the energy good's tau_c -- a resource cost and "
                    "a tax are different objects; ensure the increase is not counted twice.")
    if {"carbon_tax", "emit_carbon_penalty"} & a:
        msgs.append("carbon price must appear ONCE: set it as policy feeding both sides (carbon_tax on OG, "
                    "emit_carbon_penalty on CLEWS); do not also infer a carbon price from a CLEWS dual into OG.")
    if "capital_intensity" in a and "investment" in a:
        msgs.append("capital_intensity (private generation capital share, gamma) and investment (PUBLIC "
                    "grid/T&D capex -> K_g) are COMPLEMENTARY, not double-counting: different capital, lever.")
    if "capital_intensity" in a and "energy_capex" in a:
        msgs.append("capital_intensity (gamma, factor share) and energy_capex (ITC, cost-of-capital) are TWO "
                    "mechanisms for the same buildout, OPPOSITE sign on energy K -- pick one, do NOT stack.")
    return msgs
