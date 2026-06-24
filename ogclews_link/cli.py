"""Command-line runner: the management surface for the channel framework.

  python -m ogclews_link list                 # named experiments
  python -m ogclews_link channels             # the channel functions + direction
  python -m ogclews_link run clean_incidence  # build baseline, apply channels, solve, report
  python -m ogclews_link run coupled --out ./runs
"""
from __future__ import annotations

import argparse

from . import clews_io, experiments  # noqa: F401
from .report import print_report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ogclews_link")
    sub = ap.add_subparsers(dest="cmd")

    rp = sub.add_parser("run", help="run a named experiment")
    rp.add_argument("experiment")
    rp.add_argument("--workers", type=int, default=7, help="OG-Core J-loop worker processes (use multiprocess; avoid 1)")
    rp.add_argument("--out", default="./ogclews_runs")
    rp.add_argument("--no-progress", action="store_true")
    rp.add_argument("--clews-run", default=None,
                    help="source CLEWS/MUIOGO run dir to record in the run manifest (provenance; "
                         "scenario-source override is future work)")

    sub.add_parser("list", help="list named experiments")
    sub.add_parser("channels", help="list registered channels")

    mp = sub.add_parser("models", help="manage the installed OG-model register")
    msub = mp.add_subparsers(dest="models_cmd")
    mr = msub.add_parser("register", help="record an installed OG model by its checkout dir")
    mr.add_argument("--path", required=True, help="the OG model's checkout dir (must contain .venv/)")
    mr.add_argument("--key", default=None, help="repo key (default: the dir name, e.g. OG-PHL -> og-phl)")
    mr.add_argument("--calibration", default=None,
                    help="multisector param file to use (default: auto-pick the lone couplable one, "
                         "else single-industry)")
    mr.add_argument("--no-discovery", action="store_true",
                    help="skip calibration discovery (record single-industry unless --calibration given)")
    mr.add_argument("--registry", default=None, help="register file to write (default: $OGCLEWS_MODEL_REGISTRY or ./og_model_registry.json)")
    mc = msub.add_parser("calibrations", help="show a registered model's calibration choices (no solve)")
    mc.add_argument("model", help="repo key / package / country (e.g. og-phl)")
    mc.add_argument("--refresh", action="store_true",
                    help="re-read the package source (cheap) and update the saved status")
    mc.add_argument("--registry", default=None)
    ml = msub.add_parser("list", help="list registered OG models")
    ml.add_argument("--registry", default=None)

    args = ap.parse_args(argv)

    if args.cmd == "list":
        import inspect
        for n in experiments.names():
            doc = (inspect.getdoc(experiments.get(n)) or "").splitlines()
            print(f"{n:16} {doc[0] if doc else ''}")
        return
    if args.cmd == "channels":
        import inspect

        from . import channels
        for name in (n for n in dir(channels) if not n.startswith("_")):
            fn = getattr(channels, name)
            if not (callable(fn) and getattr(fn, "__module__", "") == channels.__name__):
                continue
            direction = "og->clews" if name.startswith("emit_") else "clews->og / policy"
            doc = (inspect.getdoc(fn) or "").splitlines()
            print(f"{name:20} {direction:18} {doc[0] if doc else ''}")
        return
    if args.cmd == "models":
        from . import discovery, models
        if args.models_cmd == "register":
            rec = models.register(args.path, key=args.key, registry_file=args.registry,
                                  calibration=args.calibration, run_discovery=not args.no_discovery)
            print(f"registered {rec['key']} ({rec['package']} {rec['version'] or '?'}) -> {rec['env_python']}")
            cal = rec.get("calibration")
            print(f"  calibration: {cal if cal else '(single-industry -- energy channels skip)'}")
            if rec.get("findings"):
                discovery.print_calibrations(rec["findings"], print)
            print(f"  written to {rec['registry']}")
        elif args.models_cmd == "calibrations":
            findings = models.calibrations(args.model, args.registry, refresh=args.refresh)
            if findings is None:
                print(f"no calibration status for {args.model} (not discovered and no source on disk)")
            else:
                if findings.get("discovered_at") and not args.refresh:
                    print(f"  (saved status from {findings['discovered_at']}; --refresh to re-read)")
                discovery.print_calibrations(findings, print)
        elif args.models_cmd == "list":
            rows = models.list_models(args.registry)
            if not rows:
                print("no OG models registered (run: ogclews-link models register --path <dir>)")
            for key, pkg, ver, cal, cc, ok in rows:
                coup = "" if cc is None else f" couplable={cc}"
                print(f"  [{'x' if ok else ' '}] {key:10} {pkg:12} {ver or '?':8} "
                      f"calib={cal or 'single-industry'}{coup}" + ("" if ok else "  (interpreter missing)"))
        else:
            mp.print_help()
        return
    if args.cmd == "run":
        from functools import partial

        from . import framework, registry, runtime
        from .country import PHL
        from .manifest import write_run_manifest

        exp = experiments.get(args.experiment)
        cfg = runtime.RunnerConfig(num_workers=args.workers, show_progress=not args.no_progress)
        entry = registry.lookup(PHL)        # OG-model provenance for the manifest (and fail-fast)
        og_model = {"repo": entry.key, "package": entry.package, "version": entry.version,
                    "env_python": entry.env_python}
        ctx = framework.run(
            exp, PHL,
            export_baseline=partial(runtime.export_baseline, cfg=cfg),
            solve_reform=partial(runtime.solve_reform, cfg=cfg),
            out_root=args.out)
        print_report(ctx)
        if ctx.clews_inputs:
            written = clews_io.write_all(ctx, f"{args.out}/{args.experiment}/clews_inputs")
            print("Wrote CLEWS inputs:", written)
        manifest = write_run_manifest(f"{args.out}/{args.experiment}", exp, PHL, ctx,
                                      clews_run=args.clews_run, og_model=og_model)
        print("Wrote run manifest:", manifest)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
