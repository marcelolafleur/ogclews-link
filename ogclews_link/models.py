"""Register management for the installed OG-model registry (the `ogclews-link models ...` subcommands).
Stdlib-only. WRITING the register is what the universal OG installer (or `models register --path`) does
after a model is installed; the link otherwise only READS it (see registry.py). An entry is a pure
install record -- {package, env_python, version} -- keyed by the OG repo key (og-phl). The UN country
code is NOT stored here; the OG package owns it (e.g. ogphl.UN_COUNTRY_CODE)."""
from __future__ import annotations

import json
import os
import tomllib

from . import registry


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


def register(install_dir: str, *, key: str | None = None, registry_file: str | None = None) -> dict:
    """Record an installed OG model into the register by introspecting its checkout dir. Resolves the
    env interpreter (``<dir>/.venv/bin/python`` -- the uv convention the installer produces), the
    package name + version (from its pyproject), and the repo key (``--key`` or the dir name, e.g.
    OG-PHL -> og-phl), then writes/merges the entry. Returns the written record (+ the registry path)."""
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

    rf = _write_target(registry_file)
    data = {"schema_version": 1, "models": {}}
    if os.path.exists(rf):
        with open(rf) as f:
            data = json.load(f)
    data.setdefault("models", {})[key] = {"package": package, "env_python": env_python, "version": version}
    with open(rf, "w") as f:
        json.dump(data, f, indent=2)
    return {"registry": rf, "key": key, "package": package, "env_python": env_python, "version": version}


def list_models(registry_file: str | None = None) -> list[tuple]:
    """The registered models as (key, package, version, interpreter_exists)."""
    reg = registry.load_registry(registry_file)
    return [(k, e.package, e.version, os.path.exists(e.env_python)) for k, e in sorted(reg.items())]
