"""Energy-flow Sankeys, MUIOGO-style: how the power system's structure transforms.

Runs in the DEDICATED viz venv (.venv-viz: plotly+kaleido) -- NEVER in the solve stack's
environments. Two panels: the system at the first and last model year (fuel -> generation
group -> electricity -> demand sector), flows in TWh.

Usage:
    .venv-viz/bin/python experiments/sankey_energy.py <case_dir> <run> <out_png> \
        [--years 2020 2053] [--label "PEP scenario, Philippines"]
"""
import csv
import os
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

GROUPS = [("Coal power", ["PHL_POW_PP_COAL", "PHL_POW_CHP_COAL_OLD", "PHL_POW_PP_COAL_CCS"], "#6b7280"),
          ("Gas/Oil power", ["PHL_POW_PP_NGCC", "PHL_POW_PP_NGCC_CCS", "PHL_POW_CHP_NG_OLD",
                             "PHL_POW_CHP_OIL_OLD"], "#a8a29e"),
          ("Hydro", ["PHL_POW_PP_HY_LA"], "#0e7490"),
          ("Geothermal", ["PHL_POW_GEO_OLD"], "#9a3412"),
          ("Solar", ["PHL_POW_PP_SPV_T1"], "#eab308"),
          ("Wind", ["PHL_POW_PP_WON_T1", "PHL_POW_PP_WOF_T1"], "#15803d"),
          ("Nuclear", ["PHL_POW_PP_NU", "PHL_POW_PP_NUSMR"], "#7c3aed"),
          ("Bio/other", ["PHL_POW_CHP_BIOM_OLD", "PHL_POW_PP_BIOM_CCS", "PHL_POW_PP_H2"], "#d6d3d1")]
FUELS = {"PHL_PRO_COAL": "Coal", "PHL_PRO_NG": "Gas", "PHL_PRO_OIL": "Oil", "PHL_PRO_UR": "Uranium"}
RENEW = {"Hydro", "Geothermal", "Solar", "Wind"}          # groups with no fuel input
SECTORS = {"PHL_POW_TD_HOU": "Households", "PHL_POW_TD_SER": "Services",
           "PHL_POW_TD_INDU": "Industry", "PHL_POW_TD_TRA": "Transport",
           "PHL_POW_TD_AGR": "Agriculture", "PHL_POW_TD_FSH": "Fisheries"}
FUEL_COLOR = {"Coal": "#6b7280", "Gas": "#a8a29e", "Oil": "#78716c", "Uranium": "#7c3aed",
              "Renewable resource": "#84cc16"}
SECTOR_COLOR = "#0F5499"


def read(case, run, fname, val, year):
    rows = []
    with open(os.path.join(case, "res", run, "csv", fname)) as fh:
        for r in csv.DictReader(fh):
            if int(r["y"]) == year:
                rows.append((r["t"], r.get("f") or r.get("c", ""), float(r[val])))
    return rows


def flows_for_year(case, run, year):
    """(source, target, TWh) triples: fuel->group, group->Electricity, Electricity->sector."""
    use = read(case, run, "UseByTechnologyByMode.csv", "UseByTechnologyByMode", year)
    prod = read(case, run, "ProductionByTechnologyByMode.csv", "ProductionByTechnologyByMode", year)
    g_of = {t: g for g, ts, _ in GROUPS for t in ts}
    links = {}

    def add(a, b, v):
        if v > 0.05:
            links[(a, b)] = links.get((a, b), 0.0) + v

    for t, f, v in use:                      # fuels into generation groups
        g = g_of.get(t)
        fuel = FUELS.get(f)
        if g and fuel:
            add(fuel, g, v / 3.6)
    gen = {}
    for t, f, v in prod:                     # generation groups into the grid
        g = g_of.get(t)
        if g and f.startswith("PHL_POW_ELE"):
            gen[g] = gen.get(g, 0.0) + v / 3.6
    for g, v in gen.items():
        add(g, "Electricity", v)
        if g in RENEW:                       # renewables: a resource node feeds the group
            add("Renewable resource", g, v)
    for t, f, v in use:                      # grid into demand sectors
        s = SECTORS.get(t)
        if s and f.startswith("PHL_POW_ELE"):
            add("Electricity", s, v / 3.6)
    return links


def sankey_trace(links):
    nodes, idx = [], {}

    def node(n):
        if n not in idx:
            idx[n] = len(nodes)
            nodes.append(n)
        return idx[n]

    src = [node(a) for a, b in links]
    tgt = [node(b) for a, b in links]
    val = [round(v, 1) for v in links.values()]
    colors = []
    for n in nodes:
        c = FUEL_COLOR.get(n) or dict((g, c) for g, _, c in GROUPS).get(n)
        colors.append(c or ("#1a1a1a" if n == "Electricity" else SECTOR_COLOR))
    def rgba(hexc, a=0.35):
        h = hexc.lstrip("#")
        return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"
    link_colors = [rgba(colors[s]) for s in src]
    return go.Sankey(node=dict(label=nodes, color=colors, pad=14, thickness=16,
                               line=dict(width=0)),
                     link=dict(source=src, target=tgt, value=val, color=link_colors),
                     valueformat=".0f", valuesuffix=" TWh")


def main():
    case, run, out_png = sys.argv[1:4]
    years = (2020, 2053)
    if "--years" in sys.argv:
        i = sys.argv.index("--years")
        years = (int(sys.argv[i + 1]), int(sys.argv[i + 2]))
    label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else run
    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "sankey"}, {"type": "sankey"}]],
                        subplot_titles=[f"{years[0]} — coal-fed, ~100 TWh",
                                        f"{years[1]} — wind- and nuclear-fed, ~430 TWh"])
    for c, y in enumerate(years, start=1):
        fig.add_trace(sankey_trace(flows_for_year(case, run, y)), row=1, col=c)
    fig.update_layout(
        title=dict(text=f"<b>The power system, rebuilt: energy flows under the scenario</b>"
                        f"<br><sup>fuel → generation → electricity → sector, TWh · {label}</sup>",
                   x=0.02, font=dict(size=20, color="#1a1a1a")),
        font=dict(family="Helvetica, Arial", size=11, color="#1a1a1a"),
        paper_bgcolor="white", width=1500, height=640,
        margin=dict(l=20, r=20, t=90, b=40),
        annotations=list(fig.layout.annotations) + [dict(
            text=f"results: {os.path.basename(case)}/{run} · solver CBC · flows below 0.05 TWh omitted",
            x=0.0, y=-0.06, xref="paper", yref="paper", showarrow=False,
            font=dict(size=9, color="#7F8C8D"), xanchor="left")])
    fig.write_image(out_png, scale=2)
    print(f"sankey written: {out_png}")


if __name__ == "__main__":
    main()
