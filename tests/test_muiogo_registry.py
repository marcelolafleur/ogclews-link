"""Link-side tests for resolving an OG model from a MUIOGO install's register (MUIOGO PR #487).

The link READS MUIOGO's ``WebAPP/DataStorage/OGCore/og_calibrations_installed.json`` (never writes it):
MUIOGO is the source of truth for the models it installed, the link's own register is the fallback, and
an explicit ``$OGCLEWS_MODEL_REGISTRY`` / ``path=`` overrides both. Fully tolerant -- a missing or corrupt
MUIOGO file must never break lookup. No OG env, no numpy/ogcore.
Run with the standalone link venv: ``uv run pytest tests/test_muiogo_registry.py``.
"""
from __future__ import annotations

import json
import os

import pytest

from ogclews_link import registry


def _muiogo_home(tmp_path, *, package="ogphl", repo="OG-PHL", python_path="/bin/sh",
                 make_source=False, country_id="PHL", state="installed"):
    """Create a fake MUIOGO install carrying one installed-OG record; return (home, local_path)."""
    ogc = tmp_path / "MUIOGO" / "WebAPP" / "DataStorage" / "OGCore"
    ogc.mkdir(parents=True)
    local_path = tmp_path / "models" / repo
    if make_source:
        (local_path / package).mkdir(parents=True)          # source_dir present -> discovery is attempted
    rec = {"country_id": country_id, "country_name": "Philippines", "package_name": package,
           "local_path": str(local_path), "python_path": python_path, "commit_sha": "abc123",
           "install_state": state}
    (ogc / "og_calibrations_installed.json").write_text(json.dumps({"calibrations": {country_id: rec}}))
    return str(tmp_path / "MUIOGO"), str(local_path)


def _link_registry(tmp_path, *, env_python="/bin/sh", key="og-phl", package="ogphl"):
    p = tmp_path / "og_model_registry.json"
    p.write_text(json.dumps({"schema_version": 1, "models": {
        key: {"package": package, "env_python": env_python, "version": "0.1.0"}}}))
    return str(p)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # isolate from the real machine's env + any sibling ../MUIOGO
    monkeypatch.delenv(registry.ENV_VAR, raising=False)
    monkeypatch.delenv(registry.MUIOGO_HOME_ENV, raising=False)


def test_resolves_model_from_muiogo_register(tmp_path, monkeypatch):
    home, local = _muiogo_home(tmp_path, make_source=True)
    monkeypatch.setenv(registry.MUIOGO_HOME_ENV, home)
    # the link's OWN discovery picks the couplable calibration from MUIOGO's checkout (MUIOGO needn't know)
    monkeypatch.setattr("ogclews_link.discovery.discover_calibrations",
                        lambda pkg_dir, package: {"recommended": "ogphl_multisector_default_parameters.json",
                                                  "couplable_count": 1})
    monkeypatch.chdir(tmp_path)                              # link-own -> packaged empty (no ./registry here)
    e = registry.lookup("og-phl")
    assert (e.key, e.package, e.env_python) == ("og-phl", "ogphl", "/bin/sh")
    assert e.source_dir == os.path.join(local, "ogphl")
    assert e.calibration == "ogphl_multisector_default_parameters.json"
    assert registry.lookup("ogphl").key == "og-phl"         # also resolvable by package name


def test_muiogo_is_source_of_truth_over_link_own(tmp_path, monkeypatch):
    home, _ = _muiogo_home(tmp_path, python_path="/bin/sh")
    monkeypatch.setenv(registry.MUIOGO_HOME_ENV, home)
    monkeypatch.chdir(tmp_path)
    _link_registry(tmp_path, env_python="/usr/bin/true")    # link-own points at a DIFFERENT interpreter
    e = registry.lookup("og-phl")                            # no explicit path -> MUIOGO overlays link-own
    assert e.env_python == "/bin/sh"                         # MUIOGO's record wins for the same key


def test_explicit_registry_bypasses_muiogo(tmp_path, monkeypatch):
    home, _ = _muiogo_home(tmp_path, python_path="/bin/sh")
    monkeypatch.setenv(registry.MUIOGO_HOME_ENV, home)
    rp = _link_registry(tmp_path, env_python="/usr/bin/true")
    assert registry.lookup("og-phl", path=rp).env_python == "/usr/bin/true"   # explicit path -> MUIOGO ignored
    monkeypatch.setenv(registry.ENV_VAR, rp)                 # $OGCLEWS_MODEL_REGISTRY is also an override
    assert registry.lookup("og-phl").env_python == "/usr/bin/true"


def test_absent_muiogo_falls_back_to_link_own(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                              # no $OGCLEWS_MUIOGO_HOME, no sibling ../MUIOGO
    assert registry.load_muiogo_registry() == {}
    rp = _link_registry(tmp_path)
    assert registry.lookup("og-phl", path=rp).package == "ogphl"


def test_corrupt_muiogo_register_is_tolerated(tmp_path, monkeypatch):
    ogc = tmp_path / "MUIOGO" / "WebAPP" / "DataStorage" / "OGCore"
    ogc.mkdir(parents=True)
    (ogc / "og_calibrations_installed.json").write_text("{ not: valid json ]")
    monkeypatch.setenv(registry.MUIOGO_HOME_ENV, str(tmp_path / "MUIOGO"))
    assert registry.load_muiogo_registry() == {}            # corrupt -> {}, never raises
    rp = _link_registry(tmp_path)
    assert registry.lookup("og-phl", path=rp).package == "ogphl"   # link still resolves


def test_incomplete_record_is_skipped(tmp_path, monkeypatch):
    # a record missing python_path/local_path/package_name is not a usable install -> ignored
    ogc = tmp_path / "MUIOGO" / "WebAPP" / "DataStorage" / "OGCore"
    ogc.mkdir(parents=True)
    (ogc / "og_calibrations_installed.json").write_text(json.dumps(
        {"calibrations": {"PHL": {"country_id": "PHL", "install_state": "installing"}}}))
    monkeypatch.setenv(registry.MUIOGO_HOME_ENV, str(tmp_path / "MUIOGO"))
    assert registry.load_muiogo_registry() == {}
