"""Register management for the installed OG-model registry (the `ogclews-link models ...` subcommands).
Stdlib-only. WRITING the register is what the universal OG installer (or `models register --path`) does
after a model is installed; the link otherwise only READS it (see registry.py). An entry is a pure
install record -- {package, env_python, version} -- keyed by the OG repo key (og-phl). The UN country
code is NOT stored here; the OG package owns it (e.g. ogphl.UN_COUNTRY_CODE)."""
from __future__ import annotations

import json
import os
import sys
import tomllib
from datetime import datetime, timezone

from . import discovery, registry


def _discovered_block(findings: dict) -> dict:
    """The discovery findings as the durable record stored in the registry entry (drops the package/dir
    that the entry already carries; stamps when it was recorded)."""
    return {"at": datetime.now(timezone.utc).isoformat(),
            "recommended": findings.get("recommended"),
            "couplable_count": findings.get("couplable_count"),
            "candidates": findings.get("candidates", [])}


def _findings_from_saved(entry) -> dict:
    """Reconstruct a findings-shaped dict from a registry entry's SAVED ``discovered`` block (so the same
    display/consumers work whether the status is read from cache or freshly discovered)."""
    d = entry.discovered or {}
    return {"og_package": entry.package, "source_dir": registry.package_source_dir(entry),
            "recommended": d.get("recommended"), "couplable_count": d.get("couplable_count"),
            "candidates": d.get("candidates", []), "discovered_at": d.get("at")}


def _read_pyproject(install_dir: str) -> dict:
    pp = os.path.join(install_dir, "pyproject.toml")
    if not os.path.exists(pp):
        return {}
    with open(pp, "rb") as f:
        return tomllib.load(f).get("project", {})


def _write_target(registry_file: str | None) -> str:
    """Where `register` writes: explicit --registry > $OGCLEWS_MODEL_REGISTRY > ./og_model_registry.json."""
    return (registry_file or os.environ.get(registry.ENV_VAR)
            or os.path.join(os.getcwd(), "og_model_registry.json"))


def register(install_dir: str, *, key: str | None = None, registry_file: str | None = None,
             calibration: str | None = None, run_discovery: bool = True) -> dict:
    """Record an installed OG model into the register by introspecting its checkout dir. Resolves the
    env interpreter (``<dir>/.venv/bin/python`` -- the uv convention the installer produces), the
    package name + version (from its pyproject), and the repo key (``--key`` or the dir name, e.g.
    OG-PHL -> og-phl). Then DISCOVERS the package's calibration choices (running og_runner in that env)
    and records the chosen one: ``calibration`` if given, else the lone couplable multisector candidate
    (auto-pick), else None (single-industry -> energy channels skip). Returns the written record (+ the
    discovery findings, so the caller can display them)."""
    install_dir = os.path.abspath(install_dir)
    env_python = os.path.join(install_dir, ".venv", "bin", "python")
    if not os.path.exists(env_python):
        raise FileNotFoundError(
            f"no model interpreter at {env_python}. Build the model's env first "
            f"(the OG installer runs `uv sync` in {install_dir}), then register.")
    proj = _read_pyproject(install_dir)
    package = proj.get("name") or os.path.basename(install_dir).lower().replace("-", "")
    key = key or os.path.basename(install_dir).lower()      # OG-PHL -> og-phl (matches repos.json)
    version = proj.get("version")
    source_dir = os.path.join(install_dir, package)         # the package's source (the checkout convention)

    findings = None
    if run_discovery:
        if os.path.isdir(source_dir):
            findings = discovery.discover_calibrations(source_dir, package)   # LINK-SIDE: reads files, no subprocess
        else:
            print(f"[models] package source not found at {source_dir}; recording single-industry "
                  "(pass --calibration to override).", file=sys.stderr)
    # explicit choice wins; else auto-pick the lone couplable candidate; else single-industry (None)
    chosen = calibration if calibration is not None else (findings or {}).get("recommended")

    rf = _write_target(registry_file)
    data = {"schema_version": 1, "models": {}}
    if os.path.exists(rf):
        with open(rf) as f:
            data = json.load(f)
    entry = {"package": package, "env_python": env_python, "version": version, "source_dir": source_dir}
    if chosen is not None:
        entry["calibration"] = chosen
    if findings is not None:
        entry["discovered"] = _discovered_block(findings)   # the durable, user-inspectable status record
    data.setdefault("models", {})[key] = entry
    with open(rf, "w") as f:
        json.dump(data, f, indent=2)
    return {"registry": rf, "key": key, "package": package, "env_python": env_python,
            "version": version, "calibration": chosen, "source_dir": source_dir, "findings": findings}


def calibrations(model, registry_file: str | None = None, *, refresh: bool = False) -> dict | None:
    """Discovery findings (the calibration menu) for a REGISTERED model, resolved by repo key / package /
    CountryConfig. By default returns the SAVED ``discovered`` status from the registry (no re-read).
    ``refresh=True`` re-reads the package source LINK-SIDE (no env, no subprocess -- cheap) and rewrites
    the saved record. Returns None if there is no saved status and the source dir is not on disk."""
    entry = registry.lookup(model, path=registry_file, require_env=False)   # discovery needs source, not env
    if not refresh and entry.discovered:
        return _findings_from_saved(entry)
    src = registry.package_source_dir(entry)
    if not os.path.isdir(src):
        return _findings_from_saved(entry) if entry.discovered else None
    findings = discovery.discover_calibrations(src, entry.package)
    if refresh:
        _save_discovered(entry.key, findings, registry_file)
    return findings


def _save_discovered(key: str, findings: dict, registry_file: str | None) -> None:
    """Rewrite a model's ``discovered`` block (and re-stamp it) in the active registry file -- used by
    ``models calibrations --refresh`` to update the saved status after a package changed."""
    rf = registry.registry_path(registry_file)
    if not os.path.exists(rf):
        return
    with open(rf) as f:
        data = json.load(f)
    if key in data.get("models", {}):
        data["models"][key]["discovered"] = _discovered_block(findings)
        with open(rf, "w") as f:
            json.dump(data, f, indent=2)


def list_models(registry_file: str | None = None) -> list[tuple]:
    """Registered models as (key, package, version, calibration, couplable_count, interpreter_exists).
    ``couplable_count`` is from the saved discovery status (None if never discovered)."""
    reg = registry.load_registry(registry_file)
    return [(k, e.package, e.version, e.calibration, (e.discovered or {}).get("couplable_count"),
             os.path.exists(e.env_python)) for k, e in sorted(reg.items())]
