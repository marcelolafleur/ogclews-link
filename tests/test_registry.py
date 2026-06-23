"""Link-side unit tests for the OG-model registry loader. No OG env, no numpy/ogcore. Run with the
standalone link venv: `uv run pytest tests/test_registry.py`.
"""
from __future__ import annotations

import json
import os
import types

from ogclews_link import registry


def _write(tmp_path, env_python="/bin/sh"):
    p = tmp_path / "og_model_registry.json"
    p.write_text(json.dumps({"version": 1, "countries": {
        "608": {"name": "Philippines", "og_package": "ogphl", "env_python": env_python,
                "og_version": "0.1.0"}}}))
    return str(p)


def test_packaged_default_parses_and_has_phl():
    reg = registry.load_registry()                       # the shipped default
    assert "608" in reg and reg["608"].og_package == "ogphl"
    assert reg["608"].params_resource_name == "ogphl_default_parameters.json"  # default applies


def test_registry_path_resolution_order(tmp_path, monkeypatch):
    monkeypatch.delenv(registry.ENV_VAR, raising=False)
    assert registry.registry_path() == registry._packaged_default()   # falls back to packaged
    envfile = _write(tmp_path)
    monkeypatch.setenv(registry.ENV_VAR, envfile)
    assert registry.registry_path() == envfile                        # env var wins


def test_lookup_success_and_params_default(tmp_path):
    entry = registry.lookup("608", path=_write(tmp_path))
    assert entry.og_package == "ogphl" and entry.name == "Philippines"
    assert entry.params_resource_name == "ogphl_default_parameters.json"
    # also resolves a CountryConfig-like object via .un_code
    country = types.SimpleNamespace(un_code="608", name="Philippines")
    assert registry.lookup(country, path=_write(tmp_path)).un_code == "608"


def test_missing_country_raises_actionable(tmp_path):
    import pytest
    with pytest.raises(registry.ModelNotInstalledError) as e:
        registry.lookup("999", path=_write(tmp_path))
    assert "No OG model registered" in str(e.value) and "999" in str(e.value)


def test_absent_interpreter_raises(tmp_path):
    import pytest
    bad = _write(tmp_path, env_python="/no/such/python")
    with pytest.raises(registry.ModelNotInstalledError) as e:
        registry.lookup("608", path=bad)
    assert "not found at" in str(e.value)
