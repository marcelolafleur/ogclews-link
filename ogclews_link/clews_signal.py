"""Extract the energy-price signal from a CLEWS run.

Two sources, in increasing rigor:

  * ``cost_of_electricity_ratio`` -- reads the curated "Cost of electricity
    generation" workbook each scenario already ships. An *average* cost index; a
    serviceable first proxy for the price the household should face.

  * ``commodity_shadow_price`` -- the rigorous source: the dual of the OSeMOSYS
    commodity-balance constraint (``EBa11``/``EBb4``), i.e. the *marginal* cost of
    the commodity. NOT in default output; the solver must be configured to emit
    marginals (GLPK ``--wglp`` + marginals, CPLEX ``.sol`` dual section, or a
    pyomo/otoole stack). This is the highest-value, least-exposed CLEWS output and
    the object the de novo analysis identifies as load-bearing.
"""
from __future__ import annotations

import pandas as pd


def cost_of_electricity_ratio(base_xlsx: str, reform_xlsx: str, *, sheet=0, year_col=None, value_col=None):
    """Reform/base ratio of the electricity cost index, by year.

    The workbook layout is curated, not standardized -- pass ``sheet``/``year_col``/
    ``value_col`` once you've eyeballed it. Returns a pandas Series indexed by year
    (reform / base), e.g. 1.10 == reform electricity is 10% costlier that year.
    """
    def _read(path):
        df = pd.read_excel(path, sheet_name=sheet)
        if year_col and value_col:
            s = df.set_index(year_col)[value_col]
        else:
            # best-effort: first column = years, last numeric column = cost
            s = df.set_index(df.columns[0]).select_dtypes("number").iloc[:, -1]
        return pd.to_numeric(s, errors="coerce").dropna()

    base, reform = _read(base_xlsx), _read(reform_xlsx)
    common = base.index.intersection(reform.index)
    return (reform.loc[common] / base.loc[common]).sort_index()


def commodity_shadow_price(*args, **kwargs):  # pragma: no cover
    """Dual of the commodity-balance constraint = the marginal energy price.

    Not implementable from the curated CSV/xlsx exports -- it requires the LP duals.
    To produce it: re-run the CLEWS scenario with the solver emitting marginals and
    read the multiplier on ``EBa11_EnergyBalanceEachTS5`` (timeslice) or
    ``EBb4_EnergyBalanceEachYear4`` (annual) for the electricity commodity, then
    un-discount by (1 + DiscountRate)^(y - y0) and demand-weight slices to annual.
    Belongs to the MUIOGO-orchestrated path where CLEWS is actually re-run.
    """
    raise NotImplementedError(
        "Commodity shadow price needs CLEWS re-run with solver marginals enabled. "
        "See docstring; use cost_of_electricity_ratio() as the first-pass proxy."
    )
