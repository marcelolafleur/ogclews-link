"""Build the short paper's gallery-based illustrations from frozen model outputs.

No model solves and no reads from mutable CLEWS scenario directories.
Run with the existing OG-PHL environment (for trusted archived parameter pickles):
  python paper-intro/build_figures.py --plot-repo ../ogclews-link \
      --archive-root ../ogclews-link/ogclews_runs/battery

The gallery's plotting functions are retained for the output charts; only their
presentation headers are adapted to the paper. Original gallery files are untouched.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import pickle
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
BLUE, TEAL, GOLD, RED = "#0F5499", "#0D7680", "#E69F00", "#B2182B"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plot-repo", type=Path, required=True)
    ap.add_argument("--archive-root", type=Path, required=True)
    args = ap.parse_args()
    repo, archive = args.plot_repo.resolve(), args.archive_root.resolve()
    sys.path.insert(0, str(repo))
    import ogclews_link
    assert Path(ogclews_link.__file__).resolve().is_relative_to(repo)
    from ogclews_link.viz import plots, style

    OUT.mkdir(exist_ok=True)
    used = {}
    def read(path):
        used[str(path.relative_to(archive.parent))] = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix == ".json":
            return json.loads(path.read_text())
        # These are the user's own saved model outputs, not downloaded pickles.
        with path.open("rb") as stream:
            return pickle.load(stream)

    base = archive / "_og_baseline_cache/og-phl-0.1.0-ogphl_multisector_default_parameters"
    bp, bt, bs = (read(base / p) for p in ("model_params.pkl", "TPI/TPI_vars.pkl", "SS/SS_vars.pkl"))
    meta = read(base / "baseline_meta.json")
    records = {}
    for name in ("energy_price", "capital_intensity", "investment", "health", "carbon", "coupled", "discount_rate", "demand"):
        root = archive / name / name
        records[name] = {
            "params": read(root / "reform/model_params.pkl"),
            "tpi": read(root / "reform/TPI/TPI_vars.pkl"),
            "ss": read(root / "reform/SS/SS_vars.pkl"),
            "manifest": read(root / "ogclews_manifest.json"),
        }
    manifest = records["coupled"]["manifest"]
    concordance = SimpleNamespace(**manifest["concordance"])
    i, m = concordance.energy_good_index, concordance.energy_industry_index
    assert (i, m) == (1, 2), "Recheck the archived Philippine concordance before plotting."
    golden = json.loads((HERE.parent / "results/golden.json").read_text())
    for name, rec in records.items():
        for v in ("Y", "C", "K", "L"):
            for idx, suffix in ((0, "t0"), (10, "t10"), (-1, "ss")):
                observed = 100 * (rec["tpi"][v][idx] / bt[v][idx] - 1)
                expected = golden[name]["pct_diff"][f"{v}_{suffix}"]
                assert np.isclose(observed, expected, atol=3e-5), (name, v, suffix)
    start, n = int(bp.start_year), 50
    years = start + np.arange(n)
    # The emitter-only experiments solve an unperturbed reform before exporting.
    # Use that saved reform as the common no-channel control, not the baseline=True solve.
    control = records["discount_rate"]
    ct, cs = control["tpi"], control["ss"]
    for v in ("Y", "C", "K", "L", "I_g", "K_g"):
        np.testing.assert_array_equal(ct[v], records["demand"]["tpi"][v])
    cumulative = {}
    for step in ("energy price", "+ investment", "+ carbon", "+ health"):
        cumulative[step] = read(archive.parent / "across_steps" / step / "TPI/TPI_vars.pkl")
    root_baseline = read(archive.parent / "baseline/TPI/TPI_vars.pkl")
    for v in ("Y", "C", "K", "L"):
        np.testing.assert_array_equal(bt[v], root_baseline[v])
        np.testing.assert_array_equal(cumulative["+ investment"][v], cumulative["+ carbon"][v])
        np.testing.assert_allclose(cumulative["+ health"][v], records["coupled"]["tpi"][v], rtol=0, atol=2e-10)

    def pct(reform, reference):
        return 100 * (np.asarray(reform) / np.asarray(reference) - 1)

    def paired_paths(left, right, titles, ylabels, name):
        fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.05))
        for ax, values, title, ylabel, color in zip(axes, (left, right), titles, ylabels, (BLUE, TEAL)):
            ax.plot(years, values[:n], color=color, lw=2)
            ax.axhline(0, color="#777777", lw=.7)
            ax.set(title=title, ylabel=ylabel, xlabel="Year")
            ax.title.set_fontsize(11)
            ax.yaxis.label.set_fontsize(10)
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=10)
        fig.tight_layout(w_pad=2)
        finish(fig, name)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

    def quiet_header(fig, *, title, **kwargs):
        # Data are unchanged; simplify headers and clarify inherited labels.
        title = {"Long-run change by industry: output, capital, jobs":
                 "Long-run industry responses: output, capital and labour input",
                 "Household spending change, by age":
                 "Long-run household consumption, by age"}.get(title, title)
        fig.suptitle(title, x=.5, y=.985, fontsize=12, fontweight="bold")
        fig.subplots_adjust(top=.86)
        if "industry responses" in title and len(fig.axes[0].get_yticks()) == 1:
            fig.set_size_inches(8.6, 2.8)
            fig.subplots_adjust(top=.82, bottom=.20)
            fig._suptitle.set_text("Electricity production: output, capital and labour input")
            ax = fig.axes[0]
            ax.set_yticklabels(["Electricity"])
            for label in ax.texts:
                label.set_fontsize(9.5)
            for label in ax.get_legend().get_texts():
                if label.get_text() == "labor":
                    label.set_text("labour input")
        for ax in fig.axes:
            ax.set_xlabel(ax.get_xlabel().replace("baseline", "control"))
            ax.set_ylabel(ax.get_ylabel().replace("baseline", "control"))
            for label in list(ax.texts):
                if label.get_text().startswith("largest deviation"):
                    if title == "Household carbon tax with transfers":
                        label.remove()
                    else:
                        label.set_text(label.get_text().replace("largest deviation", "GDP peak"))
                        label.set_anncoords("axes fraction")
                        label.set_position((.46, .88))
                elif label.get_text() == "population avg":
                    label.set_text("mean at age")

    def save_pdf(fig, path):
        target = OUT / (Path(path).stem + ".pdf")
        fig.savefig(target, bbox_inches="tight", pad_inches=.1)
        plt.close(fig)
        return str(target)

    style.title_block = quiet_header
    style.save = save_pdf
    def finish(fig, name):
        return save_pdf(fig, OUT / name)

    # Actual applied household adjustment and actual household response, same standalone run.
    ep = records["energy_price"]
    wedge = 100 * ((1 + ep["params"].tau_c[:n, i]) / (1 + bp.tau_c[:n, i]) - 1)
    quantity = pct(ep["tpi"]["C_i"][:n, i], ct["C_i"][:n, i])
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.15))
    for ax, values, title, color in zip(
        axes, (wedge, quantity),
        ("Applied household energy-price adjustment", "Household energy consumption"),
        (BLUE, TEAL),
    ):
        ax.plot(years, values, color=color, lw=2)
        ax.axhline(0, color="#777777", lw=.7)
        ax.set_title(title, fontsize=10.5)
        ax.set_ylabel("Change (%)", fontsize=10)
        ax.set_xlabel("Year")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
    fig.tight_layout(w_pad=2)
    finish(fig, "electricity-paths.pdf")

    # Signed public investment flow and the resulting public-capital stock.
    inv = records["investment"]["tpi"]
    paired_paths(pct(inv["I_g"], ct["I_g"]), pct(inv["K_g"], ct["K_g"]),
                 ("Public investment expenditure", "Public capital stock"),
                 ("Change from control (%)", "Change from control (%)"), "public-investment-paths.pdf")

    health_tpi = records["health"]["tpi"]
    paired_paths(pct(health_tpi["L"], ct["L"]), pct(health_tpi["C"], ct["C"]),
                 ("Effective labour supply", "Household consumption"),
                 ("Change from control (%)", "Change from control (%)"), "health-outcomes.pdf")

    # Capital intensity: existing gallery sectoral plot, but from the ISOLATED experiment.
    # Native SS dictionaries carry sector capital and labour, unlike the slim NPZ export.
    industry_names = meta["industry_names"]
    assert int(bp.M) == len(industry_names)
    rec = records["capital_intensity"]
    keys = ("Y_m", "K_m", "L_m")
    focused_base = {k: np.asarray(cs[k])[m:m + 1] for k in keys}
    focused_reform = {k: np.asarray(rec["ss"][k])[m:m + 1] for k in keys}
    plots.sectoral_reallocation(focused_base, focused_reform, bp, str(OUT),
                               concordance=SimpleNamespace(energy_industry_index=0),
                               industry_names=[industry_names[m]], name="capital-intensity-sectors")

    # Health: same transformations as the gallery, explicitly labelled as distributions.
    hp = records["health"]["params"]
    ages = int(bp.E) + np.arange(int(bp.S))
    survival = np.maximum(np.asarray(bp.rho)[-1] - np.asarray(hp.rho)[-1], 0) * np.asarray(bp.omega_SS)
    survival = 100 * survival / survival.sum()
    assert np.isclose(survival.sum(), 100)
    eb, er = np.asarray(bp.e), np.asarray(hp.e)
    lam = np.asarray(bp.lambdas).ravel()
    delta = (er - eb) @ lam
    t = next(k for k in range(len(delta)) if not np.allclose(er[k] @ lam, eb[k] @ lam))
    illness = 100 * delta[t] / np.abs(delta[t]).sum()
    assert np.isclose(np.abs(illness).sum(), 100)
    retirement = style.retire_age(bp)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.15))
    for ax, values, title, color in zip(
        axes, (survival, illness),
        ("Survival improvement: age distribution", "Working-capacity adjustment: age distribution"),
        (TEAL, GOLD),
    ):
        ax.bar(ages, values, width=.9, color=color)
        ax.axvline(retirement, color="#555555", ls="--", lw=1)
        ax.text(.03, .96, f"Retirement age: {retirement}", transform=ax.transAxes, va="top", fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Age")
        ax.set_ylabel("Share of the adjustment (%)", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
    fig.tight_layout(w_pad=2)
    finish(fig, "health-age-distributions.pdf")

    # Standalone carbon experiment, not the coupled run's unused carbon-price export.
    plots.macro_transition(ct, records["carbon"]["tpi"], str(OUT), start_year=start,
                           params=bp, title="Household carbon tax with transfers",
                           name="carbon-transition")

    # Combined outcomes: existing gallery functions, verified frozen July outputs.
    cp = records["coupled"]
    plots.macro_transition(ct, cp["tpi"], str(OUT), start_year=start, params=bp,
                           title="Combined outcome: the economy over time",
                           name="combined-transition")
    plots.sectoral_reallocation(cs, cp["ss"], bp, str(OUT), concordance=concordance,
                               industry_names=industry_names, name="combined-sectors")
    plots.consumption_by_age(cs, cp["ss"], bp, str(OUT), name="combined-consumption-age")

    # Retain the useful individual-vs-combined comparison, but show both horizons.
    # The lower panel is a MATCHED cumulative contrast, not a sum of standalone bars.
    names = ("energy_price", "investment", "capital_intensity", "health", "carbon", "coupled")
    labels = ("Household electricity price", "Public investment", "Capital intensity", "Health",
              "Household carbon tax", "Combined experiment")
    summary = {name: {
        "gdp_mean_2026_2035": float(np.mean(pct(records[name]["tpi"]["Y"], ct["Y"])[:10])),
        "gdp_steady_state": float(pct(records[name]["ss"]["Y"], cs["Y"])),
        "consumption_mean_2026_2035": float(np.mean(pct(records[name]["tpi"]["C"], ct["C"])[:10])),
    } for name in names}
    fig, axes = plt.subplots(2, 1, figsize=(8.8, 7.2), gridspec_kw={"height_ratios": (1.1, 1)})
    ax = axes[0]
    y = np.arange(len(names))
    for field, offset, color, marker, label in (
        ("gdp_mean_2026_2035", -.11, BLUE, "o", "2026–2035 average"),
        ("gdp_steady_state", .11, GOLD, "s", "Steady state"),
    ):
        ax.scatter([summary[name][field] for name in names], y + offset, color=color,
                   marker=marker, s=44, zorder=3, label=label)
    ax.axvline(0, color="#777777", lw=.8)
    ax.axhline(4.5, color="#aaaaaa", lw=.8)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("GDP change from control (%)")
    ax.set_title("A. Individual experiments and the combined result", loc="left", fontsize=12, weight="bold")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -.27), frameon=False, ncol=2, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax = axes[1]
    for step, color, label in (("+ investment", RED, "Electricity costs + public investment"),
                               ("+ health", TEAL, "Same channels + health (combined)")):
        ax.plot(years, pct(cumulative[step]["Y"], ct["Y"])[:n], color=color, lw=2, label=label)
    ax.axhline(0, color="#777777", lw=.8)
    ax.set(xlabel="Year", ylabel="GDP change from control (%)", xlim=(years[0], years[-1]))
    ax.set_title("B. Adding health to the same cost-and-investment scenario", loc="left", fontsize=12, weight="bold")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(h_pad=3.5)
    finish(fig, "individual-and-combined.pdf")

    # Exact returned signal, distinguished from intended user-specific demand.
    proxy = 100 * (cp["tpi"]["Y_m"][:n, m] / bt["Y_m"][:n, m] - 1)
    fig, ax = plt.subplots(figsize=(7.6, 2.7))
    ax.plot(years, proxy, color=BLUE, lw=2)
    ax.axhline(0, color="#777777", lw=.7)
    ax.set(xlabel="Year", ylabel="Change from baseline (%)",
           title="Electricity-output change used as the demand proxy")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    finish(fig, "demand-proxy.pdf")
    summary["combined_gdp_peak"] = {"year": int(years[np.argmax(pct(cp["tpi"]["Y"], ct["Y"])[:n])]),
                                    "pct": float(np.max(pct(cp["tpi"]["Y"], ct["Y"])[:n]))}
    summary["returned_demand_proxy"] = {str(start + k): float(cp["tpi"]["Y_m"][k, m] / bt["Y_m"][k, m])
                                         for k in (0, 4, 14)}
    summary["electricity_sector_capital_intensity"] = {k: float(pct(rec["ss"][k][m], cs[k][m])) for k in keys}
    # Main-paper backbone: identical outcomes, dates, colours AND scales in every
    # solved channel and in the combined result. Small responses remain visibly small.
    macro_series = (("Y", "GDP", BLUE), ("C", "Consumption", RED),
                    ("K", "Capital", TEAL), ("L", "Labour", GOLD))
    chart_names = {
        "energy_price": "Electricity cost: household route",
        "investment": "Public infrastructure investment",
        "capital_intensity": "Generation capital intensity",
        "health": "Air pollution and health",
        "carbon": "Household carbon tax with transfers",
        "coupled": "Combined outcome",
    }
    for name, title in chart_names.items():
        fig, ax = plt.subplots(figsize=(8.6, 3.0))
        for key, label, color in macro_series:
            values = pct(records[name]["tpi"][key], ct[key])[:n]
            assert np.all(np.isfinite(values)), (name, key, "nonfinite chart data")
            assert values.min() >= -.4 and values.max() <= 1.4, (name, key, "shared scale would clip")
            ax.plot(years, values, color=color, lw=1.9, label=label,
                    ls={"Y": "-", "C": "-", "K": "--", "L": "-."}[key])
        ax.axhline(0, color="#555555", lw=.8)
        ax.set(xlim=(years[0], years[-1]), ylim=(-.4, 1.4), xlabel="Year",
               ylabel="Change from control (%)")
        ax.set_yticks(np.arange(-.4, 1.41, .4))
        ax.set_title(title, loc="left", fontsize=12, weight="bold")
        ax.legend(loc="upper right", frameon=False, ncol=2, fontsize=9.5)
        ax.grid(axis="y", color="#E5E5E5", lw=.7)
        ax.spines[["top", "right"]].set_visible(False)
        if name == "investment":
            ax.text(.02, .81, "Largest absolute GDP change: 0.0018%", transform=ax.transAxes,
                    fontsize=10, color="#555555")
        fig.tight_layout()
        finish(fig, f"channel-macro-{name}.pdf")
    summary["common_chart_scale"] = {"years": [2026, 2075], "y_min": -.4, "y_max": 1.4}
    (OUT / "figure-values.json").write_text(json.dumps(summary, indent=2) + "\n")
    provenance = {
        "archive": str(archive), "plot_module": str(Path(plots.__file__).resolve()),
        "case": manifest["scenario"]["name"], "manifest_timestamp": manifest["timestamp"],
        "source_hashes": used,
        "note": "Frozen July model outputs only. No model solves or current CLEWS input reads.",
        "checks": "All plotted-run Y/C/K/L at t0/t10/final agree with committed July golden.",
        "outcome_reference": "Saved discount_rate unperturbed reform; demand control identical for Y/C/K/L/I_g/K_g. Applied parameter and actual export figures retain their original references.",
        "cumulative_check": "Original baselines bitwise identical; carbon export changes no solved macro arrays; +health equals coupled within 2e-10 absolute.",
        "plot_code_sha256": hashlib.sha256(Path(plots.__file__).read_bytes()).hexdigest(),
        "illustrative_arithmetic": {"credit_cost": 100 * (1 - .2),
                                     "pv_100_20y_4pct": 100 / 1.04**20,
                                     "pv_100_20y_recorded_rate": 100 / (1 + .08156559053581243)**20},
    }
    (OUT / "source-manifest.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"Generated paper and supporting illustrations under {OUT}; archived-output checks passed.")


if __name__ == "__main__":
    main()
