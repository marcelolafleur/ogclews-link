"""The OG-model registry: where each onboarded country model's environment lives, so the link can
locate and launch it as a subprocess without importing it. Stdlib-only (imports in the link env).

Resolution order for the registry file: $OGCLEWS_MODEL_REGISTRY, then ./og_model_registry.json in the
cwd, then the packaged default at ogclews_link/data/og_model_registry.json. Eventually MUIOGO owns this
file (it installs the models); for now it ships a Philippines entry. The link READS it -- it never
installs a model; a missing/unbuilt model raises an actionable ModelNotInstalledError.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

ENV_VAR = "OGCLEWS_MODEL_REGISTRY"


class ModelNotInstalledError(RuntimeError):
    """The requested country's OG model is not registered, or its environment is not on disk."""


@dataclass(frozen=True)
class ModelEntry:
    un_code: str
    name: str
    og_package: str            # importable package name in the model's env, e.g. "ogphl"
    env_python: str            # absolute path to that env's python interpreter
    og_version: str | None = None
    ogcore_version: str | None = None
    params_resource: str | None = None

    @property
    def params_resource_name(self) -> str:
        return self.params_resource or f"{self.og_package}_default_parameters.json"


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
    """Parse the registry into {un_code: ModelEntry}."""
    rp = registry_path(path)
    with open(rp) as f:
        data = json.load(f)
    out: dict[str, ModelEntry] = {}
    for un_code, e in data.get("countries", {}).items():
        out[str(un_code)] = ModelEntry(
            un_code=str(un_code), name=e.get("name", un_code), og_package=e["og_package"],
            env_python=e["env_python"], og_version=e.get("og_version"),
            ogcore_version=e.get("ogcore_version"), params_resource=e.get("params_resource"))
    return out


def lookup(country_or_un_code, path: str | None = None) -> ModelEntry:
    """Resolve a CountryConfig (uses .un_code) or a bare un_code string to its ModelEntry. Raises
    ModelNotInstalledError -- with an actionable message -- if the country is unregistered or its
    interpreter is not on disk. NEVER installs a model (that is MUIOGO's job)."""
    un = str(getattr(country_or_un_code, "un_code", country_or_un_code))
    name = getattr(country_or_un_code, "name", un)
    rp = registry_path(path)
    reg = load_registry(path)
    entry = reg.get(un)
    if entry is None:
        raise ModelNotInstalledError(
            f"No OG model registered for {name} (un_code {un}). Registry: {rp}. Add an entry "
            f"{{'og_package': ..., 'env_python': ...}} under countries['{un}'], or set ${ENV_VAR}.")
    if not os.path.exists(entry.env_python):
        raise ModelNotInstalledError(
            f"OG model env for {name} ({entry.og_package}) not found at {entry.env_python}. Install/build "
            f"that model and point its registry 'env_python' at the interpreter (run MUIOGO onboarding).")
    return entry
