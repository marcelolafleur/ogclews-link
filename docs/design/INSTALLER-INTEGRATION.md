# The link installer: what MUIOGO expects

**Date:** 2026-08-12. MUIOGO's OG-link integration (branch `feature/oglink-framework`,
commits `823a2d87`..`a879d945`) hard-codes a discovery contract. An installer that
follows it needs **zero configuration** on the user's machine.

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

## Register the OG models MUIOGO already installed

MUIOGO's calibration installer puts each country at `~/.muiogo/og-models/<RepoName>/`
with its own `.venv` (registry: `~/.muiogo/og-state/og_calibrations_installed.json`).
Each is exactly what `models register` expects:

```bash
~/.muiogo/ogclews-link/.venv/bin/python -m ogclews_link models register \
    --path ~/.muiogo/og-models/OG-PHL
```

The installer should iterate MUIOGO's installed-calibrations registry and register each
model, then print `models list` as its health check. (Also do this in reverse on
upgrade: re-register after a model update so versions in the registry stay honest.)

## Installer form

Mirror the working precedents:

- **MUIOGO's** `scripts/install.sh` / `install.ps1` (uv bootstrap, clone, `uv sync`,
  verify, offer to start) and **OG-Core's** uv one-liners (marcelolafleur/OG-Core) —
  same idiom: `curl -fsSL <raw url> | bash` on macOS/Linux, a PowerShell one-liner on
  Windows.
- **MUIOGO-AI's** installer discipline: one installation per machine, an uninstaller,
  and an offline health check (`models list` + import probe, no solve).

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
