"""Extract the energy-price signal from a CLEWS run.

Two sources, in increasing rigor:

  * ``cost_of_electricity_ratio`` -- reads the curated "Cost of electricity
    generation" workbook each scenario already ships. An *average* cost index; a
    serviceable first proxy for the price the household should face.

  * the *rigorous* source -- the dual of the OSeMOSYS commodity-balance constraint
    (``EBa11``/``EBb4``), i.e. the *marginal* cost of the commodity -- is implemented
    in ``signals.commodity_shadow_price`` (it reads a MUIOGO CBC dual export). NOT in
    default CLEWS output; the solver must emit marginals. This is the highest-value,
    least-exposed CLEWS output and the object the de novo analysis identifies as
    load-bearing.
"""
from __future__ import annotations

import pandas as pd


def cost_of_electricity_ratio(base_xlsx: str, reform_xlsx: str, *, sheet=0,
                              row_match="average electricity cost"):
    """Reform/base ratio of the electricity cost index, by year.

    The CLEWS "Cost of electricity generation" workbook is a metrics x years grid:
    the cost lives in a labeled ROW ("Average electricity cost (USD/kWh)"), with
    calendar years as integer column headers. Returns a pandas Series indexed by year
    (reform / base), e.g. 1.10 == reform electricity is 10% costlier that year.
    """
    def _read(path):
        df = pd.read_excel(path, sheet_name=sheet)
        label_col = df.columns[0]
        mask = df[label_col].astype(str).str.lower().str.contains(row_match)
        if not mask.any():
            raise ValueError(f"no row matching {row_match!r} in {path}")
        row = df[mask].iloc[0]
        year_cols = [c for c in df.columns if str(c).strip().isdigit()]
        years = [int(str(c)) for c in year_cols]
        vals = pd.to_numeric(pd.Series(row[year_cols].values), errors="coerce")
        return pd.Series(vals.values, index=years, dtype=float).dropna()

    base, reform = _read(base_xlsx), _read(reform_xlsx)
    common = base.index.intersection(reform.index)
    return (reform.loc[common] / base.loc[common]).sort_index()
