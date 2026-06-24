"""The OG-model registry: where each onboarded country model's environment lives, so the link can
locate and launch it as a subprocess without importing it. Stdlib-only (imports in the link env).

Keyed by the OG REPO KEY (e.g. ``og-phl``), mirroring ``OG-Core/scripts/repos.json`` and the universal
installer. An entry is a pure INSTALL RECORD -- ``{package, env_python, version}`` -- nothing about
coupling or calibration, and NOT the UN country code (the OG package owns that: ``ogphl.UN_COUNTRY_CODE``).

The link only READS this file; it never installs. The installed register is WRITTEN by the installer
(MUIOGO drives ``install.sh`` on demand) or by ``ogclews-link models register --path <dir>``. Resolution
order: explicit arg > ``$OGCLEWS_MODEL_REGISTRY`` > ``./og_model_registry.json`` > the packaged default
(which ships EMPTY -- a machine populates it via register). A missing/unbuilt model raises an actionable
ModelNotInstalledError.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

ENV_VAR = "OGCLEWS_MODEL_REGISTRY"


class ModelNotInstalledError(RuntimeError):
    """The requested OG model is not registered, or its environment is not on disk."""


@dataclass(frozen=True)
class ModelEntry:
    key: str                   # the repo key, e.g. "og-phl" (matches repos.json + the installer)
    package: str               # importable package in the model's env, e.g. "ogphl"
    env_python: str            # absolute path to that env's python interpreter
    version: str | None = None
    calibration: str | None = None   # the CHOSEN multisector param resource (from `models register`'s
                                     # discovery); None -> the package's single-industry default, so the
                                     # energy channels skip. Recorded once at onboarding, used every run.
    source_dir: str | None = None    # the package's SOURCE dir (holds its *.py + param JSONs), so the link
                                     # can read PROD_DICT/CONS_DICT + the calibrations WITHOUT importing it.
                                     # None -> derived from env_python (see package_source_dir).

    @property
    def params_resource_name(self) -> str:
        return f"{self.package}_default_parameters.json"


def _packaged_default() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "og_model_registry.json")


def registry_path(path: str | None = None) -> str:
    """The registry file to use: explicit arg > $OGCLEWS_MODEL_REGISTRY > ./og_model_registry.json >
    the packaged default."""
    if path:
        return path
    env = os.environ.get(ENV_VAR)
    if env:
        return env
    local = os.path.join(os.getcwd(), "og_model_registry.json")
    return local if os.path.exists(local) else _packaged_default()


def load_registry(path: str | None = None) -> dict[str, ModelEntry]:
    """Parse the installed register into {repo_key: ModelEntry}."""
    rp = registry_path(path)
    with open(rp) as f:
        data = json.load(f)
    out: dict[str, ModelEntry] = {}
    for key, e in data.get("models", {}).items():
        out[key] = ModelEntry(key=key, package=e["package"], env_python=e["env_python"],
                              version=e.get("version"), calibration=e.get("calibration"),
                              source_dir=e.get("source_dir"))
    return out


def package_source_dir(entry: ModelEntry) -> str:
    """The package's source dir (for link-side reading of PROD_DICT/CONS_DICT + calibrations). The stored
    ``source_dir`` if present, else derived from the env interpreter: ``<install>/.venv/bin/python`` ->
    ``<install>/<package>`` (the checkout convention the installer produces)."""
    if entry.source_dir:
        return entry.source_dir
    install = os.path.dirname(os.path.dirname(os.path.dirname(entry.env_python)))   # .venv/bin/python -> install
    return os.path.join(install, entry.package)


def lookup(model, path: str | None = None, *, require_env: bool = True) -> ModelEntry:
    """Resolve a repo key ('og-phl'), a package name ('ogphl'), or a CountryConfig (its ``og_repo``/
    ``og_package``) to its ModelEntry. Raises ModelNotInstalledError -- with an actionable message --
    if unregistered or (when ``require_env``) its interpreter is not on disk. ``require_env=False`` for
    link-side-only uses (e.g. reading the calibration menu, which needs the source dir, not the env).
    NEVER installs a model."""
    ident = str(getattr(model, "og_repo", None) or getattr(model, "og_package", None) or model)
    rp = registry_path(path)
    reg = load_registry(path)
    entry = reg.get(ident) or next((e for e in reg.values() if e.package == ident), None)
    if entry is None:
        raise ModelNotInstalledError(
            f"No OG model registered for '{ident}'. Registry: {rp}. Install + register it "
            f"(`ogclews-link models register --path <dir>`, or via the MUIOGO installer), or set "
            f"${ENV_VAR} to a registry that has it.")
    if require_env and not os.path.exists(entry.env_python):
        raise ModelNotInstalledError(
            f"OG model env for '{entry.key}' ({entry.package}) not found at {entry.env_python}. "
            f"Re-install/register that model (its interpreter moved or was never built).")
    return entry
