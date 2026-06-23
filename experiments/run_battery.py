"""Continuable, grouped test battery for the OG-Core <-> CLEWS coupling.

Runs the model THE CANONICAL (cross-env) WAY -- `ogclews_link.runtime.export_baseline` /
`solve_reform`, which subprocess the country's OG model in ITS OWN environment (per the model registry)
and exchange data files. This is exactly the path `ogclews-link run <exp>` uses, so the battery runs in
the LINK env and the OG solve runs in the OG-PHL env -- no shared interpreter, nothing hackish.

Designed to run in SMALL GROUPS so you never leave it running long, and to be fully CONTINUABLE:
state is persisted after every item, so you can stop after any group and re-run to pick up where you
left off. SS items are fast; TPI items are minutes each (the real cost).

Usage (with the LINK venv, from the repo root):
    .../ogclews-link/.venv/bin/python experiments/run_battery.py --status      # progress; runs nothing
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
        {"id": "unit_suite", "kind": "pytest",   "target": "tests/", "note": "expect 79 pass / 1 skip"},
        {"id": "baseline",   "kind": "baseline",                     "note": "solve the shared baseline ONCE (TPI -> gives SS + TPI)"},
    ]),
    ("ss_smoke", [   # fast SS convergence/sign gate -- ONLY param-setting channels (no OG-result reads)
        {"id": "energy_price_ss",      "kind": "experiment", "target": "energy_price",     "mode": "SS", "sign": "converges"},
        {"id": "investment_ss",        "kind": "experiment", "target": "investment",       "mode": "SS", "sign": "converges"},
        {"id": "capital_intensity_ss", "kind": "experiment", "target": "capital_intensity","mode": "SS", "sign": "factor-share: energy price down, energy K down"},
    ]),
    ("energy", [
        {"id": "energy_price",    "kind": "experiment", "target": "energy_price",    "mode": "TPI", "sign": "demand falls"},
        {"id": "clean_incidence", "kind": "experiment", "target": "clean_incidence", "mode": "TPI", "sign": "regressive incidence"},
        {"id": "routeB_costpush", "kind": "script", "env": "og", "target": "experiments/run_io_calibrated_energy_shock.py",
         "expect_stdout": "LOWERS GDP", "sign": "Route B lowers GDP"},
    ]),
    ("supply", [
        {"id": "investment",        "kind": "experiment", "target": "investment",       "mode": "TPI"},
        {"id": "capital_intensity", "kind": "experiment", "target": "capital_intensity","mode": "TPI", "sign": "factor-share: energy price down, energy K down"},
        {"id": "carbon",            "kind": "experiment", "target": "carbon",           "mode": "TPI"},
        {"id": "crowding_out_solve","kind": "script", "env": "og", "target": "experiments/run_capital_intensity.py", "sign": "energy price -24%, energy K -14% (factor-share, NOT crowding-out)"},
        {"id": "energy_itc",        "kind": "script", "env": "og", "target": "experiments/run_energy_itc.py"},
    ]),
    ("forward", [   # OG->CLEWS emit; MUST be TPI (they read the result time series)
        {"id": "discount_rate", "kind": "experiment", "target": "discount_rate", "mode": "TPI", "sign": "emits DiscountRate path"},
        {"id": "demand",        "kind": "experiment", "target": "demand",        "mode": "TPI", "sign": "emits demand path (inert standalone)"},
    ]),
    ("health", [
        {"id": "health",               "kind": "experiment", "target": "health", "mode": "TPI", "sign": "deaths-added converges"},
        {"id": "health_bidirectional", "kind": "script", "env": "og", "target": "experiments/test_health_bidirectional.py", "sign": "both directions converge"},
    ]),
    ("combined", [
        {"id": "across_steps","kind": "script", "env": "og", "target": "experiments/run_across_steps.py", "sign": "layered marginal contributions"},
    ]),
    ("real", [   # the full coupled run: CLEWS cost-of-electricity index energy price + GBD ambient-PM2.5 health
        {"id": "coupled", "kind": "experiment", "target": "coupled", "mode": "TPI",
         "sign": "coupled run: cheaper power (-3.8%) + real PM2.5 deaths (~44k)"},
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


# --- shared baseline: ONE baseline, exported ONCE, reused across every reform ----------------------
# The OG-PHL baseline is identical for every test (only the reform changes). Export it ONCE at TPI via
# the cross-env runner (which solves it in the OG env -- a TPI solve produces BOTH the SS and TPI
# solution, written to the content-addressed cache as baseline_solution.npz / baseline_solution_ss.npz
# plus the OG-side baseline_p.pkl + SS/ + TPI/ dirs the reform subprocess reads). Every reform reuses
# the cache (prebuilt) and only the reform is solved. Already exported -> skip. SS-mode items compare
# against the SS baseline slice; TPI items against the TPI baseline.
_BASELINE: dict = {}   # in-process: holds {template, base_tpi, dir, arrays}, built once per invocation


def _runner_cfg(ss=False):
    from ogclews_link import runtime
    return runtime.RunnerConfig(num_workers=7, show_progress=False, ss=ss)


def ensure_baseline():
    """Export the OG-PHL baseline ONCE at TPI (giving both the SS and the TPI baseline solution) via the
    cross-env runner, or reuse the cache if already exported. Returns the _BASELINE bundle dict."""
    if _BASELINE:
        return _BASELINE
    from ogclews_link import runtime
    from ogclews_link.country import PHL

    template, base_tpi, base_dir, arrays = runtime.export_baseline(PHL, OUT_ROOT, cfg=_runner_cfg(ss=False))
    _BASELINE.update(template=template, base_tpi=base_tpi, dir=base_dir, arrays=arrays)
    return _BASELINE


def _baseline_solution(base_dir, mode):
    """The matching baseline solution npz -- the SS slice for an SS reform, TPI for a TPI one."""
    from ogclews_link import serde
    name = "baseline_solution.npz" if mode == "TPI" else "baseline_solution_ss.npz"
    return serde.load_solution(os.path.join(base_dir, name))


def run_experiment(item) -> dict:
    """Apply the experiment's channels to a fresh reform on the shared baseline and solve ONLY the reform
    -- the OG runner reads the baseline from the cache dir, exactly how `ogclews-link run` works."""
    from functools import partial

    from ogclews_link import experiments, framework, golden, runtime
    from ogclews_link.country import PHL

    mode = item.get("mode", "TPI")
    bl = ensure_baseline()
    base = _baseline_solution(bl["dir"], mode)
    cfg = _runner_cfg(ss=(mode == "SS"))
    exp = experiments.get(item["target"])
    ctx = framework.run(exp, PHL, solve_reform=partial(runtime.solve_reform, cfg=cfg),
                        out_root=os.path.join(OUT_ROOT, item["id"]),
                        prebuilt=(bl["template"], base, bl["dir"], bl["arrays"]))
    rec = golden.from_context(item["id"], ctx)
    golden.save(rec)
    return {"status": "pass", "mode": mode, "reused_baseline": True,
            "pct_diff": rec.get("pct_diff", {}),
            "provenance": [pr.get("channel") for pr in getattr(ctx, "provenance", [])]}


def run_baseline(item) -> dict:
    """Establish the shared baseline (export ONCE at TPI via the cross-env runner); capture its golden."""
    from ogclews_link import golden

    bl = ensure_baseline()
    golden.save(golden.capture(item["id"], bl["base_tpi"]))
    return {"status": "pass", "base": golden.aggregates(bl["base_tpi"]),
            "baseline_dir": os.path.relpath(bl["dir"], REPO)}


def _og_env_python():
    from ogclews_link import registry
    from ogclews_link.country import PHL
    return registry.lookup(PHL).env_python


def run_script(item) -> dict:
    """Run a user-facing experiments/run_*.py; pass = exit 0 (and, if given, `expect_stdout` present).
    `env: "og"` items import ogcore directly, so they run under the OG model's interpreter with the link
    source on PYTHONPATH (ogcore from the OG env, ogclews_link pure-py from here) -- exactly the runner's
    own invocation contract. Other items run under this (link) interpreter."""
    path = os.path.join(REPO, item["target"])
    if item.get("env") == "og":
        sub_env = dict(os.environ)
        sub_env["PYTHONPATH"] = REPO + (os.pathsep + sub_env["PYTHONPATH"] if sub_env.get("PYTHONPATH") else "")
        proc = subprocess.run([_og_env_python(), path], cwd=REPO, capture_output=True, text=True, env=sub_env)
    else:
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
