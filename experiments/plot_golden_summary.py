"""Summary figures for the real PHL M=8 golden (ogcore 0.16.3, real CLEWS energy).

Reads results/golden.json (+ the across_steps layered_results.json if present) and writes clean
summary charts to results/figures/. Honest style: grey for near-zero/context, one signal colour for the
integrated `coupled` result; data-ink first, values annotated, no chartjunk.

    <og-env python> experiments/plot_golden_summary.py
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
GOLDEN = os.path.join(REPO, "results", "golden.json")
LAYERED = os.path.join(REPO, "ogclews_runs", "across_steps", "layered_results.json")
OUT = os.path.join(REPO, "results", "figures")

SIGNAL = "#1f6f78"      # coupled -- the integrated result
POS = "#4c9a2a"         # positive contribution
NEG = "#b3402f"         # negative contribution
GREY = "#c7c7c7"        # ~0 / context
NEAR_ZERO = 0.005       # |Y_ss %| below this is treated as ~0 (grey)

# human labels for the golden channels
LABELS = {
    "coupled": "Coupled (integrated)", "carbon": "Carbon price", "capital_intensity": "Capital intensity",
    "clean_incidence": "Energy-price incidence", "health": "Health (PM2.5)", "energy_price": "Energy price",
    "investment": "Public investment", "demand": "Demand (inert)", "discount_rate": "Discount-rate emit",
}


def _y_ss(rec):
    pd = rec.get("pct_diff", {})
    return pd.get("Y_ss", pd.get("Y"))


def fig_channel_bars(golden, path):
    """Horizontal bars: steady-state GDP (Y_ss) impact per TPI channel. coupled highlighted; ~0 greyed."""
    items = [(k, _y_ss(v)) for k, v in golden.items()
             if k in LABELS and _y_ss(v) is not None]
    items.sort(key=lambda kv: kv[1])
    labels = [LABELS[k] for k, _ in items]
    vals = [v for _, v in items]
    colors = []
    for k, v in items:
        if k == "coupled":
            colors.append(SIGNAL)
        elif abs(v) < NEAR_ZERO:
            colors.append(GREY)
        else:
            colors.append(POS if v > 0 else NEG)

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    y = range(len(vals))
    ax.barh(list(y), vals, color=colors, height=0.66)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.axvline(0, color="#444", lw=0.8)
    for i, v in enumerate(vals):
        ax.annotate(f"{v:+.3f}%", (v, i), xytext=(4 if v >= 0 else -4, 0),
                    textcoords="offset points", va="center",
                    ha="left" if v >= 0 else "right", fontsize=8, color="#333")
    ax.set_xlabel("Steady-state GDP change vs baseline (%)", fontsize=9)
    ax.set_title("PHL OG×CLEWS — steady-state macro impact by channel", fontsize=11, weight="bold", pad=22)
    ax.text(0.0, 1.045, "M=8 · ogcore 0.16.3 · real CLEWS 'auto' electricity price (no illustrative +20%)",
            transform=ax.transAxes, fontsize=8, color="#777")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.margins(x=0.18)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_coupled_path(golden, path):
    """The coupled result across the horizon: t0 (impact) -> t10 -> steady state, for Y/C/K/L."""
    pd = golden["coupled"]["pct_diff"]
    horizons = ["t0", "t10", "ss"]
    xlab = ["impact (t0)", "medium (t10)", "steady state"]
    series = {"Y (GDP)": SIGNAL, "C (consumption)": "#e08a1e", "K (capital)": "#6a51a3", "L (labour)": "#2b7bba"}
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for name, col in series.items():
        v = name.split()[0]
        ys = [pd.get(f"{v}_{h}") for h in horizons]
        ax.plot(xlab, ys, marker="o", color=col, label=name, lw=1.8, ms=6)
    ax.axhline(0, color="#444", lw=0.8)
    ax.set_ylabel("% change vs baseline", fontsize=9)
    ax.set_title("PHL coupled result over the transition", fontsize=11, weight="bold", pad=22)
    ax.text(0.0, 1.045, "real CLEWS energy + public investment + carbon + GBD health · M=8 · ogcore 0.16.3",
            transform=ax.transAxes, fontsize=8, color="#777")
    ax.legend(frameon=False, fontsize=8, loc="best")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_decomposition(path):
    """Cumulative across-steps decomposition of the real coupled run (if layered_results.json present)."""
    if not os.path.exists(LAYERED):
        return False
    with open(LAYERED) as f:
        lr = json.load(f)
    rows = [r for r in (lr if isinstance(lr, list) else lr.get("layered", [])) if "macro" in r]
    if not rows:
        return False
    steps = [r["step"] for r in rows]
    ys = [r["macro"].get("Y") for r in rows]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.plot(range(len(ys)), ys, marker="o", color=SIGNAL, lw=1.8, ms=6)
    ax.set_xticks(range(len(steps)))
    ax.set_xticklabels(steps, fontsize=9, rotation=15, ha="right")
    ax.axhline(0, color="#444", lw=0.8)
    for i, v in enumerate(ys):
        ax.annotate(f"{v:+.2f}%", (i, v), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=8, color="#333")
    ax.set_ylabel("GDP change vs baseline (%)", fontsize=9)
    ax.set_title("Cumulative channel contributions to the real coupled result", fontsize=11, weight="bold", pad=22)
    ax.text(0.0, 1.05, "each step adds one channel; top step = coupled · M=8 · real CLEWS energy",
            transform=ax.transAxes, fontsize=8, color="#777")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(GOLDEN) as f:
        golden = json.load(f)
    fig_channel_bars(golden, os.path.join(OUT, "golden_channel_impact.png"))
    fig_coupled_path(golden, os.path.join(OUT, "coupled_transition.png"))
    dec = fig_decomposition(os.path.join(OUT, "coupled_decomposition.png"))
    made = ["golden_channel_impact.png", "coupled_transition.png"] + (["coupled_decomposition.png"] if dec else [])
    print("wrote:", ", ".join(os.path.join("results/figures", m) for m in made))


if __name__ == "__main__":
    main()
