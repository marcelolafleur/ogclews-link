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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ogclews_link.viz import (
    style,  # the house editorial style -- kicker/title/dek/source
)

BLUE, AMBER, GRAY, INK = "#0F5499", "#E69F00", "#7F8C8D", "#1a1a1a"
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


def _ed(fig, ax, kicker, title, subtitle, source):
    """House editorial chrome: clean axes + the kicker/title/dek/source block."""
    style.clean(ax)
    fig.subplots_adjust(top=0.76, bottom=0.14)
    style.title_block(fig, title, subtitle=subtitle, source=source, kicker=kicker)


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
    style.apply()
    case, base, reform, coupled_dir, out = sys.argv[1:6]
    label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else f"{reform} vs {base}"
    os.makedirs(out, exist_ok=True)
    foot = f"{label} · results: {os.path.basename(case)} + {os.path.basename(os.path.abspath(coupled_dir))} · solver CBC + OG-Core"

    # ---- 1. Generation mix transformation (reform), TWh stacked ----
    acts = tech_by_year(case, reform)
    years = sorted({y for t in acts.values() for y in t})
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    series, colors, names = [], [], []
    for name, techs, colr in MIX:
        s = [sum(acts.get(t, {}).get(y, 0.0) for t in techs) / 3.6 for y in years]  # PJ -> TWh
        if max(s) > 0.5:
            series.append(s); colors.append(colr); names.append(name)
    ax.stackplot(years, *series, colors=colors, labels=names, alpha=0.92)
    ax.set_ylabel("generation, TWh per year", fontsize=10)
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
    _ed(fig, ax, "Energy system",
        "Coal out, offshore wind in: the power system rebuilt",
        f"Electricity generation by technology under the scenario · demand roughly quadruples by 2053 · {label}",
        foot)
    fig.savefig(f"{out}/impact_generation_mix.png"); plt.close(fig)

    # ---- 2. National CO2e BY SOURCE: scenario stacked, no-policy total for contrast ----
    SRC_GROUPS = [("Coal", ["PHL_PRO_PROC_COAL"], "#6b7280"),
                  ("Gas", ["PHL_PRO_PROC_NG"], "#a8a29e"),
                  ("Oil", ["PHL_PRO_PROC_OIL", "PHL_HOU_COOK_OIL"], "#78716c"),
                  ("Land conversion", ["LNDFORTOT"], "#b45309")]

    def co2_by_source(run):
        te, out = {}, {}
        with open(os.path.join(case, "res", run, "csv", "AnnualTechnologyEmission.csv")) as fh:
            for r in csv.DictReader(fh):
                if r["e"] == "CO2e":
                    te.setdefault(r["t"], {})
                    y = int(r["y"])
                    te[r["t"]][y] = te[r["t"]].get(y, 0.0) + float(r["AnnualTechnologyEmission"])
        with open(os.path.join(case, "res", run, "csv", "EmissionByActivityChange.csv")) as fh:
            for r in csv.DictReader(fh):
                if r["e"] == "CO2e":
                    te.setdefault(r["t"], {})
                    y = int(r["y"])
                    te[r["t"]][y] = te[r["t"]].get(y, 0.0) + float(r["EmissionByActivityChange"])
        for name, techs, _ in SRC_GROUPS:
            out[name] = {}
            for t in techs:
                for y, v in te.get(t, {}).items():
                    out[name][y] = out[name].get(y, 0.0) + v
        return out
    sb, sr = co2_by_source(base), co2_by_source(reform)
    ys = sorted(set().union(*[set(d) for d in sr.values()]))
    base_tot = {y: sum(d.get(y, 0.0) for d in sb.values()) for y in ys}
    ref_tot = {y: sum(d.get(y, 0.0) for d in sr.values()) for y in ys}
    avoided = sum(base_tot[y] - ref_tot[y] for y in ys)
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    stacks = [[max(sr[name].get(y, 0.0), 0.0) for y in ys] for name, _, _ in SRC_GROUPS]
    ax.stackplot(ys, *stacks, colors=[c for _, _, c in SRC_GROUPS],
                 labels=[n for n, _, _ in SRC_GROUPS], alpha=0.9)
    ax.plot(ys, [base_tot[y] for y in ys], color="#4d4d4d", lw=1.8, ls="--")
    ax.annotate("no-policy total", xy=(ys[-1], base_tot[ys[-1]]), xytext=(6, 0),
                textcoords="offset points", color="#4d4d4d", fontsize=9.5,
                fontweight="bold", va="center")
    ax.annotate(f"cumulative avoided vs no-policy:\n{avoided:,.0f} Mt CO2e",
                xy=(ys[len(ys)//2], base_tot[ys[len(ys)//2]] * 0.55), fontsize=11,
                color="#1a1a1a", fontweight="bold", ha="center")
    ax.set_ylabel("Mt CO2e per year", fontsize=10)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _ed(fig, ax, "Emissions",
        "Where the carbon comes from, and what the scenario avoids",
        f"National CO2e by source under the scenario; dashed line is the no-policy total · {label}",
        foot)
    fig.savefig(f"{out}/impact_co2e.png"); plt.close(fig)

    # ---- 3. Health: cleaner air -> lives AND working time ----
    import json
    man = json.load(open(os.path.join(coupled_dir, "ogclews_manifest.json")))
    deaths = pmchg = morb = None
    for p in man.get("provenance", []):
        if p.get("channel") == "health":
            deaths = -p["mortality_excess_deaths"]; pmchg = p["emissions_change"] * 100
            morb = p.get("morbidity_benefit")
    pb = read_by_year(case, base, "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission", emis="PM2_5")
    pr = read_by_year(case, reform, "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission", emis="PM2_5")
    ys = sorted(set(pb) & set(pr))
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.6, 5.0), width_ratios=[1.7, 1.0])
    ax.plot(ys, [pb[y] for y in ys], color=GRAY, lw=2.2)
    ax.plot(ys, [pr[y] for y in ys], color="#E3120B", lw=2.6)
    ax.fill_between(ys, [pr[y] for y in ys], [pb[y] for y in ys],
                    where=[pb[y] >= pr[y] for y in ys], color="#E3120B", alpha=0.08)
    ax.annotate("no-policy", xy=(ys[-1], pb[ys[-1]]), xytext=(4, 0), textcoords="offset points",
                color=GRAY, fontsize=9.5, fontweight="bold", va="center")
    ax.annotate("scenario", xy=(ys[-1], pr[ys[-1]]), xytext=(4, 0), textcoords="offset points",
                color="#E3120B", fontsize=9.5, fontweight="bold", va="center")
    ax.set_ylabel("PM2.5 emissions, kt per year", fontsize=10)
    EMPLOYED = 48.91e6  # PSA LFS 2024 annual average employed (derived from PSA's published
                        # underemployment ratio: 5.82M underemployed = 11.9% of employed)
    fte = (morb or 0.0) * EMPLOYED
    ax2.axis("off")
    ax2.text(0.0, 0.93, f"≈{deaths:,.0f}", fontsize=30, fontweight="bold", color="#E3120B", va="top")
    ax2.text(0.0, 0.76, "lives saved\n(mortality, all ages, GBD-anchored)", fontsize=10, color="#444444", va="top")
    ax2.text(0.0, 0.55, f"≈{fte:,.0f}", fontsize=30, fontweight="bold", color="#0F5499", va="top")
    ax2.text(0.0, 0.38, "full-time workers' worth of illness-time\nreturned each year (morbidity, GBD YLD)", fontsize=10, color="#444444", va="top")
    ax2.text(0.0, 0.14, f"derived: {morb:.2e} productivity gain\n× 48.91M employed (PSA LFS 2024 annual avg)", fontsize=8, color="#888888", va="top")
    _ed(fig, ax, "Health",
        "Cleaner air, counted in lives and working time",
        f"{pmchg:+.1f}% PM2.5 from the scenario · mortality and morbidity both from the GBD 2023 dose-response · {label}",
        foot)
    fig.savefig(f"{out}/impact_air_health.png"); plt.close(fig)

    # ---- 4. What gets built: new capacity by technology, 5-year bins (reform) ----
    nc = {}
    with open(os.path.join(case, "res", reform, "csv", "NewCapacity.csv")) as fh:
        for r in csv.DictReader(fh):
            nc.setdefault(r["t"], {})[int(r["y"])] = float(r["NewCapacity"])
    bins = [(2020, 2029), (2030, 2039), (2040, 2053)]
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    x = range(len(bins))
    bottom = [0.0] * len(bins)
    for name, techs, colr in MIX:
        vals = [sum(v for t in techs for y, v in nc.get(t, {}).items() if lo <= y <= hi)
                for lo, hi in bins]
        if max(vals) > 0.05:
            ax.bar(x, vals, 0.55, bottom=bottom, color=colr, label=name)
            bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_xticks(list(x), [f"{lo}\u2013{hi}" for lo, hi in bins])
    for xi, b in zip(x, bottom):
        ax.annotate(f"{b:.0f} GW", xy=(xi, b), xytext=(0, 5), textcoords="offset points",
                    ha="center", fontsize=10, fontweight="bold", color=INK)
    ax.set_ylabel("GW added", fontsize=10)
    ax.legend(frameon=False, fontsize=8.5, ncol=3)
    _ed(fig, ax, "Investment",
        "What gets built, and when",
        f"New generation capacity by technology and era under the scenario · {label}", foot)
    fig.savefig(f"{out}/impact_new_capacity.png"); plt.close(fig)

    # ---- 5. The economy: GDP, consumption, wages along the transition (coupled run) ----
    rows = {r["Year"]: r for r in csv.DictReader(open(os.path.join(coupled_dir, "macro_table.csv")))}
    yrs = sorted(y for y in rows if y.isdigit())
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    ax.axhline(0, color="#cccccc", lw=0.9)
    offsets = {"Y": -8, "C": 10, "w": -22}   # staggered so end labels never collide
    for k, colr, lbl in (("Y", BLUE, "GDP"), ("C", AMBER, "consumption"), ("w", "#0D7680", "wage")):
        ax.plot([int(y) for y in yrs], [float(rows[y][k]) for y in yrs], color=colr, lw=2.4)
        ax.annotate(f"{lbl} {float(rows['SS'][k]):+.2f}%",
                    xy=(int(yrs[-1]), float(rows[yrs[-1]][k])), xytext=(8, offsets[k]),
                    textcoords="offset points", fontsize=10, color=colr, fontweight="bold", va="center")
    ax.set_ylabel("% vs baseline (steady state labeled)", fontsize=10)
    ax.set_xlim(int(yrs[0]), int(yrs[-1]) + 6)
    _ed(fig, ax, "Macroeconomy",
        "The transition's economic price, and who feels it first",
        f"GDP, consumption and wages against the no-policy baseline, transition years · {label}", foot)
    fig.savefig(f"{out}/impact_macro.png"); plt.close(fig)

    print(f"impact deck written to {out}/ (5 charts) -- reuse the coupled deck for incidence,"
          " cohort, and fiscal figures")


if __name__ == "__main__":
    main()
