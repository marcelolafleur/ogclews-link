"""Command-line runner: the management surface for the channel framework.

  python -m ogclews_link list                 # named experiments
  python -m ogclews_link channels             # registered channels + direction/theory status
  python -m ogclews_link run energy_price     # build baseline, apply channels, solve, report
  python -m ogclews_link run transition_package --workers 1 --out ./runs
"""
from __future__ import annotations

import argparse

from . import channels, clews_io, experiments  # noqa: F401 (channels import registers them)
from .framework import all_channels
from .report import print_report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ogclews_link")
    sub = ap.add_subparsers(dest="cmd")

    rp = sub.add_parser("run", help="run a named experiment")
    rp.add_argument("experiment")
    rp.add_argument("--workers", type=int, default=7, help="OG-Core J-loop worker processes (use multiprocess; avoid 1)")
    rp.add_argument("--passes", type=int, default=1,
                    help="1 = one-way, take CLEWS as given (default); >1 = multi-pass iterate to a fixed point "
                         "(needs the CLEWS-runner hook; degrades to one pass without it)")
    rp.add_argument("--out", default="./ogclews_runs")
    rp.add_argument("--no-progress", action="store_true")
    rp.add_argument("--clews-run", default=None,
                    help="source CLEWS/MUIOGO run dir to record in the run manifest (provenance; "
                         "scenario-source override is future work)")

    sub.add_parser("list", help="list named experiments")
    sub.add_parser("channels", help="list registered channels")

    args = ap.parse_args(argv)

    if args.cmd == "list":
        for n in experiments.names():
            print(f"{n:16} {experiments.get(n).description}")
        return
    if args.cmd == "channels":
        for cid, ch in all_channels().items():
            print(f"{cid:14} {ch.direction:10} {ch.theory_status:16} {ch.label}")
        return
    if args.cmd == "run":
        from .country import PHL
        from .manifest import write_run_manifest
        from .runtime import Runtime

        exp = experiments.get(args.experiment)
        rt = Runtime(show_progress=not args.no_progress)
        if args.workers is not None:
            rt.num_workers = args.workers
        ctx = rt.runner_for(PHL).run(exp, PHL, out_root=args.out, max_passes=args.passes)
        print_report(ctx)
        if ctx.clews_inputs:
            written = clews_io.write_all(ctx, f"{args.out}/{exp.name}/clews_inputs")
            print("Wrote CLEWS inputs:", written)
        manifest = write_run_manifest(f"{args.out}/{exp.name}", exp, PHL, ctx,
                                      clews_run=args.clews_run)
        print("Wrote run manifest:", manifest)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
