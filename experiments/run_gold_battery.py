"""Matched channel battery on the GOLD base — every channel alone, the composite legs, and the
TFP variant, ALL against the same GOLD_BASE/GOLD_PEP CLEWS inputs and the same shared OG baseline.

This is the run the papers wait on (§7.2, the short paper's wedge/carbon cells, the deck's
honesty slide): matched treatments make the coupled-vs-single gaps a true decomposition.

Mechanics are the canonical cross-env path copied from run_battery.py: the battery runs in the
LINK env, each OG solve runs in the OG model's own env via `ogclews_link.runtime`; the OG
baseline is exported ONCE and every reform reuses it. All items run TPI (matched treatments).

Differences from run_battery.py, all deliberate:
  * CLEWS inputs are pinned to the GOLD run dirs via $OGCLEWS_CLEWS_BASE/_REFORM (set below,
    before any ogclews_link import) — never the packaged demo scenario.
  * Records go to results/gold-battery.json, NEVER results/golden.json (the committed golden
    is the paper's cited v9 evidence record; this battery must not touch it).
  * Run ids are prefixed gold_ so nothing collides.
  * The land-carbon channel is ABSENT by blessing constraint: the conversion-carbon series is
    excluded, so no experiment here consumes land emissions. Where a land-carbon row would
    have appeared in the report, the generator states the exclusion.

GATE: run `experiments/run_v18_gold_coupled.sh --preflight-only` first — it verifies the full
stack (ogcore PR fingerprint, the two OG-PHL calibration PRs #63/#85, the 8-sector registry
calibration, the Anderson house rule, the blessed GOLD objectives). This driver re-checks only
import shadowing and the health fixes.

Usage (from the repo root, with the LINK venv):
    .venv/bin/python experiments/run_gold_battery.py --status
    .venv/bin/python experiments/run_gold_battery.py --list
    .venv/bin/python experiments/run_gold_battery.py --next [--dry-run]
    .venv/bin/python experiments/run_gold_battery.py --item gold_energy_price [--rerun]

State: results/gold-battery-state.json (persisted after every item -> stop/resume freely).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# --- pin the GOLD CLEWS inputs BEFORE any ogclews_link import (country.py reads the env) ------
def _gold_case_dir() -> str:
    r = subprocess.run(["muiogo-ai", "case-path", "--case", "Philippines_v18_GOLD"],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SystemExit("muiogo-ai case-path failed -- is the muiogo-ai world available?\n" + r.stderr)
    return r.stdout.strip()

_CASE = _gold_case_dir()
os.environ["OGCLEWS_CLEWS_BASE"] = os.path.join(_CASE, "res", "GOLD_BASE", "csv")
os.environ["OGCLEWS_CLEWS_REFORM"] = os.path.join(_CASE, "res", "GOLD_PEP", "csv")
for _d in (os.environ["OGCLEWS_CLEWS_BASE"], os.environ["OGCLEWS_CLEWS_REFORM"]):
    if not os.path.isdir(_d):
        raise SystemExit(f"GOLD CLEWS dir missing: {_d}")

# GUARD against import shadowing (same incident-driven pattern as run_battery.py).
sys.path.insert(0, REPO)
import ogclews_link  # noqa: E402

_RESOLVED = os.path.realpath(os.path.dirname(ogclews_link.__file__))
if not _RESOLVED.startswith(os.path.realpath(REPO) + os.sep):
    raise SystemExit(
        f"run_gold_battery: `import ogclews_link` resolved OUTSIDE this checkout:\n"
        f"  resolved: {_RESOLVED}\n  expected: under {REPO}\n"
        "Use this checkout's own venv, then re-run.")

# HEALTH-FIX GUARD: refuse to run on link code that predates the income_percentiles fixes.
with open(os.path.join(REPO, "ogclews_link", "health_pop.py")) as _f:
    if "income_percentiles" not in _f.read():
        raise SystemExit("health fixes absent from this checkout -- merge the ieem branch's "
                         "link fixes before running the battery (coordination log, 2026-08-14).")

STATE_PATH = os.path.join(REPO, "results", "gold-battery-state.json")
RECORD_PATH = os.path.join(REPO, "results", "gold-battery.json")
OUT_ROOT = os.path.join(REPO, "ogclews_runs_v18gold", "battery")

# --- the matched battery: all TPI, all on the same GOLD inputs + shared baseline --------------
# Groups ordered cheap-signal-first; the composite/coupled identity check is the payoff at the
# end (coupled == energy composite exactly held on v12; re-proving it on GOLD is the point).
GROUPS = [
    ("foundation", [
        {"id": "gold_baseline", "kind": "baseline", "note": "shared OG baseline, exported once (TPI)"},
    ]),
    ("energy", [   # the decomposition legs of the headline
        {"id": "gold_energy_price",    "target": "energy_price",    "note": "household wedge alone"},
        {"id": "gold_energy_cost_push","target": "energy_cost_push","note": "cost-push leg alone"},
        {"id": "gold_energy_full",     "target": "energy_full",     "note": "composite: wedge + cost-push"},
        {"id": "gold_energy_price_tfp","target": "energy_price_tfp","note": "structural TFP variant (sign test)"},
    ]),
    ("supply", [
        {"id": "gold_investment",        "target": "investment"},
        {"id": "gold_capital_intensity", "target": "capital_intensity"},
        {"id": "gold_energy_capex",      "target": "energy_capex"},
        {"id": "gold_carbon",            "target": "carbon", "note": "combustion CO2e only; land series excluded (blessing)"},
    ]),
    ("household", [
        {"id": "gold_clean_incidence", "target": "clean_incidence"},
        {"id": "gold_health",          "target": "health", "note": "post-fix health channel (income_percentiles)"},
    ]),
    ("forward", [
        {"id": "gold_discount_rate", "target": "discount_rate"},
        {"id": "gold_demand",        "target": "demand"},
        {"id": "gold_forward",       "target": "forward"},
    ]),
    ("real", [
        {"id": "gold_coupled", "target": "coupled",
         "note": "the headline pair again, through the battery path -- identity check vs energy_full"},
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


def _stamp():
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")


_BASELINE: dict = {}


def _runner_cfg(rebuild=False):
    from ogclews_link import runtime
    return runtime.RunnerConfig(num_workers=7, show_progress=False, ss=False, rebuild=rebuild)


def ensure_baseline(rebuild=False):
    if _BASELINE:
        return _BASELINE
    from ogclews_link import runtime
    from ogclews_link.country import PHL

    template, base_tpi, base_dir, arrays = runtime.export_baseline(
        PHL, OUT_ROOT, cfg=_runner_cfg(rebuild=rebuild))
    _BASELINE.update(template=template, base_tpi=base_tpi, dir=base_dir, arrays=arrays)
    return _BASELINE


def run_baseline(item) -> dict:
    from ogclews_link import golden
    bl = ensure_baseline()
    golden.save(golden.capture(item["id"], bl["base_tpi"]), path=RECORD_PATH)
    return {"status": "pass", "base": golden.aggregates(bl["base_tpi"]),
            "baseline_dir": os.path.relpath(bl["dir"], REPO)}


def run_experiment(item) -> dict:
    from functools import partial

    from ogclews_link import experiments, framework, golden, runtime, serde
    from ogclews_link.country import PHL

    bl = ensure_baseline()
    base = serde.load_solution(os.path.join(bl["dir"], "baseline_solution.npz"))
    exp = experiments.get(item["target"])
    ctx = framework.run(exp, PHL, solve_reform=partial(runtime.solve_reform, cfg=_runner_cfg()),
                        out_root=os.path.join(OUT_ROOT, item["id"]),
                        prebuilt=(bl["template"], base, bl["dir"], bl["arrays"]))
    try:
        from ogclews_link import registry
        from ogclews_link.manifest import write_run_manifest
        entry = registry.lookup(PHL)
        run_dir = os.path.join(OUT_ROOT, item["id"], getattr(exp, "__name__", item["id"]))
        write_run_manifest(run_dir, exp, PHL, ctx, baseline_dir=bl["dir"],
                           gbd_csv=getattr(PHL, "gbd_burden_csv", None),
                           og_model={"repo": entry.key, "package": entry.package,
                                     "version": entry.version, "env_python": entry.env_python})
    except Exception as e:  # noqa: BLE001 -- provenance is a nicety; never fail the solve for it
        print(f"(manifest skipped for {item['id']}: {type(e).__name__}: {e})")
    rec = golden.from_context(item["id"], ctx)
    golden.save(rec, path=RECORD_PATH)
    return {"status": "pass", "pct_diff": rec.get("pct_diff", {}),
            "provenance": [pr.get("channel") for pr in getattr(ctx, "provenance", [])]}


def run_item(item, dry=False) -> dict:
    if dry:
        return {"status": "would-run", "target": item.get("target", "(baseline)")}
    try:
        if item.get("kind") == "baseline":
            return run_baseline(item)
        return run_experiment(item)
    except Exception as exc:  # noqa: BLE001 -- record, never crash the battery
        import traceback
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}".splitlines()[0][:300],
                "trace": traceback.format_exc().splitlines()[-4:]}


def _pending(group_name, state):
    return [it for it in dict(GROUPS)[group_name]
            if state.get(it["id"], {}).get("status") not in ("pass",)]


def next_group(state):
    for gname, _ in GROUPS:
        if _pending(gname, state):
            return gname
    return None


def cmd_status(state):
    print(f"GOLD battery status  (state: {os.path.relpath(STATE_PATH, REPO)})")
    print(f"  CLEWS base:   {os.environ['OGCLEWS_CLEWS_BASE']}")
    print(f"  CLEWS reform: {os.environ['OGCLEWS_CLEWS_REFORM']}")
    for gname, items in GROUPS:
        line = []
        for it in items:
            st = state.get(it["id"], {}).get("status", "·")
            mark = {"pass": "x", "fail": "!", "error": "E", "·": " "}.get(st, "?")
            line.append(f"[{mark}] {it['id']}")
        print(f"  {gname:11s}: " + "  ".join(line))
    print(f"\nnext pending group: {next_group(state) or '(none — battery complete)'}")


def run_items(items, state, dry):
    import time
    for it in items:
        print(f"\n>>> {it['id']}" + ("  [DRY]" if dry else ""))
        started, t0 = _stamp(), time.time()
        res = run_item(it, dry=dry)
        dur = time.time() - t0
        print(f"    -> {res.get('status')}" + ("" if dry else f"  ({round(dur)}s)"))
        if res.get("status") == "error":
            print(f"       error: {res.get('error')}")
        if not dry:
            state[it["id"]] = {**res, "started": started, "finished": _stamp(),
                               "duration_s": round(dur, 1)}
            save_state(state)
    return state


def main():
    ap = argparse.ArgumentParser(description="Matched channel battery on the GOLD base")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true")
    g.add_argument("--list", action="store_true")
    g.add_argument("--next", action="store_true")
    g.add_argument("--group")
    g.add_argument("--item")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rerun", action="store_true")
    args = ap.parse_args()

    state = load_state()
    if args.list:
        for gname, items in GROUPS:
            print(f"\n## {gname}")
            for it in items:
                print(f"  {it['id']:26s} {it.get('target','(baseline)'):20s} {it.get('note','')}")
        return
    if args.status or not (args.next or args.group or args.item):
        cmd_status(state); return

    if args.item:
        it = next((it for _, items in GROUPS for it in items if it["id"] == args.item), None)
        if not it:
            print(f"unknown item '{args.item}'"); sys.exit(2)
        items = [it]
    elif args.group:
        if args.group not in dict(GROUPS):
            print(f"unknown group '{args.group}'; groups: {[g for g, _ in GROUPS]}"); sys.exit(2)
        items = dict(GROUPS)[args.group] if args.rerun else _pending(args.group, state)
    else:
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
