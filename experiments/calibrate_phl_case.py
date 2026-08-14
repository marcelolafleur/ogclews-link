#!/usr/bin/env python3
"""Apply every PHL calibration fix to a copy of a MUIO case, with sources recorded.

Read-only on the source case: the caller copies the case first and points this at
the copy. Every constant below carries its source in `SOURCES`, and every
judgment call is stated in `DECISIONS`. Run with --report to emit a JSON record
of exactly what changed.

Usage:
    python calibrate_phl_case.py --case <path to a COPY of the case> \\
        --discount-rate 0.10 --report out.json
    python calibrate_phl_case.py --case <path> --water-factor 10.77   # second pass

MUIO parameter locations (discovered, not assumed):
    R.json      DR      DiscountRate
    RT.json     OL      OperationalLife                    (one row, tech as key)
    RYT.json    CC      CapitalCost                        (row per tech, year keys)
                FC      FixedCost
                AF      AvailabilityFactor
                TAU     TotalTechnologyAnnualActivityUpperLimit
    RYTCM.json  OAR     OutputActivityRatio                (crop yields live here)
                IAR     InputActivityRatio                 (irrigation water here)
    RYTM.json   TAMLL   TechnologyActivityByModeLowerLimit (base-year land pins)
                TAMUL   TechnologyActivityByModeUpperLimit
    RYTTs.json  CF      CapacityFactor                     (per timeslice)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# --------------------------------------------------------------------------
# Land: crop yields. Targets are PSA 2020 harvested area, in 10^3 km2.
# Yield is scaled by (solved area / target area) so the solve lands on the
# target: area = demand / yield, and demand is exogenous.
# --------------------------------------------------------------------------
CROP_TARGETS = {
    # commodity: (solved area in the UNCALIBRATED case, PSA 2020 target, note)
    # Iteration 2: the first pass overshot because one national factor cannot
    # anticipate the model reallocating crops across eight clusters of differing
    # yield. These numerators are pass-1 factor x (pass-1 solved / target), i.e.
    # one step of a fixed-point iteration. Pass-1 results: RCP 49.620, MZE 31.226,
    # CON 37.307, SGC 3.991 (exact), TOM 6.109.
    "CRPRCP": (24.156, 47.189, "palay 4,718,896 ha, PSA OpenSTAT"),
    "CRPMZE": (10.990, 25.538, "corn 2,553,781 ha, PSA OpenSTAT"),
    "CRPCON": (31.687, 36.513, "coconut 3,651,289 ha, PSA OpenSTAT"),
    "CRPSGC": (22.181, 3.991, "sugarcane 399,086 ha, PSA OpenSTAT"),
    "CRPTOM": (12.625, 5.912, "vegetables+root crops 591,243 ha, PSA summed"),
    # CRPOTH deliberately untouched -- no observed counterpart exists. See DECISIONS.
}

# --------------------------------------------------------------------------
# Land: base-year cover, from the NAMRIA concordance. km2.
# mode 25 Barren, 26 Built-up, 27 Forest, 28 Grassland, 29 Other ag, 30 Water.
# `pin` is 'equality' (lower=upper), 'floor' (lower only) or None (free).
# --------------------------------------------------------------------------
LAND_MODES = {
    25: {"km2": 1595.0, "pin": "floor", "name": "Barren and sparsely vegetated"},
    26: {"km2": 10264.9, "pin": "equality", "name": "Built-up land"},
    # Forest is an EQUALITY, not a floor. Pass 1 used a floor and forest came out
    # at 134,225 km2 -- still absorbing the residual, because a floor does not stop
    # it rising and forest carries the -10 reward while grassland carries nothing.
    # An equality in the BASE YEAR ONLY forces the residual into grassland, which is
    # the intended swing pool. Later years stay free, so land-use change still runs.
    27: {"km2": 72319.4, "pin": "equality", "name": "Forest land"},
    # Grassland is left FREE and given its NAMRIA value as data only.
    #
    # Iteration 4 pinned it as a floor at 69,741 km2 so the residual land would be
    # LABELLED grassland rather than sitting in ENV_LAND's "Unallocated" backstop.
    # That was cosmetic and it cost solvability: with Forest, Built-up and Water as
    # equalities, Barren and Grassland as floors, and Cropland fixed by exogenous
    # demand, the 2020 constraints summed to EXACTLY the land-resource floor of
    # 295.8131 -- slack 0.0000. The feasible region collapsed to a single point, a
    # maximally degenerate vertex, and CBC ran 2.5 hours without converging against
    # the ~4 minutes iteration 3 took.
    #
    # So: accept the residual sitting in Unallocated. It is the same land and the
    # account still closes on the national total exactly; only the label differs, and
    # arguably "Unallocated" is the more honest label because the model has no reason
    # to call that land grassland. The lesson generalises: leave slack somewhere.
    28: {"km2": 77745.6, "pin": None, "name": "Grassland and woodland"},
    29: {"km2": 2287.9, "pin": None, "name": "Other agricultural land"},
    30: {"km2": 6319.8, "pin": "equality", "name": "Water bodies"},
}
LAND_CLUSTERS = [f"LNDAGRPHLC{i:02d}" for i in range(1, 9)]
# Cluster areas (km2) from the build's own land-cover summary; used to apportion
# the national class totals across clusters pro rata. See DECISIONS.
CLUSTER_AREA = {
    "LNDAGRPHLC01": 9111.5, "LNDAGRPHLC02": 23681.7, "LNDAGRPHLC03": 103214.9,
    "LNDAGRPHLC04": 27387.2, "LNDAGRPHLC05": 27179.9, "LNDAGRPHLC06": 18706.9,
    "LNDAGRPHLC07": 18385.0, "LNDAGRPHLC08": 68146.0,
}

# --------------------------------------------------------------------------
# Water. Irrigated-area cap in 10^3 km2 of harvested area.
# --------------------------------------------------------------------------
IRRIGATED_MODES = [1, 2, 5, 6, 7, 9, 10, 13, 16, 17, 19, 20, 21]  # the 'I' modes
IRRIGATED_CAP_KKM2 = 32.535  # PSA 2020 irrigated palay harvested area, 3,253,454 ha

# --------------------------------------------------------------------------
# Energy.
# --------------------------------------------------------------------------
CAPITAL_COST = {
    "PHL_POW_PP_COAL": (2200, 1605, "BNEF PHL 2025 Table 3; model sat at the US level"),
    "PHL_POW_PP_NUSMR": (4482, 8000, "NREL ATB 2024 Nuclear-Small Moderate, 2030"),
}
OPERATIONAL_LIFE = {
    "PHL_POW_PP_NUSMR": (60, 40, "60y is a mature-fleet design life; FOAK gets 40"),
    "PHL_POW_PP_HY_LA": (100, 60, "real PHL hydro 50-80y; 100 overstates"),
}
CAPACITY_FACTOR_SCALE = {
    # tech: (current annual CF, target annual CF, source)
    "PHL_POW_PP_WON_T1": (0.177, 0.267, "Burgos 150MW operator-reported 2019-24 mean"),
    "PHL_POW_PP_WOF_T1": (0.154, 0.450, "World Bank/ESMAP PHL Offshore Wind Roadmap"),
}
AVAILABILITY_FACTOR = {
    "PHL_POW_GEO_OLD": (1.0, 0.629, "PHL geothermal achieved 2024, DOE-derived"),
}
# Wind resource ceilings, PJ/yr.
#   onshore  664 PJ = 184.4 TWh -- NREL/USAID 2020 "Restricted" screened potential.
#   offshore 823 PJ = 228.6 TWh -- 58 GW (the upper bound of the World Bank/ESMAP
#            screened range 27-58 GW) at the roadmap's 45% capacity factor.
#
# The offshore cap was MISSED in the first calibration pass: onshore was capped and
# its sibling was left at the inherited 3,949 PJ placeholder. The consequence was
# real but much milder than the defect it replaced -- the model built 63.3 GW
# offshore, 1.09x the upper screened bound but 0.94x the capacity the Philippine DOE
# has already awarded in offshore service contracts, against onshore's 92% of the
# entire national resource on twice the available land. Fixing one resource ceiling
# without checking the technology that substitutes for it is the general trap.
WIND_ONSHORE_CAP_PJ = 664.0
WIND_OFFSHORE_CAP_PJ = 823.0

# The national land total, 10^3 km2, forced as a LOWER limit on the land resource.
# Iteration 2 lesson: pinning Forest to its observed value freed ~74,500 km2, and
# because nothing rewards Grassland and nothing requires land to be allocated, that
# land simply left the accounts -- total land fell from 295,813 to 221,292 km2. The
# "free swing pool" was a void, not a pool. Forcing MINLNDTOT to the national total
# makes all land be accounted for, so Grassland becomes the genuine residual.
LAND_RESOURCE_TOTAL_KKM2 = 295.8131

SOURCES = {
    "crops": "PSA OpenSTAT PX-Web API, Crops database, 2020 annual, national",
    "landcover": "PSA/NAMRIA Land Asset Accounts Table 1, 2020 closing stock "
                 "(PSA Special Release 2024-203); NAMRIA Land Cover Map 2020",
    "forest": "FAO FRA 2025, PHL forest area 7,226.39 thousand ha",
    "water": "FAO AQUASTAT var 4250 Agricultural water withdrawal, 67.965 km3/yr "
             "(2023, official). The ~33 km3 figure is var 4260 NET irrigation "
             "requirement; FAO's water requirement ratio of 51% links them.",
    "irrigated_area": "PSA 2020 irrigated palay harvested area 3,253,454 ha",
    "coal_capex": "BloombergNEF, The Philippines' Path to Clean and Affordable "
                  "Electricity, 3 Jun 2025, Appendix A Table 3 (nominal 2025 USD)",
    "smr_capex": "NREL ATB 2024, Nuclear-Small 300MWe, Moderate case 2030 (2022 USD)",
    "wind_onshore_cf": "First Gen Integrated Report 2024, Burgos 150 MW, "
                       "2019-24 mean 26.7% against a P50 design 27.5%",
    "wind_onshore_cap": "NREL/USAID 2020 Restricted potential 184.4 TWh/yr",
    "wind_offshore_cf": "World Bank/ESMAP Offshore Wind Roadmap for the "
                        "Philippines, Apr 2022, 45-47% CF",
    "wind_offshore_cap": "World Bank/ESMAP Offshore Wind Roadmap, 27-58 GW after "
                         "environmental and social screening; 58 GW at 45% CF",
    "geothermal_cf": "Derived from DOE Power Statistics 2024: generation / "
                     "(installed capacity x 8760) = 62.9% in 2024",
    "discount_neda": "NEDA/ICC Memorandum 30 Sep 2016, social discount rate "
                     "10% real (down from 15%), mandatory for public appraisal",
    "discount_ogphl": "OG-PHL solved baseline TPI, r_p first-decade mean 7.344% "
                      "-- the value ogclews_link.channels.emit_discount_rate writes",
}

DECISIONS = {
    "crop_targets_are_harvested_area": (
        "Targets are PSA HARVESTED area, not physical cropland. The model has no "
        "multi-cropping mechanism, so one crop mode occupies land for a year and "
        "harvested area equals occupied land. Consequence: total model cropland "
        "(~134 x10^3 km2) exceeds NAMRIA's physical crop cover (125.3), implying a "
        "cropping intensity of about 1.07. That is why Cropland is pinned as a "
        "FLOOR, not an equality -- the excess appears as explicit base-year "
        "conversion from grassland rather than as a hidden wrong forest number."),
    "crpoth_untouched": (
        "CRPOTH has no observed counterpart -- it is a residual 'other crops' "
        "aggregate. Scaling it would require inventing a target, so its yield is "
        "left alone and its ~15 x10^3 km2 is carried as-is."),
    "crptom_basis": (
        "CRPTOM is described as a GAEZ tomato proxy but its demand of 5.4996 Mt "
        "matches PSA's whole Vegetables-and-Root-Crops table (5.737 Mt), not "
        "tomatoes (0.222 Mt). The area target is therefore that table's 591,243 ha. "
        "FAOSTAT's Vegetables Primary aggregate was rejected: 80% of it is an "
        "imputed 'other vegetables n.e.c.' residual flagged I."),
    "cluster_apportionment": (
        "NAMRIA reports land cover nationally, not by the model's eight yield "
        "clusters. National class totals are apportioned pro rata to cluster area. "
        "This is an assumption, not data: it assumes each class is distributed "
        "uniformly across clusters, which is certainly false for Built-up. It is "
        "adopted because no cluster-level NAMRIA tabulation exists."),
    "forest_floor_not_equality": (
        "Forest is a floor so the model can still afforest, and cannot deforest "
        "below observed cover in the base year. An equality would forbid any land-use "
        "change, which is the point of the model."),
    "grassland_free": (
        "Grassland and woodland is the deliberate swing pool. It gets its base-year "
        "value as data but no floor, so it absorbs residuals and donates land to "
        "cropping -- the role Forest was wrongly playing."),
    "lives_mostly_unchanged": (
        "An earlier audit in this repo reported gas at 100 years, solar at 60 and "
        "hydro at 25. That was a column-misalignment in parsing the generated "
        "datafile. The authoritative MUIO JSON has gas 25, solar 30, hydro 100, "
        "SMR 60 -- broadly sensible. Only hydro (100 to 60) and SMR (60 to 40, "
        "first-of-a-kind) are adjusted."),
    "fuel_prices_unchanged": (
        "Imported coal at 3.03 rising to 4.00 USD/GJ is 22% above the 2020 actual "
        "of 2.48 but brackets 2023-24 actuals (5.07, 3.76). Revising the path is a "
        "price forecast, not a calibration, so it is left alone and flagged."),
    "coal_availability_unchanged": (
        "PHL coal plant achieves 69.5% utilisation, but in OSeMOSYS utilisation is "
        "endogenous and AvailabilityFactor is a ceiling. Capping it at 0.695 would "
        "force rather than reproduce. Geothermal is different -- it is baseload and "
        "resource-limited, so 62.9% is a genuine availability ceiling."),
    "irrigated_cap_non_binding": (
        "The irrigated-area cap of 32.535 x10^3 km2 is set at observed irrigated "
        "palay harvested area and does NOT bind at present (the model uses ~25). It "
        "is a calibration guard against runaway irrigation, not a policy constraint."),
}


def load(p: Path):
    with p.open() as f:
        return json.load(f)


def save(p: Path, d) -> None:
    with p.open("w") as f:
        json.dump(d, f)


def year_keys(row: dict) -> list[str]:
    return [k for k in row if k.isdigit()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", required=True, type=Path, help="a COPY of the case")
    ap.add_argument("--discount-rate", type=float, default=0.10)
    ap.add_argument("--water-factor", type=float, default=None,
                    help="scale AGRWATPHL by this; omit on pass 1, supply on pass 2")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    C = args.case
    if not (C / "genData.json").is_file():
        raise SystemExit(f"not a MUIO case: {C}")

    g = load(C / "genData.json")
    tid = {t["Tech"]: t["TechId"] for t in g["osy-tech"]}
    cid = {c["Comm"]: c["CommId"] for c in g["osy-comm"]}
    changed: dict[str, object] = {}

    # 1 -- discount rate ---------------------------------------------------
    p = C / "R.json"; d = load(p)
    old = d["DR"]["SC_0"][0]["value"]
    d["DR"]["SC_0"][0]["value"] = args.discount_rate
    save(p, d)
    changed["discount_rate"] = {"from": old, "to": args.discount_rate}

    # 2 -- crop yields and irrigation water (RYTCM: OAR, IAR) --------------
    p = C / "RYTCM.json"; d = load(p)
    yfac = {cid[k]: v[0] / v[1] for k, v in CROP_TARGETS.items() if k in cid}
    n_oar = 0
    for rows in d["OAR"].values():
        for r in rows:
            f = yfac.get(r.get("CommId"))
            if f is None:
                continue
            for k in year_keys(r):
                if isinstance(r[k], (int, float)):
                    r[k] = r[k] * f
            n_oar += 1
    changed["crop_yield_rows"] = n_oar
    changed["crop_yield_factors"] = {
        k: round(v[0] / v[1], 6) for k, v in CROP_TARGETS.items()}

    if args.water_factor:
        agr = cid.get("AGRWATPHL")
        n_iar = 0
        for rows in d["IAR"].values():
            for r in rows:
                if r.get("CommId") != agr:
                    continue
                for k in year_keys(r):
                    if isinstance(r[k], (int, float)):
                        r[k] = r[k] * args.water_factor
                n_iar += 1
        changed["irrigation_rows"] = n_iar
        changed["irrigation_factor"] = args.water_factor
    save(p, d)
    del d

    # 3 -- energy costs, lives, availability, wind ceiling -----------------
    p = C / "RT.json"; d = load(p)
    row = d["OL"]["SC_0"][0]
    ol_ch = {}
    for t, (was, now, _) in OPERATIONAL_LIFE.items():
        if tid.get(t) in row:
            ol_ch[t] = {"from": row[tid[t]], "to": now}
            row[tid[t]] = now
    save(p, d); changed["operational_life"] = ol_ch

    p = C / "RYT.json"; ryt = load(p)

    def patch_ryt(doc, key, tech, value):
        """Set every year of `key` for `tech` to `value`, in every scenario."""
        for rows in doc[key].values():
            for r in rows:
                if r.get("TechId") == tid[tech]:
                    for k in year_keys(r):
                        if isinstance(r[k], (int, float)):
                            r[k] = value

    cc_ch = {}
    for t, (was, now, _) in CAPITAL_COST.items():
        patch_ryt(ryt, "CC", t, now); cc_ch[t] = {"from": was, "to": now}
    changed["capital_cost"] = cc_ch
    af_ch = {}
    for t, (was, now, _) in AVAILABILITY_FACTOR.items():
        patch_ryt(ryt, "AF", t, now); af_ch[t] = {"from": was, "to": now}
    changed["availability_factor"] = af_ch
    # wind resource ceilings -- keep the 2020 values (observed), cap later years
    for tech, cap in (("PHL_POW_PP_WON_T1", WIND_ONSHORE_CAP_PJ),
                      ("PHL_POW_PP_WOF_T1", WIND_OFFSHORE_CAP_PJ)):
        for rows in ryt["TAU"].values():
            for r in rows:
                if r.get("TechId") != tid.get(tech):
                    continue
                for k in year_keys(r):
                    if k != "2020" and isinstance(r[k], (int, float)) and r[k] > cap:
                        r[k] = cap
    # force the land resource to the full national total -- on BOTH sides. The floor (TAL)
    # makes all land be accounted for; the ceiling (TAU) is the §14 lesson from the
    # forest-carbon falsification: with a floor only, the endowment is an open bound, and
    # the moment ANY future term makes land valuable (the -10 forest reward already does)
    # the LP can conjure land -- the symmetric-price test "planted" 300 Philippines and
    # collected $43bn before the ceiling existed. The endowment is a physical fact; pinning
    # it both ways is doctrine-consistent (phl-testcase-plan.md sections 12 and 14).
    for blk in ("TAL", "TAU"):
        for rows in ryt[blk].values():
            for r in rows:
                if r.get("TechId") == tid.get("MINLNDTOT"):
                    for k in year_keys(r):
                        if isinstance(r[k], (int, float)):
                            r[k] = LAND_RESOURCE_TOTAL_KKM2
    save(p, ryt)
    changed["wind_onshore_cap_pj"] = WIND_ONSHORE_CAP_PJ
    changed["wind_offshore_cap_pj"] = WIND_OFFSHORE_CAP_PJ
    changed["land_resource_floor_kkm2"] = LAND_RESOURCE_TOTAL_KKM2
    del ryt

    # 4 -- capacity factors (RYTTs) ---------------------------------------
    p = C / "RYTTs.json"; d = load(p)
    cf_fac = {tid[t]: tgt / cur for t, (cur, tgt, _) in CAPACITY_FACTOR_SCALE.items()
              if t in tid}
    n_cf = 0
    for rows in d["CF"].values():
        for r in rows:
            f = cf_fac.get(r.get("TechId"))
            if f is None:
                continue
            for k in year_keys(r):
                if isinstance(r[k], (int, float)):
                    r[k] = min(r[k] * f, 1.0)
            n_cf += 1
    save(p, d)
    changed["capacity_factor_rows"] = n_cf
    changed["capacity_factor_scales"] = {
        t: round(tgt / cur, 4) for t, (cur, tgt, _) in CAPACITY_FACTOR_SCALE.items()}
    del d

    # 5 -- base-year land-cover pins and the irrigated-area cap (RYTM) -----
    p = C / "RYTM.json"; d = load(p)
    total_area = sum(CLUSTER_AREA.values())
    ll = {r["TechId"] + "|" + str(r["MoId"]): r for r in d["TAMLL"]["SC_0"]}
    ul = {r["TechId"] + "|" + str(r["MoId"]): r for r in d["TAMUL"]["SC_0"]}
    pins = {}
    for cl in LAND_CLUSTERS:
        share = CLUSTER_AREA[cl] / total_area
        for mode, spec in LAND_MODES.items():
            if spec["pin"] is None:
                continue
            kkm2 = spec["km2"] * share / 1000.0     # km2 -> 10^3 km2
            k = f"{tid[cl]}|{mode}"
            if k in ll:
                ll[k]["2020"] = kkm2
            if spec["pin"] == "equality" and k in ul:
                ul[k]["2020"] = kkm2
            pins.setdefault(spec["name"], {"pin": spec["pin"], "national_km2": spec["km2"]})
    # irrigated-area cap, national, apportioned pro rata, applied to all years
    for cl in LAND_CLUSTERS:
        share = CLUSTER_AREA[cl] / total_area
        # Deliberately NOT share-scaled. Pass 1 scaled the cap by cluster area,
        # which made it bind per mode per cluster and collapsed irrigated area from
        # 25.0 to 8.1 x10^3 km2 -- distorting the solution rather than guarding it.
        # Each mode now carries the NATIONAL figure, so no single mode-cluster pair
        # is constrained and the cap only stops any one of them exceeding the
        # national irrigated total. The national sum is not enforceable with a
        # per-mode parameter; that limitation is accepted and recorded.
        del share
        for mode in IRRIGATED_MODES:
            k = f"{tid[cl]}|{mode}"
            if k in ul:
                for yk in year_keys(ul[k]):
                    ul[k][yk] = IRRIGATED_CAP_KKM2
    save(p, d)
    changed["land_pins"] = pins
    changed["irrigated_cap_kkm2"] = IRRIGATED_CAP_KKM2
    del d

    print(f"calibrated {C.name}")
    for k, v in changed.items():
        print(f"  {k}: {json.dumps(v)[:150]}")
    if args.report:
        args.report.write_text(json.dumps(
            {"case": C.name, "changed": changed,
             "sources": SOURCES, "decisions": DECISIONS}, indent=2) + "\n")
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
