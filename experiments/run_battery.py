"""Continuable, grouped test battery for the OG-Core <-> CLEWS coupling.

Runs the model THE CANONICAL WAY -- `ogclews_link.runtime.build_baseline` -> `ogcore.execute.runner`,
the same Specifications + ogphl-SAM + runner flow as `OG-PHL/examples/run_og_phl_multi_industry.py`,
under the OG-PHL venv. Nothing hackish: the battery only orchestrates; the solve path is the user path.

Designed to run in SMALL GROUPS so you never leave it running long, and to be fully CONTINUABLE:
state is persisted after every item, so you can stop after any group and re-run to pick up where you
left off. SS items are fast; TPI items are minutes each (the real cost).

Usage (with the OG-PHL venv, from the repo root):
    .../OG-PHL/.venv/bin/python experiments/run_battery.py --status      # progress; runs nothing
    ...                                            run_battery.py --list                # show the plan
    ...                                            run_battery.py --next                # run next pending group
    ...                                            run_battery.py --group energy        # run one named group
    ...                                            run_battery.py --item energy_price_ss
    ...                                            run_battery.py --next --dry-run       # show, don't solve
    ...                                            run_battery.py --item X --rerun       # force re-run

State:  results/battery-state.json     Golden records:  results/golden.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE_PATH = os.path.join(REPO, "results", "battery-state.json")
OUT_ROOT = os.path.join(REPO, "ogclews_runs", "battery")

# --- the battery: ordered GROUPS of small item sets (matches docs/test-plan.md) ---------------
# item kinds:
#   experiment -> ogclews_link experiment name, solved SS or TPI via the canonical runtime
#   script     -> a standalone experiments/run_*.py (a user-facing run), checked by exit code
#   pytest     -> the unit/transform suite gate
#   baseline   -> build + solve the OG-PHL baseline only (no channel), SS or TPI
# `sign` is an INFORMATIONAL expectation (recorded for review), never a hard fail; the hard gate
# is convergence (no exception / exit 0). Magnitudes are reviewed against the golden record.
# TPI is the canonical mode (how a user runs these). SS is used ONLY where it is safe: the baseline,
# and the pure PARAM-SETTING channels (energy_price/investment/capital_intensity set p.tau_c/alpha_I/
# gamma pre-solve and read NO OG result arrays). Channels that READ the OG result dict assume TPI
# shapes and MUST run TPI, or they crash on the SS scalar/1-D dicts:
#   * forward (discount_rate, demand): og_sector_output -> Y_m[:, m]; og_interest_rate -> r[:10]
#   * clean_incidence: the c_min guard reads base_tpi["c_i"][:, i_e]
#   * carbon (recycle reads the base), health (demographic re-solve), full (contains forward)
GROUPS = [
    ("foundation", [
        {"id": "unit_suite", "kind": "pytest",   "target": "tests/", "note": "expect 77 pass / 1 skip"},
        {"id": "baseline",   "kind": "baseline",                     "note": "solve the shared baseline ONCE (TPI -> gives SS + TPI)"},
    ]),
    ("ss_smoke", [   # fast SS convergence/sign gate -- ONLY param-setting channels (no OG-result reads)
        {"id": "energy_price_ss",      "kind": "experiment", "target": "energy_price",     "mode": "SS", "sign": "converges"},
        {"id": "investment_ss",        "kind": "experiment", "target": "investment",       "mode": "SS", "sign": "converges"},
        {"id": "capital_intensity_ss", "kind": "experiment", "target": "capital_intensity","mode": "SS", "sign": "crowding-out"},
    ]),
    ("energy", [
        {"id": "energy_price",    "kind": "experiment", "target": "energy_price",    "mode": "TPI", "sign": "demand falls"},
        {"id": "clean_incidence", "kind": "experiment", "target": "clean_incidence", "mode": "TPI", "sign": "regressive incidence"},
        {"id": "routeB_costpush", "kind": "script", "target": "experiments/run_io_calibrated_energy_shock.py",
         "expect_stdout": "LOWERS GDP", "sign": "Route B lowers GDP"},
    ]),
    ("supply", [
        {"id": "investment",        "kind": "experiment", "target": "investment",       "mode": "TPI"},
        {"id": "capital_intensity", "kind": "experiment", "target": "capital_intensity","mode": "TPI", "sign": "crowding-out"},
        {"id": "carbon",            "kind": "experiment", "target": "carbon",           "mode": "TPI"},
        {"id": "crowding_out_solve","kind": "script", "target": "experiments/run_capital_intensity.py", "sign": "energy K up, other K down"},
        {"id": "energy_itc",        "kind": "script", "target": "experiments/run_energy_itc.py"},
    ]),
    ("forward", [   # OG->CLEWS emit; MUST be TPI (they read the result time series)
        {"id": "discount_rate", "kind": "experiment", "target": "discount_rate", "mode": "TPI", "sign": "emits DiscountRate path"},
        {"id": "demand",        "kind": "experiment", "target": "demand",        "mode": "TPI", "sign": "emits demand path (inert standalone)"},
    ]),
    ("health", [
        {"id": "health",               "kind": "experiment", "target": "health", "mode": "TPI", "sign": "deaths-added converges"},
        {"id": "health_bidirectional", "kind": "script", "target": "experiments/test_health_bidirectional.py", "sign": "both directions converge"},
    ]),
    ("combined", [
        {"id": "full",        "kind": "experiment", "target": "full", "mode": "TPI", "sign": "full coupled run"},
        {"id": "across_steps","kind": "script", "target": "experiments/run_across_steps.py", "sign": "layered marginal contributions"},
    ]),
]


def _all_items():
    return [(g, it) for g, items in GROUPS for it in items]


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)


# --- runners for each item kind --------------------------------------------------------------

def _stamp():
    # Date.now is unavailable in workflow scripts but this is a plain script; still avoid importing
    # time at module load. Use a coarse marker from the OS.
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")


# --- shared baseline: ONE baseline, solved ONCE, read from where OG saves it -----------------------
# The OG-PHL baseline is identical for every test (only the reform changes). Solve it ONCE at TPI into
# the standard baseline dir -- a TPI solve produces BOTH solutions, and OG-Core writes them as
# baseline/SS/SS_vars.pkl and baseline/TPI/TPI_vars.pkl. Every reform points baseline_dir at it and
# reads the baseline from disk (exactly how a user runs a reform); only the reform is solved. Already
# solved on disk -> skip the solve. No per-mode duplication, no parallel directory scheme.
_BASELINE: dict = {}   # in-process: holds {p, dir, rt}, built once per invocation


def _baseline_result(base_dir, mode):
    """Read the baseline solution OG saved on disk -- the SS slice for an SS reform, TPI for a TPI one."""
    from ogcore.utils import safe_read_pickle
    sub = ("TPI", "TPI_vars.pkl") if mode == "TPI" else ("SS", "SS_vars.pkl")
    return safe_read_pickle(os.path.join(base_dir, *sub))


def ensure_baseline():
    """Solve the OG-PHL baseline ONCE at TPI into the standard baseline dir (giving both the SS and the
    TPI solution), or skip the solve if it is already there. Returns (p_template, base_dir, runtime)."""
    if _BASELINE:
        return _BASELINE["p"], _BASELINE["dir"], _BASELINE["rt"]
    from ogclews_link.runtime import Runtime
    from ogclews_link.country import PHL

    base_dir = os.path.join(OUT_ROOT, "baseline")        # the standard OG baseline_dir; OG fills SS/ + TPI/
    rt = Runtime(show_progress=False)
    p, _ = rt.build_baseline(PHL, base_dir)              # the spec template the reforms deepcopy
    if not os.path.exists(os.path.join(base_dir, "TPI", "TPI_vars.pkl")):
        rt.solve(p, time_path=True)                      # solve ONCE at TPI -> writes SS_vars + TPI_vars
    _BASELINE.update(p=p, dir=base_dir, rt=rt)
    return p, base_dir, rt


def run_experiment(item) -> dict:
    """Apply the experiment's channels to a reform on the shared baseline and solve ONLY the reform;
    OG-Core reads the baseline from baseline_dir on disk -- exactly how a user runs a reform."""
    from ogclews_link.country import PHL
    from ogclews_link.framework import Runner
    from ogclews_link import experiments, golden

    mode = item.get("mode", "TPI")
    p, base_dir, rt = ensure_baseline()
    base = _baseline_result(base_dir, mode)              # the matching baseline solution, read from disk
    solve = (lambda pp: rt.solve(pp, time_path=(mode == "TPI")))
    runner = Runner(build_baseline=rt.build_baseline, solve=solve, apply_health=rt.apply_health_shock)
    exp = experiments.get(item["target"])
    ctx = runner.run(exp, PHL, out_root=os.path.join(OUT_ROOT, item["id"]),
                     prebuilt=(p, base, base_dir))       # reform points baseline_dir at the shared baseline
    rec = golden.from_context(item["id"], ctx)
    golden.save(rec)
    return {"status": "pass", "mode": mode, "reused_baseline": True,
            "pct_diff": rec.get("pct_diff", {}),
            "provenance": [pr.get("channel") for pr in getattr(ctx, "provenance", [])]}


def run_baseline(item) -> dict:
    """Establish the shared baseline (solve ONCE at TPI into the standard dir); capture its golden."""
    from ogclews_link import golden

    _p, base_dir, _rt = ensure_baseline()
    base = _baseline_result(base_dir, "TPI")
    golden.save(golden.capture(item["id"], base))
    return {"status": "pass", "base": golden.aggregates(base),
            "baseline_dir": os.path.relpath(base_dir, REPO)}


def run_script(item) -> dict:
    """Run a user-facing experiments/run_*.py with this interpreter; pass = exit 0 (and, if given,
    `expect_stdout` present)."""
    path = os.path.join(REPO, item["target"])
    proc = subprocess.run([sys.executable, path], cwd=REPO, capture_output=True, text=True)
    tail = "\n".join(proc.stdout.strip().splitlines()[-8:])
    ok = proc.returncode == 0
    exp = item.get("expect_stdout")
    if ok and exp and exp.lower() not in proc.stdout.lower():
        ok = False
    return {"status": "pass" if ok else "fail", "returncode": proc.returncode,
            "stdout_tail": tail, "stderr_tail": "\n".join(proc.stderr.strip().splitlines()[-5:])}


def run_pytest(item) -> dict:
    proc = subprocess.run([sys.executable, "-m", "pytest", item["target"], "-q"],
                          cwd=REPO, capture_output=True, text=True)
    return {"status": "pass" if proc.returncode == 0 else "fail", "returncode": proc.returncode,
            "stdout_tail": "\n".join(proc.stdout.strip().splitlines()[-3:])}


_DISPATCH = {"experiment": run_experiment, "baseline": run_baseline, "script": run_script, "pytest": run_pytest}


def run_item(item, dry=False) -> dict:
    if dry:
        return {"status": "would-run", "kind": item["kind"], "target": item.get("target"), "mode": item.get("mode")}
    try:
        res = _DISPATCH[item["kind"]](item)
    except Exception as exc:  # noqa: BLE001 -- record, never crash the battery
        import traceback
        res = {"status": "error", "error": f"{type(exc).__name__}: {exc}",
               "trace": traceback.format_exc().splitlines()[-4:]}
    return res


# --- selection + CLI -------------------------------------------------------------------------

def _pending(group_name, state):
    items = dict(GROUPS)[group_name]
    return [it for it in items if state.get(it["id"], {}).get("status") not in ("pass",)]


def next_group(state):
    for gname, _ in GROUPS:
        if _pending(gname, state):
            return gname
    return None


def cmd_status(state):
    print(f"Battery status  (state: {os.path.relpath(STATE_PATH, REPO)})")
    for gname, items in GROUPS:
        line = []
        for it in items:
            st = state.get(it["id"], {}).get("status", "·")
            mark = {"pass": "x", "fail": "!", "error": "E", "·": " "}.get(st, "?")
            line.append(f"[{mark}] {it['id']}")
        print(f"  {gname:11s}: " + "  ".join(line))
    nxt = next_group(state)
    print(f"\nnext pending group: {nxt or '(none — battery complete)'}")


def cmd_list():
    for gname, items in GROUPS:
        print(f"\n## {gname}")
        for it in items:
            extra = f" [{it.get('mode','')}]" if it.get("mode") else ""
            print(f"  {it['id']:24s} {it['kind']:10s} {it.get('target',''):46s}{extra}  {it.get('note', it.get('sign',''))}")


def run_items(items, state, dry):
    for it in items:
        print(f"\n>>> {it['id']}  ({it['kind']}{' '+it.get('mode','') if it.get('mode') else ''})"
              + ("  [DRY]" if dry else ""))
        res = run_item(it, dry=dry)
        print(f"    -> {res.get('status')}" + (f"  {res.get('error','')}" if res.get("status") == "error" else ""))
        if not dry:
            state[it["id"]] = {**res, "group": next(g for g, items2 in GROUPS if it in items2),
                               "kind": it["kind"], "finished": _stamp()}
            save_state(state)   # persist after EVERY item -> resumable
    return state


def main():
    ap = argparse.ArgumentParser(description="Continuable grouped test battery for the OG<->CLEWS coupling")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true", help="show progress, run nothing")
    g.add_argument("--list", action="store_true", help="list the full plan")
    g.add_argument("--next", action="store_true", help="run the next group with pending items")
    g.add_argument("--group", help="run a named group")
    g.add_argument("--item", help="run a single item by id")
    ap.add_argument("--dry-run", action="store_true", help="show what would run; no solves, no state change")
    ap.add_argument("--rerun", action="store_true", help="re-run even items already marked pass")
    args = ap.parse_args()

    state = load_state()
    if args.list:
        cmd_list(); return
    if args.status or not (args.next or args.group or args.item):
        cmd_status(state); return

    if args.item:
        it = next((it for _, items in GROUPS for it in items if it["id"] == args.item), None)
        if not it:
            print(f"unknown item '{args.item}'"); sys.exit(2)
        items = [it]
    elif args.group:
        if args.group not in dict(GROUPS):
            print(f"unknown group '{args.group}'; groups: {[g for g,_ in GROUPS]}"); sys.exit(2)
        items = dict(GROUPS)[args.group] if args.rerun else _pending(args.group, state)
    else:  # --next
        gname = next_group(state)
        if not gname:
            print("battery complete — nothing pending."); return
        print(f"running next pending group: {gname}")
        items = dict(GROUPS)[gname] if args.rerun else _pending(gname, state)

    if not items:
        print("nothing to run (all selected items already pass; use --rerun to force)."); return
    state = run_items(items, state, args.dry_run)
    if not args.dry_run:
        print()
        cmd_status(state)


if __name__ == "__main__":
    main()
