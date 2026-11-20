"""Build reproducible DERIVED tables from organizer + external data, and run arithmetic
validation checks on every transcribed official table.

Nothing in data/original or data/external is modified. All outputs go to data/derived
and outputs/. Every derived row carries a `value_type` (observed / external_observed /
derived / estimated) and a `source_id`.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config as C
from .integrity import load_original, verify_originals

E = C.EXTERNAL


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(E / name)


# ---------------------------------------------------------------------------
# Organizer data (derived copy with added mapping columns only)
# ---------------------------------------------------------------------------
def organizer_with_mapping() -> pd.DataFrame:
    df = load_original()
    out = df.copy()
    out["cea_region"] = out["State"].map(C.STATE_TO_CEA_REGION)
    zone_to_region_naive = {"North": "NR", "West": "WR", "South": "SR", "East": "ER",
                            "North-East": "NER", "Central": None}
    out["organizer_zone_equals_cea_region"] = out["Zone"].map(zone_to_region_naive) == out["cea_region"]
    out["gsdp_per_capita_inr"] = out["GSDP (crore INR)"] * 1e7 / out["Population"]
    out["value_type"] = "organizer_original_plus_derived_columns"
    return out


def demand_proxy(org: pd.DataFrame, pop_weight: float = C.POP_WEIGHT) -> pd.DataFrame:
    g = (org.groupby(["Year", "cea_region"], as_index=False)
            .agg(population=("Population", "sum"), gsdp_crore=("GSDP (crore INR)", "sum"),
                 n_states=("State", "nunique")))
    tot = g.groupby("Year")[["population", "gsdp_crore"]].transform("sum")
    g["pop_share"] = g["population"] / tot["population"]
    g["gsdp_share"] = g["gsdp_crore"] / tot["gsdp_crore"]
    g["demand_proxy_share"] = pop_weight * g["pop_share"] + (1 - pop_weight) * g["gsdp_share"]
    g = g.rename(columns={"Year": "year", "cea_region": "region"})
    g["value_type"] = "derived_from_organizer"
    return g


# ---------------------------------------------------------------------------
# National generation series
# ---------------------------------------------------------------------------
def national_generation_fy() -> pd.DataFrame:
    ps = _read("cea_psag_total_generation_fy.csv")
    ps = ps[~ps["status"].str.contains("partial")].copy()
    dgr = _read("cea_dgr_regional_conventional_fy.csv")
    bh = dgr[(dgr.region == "All India") & (dgr.type == "Bhutan Import")][["fy_end_year", "actual_mu"]]
    bh = bh.rename(columns={"actual_mu": "bhutan_import_mu"})
    gb = _read("cea_growthbook_modewise_utilities_gwh.csv")[["fy_end_year", "total_gwh"]]
    out = ps.merge(bh, on="fy_end_year", how="left").merge(gb, on="fy_end_year", how="left")
    out["total_twh"] = out["total_generation_bu"]
    out["bhutan_import_twh"] = out["bhutan_import_mu"] / C.MU_PER_TWH
    out["bhutan_import_basis"] = np.where(out["bhutan_import_mu"].notna(), "observed_CEA_DGR", "")
    # Derived imports where DGR not available but Growth-Book (excl. imports) is
    m = out["bhutan_import_twh"].isna() & out["total_gwh"].notna()
    out.loc[m, "bhutan_import_twh"] = out.loc[m, "total_twh"] - out.loc[m, "total_gwh"] / 1000
    out.loc[m, "bhutan_import_basis"] = "derived_PSAG_minus_GrowthBook"
    out["domestic_twh"] = out["total_twh"] - out["bhutan_import_twh"]
    out["value_type"] = "external_observed"
    return out[["fy_label", "fy_end_year", "total_twh", "bhutan_import_twh", "bhutan_import_basis",
                "domestic_twh", "status", "source_id", "value_type"]]


def regional_generation_fy() -> pd.DataFrame:
    """Region x source observed generation (TWh), FY2021-22..FY2024-25 (CEA utilities)."""
    dgr = _read("cea_dgr_regional_conventional_fy.csv")
    dgr = dgr[dgr.region.isin(C.DGR_REGION_TO_CODE)]
    dgr = dgr[dgr.type.isin(["Thermal", "Nuclear", "Hydro"])].copy()
    dgr["region"] = dgr["region"].map(C.DGR_REGION_TO_CODE)
    dgr["source"] = dgr["type"].map({"Thermal": "thermal", "Nuclear": "nuclear", "Hydro": "hydro"})
    dgr["twh"] = dgr["actual_mu"] / C.MU_PER_TWH
    re = _read("cea_re_regional_by_source_fy.csv")
    re = re[re.region.isin(C.REGIONS) & re.re_source.isin(C.RE_SOURCE_MAP)].copy()
    re["source"] = re["re_source"].map(C.RE_SOURCE_MAP)
    re["twh"] = re["generation_mu"] / C.MU_PER_TWH
    re = re.groupby(["fy_label", "fy_end_year", "region", "source", "source_id"], as_index=False)["twh"].sum()
    cols = ["fy_label", "fy_end_year", "region", "source", "twh", "source_id"]
    out = pd.concat([dgr[cols], re[cols]], ignore_index=True)
    years = sorted(set(re.fy_end_year))
    out = out[out.fy_end_year.isin(years)]
    # complete grid with explicit zeros for region/source not printed (e.g. nuclear ER/NER)
    grid = pd.MultiIndex.from_product([years, C.REGIONS, ["thermal", "nuclear", "hydro", "solar", "wind", "other_re"]],
                                      names=["fy_end_year", "region", "source"]).to_frame(index=False)
    out = grid.merge(out, on=["fy_end_year", "region", "source"], how="left")
    out["fy_label"] = out["fy_end_year"].map(lambda y: f"{y-1}-{str(y)[-2:]}")
    out["value_type"] = np.where(out["twh"].isna(), "zero_not_printed_in_source", "external_observed")
    out["twh"] = out["twh"].fillna(0.0)
    out["source_id"] = out["source_id"].fillna("not printed (treated as 0)")
    return out


def national_mix_fy(nat: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    """National domestic generation by source (TWh). FY2017-FY2024 coal/gas/nuclear/hydro from
    CEA Growth Book; RE split by source FY2022+ from CEA RE reports; FY2025 thermal split
    coal/gas ESTIMATED with FY2024 ratio (flagged)."""
    gb = _read("cea_growthbook_modewise_utilities_gwh.csv")
    gb = gb[gb.fy_end_year >= 2017]
    rows = []
    for _, r in gb.iterrows():
        y = int(r.fy_end_year)
        rows += [
            (y, "coal", r.coal_lignite_gwh / 1000, "external_observed", "CEA_GROWTH_2024_T3"),
            (y, "gas", (r.gas_gwh + r.diesel_gwh) / 1000, "external_observed", "CEA_GROWTH_2024_T3"),
            (y, "nuclear", r.nuclear_gwh / 1000, "external_observed", "CEA_GROWTH_2024_T3"),
            (y, "hydro", r.hydro_gwh / 1000, "external_observed", "CEA_GROWTH_2024_T3"),
        ]
        sub = reg[(reg.fy_end_year == y) & reg.source.isin(["solar", "wind", "other_re"])]
        if len(sub):
            for s, v in sub.groupby("source")["twh"].sum().items():
                rows.append((y, s, v, "external_observed", "CEA_RE_MAR2023/2025 (regional sum)"))
        else:
            rows.append((y, "res_unsplit", r.res_gwh / 1000, "external_observed", "CEA_GROWTH_2024_T3"))
    # Years after the last Growth-Book year: DGR + RE with ESTIMATED coal/gas split
    last = gb[gb.fy_end_year == gb.fy_end_year.max()].iloc[0]
    gas_ratio = (last.gas_gwh + last.diesel_gwh) / last.thermal_total_gwh
    for y in sorted(set(reg.fy_end_year) - set(gb.fy_end_year)):
        sub = reg[reg.fy_end_year == y]
        th = sub[sub.source == "thermal"].twh.sum()
        lbl = f"FY{int(last.fy_end_year)} gas+diesel/thermal ratio {gas_ratio:.4f}"
        fw = _fuelwise(y)
        if fw is not None:   # v1.1: published CEA fuel-wise actuals replace the estimate
            rows += [
                (y, "coal", fw["coal_lignite_twh"], "external_observed",
                 "CEA_18COL_SR11_202603 (coal-based + lignite-based actual)"),
                (y, "gas", fw["gas_liquid_twh"], "derived_residual",
                 "CEA_18COL_SR1_202603 thermal - CEA_18COL_SR11_202603 coal - lignite"),
            ]
        else:
            rows += [
                (y, "coal", th * (1 - gas_ratio), "estimated_split", f"CEA_DGR thermal x (1 - {lbl})"),
                (y, "gas", th * gas_ratio, "estimated_split", f"CEA_DGR thermal x {lbl}"),
            ]
        for s in ["nuclear", "hydro", "solar", "wind", "other_re"]:
            rows.append((y, s, sub[sub.source == s].twh.sum(), "external_observed",
                         "; ".join(sorted(i for i in set(sub[sub.source == s].source_id) if not i.startswith("not printed")))))
    out = pd.DataFrame(rows, columns=["fy_end_year", "source", "twh", "value_type", "source_id"])
    tot = out.groupby("fy_end_year")["twh"].transform("sum")
    out["share"] = out["twh"] / tot
    out["fy_label"] = out["fy_end_year"].map(lambda v: f"{v-1}-{str(v)[-2:]}")
    return out


def _fuelwise(fy_end: int) -> dict | None:
    """Published CEA 18-column fuel-wise actuals (v1.1; FY2025-26 only)."""
    f = E / "cea_18col_fuelwise_fy2026.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d = d[d.fy_end_year == fy_end].set_index("item")["actual_gwh"]
    if d.empty:
        return None
    coal = d["Coal based (all-India total)"] + d["Lignite based (all-India total)"]
    return {"coal_lignite_twh": coal / 1000, "gas_liquid_twh": (d["Thermal (all-India total)"] - coal) / 1000,
            "thermal_twh": d["Thermal (all-India total)"] / 1000}


def ember_cy() -> pd.DataFrame:
    df = _read("owid_ember_india_generation_cy.csv")
    df["value_type"] = "external_observed (Ember via OWID; calendar year; incl. captive)"
    return df


# ---------------------------------------------------------------------------
# Validation checks on transcribed data
# ---------------------------------------------------------------------------
def run_checks(nat: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    checks = []

    def add(cid, desc, value, tol, ok, kind="arithmetic"):
        checks.append({"check_id": cid, "kind": kind, "description": desc,
                       "value": value, "tolerance": tol, "passed": bool(ok)})

    hashes = verify_originals()
    add("ORG-HASH", "Organizer files unchanged (SHA-256)", json.dumps({k: v["ok"] for k, v in hashes.items()}), "exact",
        all(v["ok"] for v in hashes.values()), "integrity")

    dgr = _read("cea_dgr_regional_conventional_fy.csv")
    for fy, g in dgr.groupby("fy_label"):
        ai = g[g.region == "All India"].set_index("type")["actual_mu"]
        rg = g[g.region != "All India"]
        for t in ["Thermal", "Nuclear", "Hydro"]:
            s = rg[rg.type == t].actual_mu.sum()
            add(f"DGR-{fy}-{t}", f"DGR {fy}: sum of regional {t} = All-India {t}", round(s - ai[t], 3), 0.05, abs(s - ai[t]) <= 0.05)
        for r, rr in rg.groupby("region"):
            tot = rr[rr.type == "Total"].actual_mu.iloc[0]
            s = rr[rr.type != "Total"].actual_mu.sum()
            add(f"DGR-{fy}-{r}-TOT", f"DGR {fy} {r}: types sum to regional total", round(s - tot, 3), 0.05, abs(s - tot) <= 0.05)
        s = ai.drop("Total").sum()
        add(f"DGR-{fy}-AI-TOT", f"DGR {fy}: All-India types incl. Bhutan sum to total", round(s - ai["Total"], 3), 0.05,
            abs(s - ai["Total"]) <= 0.05)

    re = _read("cea_re_regional_by_source_fy.csv")
    for (fy, src), g in re.groupby(["fy_label", "re_source"]):
        ai = g[g.region == "ALL INDIA"].generation_mu.iloc[0]
        s = g[g.region != "ALL INDIA"].generation_mu.sum()
        add(f"RE-{fy}-{src}", f"RE {fy} {src}: regions sum to All-India", round(s - ai, 3), 0.05, abs(s - ai) <= 0.05)
    pr = _read("cea_re_printed_region_totals_fy.csv")
    for _, p in pr.iterrows():
        g = re[(re.fy_label == p.fy_label) & (re.region == p.region)]
        if p.includes_large_hydro == "no":
            g = g[g.re_source != "Large Hydro"]
        s = g.generation_mu.sum()
        add(f"RE-{p.fy_label}-{p.region}-TOT", f"RE {p.fy_label} {p.region}: sources sum to printed total "
            f"({'incl.' if p.includes_large_hydro == 'yes' else 'excl.'} large hydro)", round(s - p.printed_total_mu, 3), 0.05,
            abs(s - p.printed_total_mu) <= 0.05)

    gb = _read("cea_growthbook_modewise_utilities_gwh.csv")
    for _, r in gb.iterrows():
        d1 = r.coal_lignite_gwh + r.gas_gwh + r.diesel_gwh - r.thermal_total_gwh
        d2 = r.thermal_total_gwh + r.hydro_gwh + r.nuclear_gwh + r.res_gwh - r.total_gwh
        add(f"GB-{r.fy_label}-TH", f"Growth Book {r.fy_label}: coal+gas+diesel = thermal", d1, 2, abs(d1) <= 2)
        add(f"GB-{r.fy_label}-TOT", f"Growth Book {r.fy_label}: thermal+hydro+nuclear+RES = total", d2, 2, abs(d2) <= 2)
    cap = _read("cea_growthbook_captive_modewise_gwh.csv")
    for _, r in cap.iterrows():
        d = r.hydro_gwh + r.steam_gwh + r.diesel_gwh + r.gas_gwh + r.res_gwh + r.railways_gwh - r.total_gwh
        add(f"CAP-{r.fy_label}", f"Captive {r.fy_label}: modes sum to total", round(d, 2), 0.05, abs(d) <= 0.05)

    fw = _read("cea_18col_fuelwise_fy2026.csv").set_index("item")["actual_gwh"]
    d = fw[[i for i in fw.index if i.startswith("Coal based - ")]].sum() - fw["Coal based (all-India total)"]
    add("18COL-COAL-OWN", "CEA 18-col FY2025-26: coal ownership subtotals sum to coal total", round(d, 2), 0.05, abs(d) <= 0.05)
    d = fw[["Thermal (all-India total)", "Nuclear", "Hydro", "Bhutan Import"]].sum() - fw["Total conventional incl. Bhutan"]
    add("18COL-SR1-TOT", "CEA 18-col FY2025-26: thermal+nuclear+hydro+Bhutan = total", round(d, 2), 0.05, abs(d) <= 0.05)
    dg = dgr[(dgr.fy_end_year == 2026) & (dgr.region == "All India") & (dgr.type == "Thermal")].actual_mu.iloc[0]
    rel = fw["Thermal (all-India total)"] / dg - 1
    add("XFUEL-2026", "FY2025-26 thermal: CEA 18-col Sub-Report 1 vs CEA DGR (%)", round(100 * rel, 3), "0.1 %", abs(rel) <= 0.001, "cross-source")
    gas = (fw["Thermal (all-India total)"] - fw["Coal based (all-India total)"] - fw["Lignite based (all-India total)"]) / 1000
    add("XFUEL-GAS-2026", "FY2025-26 gas+liquid residual (TWh) vs audit-reported NITI/NPCIL ~26.46 BU", round(gas, 3), "0.2 TWh",
        abs(gas - 26.46) <= 0.2, "cross-source")
    hp = _read("cea_hydro_potential_region_20231031.csv").set_index("region")
    for col in ["exploitable_identified_capacity_2017_23_mw", "developed_mw"]:
        d = hp.loc[C.REGIONS, col].sum() - hp.loc["ALL INDIA", col]
        add(f"HYD-POT-{col[:12]}", f"CEA hydro potential: regions sum to All-India ({col})", round(d, 2), 1.0, abs(d) <= 1.0)
    tg = _read("tg_population_projections_2021_2036.csv")
    for y, g in tg.groupby("year"):
        ind = g[g.cea_region == "ALL INDIA"].population_thousand.iloc[0]
        rel = g[g.cea_region != "ALL INDIA"].population_thousand.sum() / ind - 1
        add(f"TG-POP-{y}", f"TG {y}: sum of state/UT projections vs India total (%)", round(100 * rel, 3), "0.5 %", abs(rel) <= 0.005)

    lg = _read("cea_lgbr_regional_requirement_fy2025.csv")
    d = lg[lg.region != "ALL INDIA"].requirement_actual_mu.sum() - lg[lg.region == "ALL INDIA"].requirement_actual_mu.iloc[0]
    add("LGBR-REQ", "LGBR 2024-25 actual requirement: regions sum to All-India", d, 2, abs(d) <= 2)

    # Cross-source reconciliation (informational thresholds)
    ps = _read("cea_psag_total_generation_fy.csv").set_index("fy_end_year")
    for y in sorted(reg.fy_end_year.unique()):
        dgr_tot = dgr[(dgr.fy_end_year == y) & (dgr.region == "All India") & (dgr.type == "Total")].actual_mu.iloc[0]
        re_y = re[(re.fy_end_year == y) & (re.region == "ALL INDIA") & (re.re_source != "Large Hydro")].generation_mu.sum()
        rel = (dgr_tot + re_y) / 1000 / ps.loc[y, "total_generation_bu"] - 1
        add(f"XREC-{y}", f"FY{y-1}-{str(y)[-2:]}: DGR total (incl. Bhutan) + RE excl. large hydro vs PSAG total",
            round(rel * 100, 3), "0.5 %", abs(rel) <= 0.005, "cross-source")
        rsum = reg[reg.fy_end_year == y].twh.sum()
        bh = nat.set_index("fy_end_year").loc[y, "bhutan_import_twh"]
        rel2 = (rsum + bh) / ps.loc[y, "total_generation_bu"] - 1
        add(f"XREG-{y}", f"FY{y-1}-{str(y)[-2:]}: sum of derived regional generation + Bhutan vs PSAG total",
            round(rel2 * 100, 3), "0.5 %", abs(rel2) <= 0.005, "cross-source")
    gbi = gb.set_index("fy_end_year")
    for y in [2021, 2022, 2023, 2024]:
        bh = dgr[(dgr.fy_end_year == y) & (dgr.region == "All India") & (dgr.type == "Bhutan Import")].actual_mu.iloc[0]
        rel = (gbi.loc[y, "total_gwh"] + bh) / 1000 / ps.loc[y, "total_generation_bu"] - 1
        add(f"XGB-{y}", f"FY{y-1}-{str(y)[-2:]}: Growth Book total + Bhutan import vs PSAG total", round(rel * 100, 3),
            "0.5 %", abs(rel) <= 0.005, "cross-source")
    pss = ps[~ps.status.str.contains("partial")]["total_generation_bu"]
    g = (pss / pss.shift(1) - 1) * 100
    pub = ps["published_growth_pct"]
    for y in g.index[1:]:
        d = g[y] - pub[y]
        add(f"PSAG-GR-{y}", f"PSAG FY{y-1}-{str(y)[-2:]}: recomputed growth vs published", round(d, 3), 0.05, abs(d) <= 0.05,
            "internal-consistency")
    return pd.DataFrame(checks)


def main() -> dict:
    C.DERIVED.mkdir(parents=True, exist_ok=True)
    C.OUTPUTS.mkdir(parents=True, exist_ok=True)
    org = organizer_with_mapping()
    org.to_csv(C.DERIVED / "organizer_with_cea_region.csv", index=False)
    dp = demand_proxy(org)
    dp.to_csv(C.DERIVED / "demand_proxy_region_year.csv", index=False)
    nat = national_generation_fy()
    nat.to_csv(C.DERIVED / "national_generation_fy.csv", index=False)
    reg = regional_generation_fy()
    reg.to_csv(C.DERIVED / "regional_generation_fy.csv", index=False)
    mix = national_mix_fy(nat, reg)
    mix.to_csv(C.DERIVED / "national_mix_fy.csv", index=False)
    ember_cy().to_csv(C.DERIVED / "ember_cy.csv", index=False)
    checks = run_checks(nat, reg)
    checks.to_csv(C.OUTPUTS / "validation_checks.csv", index=False)
    summary = {"n_checks": int(len(checks)), "n_failed": int((~checks.passed).sum()),
               "failed": checks.loc[~checks.passed, ["check_id", "value", "tolerance"]].to_dict("records")}
    (C.OUTPUTS / "validation_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"[prepare] derived tables written; validation checks: {summary['n_checks']} run, {summary['n_failed']} failed")
    return summary


if __name__ == "__main__":
    main()
