# The link installer: what MUIOGO expects

**Date:** 2026-08-12 (rev 2, same day: the registry seam is now fixed and the bootstrap
exists — `scripts/install.sh` / `install.ps1`). MUIOGO's OG-link integration (branch
`feature/oglink-framework`, commits `823a2d87`..`a879d945`) hard-codes a discovery
contract. An installer that follows it needs **zero configuration** on the user's
machine.

## Install location and layout

Install the link exactly the way MUIOGO installs OG calibrations:

- **Home:** `~/.muiogo/ogclews-link` — a clone (or release copy) of this repo.
- **Env:** `uv sync` → `~/.muiogo/ogclews-link/.venv` (Windows: `.venv\Scripts\python.exe`,
  POSIX: `.venv/bin/python`).
- **Registry:** the link's `og_model_registry.json` lives at the home root; MUIOGO runs
  the link with `cwd=<home>`, so the default `./og_model_registry.json` resolves there.

MUIOGO probes, in order: `$OGCLEWS_LINK_PYTHON` → `$OGCLEWS_LINK_HOME/.venv` →
`~/.muiogo/ogclews-link/.venv` → `../ogclews-link/.venv` (dev sibling). The env vars are
overrides for unusual setups; the installer should NOT need to set any of them.

## OG models MUIOGO installed: discovered automatically, no registration step

The link reads MUIOGO's installed-OG register directly
(`$MUIOGO_OG_DATA_DIR` / `~/.muiogo/og-state` / `og_calibrations_installed.json`; the
pre-#502 in-tree path is a legacy fallback) and maps each installed record into its
model registry at lookup time, running its own calibration discovery. So a model
installed from MUIOGO's OG tab — before or after the link's install — just appears;
the installer performs **no registration sweep**. Precedence on a key collision: the
link's **own** `models register` entry wins (an explicit pin, e.g. a dev worktree);
MUIOGO's register fills the gaps; `$OGCLEWS_MODEL_REGISTRY`/`path=` overrides both.
`models list` remains the health check, now showing the merged view.

`models register --path <dir>` / `setup.py --install-og <key>` remain for standalone
(non-MUIOGO) use and for deliberately pinning a specific checkout.

## Installer form (built)

`scripts/install.sh` / `scripts/install.ps1` bootstrap the install: clone (or
`git pull --ff-only` update) to `~/.muiogo/ogclews-link`, then run the existing
cross-platform `scripts/setup.py` (link venv via uv, CLI verify). Mirrors MUIOGO's and
OG-Core's installer idiom. While the repo is **private**, the clone rides the user's
ambient git auth and the `curl | bash` one-liner form must wait for the repo going
public — until then: clone manually (or run a local copy of `install.sh`).
Still to add, per **MUIOGO-AI's** discipline: an uninstaller and a fully offline
health check.

## What MUIOGO exposes back

- `GET /oglink/status` — link found? (`?deep=1` also runs `models list`:
  `models_registered` tells the UI whether a coupled run is actually possible.)
- `GET/POST /oglink/hookConfig?case=` — per-case post-run hook config
  (`<case>/oglink/hook.json`: `experiment`, `base_caserun`, …).
- After a configured CLEWs run, MUIOGO invokes
  `python -m ogclews_link run <experiment> --clews-base <csv> --clews-reform <csv>
  --clews-run <run dir> --out ~/.muiogo/oglink-runs/<case> --workers N --no-progress`
  with `cwd=<link home>`, and registers the outcome in the case's
  `view/resData.json` under `oglink-runs` (one entry per experiment, latest wins).
- Run outputs (and the OG baseline cache, which lives under `--out`) land in
  `~/.muiogo/oglink-runs/<case>/` — outside DataStorage, per MUIOGO's #502 rule.

## Windows notes

MUIOGO's hook kills a timed-out link run with `taskkill /F /T` (POSIX: process-group
kill), so long-running child solvers are reaped on both platforms. The installer must
create the standard `Scripts\python.exe` venv layout (uv does) — MUIOGO resolves it
with the same helper its own OG installer uses.
