# Building the OG link into MUIOGO — implementation brief

**Date:** 2026-08-12. **Audience:** a session working in `~/Projects/MUIOGO` (the Flask CLEWs
interface). This is the handoff from `ogclews-link`: what already exists, the decided design, and
the MUIOGO-side work items with expected outputs, likeliest failures, and stop conditions.
Supersedes the MUIOGO sections of `INTEGRATION-HANDOFF.md` (2026-06-17, pre-consolidation).

## 1. What exists today (verified 2026-08-12)

**ogclews-link `main`** (github.com/marcelolafleur/ogclews-link — private):

- The link runs in its **own venv** (numpy/stdlib only) and subprocesses each OG model's own
  interpreter through a model registry (`og_runner`, serde JSON-in/npz-out). It never imports
  ogcore, and MUIOGO never imports the link. Cross-env by construction, both directions.
- `ogclews_link/muiogo_run.py` — consumes a real MUIOGO run: finds `res/<caserun>/csv/`,
  validates the EBb4 commodity-balance export, lists electricity commodity codes. The CLI's
  `--clews-base/--clews-reform` flags point a run at MUIOGO scenario dirs (`--clews-run` is
  manifest provenance only).
- `ogclews_link/clews_driver.py` — **the validated re-solve seam**: `copy_case` (never mutates a
  live case) → patch the copy → `run_caserun` subprocesses **MUIOGO's own interpreter and MUIOGO's
  own pipeline** (`DataFile.generateDatafile` + `DataFile.run`, the exact code behind its `/run`
  route) → hands back the result csv dir. Proven on PHL v9: **+10% household demand → +4.28%
  electricity production**. Parameters are addressed by human codes and translated to the case's
  opaque per-case ids (`COM_*`/`TEC_*`/`EMI_*`) through the case's own `genData.json`, failing
  loudly on a miss. Currently the only patcher is `scale_annual_demand`.
- `emit_*` channels produce the og→clews artifacts (Demand, EmissionsPenalty, …) via
  `clews_io.write_all` → `<run>/clews_inputs/`.
- Evidence base: golden 16/16 on M=8 + CLEWS v9 + LCOE price; coupled Y_ss −0.138%, health −95.4
  lives at −2.65% emissions.

**What the link is still missing (link-side work, not yours):**

1. `clews_patch.py` — serialize a run's emitted artifacts into one `clews_patch.json` (the file
   contract in §3). Two known CLEWs-side data defects to fix while building it: blank
   `clews_fuel` fields and a collapsed discount-rate path in the case JSON.
2. The outer iteration controller — `framework.py` has **no** `clews_runner` hook today; the
   OG⇄CLEWS fixed-point loop (damping, residual stopping) is the last unbuilt piece. The
   mechanism under it (patch → re-solve → re-read) is done and validated.

**MUIOGO upstream** (EAPD-DRB/MUIOGO, `main` @ `ed4851d9`, local checkout fast-forwarded to it):
the shell now has a **model selector, per-model menus, and an OG-Core calibration home** with
install/update/add/retry/remove actions, live install progress, and registry install IDs
(PRs #491, #492, #494/#495). This is the natural UI surface for the coupled run — do not invent a
separate one.

**MUIOGO-AI** (marcelolafleur/MUIOGO-AI, `main` @ `8e200c6`): the headless agent layer. Hard
rule there: **HTTP only** — skills drive MUIOGO through its Flask API, never import backend
classes. It ships the installer (one installation per machine at `~/muiogoai`, uninstaller,
offline status check), the `muiogo-client` package, and the CLEWs/handoff skills mirrored from
Model-tools. Its MUIOGO pin is `928a13bb` — **14 commits behind upstream**; bump deliberately
after a passing run.

## 2. Decided design (don't relitigate without new evidence)

- OG→CLEWS closes via a link-emitted **`clews_patch.json`** (parameters addressed by human
  codes); MUIOGO materializes it into a runnable caserun using its **existing** machinery — the
  read-merge behind `/updateData`, then `/createCaseRun`, then `run()`. No new solve pipeline.
- **Never mutate a live case.** Every patch lands in a copy; the copy is registered as its own
  case/caserun so provenance survives in `view/resData.json`.
- Two integration directions, one subprocess/HTTP seam: MUIOGO→link (post-run hook shells out to
  the link CLI) and link→MUIOGO (the re-solve driver). The Flask venv never gains ogcore; the
  link venv never gains MUIOGO.
- Codes→ids translation always goes through the case's own `genData.json` and fails loudly,
  listing what exists.

## 3. MUIOGO-side work items

### W1 — `apply_oglink_patch`: materialize a patch file into a runnable caserun

Accept a `clews_patch.json` of the shape

```json
{"source": "<og run manifest path>", "case": "<case name>",
 "changes": [{"group": "Demand", "code": "ELC001", "year": 2030, "value": 123.4}, ...]}
```

copy the case, translate each `code` to the per-case id via `genData.json`, apply through the
same read-merge `/updateData` uses, create a caserun, solve, return `{caserun_id, csv_dir}`.

- **Expected output:** given a patch scaling PHL v9 household electricity demand +10%, the
  returned csv dir's production totals reproduce the validated **+4.28%** (that number is the
  acceptance test — `clews_driver.run_caserun` already produces it; your endpoint must match it).
- **Likeliest failure:** the case-copy JSON carries the two known defects (blank `clews_fuel`,
  collapsed discount path) and the datafile generator dies or silently drops rows. Countermove:
  validate the copied case JSON before solving; a generated `.txt` datafile whose row count
  differs from the source case's is the finding — report it, don't patch around it.
- **Stop when:** `/updateData`'s merge semantics can't express a change (e.g. a parameter the UI
  never writes) — report the parameter and the blocking shape; do not add a bypass writer.

### W2 — post-run hook: CLEWs run finishes → OG link runs → results reach the UI

After `run()` completes (after `generateCSVfromCBC()`/`generateResultsViewer()` in
`API/Classes/Case/DataFileClass.py`), a ~15-line subprocess call: the link CLI from its own venv
with `--clews-base/--clews-reform` pointed at the finished run dirs; then register the OG output
(the link writes `<out>/<experiment>/` with manifest, macro table, figure deck) in
`view/resData.json` so the UI can show it.

- **Expected output:** pressing Run on a case yields, alongside the CLEWs CSVs, an OG results
  entry visible in the UI whose manifest names the exact `res/<caserun>/csv` consumed.
- **Likeliest failure:** environment resolution — the hook can't find the link venv or the OG
  model registry. Countermove: resolve interpreters explicitly (no PATH guessing), honour
  `$OGCLEWS_MUIOGO_PYTHON`-style env overrides, and make the hook a no-op with a logged one-line
  reason when the link isn't installed (a CLEWs-only user must be unaffected).
- **Stop when:** the hook needs the Flask venv to import anything from the link or ogcore — that
  is a design violation, report it.

### W3 — UI surface: hang the coupled run on the new OG calibration home

Upstream's OG setup page (install registry IDs, live progress) is where "run coupled" belongs:
a per-case action that (a) fires W2's path on demand, and later (b) drives the iteration loop
when the link ships its controller. Scope minimally: one button + status, reusing the install-job
registry pattern from PR #503/#495 for job tracking.

- **Expected output:** a coupled run is startable and observable from the UI without touching a
  terminal.
- **Likeliest failure:** racing the upstream UI work — those pages landed in the last 14 commits
  and are moving. Countermove: build against local `main` (now at `ed4851d9`), keep the diff
  additive, and rebase before any PR.
- **Stop when:** the button needs upstream API changes beyond an additive route — file the
  upstream issue first (MUIOGO-AI's rule: upstreaming is deliberate, issue → branch → PR).

### Sequencing

W1 first (it has a hard acceptance number), then W2, then W3. The link-side `clews_patch.py` and
the iteration controller land in ogclews-link in parallel; W1's file contract above is the
interface — if you need to change it, change it by talking to the link side, not unilaterally.

## 4. Preflight (mandatory before any solve)

Cross-env runs have silently executed stale code before. Before every solve during this work:
print branch + HEAD of MUIOGO, MUIOGO-AI, and ogclews-link; print what each interpreter actually
imports (`<venv-python> -c "import <pkg>; print(<pkg>.__file__)"`) and assert the path is under
the intended checkout; MUIOGO's interpreter resolves via `~/.venvs/muiogo` or
`$OGCLEWS_MUIOGO_PYTHON` (see `clews_driver.muiogo_python` — it fails loudly, never falls back).

## 5. Flags — things this brief could not verify

- MUIOGO's server was not started today; the 14 new upstream commits (OG setup UI) are untested
  locally.
- The `/updateData` read-merge path was verified against MUIOGO@main as of 2026-07-10
  (`Config.DATA_STORAGE` is `__file__`-relative; `DataFile(case)` + `generateDatafile` + `run`
  are session-free) — re-verify those line references against `ed4851d9` before building on them.
- The two CLEWs case-JSON defects (blank `clews_fuel`, collapsed discount path) are recorded
  from the June design pass; confirm they still reproduce on a fresh v9 case copy.
- MUIOGO-AI's pin (`928a13bb`) predates the OG UI work; whether its client/skills still pass
  against `ed4851d9` is unknown.
