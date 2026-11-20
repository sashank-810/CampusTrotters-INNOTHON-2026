"""Scenario model (Model C): GDP-elasticity generation projection + national source mix.

    G_t = G_{t-1} * (1 + g_t) ** eps_t  + addon_t (ramp)
    g_t   : real GDP growth path (ASSUMPTION per scenario, config.SCENARIOS)
    eps_t : generation-GDP elasticity, starts at the historical estimate eps_0
            (Ember generation vs Maddison real GDP, trailing 10 years) and moves linearly
            to an assumed end value by FY2047 (structural change / efficiency).
    addon : electrification demand not captured by historical elasticity (accelerated case).

Scenario ranges are assumption-driven and are NOT statistical prediction intervals.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config as C


# ---------------------------------------------------------------------------
# Elasticity estimation (observed data only)
# ---------------------------------------------------------------------------
def _gen_gdp() -> pd.DataFrame:
    e = pd.read_csv(C.DERIVED / "ember_cy.csv")
    e = e[(e.year >= 2000)][["year", "electricity_generation", "gdp"]].dropna()
    return e.set_index("year")


def elasticity_estimates(last_year: int | None = None, window: int = 10) -> dict:
    d = _gen_gdp()
    if last_year is not None:
        d = d[d.index <= last_year]
    dl = np.log(d).diff().dropna()
    w = dl.tail(window)
    ratio = w.electricity_generation.sum() / w.gdp.sum()
    # OLS with intercept on the full available sample (for reporting)
    x, y = dl.gdp.values, dl.electricity_generation.values
    X = np.column_stack([np.ones_like(x), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    s2 = res @ res / (len(y) - 2)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return {"eps0_trailing_ratio": float(ratio), "window_years": [int(w.index.min()), int(w.index.max())],
            "ols_intercept": float(b[0]), "ols_slope": float(b[1]), "ols_slope_se": float(se[1]),
            "ols_years": [int(dl.index.min()), int(dl.index.max())]}


def conditional_backtest(max_h: int = 5) -> pd.DataFrame:
    """Backtest the elasticity engine CONDITIONAL on realised GDP (oracle GDP).
    At origin T, eps is estimated from data <= T only; forecast uses actual GDP growth."""
    d = _gen_gdp()
    years = d.index.values
    rows = []
    for T in years:
        if T < 2010 or T >= years.max():
            continue
        eps = elasticity_estimates(last_year=int(T))["eps0_trailing_ratio"]
        g_T = d.loc[T, "electricity_generation"]
        for h in range(1, max_h + 1):
            t = T + h
            if t not in d.index:
                break
            fc = g_T * (d.loc[t, "gdp"] / d.loc[T, "gdp"]) ** eps
            act = d.loc[t, "electricity_generation"]
            rows.append({"model": "gdp_elasticity_conditional", "origin": int(T), "target_year": int(t), "h": h,
                         "forecast": fc, "actual": act, "error": fc - act, "eps_used": eps})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Scenario projection
# ---------------------------------------------------------------------------
def _lin(y0: float, y1: float, t: int, t0: int, t1: int) -> float:
    if t <= t0:
        return y0
    if t >= t1:
        return y1
    return y0 + (y1 - y0) * (t - t0) / (t1 - t0)


def base_year_values() -> dict:
    nat = pd.read_csv(C.DERIVED / "national_generation_fy.csv").set_index("fy_end_year")
    mix = pd.read_csv(C.DERIVED / "national_mix_fy.csv")
    m = mix[mix.fy_end_year == C.BASE_FY_END].set_index("source")["twh"]
    return {"total_twh": float(nat.loc[C.BASE_FY_END, "total_twh"]),
            "bhutan_twh": float(nat.loc[C.BASE_FY_END, "bhutan_import_twh"]),
            "mix_twh": {s: float(m.get(s, 0.0)) for s in C.SOURCES}}


def project(scenario: str, overrides: dict | None = None, eps0: float | None = None) -> pd.DataFrame:
    """Return yearly projection FY(base+1)..HORIZON_END for one scenario.
    `overrides` may replace any key of config.SCENARIOS[scenario] (dashboard sensitivity)."""
    p = {**C.SCENARIOS[scenario], **(overrides or {})}
    mix_2047 = dict(p["mix_2047"])
    tot = sum(mix_2047.values())
    mix_2047 = {k: v / tot for k, v in mix_2047.items()}          # enforce sum to 1
    if eps0 is None:
        eps0 = elasticity_estimates()["eps0_trailing_ratio"]
    base = base_year_values()
    bhutan = p.get("bhutan_import_twh", C.BHUTAN_IMPORT_TWH_DEFAULT)
    base_dom = sum(base["mix_twh"].values())
    base_share = {s: base["mix_twh"][s] / base_dom for s in C.SOURCES}
    y0, y1 = C.BASE_FY_END + 1, C.HEADLINE_FY_END
    G_core = base["total_twh"]
    rows = []
    for t in range(y0, C.HORIZON_END + 1):
        g = _lin(p["gdp_growth_start"], p["gdp_growth_end"], t, y0, y1)
        eps = _lin(eps0, p["elasticity_end"], t, y0, y1)
        G_core = G_core * (1 + g) ** eps
        addon = _lin(0.0, p["addon_twh_2047"], t, C.ADDON_RAMP_START, y1) if t >= C.ADDON_RAMP_START else 0.0
        G = G_core + addon
        dom = G - bhutan
        r = {"scenario": scenario, "fy_end_year": t, "gdp_growth": g, "elasticity": eps,
             "addon_twh": addon, "total_generation_twh": G, "bhutan_import_twh": bhutan,
             "domestic_generation_twh": dom}
        for s in C.SOURCES:
            sh = _lin(base_share[s], mix_2047[s], t, C.BASE_FY_END, y1)
            r[f"share_{s}"] = sh
        ssum = sum(r[f"share_{s}"] for s in C.SOURCES)
        for s in C.SOURCES:
            r[f"share_{s}"] /= ssum
            r[f"{s}_twh"] = r[f"share_{s}"] * dom
        rows.append(r)
    df = pd.DataFrame(rows)
    df["non_fossil_share"] = df[[f"share_{s}" for s in C.NON_FOSSIL]].sum(axis=1)
    df["variable_re_share"] = df[[f"share_{s}" for s in C.VARIABLE_RE]].sum(axis=1)
    df["dispatchable_share"] = df[[f"share_{s}" for s in C.DISPATCHABLE]].sum(axis=1)
    for s in ["coal", "hydro", "nuclear", "solar", "wind"]:
        df[f"{s}_multiple_of_base"] = df[f"{s}_twh"] / base["mix_twh"][s]
    df["value_type"] = "scenario_projection (assumption-driven)"
    return df


def feasibility_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Provisional plausibility flags (NOT feasibility proofs)."""
    from .allocation import hydro_ceiling_twh
    df = df.copy()
    df["hydro_fraction_of_cea_ceiling"] = df["hydro_twh"] / float(hydro_ceiling_twh().sum())
    out = []
    for _, r in df.iterrows():
        f = []
        if r["variable_re_share"] > 0.30:
            f.append("VRE share >30%: storage/flexibility requirement not modelled - provisional")
        if r["hydro_multiple_of_base"] > 2.0:
            f.append("Hydro >2x FY2025-26: check against CEA hydro potential & project pipeline")
        if r["nuclear_multiple_of_base"] > 5.0:
            f.append("Nuclear >5x FY2025-26: requires sustained build-out; provisional")
        if r.get("hydro_fraction_of_cea_ceiling", 0) > 0.9:
            f.append(f"Hydro uses {100*r['hydro_fraction_of_cea_ceiling']:.0f}% of the indicative CEA-potential ceiling")
        if r["coal_multiple_of_base"] > 1.5:
            f.append("Coal >1.5x FY2025-26: emissions/coal-supply implications")
        out.append("; ".join(f))
    df = df.copy()
    df["provisional_flags"] = out
    df.attrs["note"] = "flags are plausibility prompts, not feasibility proofs"
    return df


def main() -> dict:
    est = elasticity_estimates()
    bt = conditional_backtest()
    bt.to_csv(C.OUTPUTS / "backtest_gdp_elasticity_conditional_detail.csv", index=False)
    # comparable RW-drift errors on identical (origin, target) pairs from Ember backtest
    emb = pd.read_csv(C.OUTPUTS / "backtest_ember_cy_detail.csv")
    rw = emb[emb.model == "rw_drift"].merge(bt[["origin", "target_year"]], on=["origin", "target_year"])
    from .forecast import score
    sc = pd.concat([score(bt, by=("model",)), score(rw, by=("model",))], ignore_index=True)
    sc["note"] = ["conditional on realised GDP (oracle); not an unconditional forecast skill",
                  "same origin/target pairs, unconditional"]
    sc.to_csv(C.OUTPUTS / "backtest_gdp_elasticity_vs_rw.csv", index=False)
    frames = [feasibility_flags(project(s, eps0=est["eps0_trailing_ratio"])) for s in C.SCENARIOS]
    allp = pd.concat(frames, ignore_index=True)
    # v1.1: demographic columns (central TG variant -> generation unchanged by construction)
    from . import demography as DM
    before = allp["domestic_generation_twh"].copy()
    allp = DM.apply_variant(allp, "central")
    assert np.allclose(before, allp["domestic_generation_twh"]), "central demographic variant must not change generation"
    allp["imported_generation_twh"] = allp["total_generation_twh"] - allp["domestic_generation_twh"]
    allp.to_csv(C.OUTPUTS / "national_scenarios.csv", index=False)
    DM.national_path().to_csv(C.OUTPUTS / "demography_national_path.csv", index=False)
    DM.regional_paths().to_csv(C.OUTPUTS / "demography_regional_paths.csv", index=False)
    vrows = []
    for sname in C.SCENARIOS:
        base_s = allp[allp.scenario == sname]
        for v in DM.DEMO_VARIANTS:
            for beta in (0.0, DM.URBAN_SEMI_ELASTICITY_DEFAULT, 0.02):
                if v in ("central", "low_pop", "high_pop") and beta != DM.URBAN_SEMI_ELASTICITY_DEFAULT:
                    continue
                d = DM.apply_variant(base_s, v, urban_semi_elasticity=beta)
                r = d[d.fy_end_year == C.HEADLINE_FY_END].iloc[0]
                vrows.append({"scenario": sname, "demographic_variant": v, "variant_label": DM.DEMO_VARIANTS[v]["label"],
                              "urban_semi_elasticity_per_pp": beta, "fy_end_year": C.HEADLINE_FY_END,
                              "population_m": r.population_m, "urban_pct": r.urban_pct, "demographic_factor": r.demographic_factor,
                              "domestic_generation_twh": r.domestic_generation_twh,
                              "change_vs_central_twh": r.domestic_generation_twh - base_s[base_s.fy_end_year == C.HEADLINE_FY_END].domestic_generation_twh.iloc[0],
                              "per_capita_domestic_generation_kwh": r.per_capita_domestic_generation_kwh})
    dv = pd.DataFrame(vrows)
    dv["value_type"] = "sensitivity (assumption-driven demographic variants; not observations)"
    dv.to_csv(C.OUTPUTS / "demography_sensitivity.csv", index=False)
    # Scenario mix justification: hydro share vs CEA-potential energy ceiling
    from .allocation import hydro_ceiling_twh
    hc = float(hydro_ceiling_twh().sum())
    hj = allp[allp.fy_end_year == C.HEADLINE_FY_END][["scenario", "hydro_twh"]].copy()
    hj["cea_potential_ceiling_twh_all_india"] = hc
    hj["fraction_of_ceiling"] = hj.hydro_twh / hc
    hj.to_csv(C.OUTPUTS / "mix_hydro_vs_potential.csv", index=False)
    # External plausibility check: NEP (20th EPS) REQUIREMENT converted to a generation-equivalent with
    # the observed FY2024-25 ratio requirement/generation (LGBR actual requirement / PSAG total).
    lg = pd.read_csv(C.EXTERNAL / "cea_lgbr_regional_requirement_fy2025.csv").set_index("region")
    nat = pd.read_csv(C.DERIVED / "national_generation_fy.csv").set_index("fy_end_year")
    ratio = lg.loc["ALL INDIA", "requirement_actual_mu"] / 1000 / nat.loc[2025, "total_twh"]
    ref = pd.read_csv(C.EXTERNAL / "reference_projections_and_targets.csv")
    nep = ref[ref.item.str.startswith("All-India electricity energy requirement")]
    xc = []
    for _, r in nep.iterrows():
        fy_end = int(r.period[:4]) + 1
        row = {"fy_end_year": fy_end, "nep_requirement_twh": float(r.value),
               "requirement_to_generation_ratio_fy2025": ratio,
               "nep_implied_generation_twh": float(r.value) / ratio}
        for s in C.SCENARIOS:
            row[f"{s}_twh"] = float(allp[(allp.scenario == s) & (allp.fy_end_year == fy_end)].total_generation_twh.iloc[0])
        row["rw_drift_twh"] = float(pd.read_csv(C.OUTPUTS / "national_forecast_statistical.csv").query(
            "model == 'rw_drift' and fy_end_year == @fy_end").point_twh.iloc[0])
        xc.append(row)
    xc = pd.DataFrame(xc)
    xc["value_type"] = "derived cross-check (requirement is not generation)"
    xc.to_csv(C.OUTPUTS / "crosscheck_nep_requirement.csv", index=False)
    print(xc.round(1).to_string())
    meta = {"elasticity": est, "base_year": base_year_values(), "scenarios": C.SCENARIOS,
            "conditional_backtest": sc.drop(columns=[]).to_dict("records")}
    (C.OUTPUTS / "scenario_meta.json").write_text(json.dumps(meta, indent=2, default=float))
    h = allp[allp.fy_end_year.isin([2030, 2035, 2040, 2047])][
        ["scenario", "fy_end_year", "total_generation_twh", "non_fossil_share", "variable_re_share", "provisional_flags"]]
    print("[scenarios] elasticity:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in est.items()})
    print(h.round(3).to_string())
    print(sc.round(2).to_string())
    return meta


if __name__ == "__main__":
    main()
