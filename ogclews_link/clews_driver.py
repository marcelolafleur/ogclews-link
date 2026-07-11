"""The CLEWS re-run seam: write parameter changes into a COPY of a MUIOGO case, trigger MUIOGO's own
datafile-generation + solve for a caserun, and hand the result csv dir back to the link's readers.

This is the missing consumer of the ``emit_*`` channels' artifacts and the prerequisite for testing any
og->clews idea empirically (exploration lane, idea #01). Design rules, in order of importance:

  * NEVER mutate a live case: every patch lands in a copy made by :func:`copy_case`.
  * Cross-env by construction (the og_runner idiom mirrored at the CLEWS side): the solve subprocess
    runs MUIOGO's OWN interpreter and MUIOGO's OWN pipeline (``DataFile.generateDatafile`` +
    ``DataFile.run`` -- the exact code behind its ``/run`` route), so the link never re-implements
    datafile generation, scenario merging, or solver invocation, and no MUIOGO dependency enters the
    link env.
  * Cases address parameters by OPAQUE per-case ids (``COM_*``/``TEC_*``/``EMI_*``); the patchers
    translate commodity/technology/emission CODES through the case's own ``genData.json`` registry and
    fail loudly (listing what exists) on a miss.
  * Every function returns provenance -- what was touched, before/after -- for the run manifest.

Verified mechanics (MUIOGO@main, read 2026-07-10): ``Config.DATA_STORAGE`` is ``__file__``-relative
(``API/Classes/Base/Config.py:57-62``: repo/WebAPP/DataStorage), so no cwd games are needed; a caserun
is defined by its record in ``view/resData.json`` + its ``res/<caserun>/`` dir; ``DataFile(case)``
+ ``generateDatafile(caserun)`` + ``run(solver, caserun)`` are session-free and write
``res/<caserun>/csv/`` (``DataFileClass.py:625,2070``).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

__all__ = ["muiogo_python", "copy_case", "scale_annual_demand", "run_caserun", "case_registry"]


# --- environment resolution -------------------------------------------------------

def muiogo_python(override: str | None = None) -> str:
    """MUIOGO's own interpreter: ``override`` arg > $OGCLEWS_MUIOGO_PYTHON > the setup_dev default
    (~/.venvs/muiogo, bin/ or Scripts/). Fails loudly with the fix, never falls back silently."""
    cands = [override, os.environ.get("OGCLEWS_MUIOGO_PYTHON")]
    root = Path.home() / ".venvs" / "muiogo"
    cands += [str(root / "bin" / "python"), str(root / "Scripts" / "python.exe")]
    for c in cands:
        if c and Path(c).is_file():
            return str(c)
    raise FileNotFoundError(
        "MUIOGO interpreter not found. Run MUIOGO's scripts/setup_dev.py (default venv "
        "~/.venvs/muiogo) or set $OGCLEWS_MUIOGO_PYTHON to its python.")


def _api_dir(muiogo_home: str) -> str:
    api = Path(muiogo_home) / "API"
    if not (api / "Classes" / "Case" / "DataFileClass.py").is_file():
        raise FileNotFoundError(
            f"{api} does not look like a MUIOGO API dir (no Classes/Case/DataFileClass.py); "
            "check $OGCLEWS_MUIOGO_HOME / the ../MUIOGO sibling.")
    return str(api)


# --- case copy + registry ----------------------------------------------------------

def copy_case(data_storage: str, src_case: str, dst_case: str, *, overwrite: bool = False) -> str:
    """Copy a MUIOGO case dir inside its DataStorage (the unit MUIOGO addresses by name) and stamp the
    copy's ``genData.json`` ``osy-casename``. The copy carries the caserun records (view/resData.json)
    and prior results, so an existing caserun can be re-generated + re-run in the copy as-is."""
    src = Path(data_storage) / src_case
    dst = Path(data_storage) / dst_case
    if not (src / "genData.json").is_file():
        raise FileNotFoundError(f"{src} is not a MUIOGO case (no genData.json)")
    if dst.exists():
        if not overwrite:
            raise FileExistsError(f"{dst} already exists; pass overwrite=True to replace it")
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    gd_path = dst / "genData.json"
    gd = json.loads(gd_path.read_text())
    gd["osy-casename"] = dst_case
    gd_path.write_text(json.dumps(gd))
    return str(dst)


def case_registry(case_dir: str) -> dict:
    """The case's code->opaque-id registries from genData.json:
    ``{"comm": {code: COM_*}, "tech": {code: TEC_*}, "emis": {code: EMI_*}, "scenarios": [...]}``."""
    gd = json.loads((Path(case_dir) / "genData.json").read_text())
    return {
        "comm": {c["Comm"]: c["CommId"] for c in gd.get("osy-comm", [])},
        "tech": {t["Tech"]: t["TechId"] for t in gd.get("osy-tech", [])},
        "emis": {e["Emis"]: e["EmisId"] for e in gd.get("osy-emis", [])},
        "scenarios": [s["ScenarioId"] for s in gd.get("osy-scenarios", [])],
    }


def _lookup(registry: dict, kind: str, code: str) -> str:
    table = registry[kind]
    if code not in table:
        raise KeyError(f"{kind} code {code!r} not in this case; present: {sorted(table)[:20]}"
                       f"{' ...' if len(table) > 20 else ''}")
    return table[code]


# --- parameter patchers ------------------------------------------------------------

def scale_annual_demand(case_dir: str, commodity: str, factor, *, scenario: str = "SC_0",
                        param: str = "SAD", group_file: str = "RYC.json") -> dict:
    """Scale a commodity's SpecifiedAnnualDemand (``SAD`` in ``RYC.json``; pass ``param="AAD"`` for
    AccumulatedAnnualDemand) in ONE scenario of a case COPY. ``factor`` is a scalar applied to every
    year, or a ``{year(str|int): factor}`` map for a per-year path (years absent from the map keep
    their value -- emit a full map for a full path). Returns provenance (rows/years touched,
    before/after sums). Fails loudly on an unknown commodity/scenario/param."""
    case = Path(case_dir)
    reg = case_registry(case_dir)
    comm_id = _lookup(reg, "comm", commodity)
    if scenario not in reg["scenarios"]:
        raise KeyError(f"scenario {scenario!r} not in this case; present: {reg['scenarios']}")
    gpath = case / group_file
    data = json.loads(gpath.read_text())
    if param not in data:
        raise KeyError(f"param {param!r} not in {group_file}; present: {sorted(data)}")
    rows = data[param].get(scenario)
    if rows is None:
        raise KeyError(f"{param} has no scenario {scenario!r}; present: {sorted(data[param])}")
    fmap = None if not isinstance(factor, dict) else {str(k): float(v) for k, v in factor.items()}
    touched, before_sum, after_sum = 0, 0.0, 0.0
    for row in rows:
        if row.get("CommId") != comm_id:
            continue
        for key, val in list(row.items()):
            if not key.isdigit():
                continue
            f = float(factor) if fmap is None else fmap.get(key)
            if f is None or val in (None, ""):
                continue
            before_sum += float(val)
            row[key] = float(val) * f
            after_sum += row[key]
        touched += 1
    if touched == 0:
        raise KeyError(f"{param}[{scenario}] has no row for {commodity} ({comm_id}); "
                       "the commodity has no demand rows in this scenario")
    if before_sum == 0.0:
        # Scaling an all-zero demand row is a SILENT NO-OP downstream (the solve is unchanged) --
        # the demanded commodity is usually a sibling code (e.g. PHL_HOU_ELE carries 0 while the
        # final-demand PHL_HOU_ELEF carries the load). Fail loudly instead of "succeeding".
        others = [r["CommId"] for r in rows
                  if any(k.isdigit() and r[k] not in (0, None, "") for k in r)]
        rev = {v: k for k, v in reg["comm"].items()}
        raise ValueError(
            f"{param}[{scenario}] rows for {commodity} ({comm_id}) are ALL ZERO -- scaling them "
            f"changes nothing. Commodities with nonzero {param} here: "
            f"{sorted(rev.get(c, c) for c in others)[:12]}")
    gpath.write_text(json.dumps(data))
    return {"param": param, "scenario": scenario, "commodity": commodity, "comm_id": comm_id,
            "rows": touched, "sum_before": before_sum, "sum_after": after_sum,
            "mean_factor": (after_sum / before_sum) if before_sum else None}


# --- the solve subprocess -----------------------------------------------------------

# Runs INSIDE MUIOGO's interpreter with sys.path rooted at <MUIOGO>/API (its own import style:
# `from Classes...`). Prints one JSON line to stdout as the LAST line (the parent parses the tail,
# so MUIOGO's own prints/logs above it are harmless).
_EXEC = r"""
import json, sys, time
api_dir, case, caserun, solver = sys.argv[1:5]
sys.path.insert(0, api_dir)
t0 = time.time()
try:
    from Classes.Case.DataFileClass import DataFile
    df = DataFile(case)
    df.generateDatafile(caserun)
    df.run(solver, caserun)
    out = {"ok": True, "case": case, "caserun": caserun, "solver": solver,
           "elapsed_s": round(time.time() - t0, 1)}
except Exception as e:  # noqa: BLE001 -- the parent needs the failure as data
    out = {"ok": False, "case": case, "caserun": caserun, "solver": solver,
           "error": f"{type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 1)}
print(json.dumps(out))
sys.exit(0 if out["ok"] else 3)
"""


def run_caserun(case: str, caserun: str, *, solver: str = "CBC", muiogo_home: str | None = None,
                python: str | None = None, timeout: int = 3600) -> dict:
    """Generate the datafile and solve one caserun of ``case`` via MUIOGO's own pipeline, in MUIOGO's
    own interpreter. Returns provenance including ``csv_dir`` (the result CSVs the link's readers
    consume). Raises RuntimeError with MUIOGO's own error text on a failed run."""
    from .country import _muiogo_home  # the link's existing MUIOGO-home resolution

    home = muiogo_home or _muiogo_home()
    if not home:
        raise FileNotFoundError("MUIOGO home not found: set $OGCLEWS_MUIOGO_HOME or place MUIOGO "
                                "as a sibling ../MUIOGO.")
    api = _api_dir(home)
    py = muiogo_python(python)
    # Own process GROUP + kill the group on timeout: MUIOGO's pipeline spawns the solver (CBC/glpsol)
    # as a grandchild, which subprocess.run's own timeout-kill would ORPHAN at 100% CPU (observed live:
    # a pathological LP left cbc grinding for an hour after the python child died).
    proc = subprocess.Popen([py, "-c", _EXEC, api, case, caserun, solver],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), 15)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), 9)
        raise RuntimeError(
            f"MUIOGO run timed out after {timeout}s (case={case}, caserun={caserun}, solver={solver}); "
            "the solver process group was killed. A healthy v9 solve is ~minutes -- a large overrun "
            "usually means the patch made the LP pathological (e.g. demand scaled in CALIBRATED "
            "HISTORICAL years against fixed capacity); patch the exchange window only.")
    proc = subprocess.CompletedProcess(proc.args, proc.returncode, out, err)
    tail = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    status = None
    for ln in reversed(tail):
        try:
            status = json.loads(ln)
            break
        except json.JSONDecodeError:
            continue
    if status is None:
        raise RuntimeError(f"MUIOGO run produced no status line (exit {proc.returncode}). "
                           f"stdout tail: {tail[-3:]}; stderr tail: {proc.stderr.strip().splitlines()[-3:]}")
    if not status.get("ok"):
        raise RuntimeError(f"MUIOGO run failed: {status.get('error')} "
                           f"(case={case}, caserun={caserun}, solver={solver})")
    csv_dir = Path(home) / "WebAPP" / "DataStorage" / case / "res" / caserun / "csv"
    if not csv_dir.is_dir():
        raise RuntimeError(f"MUIOGO reported success but {csv_dir} does not exist -- "
                           "result layout changed?")
    status["csv_dir"] = str(csv_dir)
    status["muiogo_python"] = py
    return status
