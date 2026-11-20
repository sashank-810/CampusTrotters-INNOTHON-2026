"""ILLUSTRATIVE, GENERATION-CONSERVING regional allocation of national source totals to the
five CEA grid regions (SciPy SLSQP; convex quadratic programme).

What this is NOT (v1.1 wording): it is not a cost/reliability/emissions optimisation of the
national mix (the national mix is a scenario ASSUMPTION), and historical regional shares are
NOT physical resource limits. The only source-backed resource check is the CEA hydro-potential
ceiling (D4). Everything else is an illustrative geography preference, tested by sensitivity.

Decision variables  x[r,k] >= 0 : generation (TWh) of source k located in region r.

HARD CONSTRAINTS (accounting / physical)
  (H1) sum_r x[r,k] = N_k            national source total from the scenario (energy conservation)
  (H2) x[r,k] >= 0
ILLUSTRATIVE GEOGRAPHY ASSUMPTIONS anchored on OBSERVED generation (not resource limits)
  (D1) x[r,k] = 0 if region r had zero observed generation of k in FY2021-22..FY2025-26
       (wind in ER/NER, nuclear in ER/NER)                      [removed in geography_mode="relaxed"]
  (D2) x[r,k] <= SHARE_CAP_MULTIPLIER[k] * rho[r,k] * N_k        [removed in geography_mode="relaxed"]
  (D3) hydro & nuclear: x[r,k] >= min(observed regional level, cap)  (existing fleet keeps generating)
SOURCE-BACKED RESOURCE CHECK (v1.1, default on)
  (D4) hydro: x[r,hydro] <= observed mean hydro generation_r x (CEA exploitable potential_r / developed_r)
       - an indicative ENERGY ceiling; replaces D2 for hydro. Assumes undeveloped sites yield like existing ones.
ILLUSTRATIVE PREFERENCES (objective weights; dashboard-adjustable)
  minimise  sum_k w_k/n_k * sum_r (x~[r,k] - rho[r,k] n_k)^2  +  lambda * sum_r (sum_k x~[r,k] - delta_r)^2
  where x~ = x/G, n_k = N_k/G, rho = observed regional share of source k, delta_r = demand-location
  proxy share (organizer population + GSDP). The first term keeps generation where resources and
  existing fleets are; the second pulls generation toward demand to limit inter-regional transfer. Demand location default:
  CEA LGBR FY2024-25 actual requirement shares drifted by organizer GSDP-share trends (the organizer
  population+GSDP proxy alone mis-locates demand by up to ~6 pp; see outputs/demand_proxy_validation.csv).

Regional generation is the location of GENERATION, not consumption. The difference
(generation - demand proxy x G) is an indicative net inter-regional transfer, not a flow study.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import optimize

from . import config as C

THERMAL_SOURCES = {"coal", "gas"}
REF_YEARS = {"coal": 5, "gas": 5, "nuclear": 5, "hydro": 5, "solar": 2, "wind": 2, "other_re": 3}


def reference_shares() -> tuple[pd.DataFrame, pd.DataFrame]:
    """rho[r,k]: observed regional share of each source (energy-weighted over recent FYs)
    and base[r,k]: mean observed regional generation (TWh) over the same years."""
    reg = pd.read_csv(C.DERIVED / "regional_generation_fy.csv")
    years = sorted(reg.fy_end_year.unique())
    rho, base = {}, {}
    for k in C.SOURCES:
        src = "thermal" if k in THERMAL_SOURCES else k
        yrs = years[-REF_YEARS[k]:]
        sub = reg[(reg.source == src) & reg.fy_end_year.isin(yrs)]
        by_r = sub.groupby("region")["twh"].sum().reindex(C.REGIONS).fillna(0.0)
        rho[k] = by_r / by_r.sum()
        base[k] = sub.groupby("region")["twh"].mean().reindex(C.REGIONS).fillna(0.0)
    rho = pd.DataFrame(rho).loc[C.REGIONS, C.SOURCES]
    base = pd.DataFrame(base).loc[C.REGIONS, C.SOURCES]
    # zero-observed rule uses ALL observed years
    allobs = {}
    for k in C.SOURCES:
        src = "thermal" if k in THERMAL_SOURCES else k
        allobs[k] = reg[reg.source == src].groupby("region")["twh"].sum().reindex(C.REGIONS).fillna(0.0)
    zero = pd.DataFrame(allobs).loc[C.REGIONS, C.SOURCES] <= 0
    rho[zero] = 0.0
    rho = rho / rho.sum(axis=0)
    return rho, base


DEMAND_BASES = {
    "lgbr_plus_demographic_drift": "CEA LGBR FY2024-25 requirement shares, drifted by TG population & urbanization projections and organizer per-capita GSDP trends (default, v1.1)",
    "lgbr_plus_gsdp_drift": "CEA LGBR FY2024-25 requirement shares, drifted by organizer GSDP-share trends (v1.0 default)",
    "lgbr_constant": "CEA LGBR FY2024-25 actual requirement shares, held constant",
    "organizer_proxy": "Organizer population + nominal GSDP shares (2024) only",
}


def gsdp_share_slopes(first: int = 2014, last: int = 2024) -> pd.Series:
    """OLS slope of log(regional nominal-GSDP share) per year, organizer data 2014-2024
    (post-bifurcation AP/Telangana)."""
    dp = pd.read_csv(C.DERIVED / "demand_proxy_region_year.csv")
    dp = dp[dp.year.between(first, last)]
    out = {}
    for r, g in dp.groupby("region"):
        x = g.year.values - g.year.mean()
        out[r] = float(np.polyfit(x, np.log(g.gsdp_share.values), 1)[0])
    return pd.Series(out).reindex(C.REGIONS)


def demand_shares(source: str = "lgbr_plus_demographic_drift", year: int = 2025, pop_weight: float = C.POP_WEIGHT,
                  drift_damping: float = 0.5, urban_semi_elasticity: float | None = None) -> pd.Series:
    """Demand-LOCATION shares used only for the transfer/proximity term (never as generation)."""
    if source in ("lgbr_requirement_fy2025", "lgbr_constant", "lgbr_plus_gsdp_drift", "lgbr_plus_demographic_drift"):
        lg = pd.read_csv(C.EXTERNAL / "cea_lgbr_regional_requirement_fy2025.csv")
        lg = lg[lg.region.isin(C.REGIONS)].set_index("region")["requirement_actual_mu"]
        s = (lg / lg.sum()).reindex(C.REGIONS)
        if source == "lgbr_plus_demographic_drift":
            from .demography import URBAN_SEMI_ELASTICITY_DEFAULT, demand_location_shares
            beta = URBAN_SEMI_ELASTICITY_DEFAULT if urban_semi_elasticity is None else urban_semi_elasticity
            return demand_location_shares(year, s, urban_semi_elasticity=beta, income_damping=drift_damping)
        if source == "lgbr_plus_gsdp_drift" and year > 2025:
            s = s * np.exp(gsdp_share_slopes() * (year - 2025) * drift_damping)
            s = s / s.sum()
        return s
    dp = pd.read_csv(C.DERIVED / "demand_proxy_region_year.csv")
    year = min(year, int(dp.year.max()))
    dp = dp[dp.year == year].set_index("region")
    s = pop_weight * dp["pop_share"] + (1 - pop_weight) * dp["gsdp_share"]
    return (s / s.sum()).reindex(C.REGIONS)


def hydro_ceiling_twh() -> pd.Series:
    """Indicative hydro ENERGY ceiling per region (TWh/yr) = mean observed hydro generation
    FY2021-22..FY2025-26 x CEA (exploitable identified potential / developed). See D4."""
    _, base = reference_shares()
    hp = pd.read_csv(C.EXTERNAL / "cea_hydro_potential_region_20231031.csv").set_index("region").loc[C.REGIONS]
    ratio = hp["exploitable_identified_capacity_2017_23_mw"] / hp["developed_mw"]
    return (base["hydro"] * ratio).rename("hydro_ceiling_twh")


def solve_year(N: dict, rho: pd.DataFrame, base: pd.DataFrame, delta: pd.Series,
               lam: float = C.DEMAND_PROXIMITY_WEIGHT, weights: dict | None = None,
               caps: dict | None = None, geography_mode: str = "observed",
               hydro_ceiling: pd.Series | None = None) -> tuple[pd.DataFrame, dict]:
    weights = weights or C.GEOGRAPHY_WEIGHTS
    caps = caps or C.SHARE_CAP_MULTIPLIER
    R, K = len(C.REGIONS), len(C.SOURCES)
    Nv = np.array([max(N[k], 0.0) for k in C.SOURCES])
    G = Nv.sum()
    n = Nv / G
    P = rho.values                                   # R x K
    target = P * n                                   # reference x~
    w = np.array([weights[k] for k in C.SOURCES]) / np.maximum(n, 1e-9)
    d = delta.values

    lb = np.zeros((R, K))
    if geography_mode == "relaxed":
        ub = np.repeat(n[None, :], R, axis=0)
    else:
        ub = np.minimum(n[None, :], np.array([caps[k] for k in C.SOURCES])[None, :] * P * n[None, :])
    hydro_flag = ""
    ceiling_mode = "off (hydro geography not resource-capped)"
    if hydro_ceiling is not None:
        ceiling_mode = "strict (indicative CEA-potential ceiling, exploratory)"
        j = C.SOURCES.index("hydro")
        cap_twh = hydro_ceiling.reindex(C.REGIONS).values
        if Nv[j] > cap_twh.sum() * (1 + 1e-9):
            # v1.2: never enlarge the source-backed ceiling. Return a structured infeasibility result.
            return None, {"success": False, "status": "infeasible_under_indicative_hydro_ceiling", "solver": "not run",
                          "message": (f"national hydro {Nv[j]:,.1f} TWh exceeds the indicative CEA-potential ceiling "
                                      f"{cap_twh.sum():,.1f} TWh; constrained allocation skipped"),
                          "objective": np.nan, "max_conservation_residual_twh_before_rescale": np.nan,
                          "max_bound_violation": np.nan, "hydro_flag": "infeasible", "ceiling_mode": ceiling_mode,
                          "hydro_required_twh": float(Nv[j]), "hydro_ceiling_total_twh": float(cap_twh.sum()),
                          "max_hydro_ceiling_violation_twh": np.nan}
        ub[:, j] = np.minimum(n[j], cap_twh / G)
    for j, k in enumerate(C.SOURCES):
        if k in ("hydro", "nuclear"):
            lb[:, j] = np.minimum(base[k].values / G, ub[:, j])
    ub = np.maximum(ub, lb)

    def f(x):
        X = x.reshape(R, K)
        dev = X - target
        rt = X.sum(axis=1) - d
        return float((w[None, :] * dev ** 2).sum() + lam * (rt ** 2).sum())

    def grad(x):
        X = x.reshape(R, K)
        g = 2 * w[None, :] * (X - target) + 2 * lam * (X.sum(axis=1) - d)[:, None]
        return g.ravel()

    A = np.zeros((K, R * K))
    for j in range(K):
        A[j, j::K] = 1.0
    cons = [{"type": "eq", "fun": lambda x: A @ x - n, "jac": lambda x: A}]
    x0 = np.clip(target, lb, ub).ravel()
    scale = 1.0 + lam                                # keeps the objective well-conditioned for large lambda
    fs = lambda x: f(x) / scale                      # noqa: E731
    gs = lambda x: grad(x) / scale                   # noqa: E731
    bnds = list(zip(lb.ravel(), ub.ravel()))
    res = optimize.minimize(fs, x0, jac=gs, bounds=bnds, constraints=cons, method="SLSQP",
                            options={"maxiter": 1000, "ftol": 1e-12})
    solver = "SLSQP"
    if not res.success:                              # robust fallback for the convex QP
        lc = optimize.LinearConstraint(A, n, n)
        res2 = optimize.minimize(fs, np.clip(res.x, lb.ravel(), ub.ravel()), jac=gs, bounds=optimize.Bounds(lb.ravel(), ub.ravel()),
                                 constraints=[lc], method="trust-constr", options={"maxiter": 3000, "gtol": 1e-10})
        if res2.success or res2.fun <= res.fun + 1e-12:
            res, solver = res2, "trust-constr (fallback)"
            res.success = True if res2.success or np.abs(A @ res2.x - n).max() < 1e-8 else res2.success
    X = res.x.reshape(R, K)
    eq_resid_before = float(np.abs(X.sum(axis=0) - n).max() * G)
    X = np.clip(X, 0, None)
    colsum = X.sum(axis=0)
    X = X * np.divide(n, colsum, out=np.zeros_like(n), where=colsum > 0)[None, :]   # exact conservation
    out = pd.DataFrame(X * G, index=C.REGIONS, columns=C.SOURCES)
    bound_viol = float(max((lb - X).max(), (X - ub).max(), 0) * G)
    hv = np.nan
    if hydro_ceiling is not None:   # check against the ORIGINAL ceiling, never an expanded bound
        hv = float(max((out["hydro"] - hydro_ceiling.reindex(C.REGIONS)).max(), 0.0))
    ok = bool(res.success) and bound_viol < 1e-6 and (np.isnan(hv) or hv < 1e-6)
    diag = {"success": ok, "status": "solved" if ok else "solver_failed_or_bounds_violated", "solver": solver,
            "message": str(res.message), "objective": float(res.fun) * scale,
            "max_conservation_residual_twh_before_rescale": eq_resid_before, "max_bound_violation": bound_viol,
            "hydro_flag": hydro_flag, "ceiling_mode": ceiling_mode, "hydro_required_twh": float(Nv[C.SOURCES.index("hydro")]),
            "hydro_ceiling_total_twh": float(hydro_ceiling.sum()) if hydro_ceiling is not None else np.nan,
            "max_hydro_ceiling_violation_twh": hv}
    return out, diag


def allocate_scenario(scen_df: pd.DataFrame, lam: float = C.DEMAND_PROXIMITY_WEIGHT,
                      demand_source: str = "lgbr_plus_demographic_drift", weights=None, caps=None,
                      pop_weight: float = C.POP_WEIGHT, drift_damping: float = 0.5,
                      geography_mode: str = "observed", use_hydro_potential: bool = True,
                      urban_semi_elasticity: float | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    rho, base = reference_shares()
    hc = hydro_ceiling_twh() if use_hydro_potential else None
    rows, diags = [], []
    for _, r in scen_df.iterrows():
        delta = demand_shares(demand_source, year=int(r["fy_end_year"]), pop_weight=pop_weight,
                              drift_damping=drift_damping, urban_semi_elasticity=urban_semi_elasticity)
        N = {k: r[f"{k}_twh"] for k in C.SOURCES}
        alloc, diag = solve_year(N, rho, base, delta, lam, weights, caps, geography_mode, hc)
        G = sum(N.values())
        if alloc is not None:            # infeasible years produce NO allocation rows (see diag.status)
            for reg in C.REGIONS:
                for k in C.SOURCES:
                    rows.append({"scenario": r["scenario"], "fy_end_year": int(r["fy_end_year"]), "region": reg,
                                 "source": k, "twh": alloc.loc[reg, k]})
        diag.update({"scenario": r["scenario"], "fy_end_year": int(r["fy_end_year"]), "national_twh": G,
                     **{f"demand_share_{k}": v for k, v in delta.items()}})
        diags.append(diag)
    out = pd.DataFrame(rows, columns=["scenario", "fy_end_year", "region", "source", "twh"])
    out["value_type"] = ("conditional regional projection - illustrative allocation; hydro ceiling "
                         + ("ON (strict)" if use_hydro_potential else "OFF (unconstrained hydro geography)"))
    return out, pd.DataFrame(diags)


def infeasible_years(diag: pd.DataFrame) -> pd.DataFrame:
    return diag[diag["status"] == "infeasible_under_indicative_hydro_ceiling"]


def regional_summary(alloc: pd.DataFrame, diag: pd.DataFrame) -> pd.DataFrame:
    g = alloc.groupby(["scenario", "fy_end_year", "region"])["twh"].sum().rename("generation_twh").reset_index()
    nat = g.groupby(["scenario", "fy_end_year"])["generation_twh"].transform("sum")
    g["share_of_national"] = g["generation_twh"] / nat
    dl = diag.melt(id_vars=["scenario", "fy_end_year"], value_vars=[f"demand_share_{r}" for r in C.REGIONS],
                   var_name="region", value_name="demand_proxy_share")
    dl["region"] = dl["region"].str.replace("demand_share_", "", regex=False)
    g = g.merge(dl, on=["scenario", "fy_end_year", "region"])
    g["demand_equivalent_twh"] = g["demand_proxy_share"] * nat
    g["indicative_net_export_twh"] = g["generation_twh"] - g["demand_equivalent_twh"]
    piv = alloc.pivot_table(index=["scenario", "fy_end_year", "region"], columns="source", values="twh").reset_index()
    piv["non_fossil_share"] = piv[C.NON_FOSSIL].sum(axis=1) / piv[C.SOURCES].sum(axis=1)
    piv["variable_re_share"] = piv[C.VARIABLE_RE].sum(axis=1) / piv[C.SOURCES].sum(axis=1)
    piv["dispatchable_share"] = piv[C.DISPATCHABLE].sum(axis=1) / piv[C.SOURCES].sum(axis=1)
    out = g.merge(piv[["scenario", "fy_end_year", "region", "non_fossil_share", "variable_re_share",
                       "dispatchable_share"]], on=["scenario", "fy_end_year", "region"])
    out["value_type"] = "model_generated (illustrative allocation; transfer is indicative)"
    return out


def conservation_checks(alloc: pd.DataFrame, scen: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (s, y), g in alloc.groupby(["scenario", "fy_end_year"]):
        sr = scen[(scen.scenario == s) & (scen.fy_end_year == y)].iloc[0]
        nat = sr["domestic_generation_twh"]
        by_src = g.groupby("source")["twh"].sum()
        rows.append({"scenario": s, "fy_end_year": y,
                     "sum_regions_minus_national_twh": g["twh"].sum() - nat,
                     "max_source_conservation_error_twh": max(abs(by_src[k] - sr[f"{k}_twh"]) for k in C.SOURCES),
                     "min_value_twh": g["twh"].min(),
                     "region_shares_sum_pct": 100 * (g.groupby("region")["twh"].sum() / g["twh"].sum()).sum()})
    df = pd.DataFrame(rows)
    df["passed"] = (df.sum_regions_minus_national_twh.abs() < 1e-6) & (df.max_source_conservation_error_twh < 1e-6) & \
                   (df.min_value_twh >= 0) & ((df.region_shares_sum_pct - 100).abs() < 1e-9)
    return df


def main() -> dict:
    scen = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
    rho, base = reference_shares()
    delta_org = demand_shares("organizer_proxy", year=2024)
    delta = demand_shares("lgbr_constant")
    delta_lgbr = delta
    rho.to_csv(C.OUTPUTS / "allocation_reference_shares.csv")
    pd.DataFrame({"demand_proxy_organizer_2024": delta_org, "lgbr_actual_requirement_share_fy2025": delta_lgbr,
                  "difference_pp": 100 * (delta_org - delta_lgbr),
                  "organizer_gsdp_share_log_slope_2014_2024": gsdp_share_slopes(),
                  "v1_0_default_demand_share_fy2047": demand_shares("lgbr_plus_gsdp_drift", year=2047),
                  "v1_1_default_demand_share_fy2047": demand_shares("lgbr_plus_demographic_drift", year=2047)}
                 ).to_csv(C.OUTPUTS / "demand_proxy_validation.csv")
    alloc, diag = allocate_scenario(scen)
    alloc.to_csv(C.OUTPUTS / "regional_allocation.csv", index=False)
    diag.to_csv(C.OUTPUTS / "allocation_solver_diagnostics.csv", index=False)
    summ = regional_summary(alloc, diag)
    summ.to_csv(C.OUTPUTS / "regional_summary.csv", index=False)
    chk = conservation_checks(alloc, scen)
    chk.to_csv(C.OUTPUTS / "allocation_conservation_checks.csv", index=False)
    # observed implied transfer in the base year for context
    reg = pd.read_csv(C.DERIVED / "regional_generation_fy.csv")
    obs = reg[reg.fy_end_year == C.BASE_FY_END].groupby("region")["twh"].sum().reindex(C.REGIONS)
    lg = pd.read_csv(C.EXTERNAL / "cea_lgbr_regional_requirement_fy2025.csv").set_index("region")
    meta = {"solver_all_success": bool(diag.success.all()), "n_solves": int(len(diag)),
            "max_conservation_residual_before_rescale_twh": float(diag.max_conservation_residual_twh_before_rescale.max()),
            "max_bound_violation_twh": float(diag.max_bound_violation.max()),
            "conservation_checks_passed": bool(chk.passed.all()),
            "observed_generation_share_base_year": (obs / obs.sum()).round(4).to_dict(),
            "demand_basis_default": DEMAND_BASES["lgbr_plus_demographic_drift"],
            "hydro_ceiling_twh": hydro_ceiling_twh().round(2).to_dict(),
            "statuses": diag.status.value_counts().to_dict(),
            "n_infeasible_under_hydro_ceiling": int(len(infeasible_years(diag))),
            "max_hydro_ceiling_violation_twh_vs_original": float(np.nanmax(diag.max_hydro_ceiling_violation_twh)),
            "organizer_proxy_share_2024": delta_org.round(4).to_dict(),
            "lgbr_requirement_share_fy2025": delta_lgbr.round(4).to_dict(),
            "reference_shares": rho.round(4).to_dict()}
    (C.OUTPUTS / "allocation_meta.json").write_text(json.dumps(meta, indent=2, default=float))
    sensitivity_and_checks(scen)
    print(f"[allocation] {meta['n_solves']} solves; all success={meta['solver_all_success']}; "
          f"conservation passed={meta['conservation_checks_passed']}")
    return meta


SENSITIVITY_CASES = {
    "v1.1 default (demographic demand drift; CEA hydro ceiling; observed geography)": {},
    "v1.0 settings (GSDP-share drift; no hydro ceiling)": {"demand_source": "lgbr_plus_gsdp_drift", "use_hydro_potential": False},
    "Relaxed geography (no zero rules, no share caps; hydro ceiling kept)": {"geography_mode": "relaxed"},
    "Demand basis: organizer population+GSDP proxy only": {"demand_source": "organizer_proxy"},
    "No demand-proximity term (lambda = 0)": {"lam": 0.0},
    "Strong demand proximity (lambda = 10)": {"lam": 10.0},
    "Urbanization semi-elasticity 0 (population only)": {"urban_semi_elasticity": 0.0},
    "Urbanization semi-elasticity 2%/pp": {"urban_semi_elasticity": 0.02},
    "No capacity- or consumption-derived inputs (hydro ceiling OFF, lambda = 0)": {"use_hydro_potential": False, "lam": 0.0},
}


def sensitivity_and_checks(scen: pd.DataFrame, year: int = C.HEADLINE_FY_END) -> pd.DataFrame:
    """Headline-year regional sensitivity + hydro-potential check (all scenarios)."""
    rows, hyd = [], []
    hc = hydro_ceiling_twh()
    for case, kw in SENSITIVITY_CASES.items():
        sub = scen[scen.fy_end_year == year]
        al, dg = allocate_scenario(sub, **kw)
        sm = regional_summary(al, dg)
        for _, r in sm.iterrows():
            rows.append({"case": case, "scenario": r.scenario, "fy_end_year": year, "region": r.region,
                         "generation_twh": r.generation_twh, "share_of_national": r.share_of_national,
                         "demand_location_share": r.demand_proxy_share,
                         "indicative_net_export_twh": r.indicative_net_export_twh, "non_fossil_share": r.non_fossil_share})
        h = al[al.source == "hydro"]
        for _, r in h.iterrows():
            hyd.append({"case": case, "scenario": r.scenario, "region": r.region, "hydro_twh": r.twh,
                        "cea_potential_ceiling_twh": hc[r.region], "utilisation_of_ceiling": r.twh / hc[r.region],
                        "exceeds_ceiling": r.twh > hc[r.region] * (1 + 1e-6)})
    out = pd.DataFrame(rows)
    out["value_type"] = "model_generated sensitivity (illustrative)"
    out.to_csv(C.OUTPUTS / "allocation_sensitivity.csv", index=False)
    hy = pd.DataFrame(hyd)
    hy["value_type"] = "check: model allocation vs indicative CEA-potential energy ceiling"
    hy.to_csv(C.OUTPUTS / "hydro_potential_check.csv", index=False)
    return out


if __name__ == "__main__":
    main()
