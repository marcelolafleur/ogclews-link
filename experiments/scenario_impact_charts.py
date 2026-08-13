"""The scenario-impact deck: the country's story under the reform, not calibration comparisons.

Marcelo's directive (2026-08-13): the run's output should SHOW the scenario's impact and the
country's trends -- CO2e, health, the power system, land on the CLEWs side; the OG side shows
the economic trends. No version-vs-version charts.

Reads any solved (base, reform) CLEWs csv pair plus the coupled OG run dir, and writes the
chart set. Built and proven on v16; regenerates unchanged on v18 (same export schema).

Usage:
    <og-venv-python> scenario_impact_charts.py <case_dir> <base_run> <reform_run> \
        <coupled_run_dir> <out_dir> [--label "PEP vs Base, Philippines vXX"]
"""
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, AMBER, GRAY, INK = "#4269d0", "#b45309", "#9498a0", "#333333"
# generation-mix palette: fixed order, muted, coal->clean; validated family + gray others
MIX = [("Coal", ["PHL_POW_PP_COAL", "PHL_POW_CHP_COAL_OLD", "PHL_POW_PP_COAL_CCS"], "#6b7280"),
       ("Gas/Oil", ["PHL_POW_PP_NGCC", "PHL_POW_PP_NGCC_CCS", "PHL_POW_CHP_NG_OLD",
                    "PHL_POW_CHP_OIL_OLD"], "#a8a29e"),
       ("Hydro", ["PHL_POW_PP_HY_LA"], "#0e7490"),
       ("Geothermal", ["PHL_POW_GEO_OLD"], "#9a3412"),
       ("Solar", ["PHL_POW_PP_SPV_T1"], "#eab308"),
       ("Wind onshore", ["PHL_POW_PP_WON_T1"], "#65a30d"),
       ("Wind offshore", ["PHL_POW_PP_WOF_T1"], "#15803d"),
       ("Nuclear", ["PHL_POW_PP_NU", "PHL_POW_PP_NUSMR"], "#7c3aed"),
       ("Other", ["PHL_POW_CHP_BIOM_OLD", "PHL_POW_PP_BIOM_CCS", "PHL_POW_PP_H2"], "#d6d3d1")]


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e8e8e6", lw=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK, labelsize=9)


def read_by_year(case, run, fname, val, tech=None, emis=None):
    out = {}
    with open(os.path.join(case, "res", run, "csv", fname)) as fh:
        for r in csv.DictReader(fh):
            if tech and r["t"] != tech:
                continue
            if emis and r.get("e") != emis:
                continue
            y = int(r["y"])
            out[y] = out.get(y, 0.0) + float(r[val])
    return out


def tech_by_year(case, run):
    out = {}
    with open(os.path.join(case, "res", run, "csv", "TotalAnnualTechnologyActivityByMode.csv")) as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["t"], {})
            y = int(r["y"])
            out[r["t"]][y] = out[r["t"]].get(y, 0.0) + float(r["TotalAnnualTechnologyActivityByMode"])
    return out


def main():
    case, base, reform, coupled_dir, out = sys.argv[1:6]
    label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else f"{reform} vs {base}"
    os.makedirs(out, exist_ok=True)
    foot = f"{label} · results: {os.path.basename(case)} + {os.path.basename(os.path.abspath(coupled_dir))} · solver CBC + OG-Core"

    # ---- 1. Generation mix transformation (reform), TWh stacked ----
    acts = tech_by_year(case, reform)
    years = sorted({y for t in acts.values() for y in t})
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    style(ax)
    series, colors, names = [], [], []
    for name, techs, colr in MIX:
        s = [sum(acts.get(t, {}).get(y, 0.0) for t in techs) / 3.6 for y in years]  # PJ -> TWh
        if max(s) > 0.5:
            series.append(s); colors.append(colr); names.append(name)
    ax.stackplot(years, *series, colors=colors, labels=names, alpha=0.92)
    ax.set_title(f"How the power system transforms under the scenario ({label})",
                 fontsize=12, color=INK, loc="left")
    ax.set_ylabel("generation, TWh/yr", fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    fig.text(0.01, 0.01, foot, fontsize=6, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(f"{out}/impact_generation_mix.png", dpi=160); plt.close(fig)

    # ---- 2. National CO2e: base vs reform (energy + booked land conversion) ----
    def co2(run):
        e = read_by_year(case, run, "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission", emis="CO2e")
        c = read_by_year(case, run, "EmissionByActivityChange.csv", "EmissionByActivityChange", emis="CO2e")
        return {y: e.get(y, 0.0) + max(c.get(y, 0.0), 0.0) for y in sorted(set(e) | set(c))}
    cb, cr = co2(base), co2(reform)
    ys = sorted(set(cb) & set(cr))
    avoided = sum(cb[y] - cr[y] for y in ys)
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    style(ax)
    ax.plot(ys, [cb[y] for y in ys], color=GRAY, lw=2, label="no-policy base")
    ax.plot(ys, [cr[y] for y in ys], color=BLUE, lw=2, label="scenario")
    ax.fill_between(ys, [cr[y] for y in ys], [cb[y] for y in ys],
                    where=[cb[y] >= cr[y] for y in ys], color=BLUE, alpha=0.12)
    ax.annotate(f"cumulative avoided: {avoided:,.0f} Mt CO2e",
                xy=(ys[len(ys) * 3 // 4], (cb[ys[len(ys) * 3 // 4]] + cr[ys[len(ys) * 3 // 4]]) / 2),
                fontsize=10, color=BLUE, fontweight="bold", ha="center")
    ax.set_title("National CO2e, including land conversion: the scenario against the no-policy path",
                 fontsize=12, color=INK, loc="left")
    ax.set_ylabel("Mt CO2e / yr", fontsize=9)
    ax.legend(frameon=False, fontsize=9)
    fig.text(0.01, 0.01, foot, fontsize=6, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(f"{out}/impact_co2e.png", dpi=160); plt.close(fig)

    # ---- 3. Air quality and lives: PM2.5 base vs reform, deaths averted from the manifest ----
    import json
    man = json.load(open(os.path.join(coupled_dir, "ogclews_manifest.json")))
    deaths = pmchg = None
    for p in man.get("provenance", []):
        if p.get("channel") == "health":
            deaths = -p["mortality_excess_deaths"]; pmchg = p["emissions_change"] * 100
    pb = read_by_year(case, base, "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission", emis="PM2_5")
    pr = read_by_year(case, reform, "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission", emis="PM2_5")
    ys = sorted(set(pb) & set(pr))
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    style(ax)
    ax.plot(ys, [pb[y] for y in ys], color=GRAY, lw=2, label="no-policy base")
    ax.plot(ys, [pr[y] for y in ys], color=AMBER, lw=2, label="scenario")
    ax.fill_between(ys, [pr[y] for y in ys], [pb[y] for y in ys],
                    where=[pb[y] >= pr[y] for y in ys], color=AMBER, alpha=0.15)
    if deaths is not None:
        ax.annotate(f"{pmchg:+.1f}% PM2.5 → ≈{deaths:,.0f} deaths averted\n(GBD 2023 dose-response, ages profiled)",
                    xy=(ys[len(ys) // 2], (pb[ys[len(ys) // 2]] + pr[ys[len(ys) // 2]]) / 2),
                    fontsize=10, color=AMBER, fontweight="bold", ha="center")
    ax.set_title("Cleaner air, counted in lives: PM2.5 under the scenario", fontsize=12, color=INK, loc="left")
    ax.set_ylabel("PM2.5 emissions, kt/yr", fontsize=9)
    ax.legend(frameon=False, fontsize=9)
    fig.text(0.01, 0.01, foot, fontsize=6, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(f"{out}/impact_air_health.png", dpi=160); plt.close(fig)

    # ---- 4. What gets built: new capacity by technology, 5-year bins (reform) ----
    nc = {}
    with open(os.path.join(case, "res", reform, "csv", "NewCapacity.csv")) as fh:
        for r in csv.DictReader(fh):
            nc.setdefault(r["t"], {})[int(r["y"])] = float(r["NewCapacity"])
    bins = [(2020, 2029), (2030, 2039), (2040, 2053)]
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    style(ax)
    x = range(len(bins))
    bottom = [0.0] * len(bins)
    for name, techs, colr in MIX:
        vals = [sum(v for t in techs for y, v in nc.get(t, {}).items() if lo <= y <= hi)
                for lo, hi in bins]
        if max(vals) > 0.05:
            ax.bar(x, vals, 0.55, bottom=bottom, color=colr, label=name)
            bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_xticks(list(x), [f"{lo}–{hi}" for lo, hi in bins])
    ax.set_title("What gets built: new generation capacity under the scenario", fontsize=12, color=INK, loc="left")
    ax.set_ylabel("GW added", fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=3)
    fig.text(0.01, 0.01, foot, fontsize=6, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(f"{out}/impact_new_capacity.png", dpi=160); plt.close(fig)

    # ---- 5. The economy: GDP, consumption, wages along the transition (coupled run) ----
    rows = {r["Year"]: r for r in csv.DictReader(open(os.path.join(coupled_dir, "macro_table.csv")))}
    yrs = sorted(y for y in rows if y.isdigit())
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    style(ax)
    ax.axhline(0, color="#cccccc", lw=0.8)
    for k, colr, lbl in (("Y", BLUE, "GDP"), ("C", AMBER, "consumption"), ("w", "#15803d", "wage")):
        ax.plot([int(y) for y in yrs], [float(rows[y][k]) for y in yrs], color=colr, lw=2, label=lbl)
        ax.annotate(f"SS {float(rows['SS'][k]):+.2f}%", xy=(int(yrs[-1]), float(rows[yrs[-1]][k])),
                    xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=colr, fontweight="bold")
    ax.set_title("The macro cost of the transition: GDP, consumption and wages vs baseline",
                 fontsize=12, color=INK, loc="left")
    ax.set_ylabel("% vs baseline", fontsize=9)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.text(0.01, 0.01, foot, fontsize=6, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(f"{out}/impact_macro.png", dpi=160); plt.close(fig)

    print(f"impact deck written to {out}/ (5 charts) -- reuse the coupled deck for incidence,"
          " cohort, and fiscal figures")


if __name__ == "__main__":
    main()
