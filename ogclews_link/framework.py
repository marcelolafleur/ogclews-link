"""The channel framework: the architecture for composing, running, and testing the
OG-Core <-> CLEWS integration channels.

A Channel is a small, economically-grounded transform in ONE direction:
  * clews->og : reads a CLEWS signal, mutates the OG reform Specifications.
  * og->clews : reads OG output, writes a CLEWS input artifact (the forward direction).
  * policy    : a shared exogenous lever applied to both sides.

An Experiment names a country, a scenario pair, and a list of channels (with options).
The Runner builds the OG baseline, applies the pre-solve channels to the reform, solves,
then applies the post-solve (og->clews) channels using the results. Heavy bits (build a
country baseline, invoke OG-Core / CLEWS) are INJECTED so the channel transforms stay
unit-testable without ogcore.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

CLEWS_TO_OG = "clews->og"
OG_TO_CLEWS = "og->clews"
POLICY = "policy"


@dataclass
class ExperimentContext:
    """Everything a channel reads or writes during a run."""
    country: Any                              # CountryConfig
    og_reform: Any = None                     # Specifications the pre-solve channels mutate
    base_tpi: dict | None = None              # baseline OG outputs (for requires_og_baseline)
    reform_tpi: dict | None = None            # reform OG outputs (for post-solve channels)
    clews: dict = field(default_factory=dict)         # cached CLEWS signals
    clews_inputs: dict = field(default_factory=dict)  # OG->CLEWS artifacts to write
    extras: dict = field(default_factory=dict)        # e.g. mortality effect for the runtime
    provenance: list = field(default_factory=list)

    def log(self, channel_id: str, **info) -> dict:
        rec = {"channel": channel_id, **info}
        self.provenance.append(rec)
        return rec


class Channel(ABC):
    id: str = ""
    label: str = ""
    direction: str = CLEWS_TO_OG
    theory_status: str = "reduced_form"   # structural_core | reduced_form | research
    requires_og_baseline: bool = False    # needs baseline OG outputs before apply
    post_solve: bool = False              # apply AFTER the reform solve (og->clews producers)

    @abstractmethod
    def apply(self, ctx: ExperimentContext, **opts) -> dict:
        """Mutate ctx.og_reform and/or ctx.clews_inputs; return a provenance dict."""

    def validate(self, ctx: ExperimentContext, active_ids: list[str]) -> list[str]:
        """Guardrail messages given the other active channels (double-counting, etc.)."""
        return []


# --- registry -------------------------------------------------------------------

_REGISTRY: dict[str, Channel] = {}


def register(channel: Channel) -> Channel:
    if channel.id in _REGISTRY:
        raise ValueError(f"duplicate channel id: {channel.id}")
    _REGISTRY[channel.id] = channel
    return channel


def get(channel_id: str) -> Channel:
    return _REGISTRY[channel_id]


def all_channels() -> dict[str, Channel]:
    return dict(_REGISTRY)


# --- experiment + runner --------------------------------------------------------

@dataclass
class Experiment:
    """A named, reproducible configuration: which channels (by id) with which options."""
    name: str
    channels: list[tuple[str, dict]]          # [(channel_id, opts), ...]
    description: str = ""

    def channel_ids(self) -> list[str]:
        return [cid for cid, _ in self.channels]


@dataclass
class Runner:
    """Orchestrates a coupled run. The ogcore-touching callables are injected:
        build_baseline(country) -> (Specifications, aux)
        solve(p) -> tpi_dict
        apply_mortality(p, effect) -> p     (optional; health channel, needs get_pop_data)
    so the framework + channels import only numpy/pandas and stay testable.
    """
    build_baseline: Callable
    solve: Callable
    apply_health: Callable | None = None   # runtime hook: recompute population under a mortality shock

    def run(self, experiment: Experiment, country, out_root: str = "./ogclews_runs",
            max_passes: int = 1, clews_runner=None, tol: float = 1e-2, damp: float = 0.5) -> ExperimentContext:
        """Run an experiment. max_passes=1 is ONE-WAY (take CLEWS as given, solve the economy
        once -- correct for evaluating a fixed scenario). max_passes>1 is MULTI-PASS: iterate
        OG<->CLEWS to a fixed point, which needs ``clews_runner(clews_inputs, country, pass)``
        to re-solve CLEWS each pass (the unbuilt OSeMOSYS-invocation seam). Without it,
        multi-pass honestly degrades to one pass.
        """
        import copy
        import os

        ctx = ExperimentContext(country=country)
        base_dir = os.path.join(out_root, experiment.name, "baseline")
        reform_dir = os.path.join(out_root, experiment.name, "reform")
        for w in self.preflight(experiment, country):
            print(f"[guardrail] {w}")

        # baseline solved ONCE; only the reform is recomputed across passes
        p, _aux = self.build_baseline(country, base_dir)
        ctx.base_tpi = self.solve(p)

        exchanged_prev = None
        for pass_idx in range(max(1, max_passes)):
            ctx.clews_inputs, ctx.extras = {}, {}
            ctx.og_reform = self._fresh_reform(p, base_dir, reform_dir)
            self._apply_pre_solve(ctx, experiment.channels, pass_idx)
            ctx.reform_tpi = self.solve(ctx.og_reform)
            self._apply_post_solve(ctx, experiment.channels, pass_idx)

            if max_passes <= 1:
                break
            if clews_runner is None:
                print("[iterate] multi-pass requested but no CLEWS runner wired -> one pass only "
                      "(the CLEWS re-solve + dual extraction is the seam still to build).")
                break
            country.scenario.reform_dir = clews_runner(ctx.clews_inputs, country, pass_idx)
            exch = self._exchanged_quantity(ctx, country)
            if exchanged_prev is not None and abs(exch - exchanged_prev) <= tol * abs(exchanged_prev):
                print(f"[iterate] converged at pass {pass_idx} (relative change < {tol})")
                break
            exchanged_prev = damp * exch + (1 - damp) * (exchanged_prev or exch)
        return ctx

    def run_across_steps(self, steps, country, out_root: str = "./ogclews_runs"):
        """Solve the baseline ONCE, then one reform per CUMULATIVE channel set. ``steps`` is a
        list of (label, channels). Returns [(label, ExperimentContext), ...] sharing the baseline
        -- the layered 'what does each added channel do' view. Each step is one-way."""
        import os

        base_dir = os.path.join(out_root, "across_steps", "baseline")
        p, _aux = self.build_baseline(country, base_dir)
        base_tpi = self.solve(p)
        results = []
        for label, channels_list in steps:
            ctx = ExperimentContext(country=country, base_tpi=base_tpi)
            ctx.og_reform = self._fresh_reform(p, base_dir, os.path.join(out_root, "across_steps", label))
            try:
                self._apply_pre_solve(ctx, channels_list, 0, step=label)
                ctx.reform_tpi = self.solve(ctx.og_reform)
                self._apply_post_solve(ctx, channels_list, 0, step=label)
            except Exception as e:  # one non-converging step must not kill the whole batch
                print(f"[across_steps] step '{label}' did NOT solve: {type(e).__name__}: {e}")
                ctx.extras["error"] = f"{type(e).__name__}: {e}"
            results.append((label, ctx))
        return results

    # --- shared reform helpers ---------------------------------------------------

    def _fresh_reform(self, p, base_dir, reform_dir):
        import copy

        r = copy.deepcopy(p)
        r.baseline = False
        r.baseline_dir = base_dir
        r.output_base = reform_dir
        r.__dict__.pop("_e_long_cache", None)  # ogcore memoizes e; reform edits must take
        return r

    def _apply_pre_solve(self, ctx, channels, pass_idx, step=None):
        for cid, opts in channels:
            ch = get(cid)
            if ch.post_solve:
                continue
            ctx.log(cid, pass_idx=pass_idx, step=step, **ch.apply(ctx, **opts))
        if ctx.extras.get("health_shock") is not None and self.apply_health:
            ctx.og_reform = self.apply_health(ctx.og_reform, ctx.extras["health_shock"])

    def _apply_post_solve(self, ctx, channels, pass_idx, step=None):
        for cid, opts in channels:
            ch = get(cid)
            if not ch.post_solve:
                continue
            ctx.log(cid, pass_idx=pass_idx, step=step, **ch.apply(ctx, **opts))

    def _exchanged_quantity(self, ctx, country):
        """The quantity convergence is judged on (mean near-term energy-good demand)."""
        import numpy as np

        ie = country.concordance.energy_good_index
        return float(np.asarray(ctx.reform_tpi["C_i"])[:10, ie].mean())

    def preflight(self, experiment: Experiment, country) -> list[str]:
        """Run every channel's validate() against the active set (no solving)."""
        ctx = ExperimentContext(country=country)
        active = experiment.channel_ids()
        msgs: list[str] = []
        for cid, _ in experiment.channels:
            msgs.extend(get(cid).validate(ctx, active))
        return msgs
