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
    if args.cmd == "run":
        from functools import partial

        from . import framework, registry, runtime
        from .country import PHL
        from .manifest import write_run_manifest

        exp = experiments.get(args.experiment)
        cfg = runtime.RunnerConfig(num_workers=args.workers, show_progress=not args.no_progress)
        entry = registry.lookup(PHL)        # OG-model provenance for the manifest (and fail-fast)
        og_model = {"package": entry.og_package, "og_version": entry.og_version,
                    "ogcore_version": entry.ogcore_version, "env_python": entry.env_python}
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
