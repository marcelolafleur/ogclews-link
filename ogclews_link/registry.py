"""The OG-model registry: where each onboarded country model's environment lives, so the link can
locate and launch it as a subprocess without importing it. Stdlib-only (imports in the link env).

Keyed by the OG REPO KEY (e.g. ``og-phl``), mirroring ``OG-Core/scripts/repos.json`` and the universal
installer. An entry is a pure INSTALL RECORD -- ``{package, env_python, version}`` -- nothing about
coupling or calibration, and NOT the UN country code (the OG package owns that: ``ogphl.UN_COUNTRY_CODE``).

The link only READS registries; it never installs. Resolution: an explicit registry (the ``path`` arg or
``$OGCLEWS_MODEL_REGISTRY``) is used ALONE; otherwise the link's own register (``./og_model_registry.json``
> the packaged EMPTY default) is overlaid by a present MUIOGO install's register
(``$OGCLEWS_MUIOGO_HOME/WebAPP/DataStorage/OGCore/og_calibrations_installed.json`` -- written by MUIOGO's
OG installer, PR #487) -- so a MUIOGO-managed model is the source of truth for what MUIOGO installed, with
the link's own register as the fallback. The link maps MUIOGO's record (``python_path`` / ``local_path`` /
``package_name``) to an entry and picks the couplable calibration with its OWN discovery (MUIOGO needn't
know anything about energy-coupling). A missing/unbuilt model raises an actionable ModelNotInstalledError.
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
    discovered: dict | None = None   # the SAVED discovery findings (calibration menu + couplability +
                                     # an 'at' timestamp), recorded at register time so the status is
                                     # durable + user-inspectable without re-running. The authoritative
                                     # CHOICE is `calibration` (edit that to override); `discovered` is the
                                     # record. Re-read with `models calibrations --refresh` (it's cheap).

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
                              source_dir=e.get("source_dir"), discovered=e.get("discovered"))
    return out


def package_source_dir(entry: ModelEntry) -> str:
    """The package's source dir (for link-side reading of PROD_DICT/CONS_DICT + calibrations). The stored
    ``source_dir`` if present, else derived from the env interpreter: ``<install>/.venv/bin/python`` ->
    ``<install>/<package>`` (the checkout convention the installer produces)."""
    if entry.source_dir:
        return entry.source_dir
    install = os.path.dirname(os.path.dirname(os.path.dirname(entry.env_python)))   # .venv/bin/python -> install
    return os.path.join(install, entry.package)


MUIOGO_HOME_ENV = "OGCLEWS_MUIOGO_HOME"


def _muiogo_home() -> str | None:
    """The MUIOGO install dir: $OGCLEWS_MUIOGO_HOME, else a sibling ``../MUIOGO``. Mirrors
    country._muiogo_home so registry + CLEWS-scenario resolution agree on where MUIOGO lives."""
    env = os.environ.get(MUIOGO_HOME_ENV)
    if env:
        return env
    sibling = os.path.normpath(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.pardir, "MUIOGO"))
    return sibling if os.path.isdir(sibling) else None


def load_muiogo_registry() -> dict[str, ModelEntry]:
    """MUIOGO's installed-OG register as ``{repo_key: ModelEntry}``, or ``{}`` when there is no MUIOGO
    install / file / usable record. Read-only and FULLY TOLERANT: a missing or corrupt MUIOGO registry
    must never break the link -- it just falls back to the link's own. MUIOGO records where a model is
    installed (``python_path`` / ``local_path`` / ``package_name``); the link's own discovery picks the
    couplable calibration, so the link never depends on MUIOGO understanding coupling."""
    home = _muiogo_home()
    if not home:
        return {}
    f = os.path.join(home, "WebAPP", "DataStorage", "OGCore", "og_calibrations_installed.json")
    try:
        with open(f, encoding="utf-8-sig") as fh:        # utf-8-sig: tolerate a BOM (MUIOGO writes utf-8)
            records = json.load(fh)["calibrations"].values()
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        return {}
    from . import discovery      # lazy: keep the module import graph flat (registry loads early)
    out: dict[str, ModelEntry] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        env_python, local_path, package = rec.get("python_path"), rec.get("local_path"), rec.get("package_name")
        if not (env_python and local_path and package):
            continue                                     # not a usable/complete install record
        key = os.path.basename(os.path.normpath(local_path)).lower()    # OG-PHL -> og-phl (repos.json key)
        source_dir = os.path.join(local_path, package)                  # the checkout convention
        calibration = disc = None
        if os.path.isdir(source_dir):
            try:                                         # best-effort: a bad source dir -> single-industry
                disc = discovery.discover_calibrations(source_dir, package)
                calibration = disc.get("recommended")
            except Exception:                            # noqa: BLE001 -- discovery must never break lookup
                disc = None
        out[key] = ModelEntry(key=key, package=package, env_python=env_python,
                              version=rec.get("commit_sha"), calibration=calibration,
                              source_dir=source_dir, discovered=disc)
    return out


def lookup(model, path: str | None = None, *, require_env: bool = True) -> ModelEntry:
    """Resolve a repo key ('og-phl'), a package name ('ogphl'), or a CountryConfig (its ``og_repo``/
    ``og_package``) to its ModelEntry. Raises ModelNotInstalledError -- with an actionable message --
    if unregistered or (when ``require_env``) its interpreter is not on disk. ``require_env=False`` for
    link-side-only uses (e.g. reading the calibration menu, which needs the source dir, not the env).
    NEVER installs a model."""
    ident = str(getattr(model, "og_repo", None) or getattr(model, "og_package", None) or model)
    rp = registry_path(path)
    reg = load_registry(path)
    # Unless an explicit registry is pinned (the arg or $OGCLEWS_MODEL_REGISTRY -- the override/escape
    # hatch), overlay a present MUIOGO install's register on top of the link's own, so MUIOGO is the
    # source of truth for the models it installed. A missing/corrupt MUIOGO registry yields {} -> no-op.
    saw_muiogo = False
    if not path and not os.environ.get(ENV_VAR):
        muiogo = load_muiogo_registry()
        if muiogo:
            reg = {**reg, **muiogo}
            saw_muiogo = True
    entry = reg.get(ident) or next((e for e in reg.values() if e.package == ident), None)
    if entry is None:
        raise ModelNotInstalledError(
            f"No OG model registered for '{ident}'. Registry: {rp}"
            f"{' (+ MUIOGO install)' if saw_muiogo else ''}. Install + register it "
            f"(`ogclews-link models register --path <dir>`, or via the MUIOGO OG installer/tab), or set "
            f"${ENV_VAR} to a registry that has it.")
    if require_env and not os.path.exists(entry.env_python):
        raise ModelNotInstalledError(
            f"OG model env for '{entry.key}' ({entry.package}) not found at {entry.env_python}. "
            f"Re-install/register that model (its interpreter moved or was never built).")
    return entry
