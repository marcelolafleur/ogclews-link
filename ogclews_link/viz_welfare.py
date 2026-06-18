"""Welfare figures -- consumption-equivalent variation (CEV), the proper welfare metric the
``consumption_by_J`` incidence proxy only approximates. CEV_j is the uniform % change in baseline
lifetime consumption that makes a household as well off as under the reform; negative = worse off.

The felicity is reconstructed faithfully from OG-Core's own household FOCs (it ships only marginal
utilities, not levels):
  * consumption  u(c) = c^(1-σ)/(1-σ)                       [MU_c = c^-σ]
  * labor        -χ^n_s · b_ellipse · [1 - (1-(n/l̃)^υ)^(1/υ)]  [antiderivative of MDU_n]
  * per-period weight  W_s = (β_j · e^{g_y(1-σ)})^s · Π_{u<s}(1-ρ_u)
    -- the discount/survival/growth structure read straight off the savings Euler.
The warm-glow bequest term is omitted (second-order; flagged in the captions). CEV is solved
by a 1-D root find per group/cohort.

Two views: cev_by_group (long-run, steady-state, by lifetime-income group) and cev_by_age
(remaining-lifetime, by age at the reform -- who alive today bears it). Import-safe (Agg).
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

from . import style  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402

from .figures import _labels  # noqa: E402

_SRC = style.SRC
_BEQ_NOTE = "lifetime CEV (consumption + labor felicity; warm-glow bequest omitted, second-order)"


class _Felicity:
    """OG-Core household felicity + per-period weights, pulled from a model_params object."""

    def __init__(self, p):
        self.sigma = float(p.sigma)
        self.g_y = float(p.g_y)
        self.b_ellipse = float(p.b_ellipse)
        self.upsilon = float(p.upsilon)
        self.ltilde = float(p.ltilde)
        self.beta = np.asarray(p.beta, float).ravel()
        self.S = int(p.S)

    def labor_disutil(self, n):
        x = np.clip(np.asarray(n, float) / self.ltilde, 0.0, 1.0 - 1e-9)
        return self.b_ellipse * (1.0 - (1.0 - x ** self.upsilon) ** (1.0 / self.upsilon))

    def u_c(self, c):
        c = np.maximum(np.asarray(c, float), 1e-12)
        s = self.sigma
        return np.log(c) if abs(1.0 - s) < 1e-9 else c ** (1.0 - s) / (1.0 - s)

    def weights(self, rho, j):
        """W_s = (β_j e^{g_y(1-σ)})^s · cumulative survival to age s."""
        rho = np.asarray(rho, float)
        L = len(rho)
        surv = np.concatenate([[1.0], np.cumprod(1.0 - rho)[:-1]])
        disc = (self.beta[j] * np.exp(self.g_y * (1.0 - self.sigma))) ** np.arange(L)
        return disc * surv

    def V(self, c, n, chi_n, rho, j, phi=0.0):
        W = self.weights(rho, j)
        return float(np.sum(W * (self.u_c((1.0 + phi) * c) - np.asarray(chi_n, float) * self.labor_disutil(n))))

    def cev(self, base, reform, chi_n, rho_b, rho_r, j):
        """Solve V_base((1+φ)·c) = V_reform for φ (the CEV). base/reform are (c, n) tuples."""
        v_ref = self.V(reform[0], reform[1], chi_n, rho_r, j)
        f = lambda phi: self.V(base[0], base[1], chi_n, rho_b, j, phi) - v_ref  # noqa: E731
        try:
            return brentq(f, -0.99, 20.0, xtol=1e-10)
        except (ValueError, RuntimeError):
            return np.nan


# --- CEV by lifetime-income group (long-run, steady state) -----------------------

def cev_by_group(base_ss, reform_ss, base_params, reform_params, out_dir, *, note=None,
                 name="welfare_cev_by_group"):
    """Steady-state lifetime CEV by lifetime-income group -- the long-run welfare effect. Read it
    against the incidence_hero's consumption proxy: the proxy is near-term and cross-sectional,
    while CEV is the proper long-run lifetime-welfare measure."""
    fe = _Felicity(base_params)
    cb, nb = np.asarray(base_ss["c"], float), np.asarray(base_ss["n"], float)      # (S, J)
    cr, nr = np.asarray(reform_ss["c"], float), np.asarray(reform_ss["n"], float)
    chi = np.asarray(base_params.chi_n, float)[-1]                                  # SS row (S,)
    rho_b = np.asarray(base_params.rho, float)[-1]
    rho_r = np.asarray(reform_params.rho, float)[-1]
    J = cb.shape[1]
    cev = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cr[:, j], nr[:, j]),
                                   chi, rho_b, rho_r, j) for j in range(J)])
    lab = _labels(J, np.asarray(base_params.lambdas, float).ravel())

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.16, left=0.10, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    ax.bar(range(J), cev, width=0.66, color=style.signed(cev), zorder=2)
    pad = 0.03 * (np.nanmax(np.abs(cev)) or 1.0)
    for j, v in enumerate(cev):
        ax.annotate(f"{v:+.2f}%", (j, v), xytext=(0, -11 if v < 0 else 6),
                    textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                    fontsize=9, fontweight="bold", color=style.LOSS if v < 0 else style.GAIN)
    ax.set_xticks(range(J))
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.margins(y=0.20)
    ax.set_ylabel("consumption-equivalent variation (%)")
    style.title_block(
        fig, title="Lifetime welfare effect by income group (CEV)",
        subtitle=f"Steady-state lifetime CEV by income group, poorest to richest  ·  "
                 f"mean {np.nanmean(cev):+.2f}% (range {np.nanmin(cev):+.2f}% to {np.nanmax(cev):+.2f}%)  ·  negative = worse off",
        source=f"{_SRC}.  {_BEQ_NOTE}.  {note}" if note else f"{_SRC}.  {_BEQ_NOTE}.",
        kicker="welfare: CEV by group", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- CEV channel decomposition: consumption vs labor (steady state, by group) ----

def cev_decomposition(base_ss, reform_ss, base_params, reform_params, out_dir, *, note=None,
                      name="welfare_cev_decomposition"):
    """Steady-state lifetime CEV by income group, split into the channel it travels through.
    The consumption-only partial CEV holds LABOR n at baseline and lets only c move to reform;
    the labor-only partial CEV holds c at baseline and lets only n move. Each is a separate
    nonlinear root-find on the consumption-scaling φ that equates baseline felicity to the
    channel-shifted felicity, so the two partials do NOT add up to the full CEV -- they read as
    'how much of the welfare move would this channel deliver on its own'. Grouped bars per group,
    sign-colored by the computed value."""
    fe = _Felicity(base_params)
    cb, nb = np.asarray(base_ss["c"], float), np.asarray(base_ss["n"], float)      # (S, J)
    cr, nr = np.asarray(reform_ss["c"], float), np.asarray(reform_ss["n"], float)
    chi = np.asarray(base_params.chi_n, float)[-1]                                  # SS row (S,)
    rho_b = np.asarray(base_params.rho, float)[-1]
    rho_r = np.asarray(reform_params.rho, float)[-1]
    J = cb.shape[1]
    # Consumption channel: reform c, baseline n.  Labor channel: baseline c, reform n.  Each is
    # solved by the same root-find as the full CEV, just with the relevant reform component swapped.
    cev_c = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cr[:, j], nb[:, j]),
                                     chi, rho_b, rho_r, j) for j in range(J)])
    cev_n = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cb[:, j], nr[:, j]),
                                     chi, rho_b, rho_r, j) for j in range(J)])
    lab = _labels(J, np.asarray(base_params.lambdas, float).ravel())

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.16, left=0.10, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    x = np.arange(J)
    bw = 0.38
    for off, vals in ((-bw / 2, cev_c), (bw / 2, cev_n)):
        ax.bar(x + off, vals, width=bw, color=style.signed(vals), zorder=2,
               edgecolor="white", linewidth=0.6)
    # hatch the labor-channel bars so the two channels read apart beyond color (color = sign only)
    for j in range(J):
        ax.bar(x[j] + bw / 2, cev_n[j], width=bw, fill=False, hatch="////",
               edgecolor="white", linewidth=0.0, zorder=3)
    for off, vals in ((-bw / 2, cev_c), (bw / 2, cev_n)):
        for j, v in enumerate(vals):
            if not np.isfinite(v):
                continue
            ax.annotate(f"{v:+.2f}", (x[j] + off, v), xytext=(0, -10 if v < 0 else 5),
                        textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                        fontsize=9, fontweight="bold", color=style.LOSS if v < 0 else style.GAIN)
    # Channels are read apart by fill (solid = consumption, hatched = labor) and explained in the
    # subtitle -- no floating legend box, which in a packed 7-group bar panel can only land on the data.
    ax.set_xticks(x)
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.margins(y=0.20)
    ax.set_ylabel("partial consumption-equivalent variation (%)")
    fin_c, fin_n = cev_c[np.isfinite(cev_c)], cev_n[np.isfinite(cev_n)]
    parts = []
    if fin_c.size:
        parts.append(f"consumption mean {np.mean(fin_c):+.2f}%")
    if fin_n.size:
        parts.append(f"labor mean {np.mean(fin_n):+.2f}%")
    means = "  ·  ".join(parts)
    style.title_block(
        fig, title="Lifetime CEV by income group: consumption vs labor channel",
        subtitle="Solid = consumption channel, hatched = labor channel  ·  partial CEVs, not additive"
                 + (f"  ·  {means}" if means else "") + "  ·  negative = worse off",
        source=f"{_SRC}.  {_BEQ_NOTE}.  {note}" if note else f"{_SRC}.  {_BEQ_NOTE}.",
        kicker="welfare: CEV decomposition", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# --- CEV by age at the reform (remaining lifetime, transition cohorts) -----------

def cev_by_age(base_tpi, reform_tpi, base_params, reform_params, out_dir, *, note=None,
               max_age=80, name="welfare_cev_by_age"):
    """Remaining-lifetime CEV for each cohort alive at the reform, by current age -- who, among
    people alive today, bears the cost. λ-weighted across income groups, with the group range as a
    band. Capped at ``max_age``: the extreme-old remaining-lifetime CEV is numerically ill-
    conditioned (a near-zero remaining-life utility blows up the ratio)."""
    fe = _Felicity(base_params)
    cB, nB = np.asarray(base_tpi["c"], float), np.asarray(base_tpi["n"], float)     # (T, S, J)
    cR, nR = np.asarray(reform_tpi["c"], float), np.asarray(reform_tpi["n"], float)
    chi_t = np.asarray(base_params.chi_n, float)                                    # (T+S, S)
    rhoB, rhoR = np.asarray(base_params.rho, float), np.asarray(reform_params.rho, float)
    lam = np.asarray(base_params.lambdas, float).ravel()
    S, E, J = fe.S, int(base_params.E), cB.shape[2]
    a_max = min(int(max_age) - E, S - 20)                                           # ≥20 periods left

    def diag(arr, a, j):    # cohort aged index a at t=0: ages a..S-1 over times 0..S-1-a
        return np.array([arr[t, a + t, j] for t in range(S - a)])

    max_cev = 0.05  # real signal is ~0.3%; |CEV|>5% is a root-find blow-up (e.g. at the labor=0
    #                 retirement kink or a near-zero remaining-life utility), not an economic result
    ages, cev_w, cev_lo, cev_hi = [], [], [], []
    for a in range(0, a_max + 1):
        chi = np.array([chi_t[t, a + t] for t in range(S - a)])
        rb = np.array([rhoB[t, a + t] for t in range(S - a)])
        rr = np.array([rhoR[t, a + t] for t in range(S - a)])
        cj = np.array([fe.cev((diag(cB, a, j), diag(nB, a, j)),
                              (diag(cR, a, j), diag(nR, a, j)), chi, rb, rr, j) for j in range(J)])
        ok = np.isfinite(cj) & (np.abs(cj) <= max_cev)
        if lam[ok].sum() < 0.5:                      # need most of the population to be reliable
            continue
        w = lam[ok] / lam[ok].sum()
        ages.append(E + a)
        cev_w.append(float(np.sum(w * cj[ok])) * 100)
        cev_lo.append(float(np.min(cj[ok])) * 100)
        cev_hi.append(float(np.max(cj[ok])) * 100)
    if not ages:
        return []
    ages = np.array(ages)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    style.zero_line(ax)
    col = style.LOSS if np.nanmean(cev_w) < 0 else style.GAIN  # sign-honest, not assumed-loss
    ax.fill_between(ages, cev_lo, cev_hi, color=col, alpha=0.10, zorder=1,
                    label="income-group range")
    ax.plot(ages, cev_w, color=col, lw=2.4, zorder=3)
    style.label_ends(ax, [(ages[-1], cev_w[-1], "population avg", col)])
    _retire = style.retire_age(base_params)
    if _retire is not None:
        ax.axvline(_retire, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=2)
        ax.annotate("retirement", (_retire, ax.get_ylim()[0]), xytext=(5, 6),
                    textcoords="offset points", fontsize=8.5, color=style.SUB)
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.16)
    ax.set_xlabel("age at the reform")
    ax.set_ylabel("remaining-lifetime CEV (%)")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Remaining-lifetime welfare effect by age (CEV)",
        subtitle=f"Remaining-lifetime CEV by age at the reform, λ-weighted  ·  ages {ages[0]}–{ages[-1]}",
        source=f"{_SRC}.  {_BEQ_NOTE}.  {note}" if note else f"{_SRC}.  {_BEQ_NOTE}.",
        kicker="welfare: CEV by age", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
