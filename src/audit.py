"""Dataset audit -> reports/data_quality_report.md and outputs/audit_*.csv.

Audits the organizer (base-truth) data WITHOUT modifying it, summarises the arithmetic
validation of every transcribed external table, and records conflicts between sources.
"""
from __future__ import annotations

import pandas as pd

from . import config as C
from .integrity import load_original, verify_originals


def _md(df: pd.DataFrame, floatfmt: str = "{:,.3f}") -> str:
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else floatfmt.format(v))
    head = "| " + " | ".join(map(str, d.columns)) + " |\n|" + "---|" * len(d.columns) + "\n"
    return head + "\n".join("| " + " | ".join(map(str, r)) + " |" for r in d.values.tolist())


def organizer_audit(df: pd.DataFrame) -> dict:
    d = df.sort_values(["State", "Year"]).reset_index(drop=True)
    res: dict = {}
    res["shape"] = d.shape
    res["columns"] = pd.DataFrame({
        "column": d.columns,
        "dtype": [str(t) for t in d.dtypes],
        "unit / meaning (from upstream README + inspection)": [
            "State/UT name", "Year (calendar vs financial year NOT stated)", "Installed capacity, MW",
            "Installed capacity, MW", "Installed capacity, MW", "Installed capacity, MW",
            "Organizer zone label (6-zone scheme; differs from CEA grid regions)", "Installed capacity, MW",
            "Persons (estimated)", "Nominal GSDP, INR crore (not inflation-adjusted)"],
        "used_in_models": ["key", "key", "NO (capacity)", "NO (capacity)", "NO (capacity)", "NO (capacity)",
                            "audit only", "NO (capacity)", "YES (demand proxy)", "YES (demand proxy)"],
    })
    res["missing"] = int(d.isna().sum().sum())
    res["dup_state_year"] = int(d.duplicated(["State", "Year"]).sum())
    cov = d.groupby("State").agg(first_year=("Year", "min"), last_year=("Year", "max"), n_years=("Year", "nunique"))
    cov["missing_years"] = [sorted(set(range(r.first_year, r.last_year + 1)) - set(d[d.State == s].Year))
                            for s, r in cov.iterrows()]
    res["coverage_gaps"] = cov[(cov.n_years < 19)].reset_index()
    cap = [c for c in d.columns if c.startswith("Installed")]
    rows = []
    for c in cap + ["Population", "GSDP (crore INR)"]:
        dd = d.groupby("State")[c].diff()
        rows.append({"column": c, "year_on_year_decreases": int((dd < 0).sum()),
                     "exact_repeats_of_previous_year": int((dd == 0).sum()), "zeros": int((d[c] == 0).sum())})
    res["yoy"] = pd.DataFrame(rows)
    # GSDP repeats (possible carried-forward / imputed values)
    rep = d[d.groupby("State")["GSDP (crore INR)"].diff() == 0][["State", "Year", "GSDP (crore INR)"]]
    res["gsdp_repeats"] = rep
    dec = d.assign(chg=d.groupby("State")["GSDP (crore INR)"].pct_change())
    res["gsdp_large_declines"] = dec[dec.chg < -0.10][["State", "Year", "GSDP (crore INR)", "chg"]]
    # Zone vs CEA region
    z = d[["State", "Zone"]].drop_duplicates()
    z["cea_region"] = z.State.map(C.STATE_TO_CEA_REGION)
    naive = {"North": "NR", "West": "WR", "South": "SR", "East": "ER", "North-East": "NER", "Central": "(none)"}
    z["zone_as_region"] = z.Zone.map(naive)
    res["zone_mismatch"] = z[z.zone_as_region != z.cea_region].sort_values("State")
    res["unmapped_states"] = sorted(set(d.State) - set(C.STATE_TO_CEA_REGION))
    # External conflict: population totals vs OWID India population
    owid = pd.read_csv(C.EXTERNAL / "owid_ember_india_generation_cy.csv").set_index("year")["population"]
    pop = d.groupby("Year")["Population"].sum()
    res["pop_vs_owid"] = pd.DataFrame({"year": pop.index, "organizer_sum_of_states": pop.values,
                                       "owid_india_population": owid.reindex(pop.index).values})
    res["pop_vs_owid"]["ratio"] = res["pop_vs_owid"].organizer_sum_of_states / res["pop_vs_owid"].owid_india_population
    # AP / Telangana bifurcation
    res["ap_ts"] = d[d.State.isin(["Andhra Pradesh", "Telangana"]) & d.Year.between(2011, 2015)][
        ["State", "Year", "Population", "GSDP (crore INR)"]]
    return res


def main() -> None:
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    hashes = verify_originals()
    df = load_original()
    a = organizer_audit(df)
    checks = pd.read_csv(C.OUTPUTS / "validation_checks.csv")
    a["yoy"].to_csv(C.OUTPUTS / "audit_organizer_yoy.csv", index=False)
    a["zone_mismatch"].to_csv(C.OUTPUTS / "audit_zone_vs_cea_region.csv", index=False)
    a["pop_vs_owid"].to_csv(C.OUTPUTS / "audit_population_vs_owid.csv", index=False)

    nat = pd.read_csv(C.DERIVED / "national_generation_fy.csv")
    emb = pd.read_csv(C.DERIVED / "ember_cy.csv")[["year", "electricity_generation"]]
    cmp_ = nat[["fy_label", "fy_end_year", "total_twh", "domestic_twh"]].merge(
        emb.rename(columns={"year": "fy_end_year", "electricity_generation": "ember_cy_twh_of_calendar_year_fy_end_minus_1"}).assign(
            fy_end_year=lambda x: x.fy_end_year + 1), on="fy_end_year", how="left")
    cmp_["ember_minus_cea_twh"] = cmp_.iloc[:, -1] - cmp_.total_twh
    cmp_.to_csv(C.OUTPUTS / "audit_ember_vs_cea.csv", index=False)

    failed = checks[~checks.passed]
    L = []
    L.append("# Data-Quality Report (auto-generated by `src/audit.py`)\n")
    L.append("Generated from the repository data; do not edit by hand. Organizer data were **not modified**; "
             "all findings below are flags, not corrections.\n")
    L.append("## 1. Integrity of organizer (base-truth) files\n")
    L.append(_md(pd.DataFrame([{"file": k, "sha256": v["actual"], "matches_recorded_hash": v["ok"]} for k, v in hashes.items()])))
    L.append("\n\nThe organizer CSV is loaded read-only through `src/integrity.load_original()`, which re-verifies the "
             "SHA-256 before every load. Derived columns (CEA region mapping, per-capita GSDP) are written to "
             "`data/derived/organizer_with_cea_region.csv`, never to the original.\n")
    L.append("## 2. Organizer dataset audit\n")
    L.append(f"* Rows x columns: **{a['shape'][0]} x {a['shape'][1]}**; missing cells: **{a['missing']}**; "
             f"duplicate (State, Year) rows: **{a['dup_state_year']}**.")
    L.append("* Coverage: 34 States/UTs, 2006-2024. **Ladakh** and **Dadra & Nagar Haveli and Daman & Diu** are absent "
             "(they appear in CEA tables). Whether J&K rows after 2019 include Ladakh is not documented.")
    L.append("* Upstream README states that **some values were imputed with XGBoost regression** without flagging which "
             "cells; imputed and observed values therefore cannot be distinguished. GSDP is **nominal**.")
    L.append("* The `Year` field does not state calendar vs financial year. We treat it as an index aligned to FY end-year "
             "only for cross-sectional shares (see mentor questions).\n")
    L.append("### 2.1 Column definitions and use\n")
    L.append(_md(a["columns"]))
    L.append("\n\n**Installed-capacity columns are audited but never used as a forecasting target, predictor or comparison "
             "metric** (organizer rule: forecasts concern electricity generated).\n")
    L.append("### 2.2 Coverage gaps\n")
    L.append(_md(a["coverage_gaps"].astype(str)))
    L.append("\n\nTelangana is missing 2013 and is present as a separate state for 2006-2012 (before its 2014 formation), "
             "so pre-2014 Andhra Pradesh/Telangana values are back-cast splits of unknown method:\n")
    L.append(_md(a["ap_ts"]))
    L.append("\n### 2.3 Year-on-year anomalies\n")
    L.append(_md(a["yoy"]))
    L.append("\n\nCumulative installed capacity should rarely fall; the decreases above suggest reclassification, "
             "decommissioning or imputation artefacts (not used in models). Population never decreases and shows no "
             "jump >5%, consistent with smooth interpolation. GSDP has exact repeats (carried-forward values) and declines:\n")
    L.append(_md(a["gsdp_repeats"]))
    L.append("\n\nGSDP declines >10% year-on-year (nominal):\n")
    L.append(_md(a["gsdp_large_declines"]) if len(a["gsdp_large_declines"]) else "None.")
    L.append("\n### 2.4 Zone labels vs CEA grid regions\n")
    L.append("The organizer `Zone` uses a 6-zone scheme. All generation data (CEA) use the 5 grid regions. We map states to "
             "CEA regions in a separate derived table; the organizer `Zone` column is retained unchanged. Mismatches:\n")
    L.append(_md(a["zone_mismatch"]))
    L.append(f"\n\nUnmapped organizer states: {a['unmapped_states'] or 'none'}.\n")
    L.append("### 2.5 Conflict with external population data\n")
    L.append("Sum of organizer state populations vs OWID (UN-based) India population. Both values are kept; the organizer "
             "values are used only as *relative shares* in the demand proxy.\n")
    L.append(_md(a["pop_vs_owid"]))
    L.append("\n\nThe ~4% shortfall is consistent with missing UTs and differing population sources; the 2013 dip reflects "
             "the missing Telangana row.\n")
    L.append("## 3. Validation of transcribed official tables\n")
    L.append(f"{len(checks)} automated checks (`outputs/validation_checks.csv`): **{len(checks) - len(failed)} passed, "
             f"{len(failed)} failed**. Arithmetic checks confirm that every transcribed CEA table reproduces its own printed "
             "subtotals (regional sums = All-India; source sums = regional totals) within 0.05 MU, which guards against "
             "transcription errors from PDF text extraction.\n")
    if len(failed):
        L.append("Failed checks (source-internal inconsistencies, kept as published):\n")
        L.append(_md(failed[["check_id", "description", "value", "tolerance"]]))
        L.append("\n\n* `PSAG-GR-2011`: the published FY2010-11 growth (5.59%) is inconsistent with the published FY2009-10 and "
                 "FY2010-11 totals (recomputed 5.18%). The extraction also noted the source chart shows 805.4 BU for "
                 "FY2009-10 while the table shows 808.498 BU. Table values are retained; FY2009-10 is flagged.\n")
    L.append("Cross-source reconciliation:\n")
    L.append(_md(checks[checks.kind == "cross-source"][["check_id", "description", "value", "passed"]]))
    L.append("\n\n## 4. Scope differences between generation sources (kept side by side, not reconciled)\n")
    L.append("* **CEA / Power Sector at a Glance (PSAG)**: utility generation incl. RE, Indian FY, **includes Bhutan imports**, "
             "excludes captive plants. This is the **forecast target**.\n"
             "* **CEA Growth Book Table 3**: utility generation by mode, **excludes** Bhutan imports.\n"
             "* **CEA DGR**: conventional stations >25 MW only (no RE), regional.\n"
             "* **CEA RE reports**: RE by source and region; 2025 edition totals include large hydro, 2023 edition totals do not. "
             "Large hydro in the RE report differs slightly from DGR hydro (we use DGR hydro to avoid double counting).\n"
             "* **Ember via OWID**: calendar year, **includes captive generation estimates**; therefore ~10-12% above CEA "
             "utility totals. Used for longer-history backtesting and by-source history only.\n")
    L.append(_md(cmp_.rename(columns={"ember_cy_twh_of_calendar_year_fy_end_minus_1": "ember_cy_twh (CY = FY start year)"})))
    L.append("\n\n## 5. Estimated (non-observed) values used downstream\n")
    L.append("* FY2024-25 national coal vs gas split: CEA DGR reports thermal only; split uses the FY2023-24 Growth-Book "
             "gas+diesel/thermal ratio (2.39%). Flagged `estimated_split`.\n"
             "* FY2025-26 (v1.1): coal+lignite = CEA 18-column Sub-Report 11 actuals (observed); gas+diesel = Sub-Report 1 "
             "thermal minus coal minus lignite (`derived_residual`, 26.46 TWh). Sub-Report 1 thermal differs from DGR thermal "
             "by 0.02% (both kept).\n"
             "* Regional coal vs gas split of thermal: not available in retrieved sources; projections allocate gas with the "
             "regional thermal geography (provisional).\n"
             "* Bhutan imports FY2011-12 and FY2016-17..FY2019-20: derived as PSAG minus Growth Book (`derived_PSAG_minus_GrowthBook`).\n"
             "* Regions/sources not printed in a CEA table (e.g., nuclear in ER/NER) are recorded as 0 with "
             "`value_type = zero_not_printed_in_source`.\n")
    (C.REPORTS / "data_quality_report.md").write_text("\n".join(L))
    print("[audit] reports/data_quality_report.md written")


if __name__ == "__main__":
    main()
