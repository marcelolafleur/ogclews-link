"""Write a single-page HTML report from a layered across-steps result list, so results can be
opened in a browser and explored variable by variable. Reusable for any run that produces the
layered_results.json shape.

Not fully self-contained: the page loads Chart.js from a public CDN, so a network connection is
required when it is first opened (the rest -- data, styling, layout -- is inlined).
"""
from __future__ import annotations

import json

from . import style

_CDN = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"
# Chart.js palette derived from the editorial categorical cycle (single source of truth in
# style.py) -- steps reuse the cycle in order; the macro vars map to its first four hues.
STEP_COLORS = list(style.CATEGORICAL)
VAR_COLORS = dict(zip(("Y", "C", "K", "L"), style.CATEGORICAL))


def write_html_report(layered, out_path, title="OG-CLEWS across-steps results"):
    solved = [r for r in layered if "macro" in r]
    failed = [r["step"] for r in layered if "macro" not in r]
    steps = [r["step"] for r in solved]
    J = len(solved[0]["consumption_by_J"]) if solved else 7
    jlabels = style.income_labels(J)
    payload = {
        "steps": steps,
        "energy_demand": [r["energy_demand_pct"] for r in solved],
        "macro": {v: [r["macro"].get(v) for r in solved] for v in ("Y", "C", "K", "L")},
        "revenue": [r["fiscal"]["cons_tax_revenue_pct"] for r in solved],
        "welfare": [r["consumption_by_J"] for r in solved],
        "energyJ": [r["energy_by_J"] for r in solved],
        "jlabels": jlabels,
        "stepColors": STEP_COLORS[:len(steps)],
        "varColors": VAR_COLORS,
    }
    failed_html = (f'<p class="note">Did not converge (omitted): {", ".join(failed)}</p>'
                   if failed else "")
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#1a1a1a;}}
 h1{{font-size:22px;font-weight:500;}} h2{{font-size:15px;font-weight:500;color:#555;margin:1.5rem 0 .5rem;}}
 .note{{color:#a32d2d;font-size:14px;}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;}}
 .cell{{border:0.5px solid #ddd;border-radius:12px;padding:1rem;}} .full{{grid-column:1/-1;}}
 .wrap{{position:relative;width:100%;height:300px;}}
</style></head><body>
<h1>{title}</h1>{failed_html}
<div class="grid">
 <div class="cell"><h2>energy demand (% vs baseline)</h2><div class="wrap"><canvas id="c_energy" role="img" aria-label="energy demand by step"></canvas></div></div>
 <div class="cell"><h2>government revenue (% change)</h2><div class="wrap"><canvas id="c_rev" role="img" aria-label="government revenue by step"></canvas></div></div>
 <div class="cell full"><h2>macro aggregates (% change)</h2><div class="wrap"><canvas id="c_macro" role="img" aria-label="macro aggregates by step"></canvas></div></div>
 <div class="cell full"><h2>consumption change by income group (one line per step)</h2><div class="wrap" style="height:340px;"><canvas id="c_welfare" role="img" aria-label="consumption change by income group across steps"></canvas></div></div>
 <div class="cell full"><h2>energy-demand change by income group (one line per step)</h2><div class="wrap" style="height:340px;"><canvas id="c_energyJ" role="img" aria-label="energy demand by income group across steps"></canvas></div></div>
</div>
<script src="{_CDN}"></script>
<script>
const D={json.dumps(payload)};
const pct=v=>(v>0?'+':'')+(Math.round(v*1000)/1000)+'%';
const base={{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>pct(c.raw)}}}}}}}};
new Chart(c_energy,{{type:'bar',data:{{labels:D.steps,datasets:[{{data:D.energy_demand,backgroundColor:'#1D9E75',borderRadius:4}}]}},options:base}});
new Chart(c_rev,{{type:'bar',data:{{labels:D.steps,datasets:[{{data:D.revenue,backgroundColor:'#378ADD',borderRadius:4}}]}},options:base}});
new Chart(c_macro,{{type:'bar',data:{{labels:D.steps,datasets:Object.keys(D.macro).map(v=>({{label:v,data:D.macro[v],backgroundColor:D.varColors[v],borderRadius:4}}))}},
 options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:true,position:'top'}},tooltip:{{callbacks:{{label:c=>c.dataset.label+' '+pct(c.raw)}}}}}}}}}});
const DASHES=[[],[6,4],[2,3],[10,4,2,4],[1,3]];  // step 0 solid (baseline); reform steps cycle distinct patterns
const lineSets=key=>D[key].map((row,i)=>({{label:D.steps[i],data:row,borderColor:D.stepColors[i],backgroundColor:D.stepColors[i],borderDash:DASHES[i%DASHES.length],borderWidth:2,pointRadius:3,tension:.25}}));
const lineOpts={{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:true,position:'top'}},tooltip:{{callbacks:{{label:c=>c.dataset.label+': '+pct(c.raw)}}}}}},scales:{{x:{{title:{{display:true,text:'lifetime-income group (lowest to highest)'}}}}}}}};
new Chart(c_welfare,{{type:'line',data:{{labels:D.jlabels,datasets:lineSets('welfare')}},options:lineOpts}});
new Chart(c_energyJ,{{type:'line',data:{{labels:D.jlabels,datasets:lineSets('energyJ')}},options:lineOpts}});
</script></body></html>"""
    with open(out_path, "w") as f:
        f.write(html)
    return out_path
