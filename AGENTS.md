# Agent operating rules for ogclews-link

Rules any AI agent (and human) must follow when working in this repo. Written after a full battery
ran stale code via import shadowing (2026-07-07) — these are load-bearing, not style.

## Before ANY model run (solve, battery, `run <experiment>`)

1. **Verify the branch of every repo involved** — this link worktree, the registered OG model
   worktree (`og_model_registry.json` → `source_dir`/`env_python`), and MUIOGO. Print branch + HEAD.
   Do not launch from memory of what they were.
2. **Verify what the interpreter actually imports.** The link venv is typically an *editable install*
   that can point at a DIFFERENT worktree/branch than your cwd, and a script invocation puts the
   script's own directory (not the repo root) at `sys.path[0]`:

   ```
   <venv-python> -c "import ogclews_link; print(ogclews_link.__file__)"
   ```

   The printed path MUST be inside the worktree you intend to test. For the OG side, check
   `import ogphl, ogcore` the same way with the registered `env_python`.
   **Third vector — cwd:** `python -c ...` and `python script.py` put the cwd / script dir at
   `sys.path[0]`, so running from ANOTHER checkout's root imports THAT checkout's `ogclews_link/`
   regardless of which venv you use. Always run from the worktree under test (console scripts are
   immune — they don't put cwd on `sys.path`). Launch wrappers must assert the resolved path.
3. **Each worktree gets its own venv** (`python -m venv .venv && .venv/bin/pip install -e .`).
   Entry scripts that must run from any checkout pin `sys.path.insert(0, REPO)` **and assert** the
   resolved `ogclews_link.__file__` is under `REPO` (see `experiments/run_battery.py`).
4. **Run as a user would**: the documented CLI (`ogclews-link run <exp> --clews-base ... --clews-reform ...`)
   from the checkout's own venv. Not ad-hoc scripts with inherited env state.
5. **Contamination heuristic**: if a fresh run reproduces a number from a known-buggy earlier run,
   assume the wrong code ran. Stop, re-verify imports, and never commit/bless those outputs.

## Environments (this project is deliberately cross-env)

- **link env**: numpy/pandas only — NO ogcore. It subprocesses the OG model's own interpreter
  (from the registry) for every solve. Nothing about a solve should import ogcore in the link env.
- **OG model env**: the registry entry's `env_python` (e.g. OG-PHL's worktree venv). The calibration
  the runner loads is the registry entry's `calibration` (PHL: the discovered M=8 multisector file).
  M=4 aggregations are dead — the link never authors one; it discovers and loads the country's own file.
- **CLEWS inputs**: MUIOGO run-output csv dirs (`.../DataStorage/<case>/res/<run>/csv`), passed
  explicitly via `--clews-base/--clews-reform` (or `$OGCLEWS_CLEWS_BASE/REFORM`). Do not export those
  env vars globally in a shell that will also run pytest — two tests change behavior when real CLEWS
  dirs are visible.

## Orchestration

The main loop orchestrates and verifies; execution work is delegated to agents (Opus 4.8). Judgment
lives in files (this one, checklists, skills), so executors run them mechanically and report
PASS/FAIL with evidence. The orchestrator spot-checks results before acting on them; executors never
bless their own output.
