"""The link-side run orchestrator. numpy/stdlib only -- it imports NO ogcore and NO country package.
To solve, it looks up the country's OG model in the registry and drives that model's OWN interpreter as
a subprocess (ogclews_link.og_runner), handing over data files (JSON overrides in, .npz solutions out).
The link and the OG model stay in separate, independently-installed environments.

  export_baseline(country) -> (og_reform template, base_tpi, baseline_dir, baseline_arrays)
  solve_reform(og_reform, baseline_arrays, health_shock, base_dir, reform_dir, country) -> reform_tpi

These are injected into framework.run (replacing the old in-process build/solve/apply_health). The
baseline export is content-addressed + cached, so a battery of reforms re-uses one solved baseline.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

from . import registry, serde

# parent of the ogclews_link/ package dir -- put on the subprocess PYTHONPATH so the OG env's python
# can import ogclews_link.og_runner (+ the pure-python serde/_demog/health_pop/_calibration/progress it
# uses) from the link source, while ogcore + the country package come from the OG env.
_LINK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class RunnerConfig:
    num_workers: int = 1
    show_progress: bool = True
    ss: bool = False                 # steady-state-only solve (fast; for the SS smoke / ss_smoke battery)
    registry_path: str | None = None


def _run(entry, args, label):
    env = dict(os.environ)
    env["PYTHONPATH"] = _LINK_ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run([entry.env_python, "-m", "ogclews_link.og_runner", *args],
                          env=env, capture_output=True, text=True)
    if proc.stderr:
        sys.stderr.write(proc.stderr)                      # surface runner diagnostics (progress, RC_SS)
    if proc.returncode != 0:
        raise RuntimeError(f"og_runner {label} failed (exit {proc.returncode}) in the {entry.package} "
                           f"env [{entry.env_python}]. See stderr above.")
    return proc


def _cache_dir(out_root, entry, country, cfg):
    # the baseline is per-OG-model + scenario-independent; key the cache by the model + version
    tag = f"{entry.key}-{entry.version or 'na'}" + ("-ss" if cfg.ss else "")
    return os.path.join(out_root, "_og_baseline_cache", tag)


def export_baseline(country, out_root="./ogclews_runs", cfg: RunnerConfig | None = None):
    """Ensure a solved baseline exists for ``country`` (subprocess the OG runner if not cached), then load
    its exported params + solution. Returns (OGParams template, base_tpi, baseline_dir, baseline_arrays)."""
    cfg = cfg or RunnerConfig()
    entry = registry.lookup(country, path=cfg.registry_path)         # fail-fast before any subprocess
    cache = _cache_dir(out_root, entry, country, cfg)
    params_npz = os.path.join(cache, "baseline_params.npz")
    solution_npz = os.path.join(cache, "baseline_solution.npz")
    if not (os.path.exists(params_npz) and os.path.exists(os.path.join(cache, "baseline_meta.json"))):
        os.makedirs(cache, exist_ok=True)
        args = ["export-baseline", "--og-package", entry.package,
                "--params-resource", entry.params_resource_name,
                "--og-start-year", str(country.scenario.og_start_year),
                "--num-workers", str(cfg.num_workers), "--out-dir", cache]
        if cfg.ss:
            args.append("--ss")
        if not cfg.show_progress:
            args.append("--no-progress")
        _run(entry, args, "export-baseline")
    og, base_tpi, baseline_arrays = serde.load_baseline_bundle(params_npz, solution_npz)
    return og, base_tpi, cache, baseline_arrays


def solve_reform(og_reform, baseline_arrays, health_shock, base_dir, reform_dir, country,
                 cfg: RunnerConfig | None = None):
    """Serialize the channels' parameter overrides (+ a health shock if any), subprocess the OG runner to
    solve the reform in the OG env, and load the reform solution back. Returns reform_tpi (a dict)."""
    cfg = cfg or RunnerConfig()
    entry = registry.lookup(country, path=cfg.registry_path)
    os.makedirs(reform_dir, exist_ok=True)
    overrides = os.path.join(reform_dir, "reform_overrides.json")
    serde.write_overrides_json(serde.diff_against_baseline(og_reform, baseline_arrays), overrides)
    args = ["solve-reform", "--baseline-dir", base_dir, "--reform-dir", reform_dir,
            "--overrides", overrides, "--num-workers", str(cfg.num_workers),
            # the reform rebuilds the baseline fresh, so pass the same build inputs as export-baseline:
            "--og-package", entry.package, "--params-resource", entry.params_resource_name,
            "--og-start-year", str(country.scenario.og_start_year)]
    if health_shock is not None:
        hpath = os.path.join(reform_dir, "health.json")
        serde.write_health_json(health_shock, hpath)
        args += ["--health-shock", hpath]
    if cfg.ss:
        args.append("--ss")
    if not cfg.show_progress:
        args.append("--no-progress")
    _run(entry, args, "solve-reform")
    sol_npz = os.path.join(reform_dir, "reform_solution.npz")
    if not os.path.exists(sol_npz):
        raise RuntimeError(f"og_runner solve-reform produced no reform_solution.npz in {reform_dir}")
    return serde.load_solution(sol_npz)
