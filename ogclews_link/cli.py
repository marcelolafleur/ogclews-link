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
    rp.add_argument("--country", default=None,
                    help="country to run (name / UN code / og-repo key, e.g. 'phl' or 'og-zaf'); "
                         "default: $OGCLEWS_COUNTRY, else the packaged PHL example")
    rp.add_argument("--countries", default=None,
                    help="countries JSON defining your own CountryConfig entries (default: "
                         "$OGCLEWS_COUNTRIES, else ./ogclews_countries.json if present; see "
                         "ogclews_countries.example.json)")
    rp.add_argument("--workers", type=int, default=7, help="OG-Core J-loop worker processes (use multiprocess; avoid 1)")
    rp.add_argument("--out", default="./ogclews_runs")
    rp.add_argument("--no-progress", action="store_true")
    rp.add_argument("--rebuild-baseline", action="store_true",
                    help="force a fresh baseline solve, ignoring any cached one (e.g. to pick up newer "
                         "UN demographics or a re-baked calibration)")
    rp.add_argument("--clews-base", default=None,
                    help="CLEWS baseline scenario dir (overrides $OGCLEWS_CLEWS_BASE / the MUIOGO-install "
                         "resolution); e.g. <MUIOGO>/WebAPP/DataStorage/<case>/res/<run>/csv")
    rp.add_argument("--clews-reform", default=None, help="CLEWS reform scenario dir (the reform side)")
    rp.add_argument("--clews-run", default=None,
                    help="CLEWS/MUIOGO run dir recorded in the manifest for provenance")

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

        import os

        from . import framework, registry, runtime
        from .country import CLEWS_SCENARIO_HELP, resolve_country
        from .manifest import write_run_manifest
        from .muiogo_run import preflight

        exp = experiments.get(args.experiment)
        # Country: CLI flag > $OGCLEWS_COUNTRY > the packaged PHL example. Countries beyond the packaged
        # ones are defined declaratively in a countries JSON (--countries / $OGCLEWS_COUNTRIES /
        # ./ogclews_countries.json) -- onboarding never edits link source.
        country = resolve_country(args.country or os.environ.get("OGCLEWS_COUNTRY") or "phl",
                                  config_file=args.countries)
        print(f"Country: {country.name} (un {country.un_code}, OG model {country.og_repo})")
        cfg = runtime.RunnerConfig(num_workers=args.workers, show_progress=not args.no_progress,
                                   rebuild=args.rebuild_baseline)
        # CLEWS scenario source: CLI flag > env / MUIOGO-install resolution (country.clews_scenario_dir)
        if args.clews_base:
            country.scenario.base_dir = args.clews_base
        if args.clews_reform:
            country.scenario.reform_dir = args.clews_reform
        pre = {}
        for side, d in (("base", country.scenario.base_dir), ("reform", country.scenario.reform_dir)):
            status = "ok" if d and os.path.isdir(d) else "NOT FOUND -- CLEWS-reading channels will fail"
            print(f"CLEWS {side:6} scenario: {d or '(unset)'}  [{status}]")
            if not (d and os.path.isdir(d)):
                print(f"  {CLEWS_SCENARIO_HELP}")
            else:
                pre[side] = preflight(d, label=side)   # loud export checklist BEFORE the expensive solve
        entry = registry.lookup(country)    # OG-model provenance for the manifest (and fail-fast)
        # FAIL-FAST, not warn-then-burn: an experiment that unconditionally sources the energy price
        # (its source calls _auto_price_ratio) needs the cost workbook or the EBb4 dual in BOTH scenario
        # dirs. If neither exists -- and the registered calibration is couplable, so the energy legs
        # won't just skip -- the run is GUARANTEED to die after the multi-minute baseline solve; refuse
        # now with the fix instead. (calibration None -> single-industry -> energy legs skip -> no gate.)
        import inspect

        from . import signals as _signals
        try:
            needs_price = "_auto_price_ratio" in inspect.getsource(exp)
        except (OSError, TypeError):        # no source (frozen/builtin) -> can't tell -> don't gate
            needs_price = False
        if needs_price and entry.calibration and len(pre) == 2:
            ebb4 = all(v.get("EBb4_EnergyBalanceEachYear4_ICR") for v in pre.values())
            workbook = all(_signals._has_cost_xlsx(d) for d in
                           (country.scenario.base_dir, country.scenario.reform_dir))
            if not (ebb4 or workbook):
                raise SystemExit(
                    f"experiment {args.experiment!r} needs an energy-price source, but neither the "
                    "cost-of-electricity workbook nor the EBb4 commodity-balance dual is present in "
                    "both scenario dirs (see the export checklist above). Re-solve the CLEWS case with "
                    "CBC and '-printing all' (produces the EBb4 export), or point --clews-base/"
                    "--clews-reform at run dirs that carry a price source.")
        og_model = {"repo": entry.key, "package": entry.package, "version": entry.version,
                    "env_python": entry.env_python}
        ctx = framework.run(
            exp, country,
            export_baseline=partial(runtime.export_baseline, cfg=cfg),
            solve_reform=partial(runtime.solve_reform, cfg=cfg),
            out_root=args.out)
        print_report(ctx)
        if ctx.base_tpi is not None and ctx.reform_tpi is not None:
            import os

            from .report import macro_table
            mt_path = os.path.join(args.out, args.experiment, "macro_table.csv")
            try:
                os.makedirs(os.path.dirname(mt_path), exist_ok=True)
                macro_table(ctx.base_tpi, ctx.reform_tpi, country.scenario.og_start_year).to_csv(mt_path)
                print("Wrote macro table:", mt_path)
            except Exception as e:  # noqa: BLE001 -- the CSV is a convenience; never fail the run for it
                print(f"(macro table CSV skipped: {type(e).__name__})")
        if ctx.clews_inputs:
            written = clews_io.write_all(ctx, f"{args.out}/{args.experiment}/clews_inputs")
            print("Wrote CLEWS inputs:", written)
        manifest = write_run_manifest(f"{args.out}/{args.experiment}", exp, country, ctx,
                                      clews_run=args.clews_run, og_model=og_model)
        print("Wrote run manifest:", manifest)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
