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
        source=style.source_line(note, base=gbd_src), kicker="health: age profiles", top=0.965)
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
                    (ages[0] + 2, np.max(dist) * 0.82), fontsize=9, color=style.SUB, va="top")
    ax.set_xlim(ages[0] - 1, ages[-1] + 1)
    ax.set_xlabel("age")
    ax.set_ylabel("share of avoided deaths (%)")
    style.title_block(
        fig, title=f"Avoided mortality by age, peaking near {peak_age}",
        subtitle="Age distribution of the reform's avoided mortality (solved survival rates)",
        source=style.source_line(note), kicker="health: avoided mortality", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- 2b. where the reform's effective-labor change falls -------------------------

def morbidity_by_age(base_params, reform_params, out_dir, *, note=None, retire_age=None,
                     work_lo=None, name="health_morbidity_by_age"):
    """Companion to mortality_by_age, on the morbidity side of the health channel: the age
    distribution of the reform's effective-labor change, from the solved e(t,s,j) profile.
    For a near-term transition row we lambda-weight e over the J income groups, take
    (e_reform - e_base) by age, and render each age's share of the total change as bars, with
    the working-age band shaded and the retirement age marked. retire_age defaults to the
    model's own retirement age; the working-age share is shown as a computed number."""
    if retire_age is None:
        retire_age = style.retire_age(base_params)
    E, S = int(base_params.E), int(base_params.S)
    e_b, e_r = getattr(base_params, "e", None), getattr(reform_params, "e", None)
    if e_b is None or e_r is None:                       # degrade gracefully if the field is absent
        return []
    eb = np.asarray(e_b, float)
    er = np.asarray(e_r, float)
    if eb.ndim != 3 or er.ndim != 3 or eb.shape != er.shape:
        return []
    lam = np.asarray(base_params.lambdas, float).ravel()
    if lam.shape[0] != eb.shape[2]:                      # fall back to equal weights if mismatched
        lam = np.full(eb.shape[2], 1.0 / eb.shape[2])

    def _by_age(arr_t):                                  # lambda-weight over J -> per-age effective labor
        return (arr_t * lam[None, :]).sum(axis=1)

    # pick a near-term row that actually carries the uplift (t=0 can be pre-phase-in / all zero)
    T = eb.shape[0]
    t = 0
    for k in range(T):
        if not np.allclose(_by_age(er[k]), _by_age(eb[k])):
            t = k
            break
    delta = _by_age(er[t]) - _by_age(eb[t])              # change in effective labor by age
    ages = E + np.arange(S)
    net = float(delta.sum())
    tot = float(np.abs(delta).sum())
    if tot <= 0:
        return []
    dist = 100.0 * delta / tot                           # % of total |effective-labor change| by age
    year = int(getattr(base_params, "start_year", 0) or 0) + t

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.085, right=0.95)
    style.clean(ax)
    style.zero_line(ax)                                  # change can be signed by age
    ax.bar(ages, dist, width=0.92, color=style.signed(dist, gain=MORB, loss=style.LOSS), zorder=2)
    if retire_age is not None:                           # mark retirement + working-age split only if known
        if work_lo is None:
            work_lo = ages[0]
        work_share = float(dist[(ages >= work_lo) & (ages < retire_age)].sum())
        ax.axvspan(work_lo, retire_age, color="0.90", zorder=0)
        ax.axvline(retire_age, color=style.INK, lw=1.0, ls=(0, (4, 3)), zorder=3)
        ax.annotate(f"retirement ({retire_age})", (retire_age, ax.get_ylim()[1] * 0.92),
                    xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=style.SUB, va="top")
        ax.annotate(f"working-age band: {work_share:+.0f}% of the change",
                    (ages[0] + 1, ax.get_ylim()[1] * 0.90), fontsize=9, color=style.SUB, va="top")
        # label the peak bar so the largest labeled magnitude sits on the visual mass
        peak_i = int(np.argmax(np.abs(dist)))
        peak_age = int(ages[peak_i])
        peak_share = float(dist[peak_i])
        ax.annotate(f"peak age {peak_age}: {peak_share:+.0f}%",
                    (peak_age, dist[peak_i]),
                    xytext=(0, 8 if dist[peak_i] >= 0 else -8), textcoords="offset points",
                    ha="center", va="bottom" if dist[peak_i] >= 0 else "top",
                    fontsize=8.5, color=style.SUB)
    ax.set_xlim(ages[0] - 1, ages[-1] + 1)
    ax.set_xlabel("age")
    ax.set_ylabel("share of effective-labor change (%)")
    yr_txt = f"transition year {year}" if year else f"transition row t={t}"
    style.title_block(
        fig, title="Age distribution of the reform's effective-labor change",
        subtitle=f"Effective-labor change by age, lambda-weighted over income groups  ·  {yr_txt}",
        source=style.source_line(note), kicker="health: morbidity", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- 2c. how the population share by age shifts over the transition --------------

def demographic_transition_by_age(base_params, reform_params, out_dir, *, note=None,
                                  years=None, name="health_demography"):
    """Reform-minus-base change in the population share by age for a few transition years (a few
    lines / small multiple). omega is a population SHARE by age whose rows sum to 1, so the
    plotted quantity is a change in share -- not a head-count. Guards if omega is absent or the
    two runs disagree on shape; picks evenly spaced transition years when none are given."""
    ob = np.asarray(getattr(base_params, "omega", None), float) if getattr(base_params, "omega", None) is not None else None
    orf = np.asarray(getattr(reform_params, "omega", None), float) if getattr(reform_params, "omega", None) is not None else None
    if ob is None or orf is None or ob.ndim != 2 or ob.shape != orf.shape:
        return []
    E, S = int(base_params.E), int(base_params.S)
    if ob.shape[1] != S:
        return []
    ages = E + np.arange(S)
    T = ob.shape[0]
    start = int(getattr(base_params, "start_year", 0) or 0)

    # cap to the near/mid transition horizon: far-future rows are high-amplitude oscillations
    # that dominate the plot and mislead, so clamp the top pick to ~start_year + 50yr (annual rows)
    horizon = min(T - 1, 50)
    if years is None:                                    # spaced rows across the near/mid transition
        idx = [int(round(f * horizon)) for f in (0.03, 0.12, 0.35)]
    else:
        idx = [t for t in years if 0 <= t < T]
    idx = sorted(set(t for t in idx if t > 0)) or [min(horizon, max(1, T // 3))]

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.10, right=0.86)
    style.clean(ax)
    style.zero_line(ax)
    colors = style.SEQUENTIAL[-len(idx):] if len(idx) <= len(style.SEQUENTIAL) else \
        [style.SEQUENTIAL[-1]] * len(idx)
    ends, peak_abs = [], 0.0
    for c, t in zip(colors, idx):
        d = 100.0 * (orf[t] - ob[t])                     # change in population share (% points) by age
        peak_abs = max(peak_abs, float(np.abs(d).max()))
        lab = str(start + t) if start else f"t={t}"
        ax.plot(ages, d, color=c, lw=2.0, zorder=3)
        ends.append((ages[-1], float(d[-1]), lab, c))
    ymin, ymax = ax.get_ylim()                           # gap as a fraction of the actual y span
    span = ymax - ymin
    style.label_ends(ax, ends, min_gap=(0.05 * span if span > 0 else None))
    ax.set_xlim(ages[0], ages[-1] + 8)
    ax.set_xlabel("age")
    ax.set_ylabel("change in population share")
    yrs = ", ".join(str(start + t) if start else f"t={t}" for t in idx)
    style.title_block(
        fig, title="Change in population share by age over the transition",
        subtitle=f"Reform-minus-base population share by age  ·  years {yrs}  ·  peak |change| {peak_abs:.3f} pts",
        source=style.source_line(note), kicker="health: demography", top=0.965)
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
        source=style.source_line(note), kicker="health: GDP split", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
