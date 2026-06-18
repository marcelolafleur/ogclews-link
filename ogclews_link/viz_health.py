"""Health-channel visuals -- the newest coupling. Three figures that show the channel from the
data itself:

  1. gbd_age_profiles      -- the GBD age shapes h(s) (pollution deaths) and g(s) (pollution
                              disability/YLDs) by age. These are the channel's actual inputs;
                              avoided deaths/YLDs share their shape.
  2. mortality_by_age      -- where the reform's avoided mortality falls by age, from the solved
                              baseline-vs-reform survival rates.
  3. gdp_split             -- the resulting GDP contribution split into its mortality and morbidity
                              parts, a standalone of the waterfall's health segment.

Colors match the waterfall legend (mortality=teal, morbidity=orange) so the deck reads as one.
Builders take already-loaded data (a CSV path / the model_params objects / the layered list), so
they run from disk in seconds. Import-safe (matplotlib Agg).
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

from . import health_profile, style  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402

_SRC = style.SRC
MORT, MORB = style.CATEGORICAL[2], style.CATEGORICAL[3]  # teal / orange -- match the waterfall


# --- 1. the GBD age shapes (the channel's inputs) --------------------------------

def gbd_age_profiles(csv_path, location, year, out_dir, *, note=None, work_lo=15, work_hi=65,
                     name="health_age_profiles"):
    """Mortality h(s) and morbidity g(s) age profiles from the IHME GBD export (the exact builder
    the channel uses), as peak-1 relative shapes over single ages. Shades the working-age band so
    the deaths-vs-disability contrast by age is legible."""
    gbd_src = (f"Source: IHME GBD {year}, ambient particulate-matter burden, "
               f"{location} · author's calculations")
    hs = health_profile.build_profile_from_gbd(csv_path, location, year,
                                               key_col="cause_name", key_value="All causes")
    gs = health_profile.build_morbidity_profile_from_gbd(csv_path, location, year)
    ages = np.arange(len(hs))
    os.makedirs(out_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.08, right=0.86)
    style.clean(ax)
    ax.axvspan(work_lo, work_hi, color="0.90", zorder=0)
    ax.plot(ages, hs, color=MORT, lw=2.4, zorder=3)
    ax.plot(ages[:len(gs)], gs, color=MORB, lw=2.4, zorder=3)
    style.label_ends(ax, [(ages[-1], hs[-1], "mortality h(s)", MORT),
                          (len(gs) - 1, gs[-1], "morbidity g(s)", MORB)], min_gap=0.07)
    # working-age contrast: morbidity vs mortality at the band midpoint
    mid = (work_lo + work_hi) // 2
    ax.annotate(f"at age {mid}, disability is ~{gs[mid] / max(hs[mid], 1e-9):.0f}× the death risk",
                xy=(mid, gs[mid]), xytext=(0.04, 0.93), textcoords="axes fraction",
                fontsize=8.5, color=style.SUB, va="top", ha="left",
                arrowprops=dict(arrowstyle="->", color="#BBBBBB", lw=0.8))
    ax.annotate("working ages", (mid, 0.02), ha="center", va="bottom", fontsize=8.5,
                color=style.MUTE)
    ax.set_xlim(0, ages[-1] + 8)
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("age")
    ax.set_ylabel("attributable rate by age (peak = 1)")
    style.title_block(
        fig, title="Attributable burden by age: deaths vs disability",
        subtitle="Ambient-PM2.5 attributable rate by age, peak-normalized  ·  deaths h(s) vs disability g(s)",
        source=f"{gbd_src}.  {note}" if note else gbd_src, kicker="health: age profiles", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- 2. where the reform's avoided mortality falls -------------------------------

def mortality_by_age(base_params, reform_params, out_dir, *, note=None, retire_age=None,
                     name="health_mortality_by_age"):
    """Age distribution of the reform's avoided mortality, from the solved SS survival rates:
    avoided deaths at age a ∝ (rho_base - rho_reform) × population share, with the retirement age
    marked. retire_age defaults to the model's own retirement age."""
    if retire_age is None:
        retire_age = style.retire_age(base_params)
    E, S = int(base_params.E), int(base_params.S)
    rho_b = np.asarray(base_params.rho, float)[-1]
    rho_r = np.asarray(reform_params.rho, float)[-1]
    omega = np.asarray(base_params.omega_SS, float)
    ages = E + np.arange(S)
    avoided = np.maximum(rho_b - rho_r, 0.0) * omega   # ∝ avoided deaths by age
    tot = avoided.sum()
    if tot <= 0:
        return []
    dist = 100.0 * avoided / tot                       # % of avoided deaths by age
    peak_age = int(ages[int(np.argmax(dist))])

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.085, right=0.95)
    style.clean(ax)
    ax.bar(ages, dist, width=0.92, color=MORT, zorder=2)
    if retire_age is not None:                                   # mark retirement + split only if known
        work_share = float(dist[ages < retire_age].sum())
        ax.axvspan(ages[0], retire_age, color="0.90", zorder=0)
        ax.axvline(retire_age, color=style.INK, lw=1.0, ls=(0, (4, 3)), zorder=3)
        ax.annotate(f"retirement ({retire_age})", (retire_age, ax.get_ylim()[1] * 0.92),
                    xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=style.SUB, va="top")
        ax.annotate(f"{work_share:.0f}% working-age · {100 - work_share:.0f}% retired",
                    (ages[0] + 2, max(dist) * 0.82), fontsize=9, color=style.SUB, va="top")
    ax.set_xlim(ages[0] - 1, ages[-1] + 1)
    ax.set_xlabel("age")
    ax.set_ylabel("share of avoided deaths (%)")
    style.title_block(
        fig, title=f"Avoided mortality by age, peaking near {peak_age}",
        subtitle="Age distribution of the reform's avoided mortality (solved survival rates)",
        source=f"{_SRC}.  {note}" if note else _SRC, kicker="health: avoided mortality", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- 3. the GDP split: mortality vs morbidity ------------------------------------

def gdp_split(layered, out_dir, *, prev_step="+ carbon", health_step="+ health", note=None,
              name="health_gdp_split"):
    """Standalone of the waterfall's health segment: the health channel's marginal GDP, split into
    its mortality and morbidity parts (a clean standalone of the waterfall's health bar)."""
    by = {r.get("step"): r for r in layered}
    if health_step not in by or prev_step not in by or "health_split" not in by[health_step]:
        return []
    prevY = by[prev_step]["macro"]["Y"]
    split = by[health_step]["health_split"]
    mort = split["mortality"] - prevY
    morb = (split["combined"] - prevY) - mort
    vals = [mort, morb]
    labs = ["mortality", "morbidity"]

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    fig.subplots_adjust(top=0.74, bottom=0.12, left=0.16, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    bars = ax.bar([0, 1], vals, width=0.56, color=[MORT, MORB], zorder=2)
    for x, v, b in zip([0, 1], vals, bars):
        ax.annotate(f"{v:+.4f}%", (x, v), xytext=(0, 6 if v >= 0 else -6),
                    textcoords="offset points", ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=11, fontweight="bold", color=style.INK)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labs)
    ax.margins(y=0.22)
    ax.set_ylabel("marginal contribution to GDP (%)")
    style.title_block(
        fig, title="Health channel: mortality vs morbidity contribution to GDP",
        subtitle=f"GDP contribution of the health channel  ·  net {mort + morb:+.4f}%",
        source=f"{_SRC}.  {note}" if note else _SRC, kicker="health: GDP split", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
