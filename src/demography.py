"""Population growth and urbanization (v1.1).

Source: Technical Group on Population Projections (NCP/MoHFW, July 2020) - official state-wise
projections of total population and urban share for 2021, 2026, 2031, 2036 (1 March).
`data/external/tg_population_projections_2021_2036.csv`.

How demographics enter the model WITHOUT double counting GDP
------------------------------------------------------------
* The core scenario GDP path (config.SCENARIOS) is interpreted as already containing the
  TG central population path. We therefore report the implied per-capita GDP growth
  y_t = (1+g_t)/(1+n_t) - 1 and per-capita generation, but the CENTRAL demographic variant
  leaves national generation unchanged (ratio = 1).
* Demographic VARIANTS (sensitivity, not observations) change population growth and/or the
  pace of urbanization while holding per-capita income and per-capita generation paths fixed:
      G_var(t) = G_core(t) * P_var(t)/P_c(t) * (1 + beta_u * (U_var(t) - U_c(t)))
  where beta_u is an ASSUMED urbanization semi-elasticity (fraction of generation per
  percentage point of urban share beyond the income effect). It is not estimated here.
* Regionally, the demand-LOCATION shares used by the allocation's transfer term drift with
  TG regional population shares and urban shares, plus organizer per-capita GSDP trends
  (organizer GSDP share / organizer population share), so population and income are separated.

FY convention: TG values "as on 1 March of year Y" are aligned to FY end-year Y.
Years after 2036 are EXTRAPOLATIONS (assumptions) documented below.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

TG_YEARS = (2021, 2026, 2031, 2036)
DEMO_VARIANTS = {
    "central": {"label": "Central (TG projection; trends extrapolated after 2036)", "pop_growth_delta_pp": 0.0, "urban_pace": 1.0},
    "low_pop": {"label": "Low population growth (-0.2 pp/yr after FY2026)", "pop_growth_delta_pp": -0.2, "urban_pace": 1.0},
    "high_pop": {"label": "High population growth (+0.2 pp/yr after FY2026)", "pop_growth_delta_pp": 0.2, "urban_pace": 1.0},
    "slow_urban": {"label": "Slow urbanization (half the TG pace after FY2026)", "pop_growth_delta_pp": 0.0, "urban_pace": 0.5},
    "fast_urban": {"label": "Fast urbanization (double the TG pace after FY2026)", "pop_growth_delta_pp": 0.0, "urban_pace": 2.0},
}
URBAN_SEMI_ELASTICITY_DEFAULT = 0.005   # ASSUMPTION: +0.5% generation per +1 pp urban share (illustrative)


def load_tg() -> pd.DataFrame:
    return pd.read_csv(C.EXTERNAL / "tg_population_projections_2021_2036.csv")


def _interp_geometric(anchors: dict, years: range) -> pd.Series:
    ks = sorted(anchors)
    out = {}
    for y in years:
        if y <= ks[0]:
            out[y] = anchors[ks[0]]
            continue
        for a, b in zip(ks[:-1], ks[1:]):
            if a <= y <= b:
                out[y] = anchors[a] * (anchors[b] / anchors[a]) ** ((y - a) / (b - a))
                break
    return pd.Series(out)


def national_path(end: int = C.HORIZON_END, pop_growth_delta_pp: float = 0.0, urban_pace: float = 1.0) -> pd.DataFrame:
    """India population (million) and urban share (%) by FY end-year 2021..end.
    2021-2036: TG official projection (geometric / linear interpolation between anchors).
    2037+: EXTRAPOLATION - annual growth rate declines linearly at the pace implied by the three
    TG 5-year periods (floored at 0); urban share continues the TG 2031-36 increment."""
    tg = load_tg()
    ind = tg[tg.cea_region == "ALL INDIA"].set_index("year")
    P = {y: ind.loc[y, "population_thousand"] / 1000 for y in TG_YEARS}
    U = {y: ind.loc[y, "urban_pct"] for y in TG_YEARS}
    yrs = range(2021, end + 1)
    pop = _interp_geometric(P, range(2021, 2037))
    # period average annual growth rates at mid-points; linear trend for extrapolation
    mids = np.array([2023.5, 2028.5, 2033.5])
    rates = np.array([(P[b] / P[a]) ** (1 / 5) - 1 for a, b in zip(TG_YEARS[:-1], TG_YEARS[1:])])
    slope, icpt = np.polyfit(mids, rates, 1)
    for y in range(2037, end + 1):
        pop[y] = pop[y - 1] * (1 + max(icpt + slope * (y - 0.5), 0.0))
    urb = pd.Series({y: np.interp(y, TG_YEARS, [U[k] for k in TG_YEARS]) for y in range(2021, 2037)})
    inc = (U[2036] - U[2031]) / 5
    for y in range(2037, end + 1):
        urb[y] = min(urb[y - 1] + inc, 100.0)
    df = pd.DataFrame({"fy_end_year": list(yrs), "population_m": pop.reindex(yrs).values, "urban_pct": urb.reindex(yrs).values})
    df["basis"] = np.where(df.fy_end_year <= 2036, "TG official projection (interpolated between 5-yr anchors)",
                           "EXTRAPOLATION of TG trends (assumption)")
    # variants: modify only after FY2026 (base year)
    if pop_growth_delta_pp or urban_pace != 1.0:
        b = C.BASE_FY_END
        p0 = df.set_index("fy_end_year")
        newp, newu = [], []
        for y in df.fy_end_year:
            if y <= b:
                newp.append(p0.loc[y, "population_m"])
                newu.append(p0.loc[y, "urban_pct"])
            else:
                g_c = p0.loc[y, "population_m"] / p0.loc[y - 1, "population_m"] - 1
                newp.append(newp[-1] * (1 + g_c + pop_growth_delta_pp / 100))
                newu.append(min(p0.loc[b, "urban_pct"] + urban_pace * (p0.loc[y, "urban_pct"] - p0.loc[b, "urban_pct"]), 100.0))
        df["population_m"], df["urban_pct"] = newp, newu
        df["basis"] = df["basis"] + np.where(df.fy_end_year > b, " + SENSITIVITY VARIANT", "")
    df["population_growth_pct"] = 100 * df.population_m.pct_change()
    return df


def regional_paths(end: int = C.HORIZON_END) -> pd.DataFrame:
    """Regional (CEA grid) population shares and urban % by FY end-year.
    2021-2036 from TG state rows summed to regions; 2037+ EXTRAPOLATED (log-linear share trend
    2026-2036; linear urban-% trend 2031-2036), renormalised to sum to 1."""
    tg = load_tg()
    st = tg[tg.cea_region.isin(C.REGIONS)].copy()
    st["urban_thousand"] = st.population_thousand * st.urban_pct / 100
    g = st.groupby(["cea_region", "year"])[["population_thousand", "urban_thousand"]].sum().reset_index()
    rows = []
    for r, d in g.groupby("cea_region"):
        d = d.set_index("year")
        P = {y: d.loc[y, "population_thousand"] for y in TG_YEARS}
        Uu = {y: d.loc[y, "urban_thousand"] / d.loc[y, "population_thousand"] * 100 for y in TG_YEARS}
        pop = _interp_geometric(P, range(2021, 2037))
        urb = {y: np.interp(y, TG_YEARS, [Uu[k] for k in TG_YEARS]) for y in range(2021, 2037)}
        for y in range(2021, 2037):
            rows.append((r, y, pop[y], urb[y]))
    df = pd.DataFrame(rows, columns=["region", "fy_end_year", "population_thousand", "urban_pct"])
    df["pop_share"] = df.population_thousand / df.groupby("fy_end_year").population_thousand.transform("sum")
    ext = []
    for r, d in df.groupby("region"):
        d = d.set_index("fy_end_year")
        s_slope = (np.log(d.loc[2036, "pop_share"]) - np.log(d.loc[2026, "pop_share"])) / 10
        u_inc = (d.loc[2036, "urban_pct"] - d.loc[2031, "urban_pct"]) / 5
        for y in range(2037, end + 1):
            ext.append((r, y, np.nan, min(d.loc[2036, "urban_pct"] + u_inc * (y - 2036), 100.0),
                        d.loc[2036, "pop_share"] * np.exp(s_slope * (y - 2036))))
    e = pd.DataFrame(ext, columns=["region", "fy_end_year", "population_thousand", "urban_pct", "pop_share"])
    e["pop_share"] = e.pop_share / e.groupby("fy_end_year").pop_share.transform("sum")
    out = pd.concat([df, e], ignore_index=True).sort_values(["fy_end_year", "region"])
    out["basis"] = np.where(out.fy_end_year <= 2036, "TG official projection (states summed to CEA regions)",
                            "EXTRAPOLATION of TG regional trends (assumption)")
    out["value_type"] = np.where(out.fy_end_year <= 2036, "external_projection", "extrapolated_assumption")
    return out.reset_index(drop=True)


def organizer_per_capita_gsdp_slopes(first: int = 2014, last: int = 2024) -> pd.Series:
    """Slope of log(regional GSDP share / regional population share) per year from organizer data:
    relative per-capita income trend, separated from population so it is not double counted."""
    dp = pd.read_csv(C.DERIVED / "demand_proxy_region_year.csv")
    dp = dp[dp.year.between(first, last)]
    out = {}
    for r, g in dp.groupby("region"):
        x = g.year.values - g.year.mean()
        out[r] = float(np.polyfit(x, np.log(g.gsdp_share.values / g.pop_share.values), 1)[0])
    return pd.Series(out).reindex(C.REGIONS)


def demand_location_shares(year: int, base: pd.Series, urban_semi_elasticity: float = URBAN_SEMI_ELASTICITY_DEFAULT,
                           income_damping: float = 0.5, base_year: int = 2025) -> pd.Series:
    """delta_r(t) proportional to base_r * popshare_r(t)/popshare_r(base) * (1 + beta_u * dU_r) * exp(damp * slope_pc_r * dt)."""
    if year <= base_year:
        return base / base.sum()
    rp = regional_paths().set_index(["fy_end_year", "region"])
    ps_t = rp.loc[year, "pop_share"].reindex(C.REGIONS)
    ps_0 = rp.loc[base_year, "pop_share"].reindex(C.REGIONS)
    du = (rp.loc[year, "urban_pct"] - rp.loc[base_year, "urban_pct"]).reindex(C.REGIONS)
    pc = organizer_per_capita_gsdp_slopes()
    s = base * (ps_t / ps_0) * (1 + urban_semi_elasticity * du) * np.exp(income_damping * pc * (year - base_year))
    return s / s.sum()


def apply_variant(scen: pd.DataFrame, variant: str = "central", urban_semi_elasticity: float = URBAN_SEMI_ELASTICITY_DEFAULT,
                  pop_growth_delta_pp: float | None = None, urban_pace: float | None = None) -> pd.DataFrame:
    """Return a copy of a scenario projection adjusted for a demographic variant (sensitivity).
    Central variant returns identical generation; demographic columns are added in all cases."""
    v = dict(DEMO_VARIANTS[variant])
    if pop_growth_delta_pp is not None:
        v["pop_growth_delta_pp"] = pop_growth_delta_pp
    if urban_pace is not None:
        v["urban_pace"] = urban_pace
    c = national_path().set_index("fy_end_year")
    a = national_path(pop_growth_delta_pp=v["pop_growth_delta_pp"], urban_pace=v["urban_pace"]).set_index("fy_end_year")
    df = scen.copy()
    y = df.fy_end_year
    ratio = (a.loc[y, "population_m"].values / c.loc[y, "population_m"].values) * \
            (1 + urban_semi_elasticity * (a.loc[y, "urban_pct"].values - c.loc[y, "urban_pct"].values))
    df["demographic_variant"] = variant
    df["demographic_factor"] = ratio
    imports = df["total_generation_twh"] - df["domestic_generation_twh"]
    df["domestic_generation_twh"] = df["domestic_generation_twh"] * ratio
    df["total_generation_twh"] = df["domestic_generation_twh"] + imports
    for k in C.SOURCES:
        df[f"{k}_twh"] = df[f"share_{k}"] * df["domestic_generation_twh"]
    df["population_m"] = a.loc[y, "population_m"].values
    df["urban_pct"] = a.loc[y, "urban_pct"].values
    df["per_capita_domestic_generation_kwh"] = df["domestic_generation_twh"] * 1e9 / (df["population_m"] * 1e6)
    pop_g = a.loc[y, "population_m"].values / a.loc[y - 1, "population_m"].values - 1
    if "gdp_growth" in df:
        df["implied_per_capita_gdp_growth"] = (1 + df["gdp_growth"]) / (1 + pop_g) - 1
    return df
