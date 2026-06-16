"""Age profile of pollution-attributable mortality h(s) for the health channel.

The method is the one in DeBacker, Evans & LaFleur "The Macroeconomic Returns to Public
Health Investments" (the CostOfDisease repo): an age-specific mortality shock
rho(s,t) = rho0 + kappa * g_t * h(s), phased in, then the population is recomputed.

h(s) is a *relative age shape* (normalized to peak 1); the magnitude is carried by kappa
(the dose-response), so the scale of the profile does not matter -- only the age pattern.

DATA: the real h(s) must come from IHME GBD (deaths attributable to ambient particulate
matter pollution, by age, Philippines) -- see DATA.md for the exact query. Until that CSV
is on disk, placeholder_profile() supplies a clearly-flagged elderly-skewed shape so the
mechanism runs; it is NOT calibrated.
"""
from __future__ import annotations

import csv

import numpy as np

# GBD fine, non-overlapping age bins -> (anchor age = bin midpoint, single ages covered).
# Same bins the HIV profile builder uses (build_hiv_mortality_profile.py).
GBD_GROUPS = [
    ("<1 year", 0.0, [0]), ("12-23 months", 1.0, [1]), ("2-4 years", 3.0, [2, 3, 4]),
    ("5-9 years", 7.0, list(range(5, 10))), ("10-14 years", 12.0, list(range(10, 15))),
    ("15-19 years", 17.0, list(range(15, 20))), ("20-24 years", 22.0, list(range(20, 25))),
    ("25-29 years", 27.0, list(range(25, 30))), ("30-34 years", 32.0, list(range(30, 35))),
    ("35-39 years", 37.0, list(range(35, 40))), ("40-44 years", 42.0, list(range(40, 45))),
    ("45-49 years", 47.0, list(range(45, 50))), ("50-54 years", 52.0, list(range(50, 55))),
    ("55-59 years", 57.0, list(range(55, 60))), ("60-64 years", 62.0, list(range(60, 65))),
    ("65-69 years", 67.0, list(range(65, 70))), ("70-74 years", 72.0, list(range(70, 75))),
    ("75-79 years", 77.0, list(range(75, 80))), ("80-84 years", 82.0, list(range(80, 85))),
    ("85-89 years", 87.0, list(range(85, 90))), ("90-94 years", 92.0, list(range(90, 95))),
    ("95+ years", 97.0, list(range(95, 100))),
]


def _to_shape(rates_by_age: np.ndarray) -> np.ndarray:
    """Normalize an age-rate vector to a relative shape with peak 1 (kappa carries magnitude)."""
    rates_by_age = np.asarray(rates_by_age, dtype=float)
    peak = rates_by_age.max()
    return rates_by_age / peak if peak > 0 else rates_by_age


def build_profile_from_gbd(csv_path: str, location_name: str, year: int,
                           key_col: str = "rei_name",
                           key_value: str = "Ambient particulate matter pollution",
                           num_ages: int = 100) -> np.ndarray:
    """Build h(s) from an IHME GBD Results CSV, replicating build_hiv_mortality_profile.py:
    take the 'Rate' rows for the matching location/year/risk, anchor each fine age bin at its
    midpoint, PCHIP-interpolate in log-rate space to single ages, flat-fill past the last
    anchor. Returns a length-num_ages relative shape (peak 1). For a *risk* export use
    key_col='rei_name'; for a *cause* export use key_col='cause_name'.
    """
    from scipy.interpolate import PchipInterpolator

    labels = {g[0] for g in GBD_GROUPS}
    anchor = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("location_name") == location_name and row.get("sex_name") == "Both"
                    and int(row["year"]) == year and row.get("measure_name") == "Deaths"
                    and row.get(key_col) == key_value and row.get("metric_name") == "Rate"
                    and row.get("age_name") in labels):
                anchor[row["age_name"]] = float(row["val"]) / 100_000.0
    missing = labels - set(anchor)
    if missing:
        raise ValueError(f"GBD CSV missing age bins {sorted(missing)} for {key_value}/{location_name}/{year}")
    ages = np.array([g[1] for g in GBD_GROUPS])
    rates = np.array([max(anchor[g[0]], 1e-12) for g in GBD_GROUPS])
    fit = PchipInterpolator(ages, np.log(rates), extrapolate=False)
    out = np.zeros(num_ages)
    last = int(ages[-1])
    out[: last + 1] = np.exp(fit(np.arange(last + 1, dtype=float)))
    out[last + 1:] = rates[-1]
    return _to_shape(np.maximum(out, 0.0))


def total_deaths_from_gbd(csv_path: str, location_name: str, year: int,
                          key_col: str = "rei_name",
                          key_value: str = "Ambient particulate matter pollution") -> float:
    """Total attributable deaths -- the ``excess_deaths`` TARGET for the disease_pop calibration --
    from the SAME IHME GBD export used for h(s), via its ``Number`` metric (deaths counts, not the
    per-100k rate). Prefers an 'All ages' row; otherwise sums the fine non-overlapping age bins.

    Pairing this with build_profile_from_gbd makes BOTH the age shape AND the magnitude GBD-sourced
    (COD-HIV took the shape from GBD but the total from a separate estimate; for pollution GBD gives
    both). For a *risk* export use key_col='rei_name'; for a *cause* export use key_col='cause_name'.
    """
    bin_labels = {g[0] for g in GBD_GROUPS}
    all_ages, bin_total, seen = None, 0.0, set()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if not (row.get("location_name") == location_name and row.get("sex_name") == "Both"
                    and int(row["year"]) == year and row.get("measure_name") == "Deaths"
                    and row.get(key_col) == key_value and row.get("metric_name") == "Number"):
                continue
            age = row.get("age_name")
            if age == "All ages":
                all_ages = float(row["val"])
            elif age in bin_labels and age not in seen:
                seen.add(age)
                bin_total += float(row["val"])
    if all_ages is not None:
        return all_ages
    if seen:
        return bin_total
    raise ValueError(f"GBD CSV has no 'Number' (deaths-count) rows for "
                     f"{key_value}/{location_name}/{year}")


def placeholder_profile(num_ages: int = 100) -> np.ndarray:
    """PLACEHOLDER elderly-skewed age shape (peak 1) -- NOT calibrated. Pollution-attributable
    mortality concentrates at older ages (cardiopulmonary); this is a smooth stand-in until the
    real GBD profile (DATA.md) is loaded. The SHAPE matters; magnitude is set by kappa."""
    s = np.arange(num_ages, dtype=float)
    shape = 1.0 / (1.0 + np.exp(-(s - 68.0) / 8.0))  # logistic rising through the 60s-70s
    shape[s < 30] *= 0.02                             # near-zero pollution mortality in the young
    return _to_shape(shape)


def load_profile(path: str) -> np.ndarray:
    """Load a saved 1-column age profile (the build_*_profile output format), as a peak-1 shape."""
    return _to_shape(np.loadtxt(path, delimiter=","))
