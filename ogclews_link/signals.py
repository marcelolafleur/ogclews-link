"""Signal extraction: turn CLEWS run outputs (and OG-Core results) into the series the
channels consume. Handles the two CLEWS CSV layouts (the 'Sum of ...' pivot and plain
long r,t,*,y,value) and the 999999 sentinel.

Two energy-price signals live here: the cost-index PROXY (cost_of_electricity_ratio) and
the RIGOROUS one -- the dual of the OSeMOSYS commodity-balance constraint (the marginal
energy price). MUIOGO's CBC solve (`-printing all`) already exports that dual to
`res/<run>/csv/EBb4_EnergyBalanceEachYear4_ICR.csv` (columns r,f,y,dual,DiscountRate),
indexed by (region, fuel, year); read it via commodity_shadow_price() /
commodity_shadow_price_ratio().
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

from .clews_signal import cost_of_electricity_ratio  # re-exported

SENTINEL = 999999.0
__all__ = ["cost_of_electricity_ratio", "read_clews_matrix", "read_clews_long",
           "power_capex_increment", "emissions_by_year", "emissions_ratio",
           "og_sector_output", "og_consumption_good", "og_interest_rate",
           "commodity_shadow_price", "commodity_shadow_price_ratio"]


def _find(scenario_dir: str, metric: str, exclude: str = "") -> str:
    hits = sorted(glob.glob(os.path.join(scenario_dir, f"*{metric}*.csv")))
    if exclude:
        hits = [h for h in hits if exclude.lower() not in os.path.basename(h).lower()] or hits
    # prefer the exact-suffix match (".../<...>Metric.csv")
    exact = [h for h in hits if os.path.basename(h).replace(" ", "").lower().endswith(metric.lower() + ".csv")]
    if exact:
        return exact[0]
    if hits:
        return hits[0]
    raise FileNotFoundError(f"no '*{metric}*.csv' in {scenario_dir}")


def read_clews_matrix(path: str) -> pd.DataFrame:
    """CLEWS per-technology x year export -> DataFrame indexed by technology, int YEAR
    columns, sentinels zeroed. Handles the 'Sum of ...' pivot banner; falls back to a
    long r,t,y,value file (pivoted to tech x year)."""
    raw = pd.read_csv(path, header=None, dtype=str)

    def yr_cells(row):
        return sum(1 for x in row if str(x).strip().isdigit() and 2000 <= int(str(x).strip()) <= 2100)

    hdr = max(range(min(len(raw), 6)), key=lambda i: yr_cells(raw.iloc[i]))
    if yr_cells(raw.iloc[hdr]) >= 3:  # pivot: years across the header row
        cols = [str(x).strip() for x in raw.iloc[hdr]]
        body = raw.iloc[hdr + 1:].copy()
        body.columns = cols
        year_cols = [c for c in cols if c.isdigit() and 2000 <= int(c) <= 2100]
        label_col = cols[0]
        body = body[[label_col] + year_cols].dropna(subset=[label_col])
        body = body[~body[label_col].astype(str).str.lower().str.contains("grand total|sum of", na=False)]
        df = body.set_index(label_col)
        df.columns = [int(c) for c in year_cols]
    else:  # long: region, tech, year, value
        long = pd.read_csv(path)
        cols = list(long.columns)
        lower = [c.lower() for c in cols]
        ycol = next(c for c in cols if long[c].astype(str).str.fullmatch(r"\d{4}").all())
        vcol = cols[-1]
        tcol = cols[1] if len(cols) >= 4 else cols[0]
        # if multiple emission species / modes are present, keep the first emission so the
        # pivot does not silently sum CO2e + PM2.5 (or across modes) into one number
        for disc in ("e", "emission"):
            if disc in lower:
                ec = cols[lower.index(disc)]
                long = long[long[ec] == long[ec].iloc[0]]
                break
        df = long.pivot_table(index=tcol, columns=ycol, values=vcol, aggfunc="sum")
        df.columns = [int(c) for c in df.columns]
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    df[df >= SENTINEL] = 0.0
    return df


def read_clews_long(path: str, value_col: str | None = None) -> pd.DataFrame:
    """Plain long CLEWS file (e.g. r,t,e,y,value or r,l,f,y,Demand) as a DataFrame."""
    df = pd.read_csv(path)
    if value_col is None:
        value_col = df.columns[-1]
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)
    return df


def power_capex_increment(base_dir, reform_dir, country, public_only=False) -> pd.Series:
    """Reform-minus-base CLEWS CapitalInvestment summed over power technologies, by year.
    This is the extra capital the transition requires -- the investment-channel signal."""
    def _sum(folder):
        m = read_clews_matrix(_find(folder, "CapitalInvestment"))
        keep = [t for t in m.index if (country.is_public(t) if public_only else country.is_power(t))]
        return m.loc[keep].sum(axis=0)
    base, reform = _sum(base_dir), _sum(reform_dir)
    years = sorted(set(base.index) & set(reform.index))
    return (reform.loc[years] - base.loc[years]).sort_index()


def emissions_by_year(scenario_dir, country, species=None) -> pd.Series:
    """Total emissions of `species` (default ``country.co2_emission``, e.g. CO2e; the health channel
    passes ``country.health_emission`` = PM2.5) by year. Prefers the *ByMode variant, which is present
    for BOTH base and reform here, so the two sides are aggregated identically (avoids a
    base=ByMode / reform=plain mismatch); summing over modes recovers the total."""
    try:
        path = _find(scenario_dir, "AnnualTechnologyEmissionByMode")
    except FileNotFoundError:
        path = _find(scenario_dir, "AnnualTechnologyEmission")
    df = read_clews_long(path)
    cols = {c.lower(): c for c in df.columns}
    ycol = cols.get("y") or next(c for c in df.columns if df[c].astype(str).str.fullmatch(r"\d{4}").all())
    ecol = cols.get("e")
    vcol = df.columns[-1]
    if ecol is not None:
        df = df[df[ecol].astype(str).str.contains(species or country.co2_emission, case=False, na=False)]
    return df.groupby(ycol)[vcol].sum().sort_index()


def emissions_ratio(base_dir, reform_dir, country, species=None) -> pd.Series:
    base, reform = (emissions_by_year(base_dir, country, species),
                    emissions_by_year(reform_dir, country, species))
    years = sorted(set(base.index) & set(reform.index))
    b = base.loc[years].replace(0.0, np.nan)
    return (reform.loc[years] / b).sort_index()


# --- OG-Core output extractors (for og->clews and recycling channels) -----------

def og_sector_output(tpi: dict, m: int) -> np.ndarray:
    return np.asarray(tpi["Y_m"])[:, m]


def og_consumption_good(tpi: dict, i: int) -> np.ndarray:
    return np.asarray(tpi["C_i"])[:, i]


def og_interest_rate(tpi: dict, key: str = "r_p") -> np.ndarray:
    return np.asarray(tpi[key])


_DUAL_CONSTRAINT = "EBb4_EnergyBalanceEachYear4_ICR"  # OSeMOSYS annual commodity balance


def commodity_shadow_price(source, *, fuel=None, undiscount=True, start_year=None,
                           constraint=_DUAL_CONSTRAINT) -> pd.Series:
    """The rigorous energy price: the annual dual of the OSeMOSYS commodity-balance
    constraint, as exported by a MUIOGO CBC solve to
    `res/<run>/csv/EBb4_EnergyBalanceEachYear4_ICR.csv` (columns r,f,y,<dual>,DiscountRate).
    Returns a Series indexed by int year for the chosen fuel(s).

    ``source`` is that CSV file, or a run/csv directory containing it. ``fuel`` selects the
    commodity good households face: a code (e.g. 'ELC001') or list of codes; default matches
    electricity codes (prefix 'ELC'). MUIOGO writes the dual *discounted* to start-year PV
    (raw x (1+DR)^(y-start_year+0.5)); ``undiscount=True`` recovers the raw per-year marginal
    (the genuine shadow price in that year). ``start_year`` defaults to the first year present.
    """
    path = source if os.path.isfile(source) else _find(source, constraint.split("_", 1)[0])
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    low = {c.lower(): c for c in df.columns}
    rcol, fcol, ycol = low["r"], low["f"], low["y"]
    dr_col = low.get("discountrate")
    val_col = next((c for c in df.columns if "energybalance" in c.lower()), None)
    if val_col is None:  # fall back to the lone remaining numeric column
        val_col = next(c for c in df.columns if c not in (rcol, fcol, ycol, dr_col))
    df[ycol] = pd.to_numeric(df[ycol], errors="coerce")
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

    if fuel is None:
        mask = df[fcol].astype(str).str.upper().str.startswith("ELC")
    else:
        codes = [fuel] if isinstance(fuel, str) else list(fuel)
        mask = df[fcol].astype(str).isin(codes)
    sub = df[mask].dropna(subset=[ycol, val_col]).copy()
    if sub.empty:
        present = sorted(df[fcol].astype(str).unique())
        raise ValueError(f"commodity_shadow_price: no rows for fuel={fuel!r} in {path}; "
                         f"fuels present: {present[:15]}{'...' if len(present) > 15 else ''}")
    if undiscount and dr_col is not None:
        dr = pd.to_numeric(sub[dr_col], errors="coerce").fillna(0.0)
        sy = int(start_year) if start_year is not None else int(sub[ycol].min())
        sub[val_col] = sub[val_col] / (1.0 + dr) ** (sub[ycol].astype(float) - sy + 0.5)
    s = sub.groupby(ycol)[val_col].mean().sort_index()   # mean across matched fuels (usually one)
    s.index = s.index.astype(int)
    return s.rename("shadow_price")


def commodity_shadow_price_ratio(base_source, reform_source, *, fuel=None,
                                 undiscount=True, start_year=None) -> pd.Series:
    """Reform/baseline annual energy shadow-price ratio -- the rigorous analogue of
    cost_of_electricity_ratio(), to drive the energy_price channel from the true LP dual
    instead of the cost-index proxy. Ratio by year (reform shadow price / baseline)."""
    b = commodity_shadow_price(base_source, fuel=fuel, undiscount=undiscount, start_year=start_year)
    r = commodity_shadow_price(reform_source, fuel=fuel, undiscount=undiscount, start_year=start_year)
    years = sorted(set(b.index) & set(r.index))
    bb = b.loc[years].replace(0.0, np.nan)
    return (r.loc[years] / bb).sort_index()
