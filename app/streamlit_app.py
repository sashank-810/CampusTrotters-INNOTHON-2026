"""India 2047 Electricity GENERATION - interactive dashboard (Streamlit), final v1.3.

Run from the repository root:
    python run_all.py
    streamlit run app/streamlit_app.py

Every number shown is either (a) an observed value from a file in data/ (labelled with its source),
or (b) recomputed live by the same code in src/ that produced outputs/. Nothing is hard-coded.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import allocation, config as C, demography as DM, scenarios  # noqa: E402

st.set_page_config(page_title="India 2047 Electricity Generation", layout="wide")
LBL = C.SOURCE_LABELS
SHORT = {k: v.split(" (")[0] for k, v in LBL.items()}
SHORT["gas"] = "Gas + minor diesel"


@st.cache_data
def load():
    return {
        "nat": pd.read_csv(C.DERIVED / "national_generation_fy.csv"),
        "mix": pd.read_csv(C.DERIVED / "national_mix_fy.csv"),
        "reg": pd.read_csv(C.DERIVED / "regional_generation_fy.csv"),
        "ember": pd.read_csv(C.DERIVED / "ember_cy.csv"),
        "stat": pd.read_csv(C.OUTPUTS / "national_forecast_statistical.csv"),
        "bt_cea": pd.read_csv(C.OUTPUTS / "backtest_cea_fy_summary.csv"),
        "bt_emb": pd.read_csv(C.OUTPUTS / "backtest_ember_cy_summary.csv"),
        "bt_cea_h": pd.read_csv(C.OUTPUTS / "backtest_cea_fy_by_horizon.csv"),
        "bt_gdp": pd.read_csv(C.OUTPUTS / "backtest_gdp_elasticity_vs_rw.csv"),
        "checks": pd.read_csv(C.OUTPUTS / "validation_checks.csv"),
        "manifest": pd.read_csv(C.EXTERNAL / "SOURCE_MANIFEST.csv"),
        "nep": pd.read_csv(C.OUTPUTS / "crosscheck_nep_requirement.csv"),
        "dpv": pd.read_csv(C.OUTPUTS / "demand_proxy_validation.csv", index_col=0),
        "hyd": pd.read_csv(C.OUTPUTS / "hydro_potential_check.csv"),
        "sens": pd.read_csv(C.OUTPUTS / "allocation_sensitivity.csv"),
        "demo_reg": pd.read_csv(C.OUTPUTS / "demography_regional_paths.csv"),
        "dq": (C.REPORTS / "data_quality_report.md").read_text(),
        "elas": scenarios.elasticity_estimates(),
        "hceil": allocation.hydro_ceiling_twh(),
    }


@st.cache_data
def run_scenario(name: str, overrides: tuple, eps0: float, demo: tuple) -> pd.DataFrame:
    ov = dict(overrides)
    if "mix_2047" in ov:
        ov["mix_2047"] = dict(ov["mix_2047"])
    df = scenarios.feasibility_flags(scenarios.project(name, overrides=ov, eps0=eps0))
    d = dict(demo)
    return DM.apply_variant(df, d.get("variant", "central"), urban_semi_elasticity=d.get("beta", DM.URBAN_SEMI_ELASTICITY_DEFAULT))


@st.cache_data
def run_allocation(scen_df: pd.DataFrame, lam: float, demand_source: str, pop_weight: float, damping: float,
                   geo: str, hydro_pot: bool, beta: float):
    al, diag = allocation.allocate_scenario(scen_df, lam=lam, demand_source=demand_source, pop_weight=pop_weight,
                                            drift_damping=damping, geography_mode=geo, use_hydro_potential=hydro_pot,
                                            urban_semi_elasticity=beta)
    return al, diag, allocation.regional_summary(al, diag)


D = load()
base_fy = C.BASE_FY_END
H = C.HEADLINE_FY_END
fy = lambda y: f"FY{y-1}-{str(y)[-2:]}"  # noqa: E731

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Scenario")
scen_key = st.sidebar.radio("Scenario", list(C.SCENARIOS), format_func=lambda k: C.SCENARIOS[k]["label"], index=1, key="scenario")
P = C.SCENARIOS[scen_key]
st.sidebar.caption("Scenario ranges are assumption-driven, not statistical intervals.")

st.sidebar.header("Economy & electrification (assumptions)")
g0 = st.sidebar.slider("Real GDP growth, FY2026-27 (%)", 3.0, 9.0, round(P["gdp_growth_start"] * 100, 1), 0.1, key="g0") / 100
g1 = st.sidebar.slider("Real GDP growth reached by FY2046-47 (%)", 2.0, 8.0, round(P["gdp_growth_end"] * 100, 1), 0.1, key="g1") / 100
e0 = st.sidebar.slider("Starting generation-GDP elasticity (estimated %.3f)" % D["elas"]["eps0_trailing_ratio"],
                       0.40, 1.30, round(D["elas"]["eps0_trailing_ratio"], 2), 0.01, key="e0")
e1 = st.sidebar.slider("Elasticity by FY2046-47", 0.30, 1.20, float(P["elasticity_end"]), 0.01, key="e1")
addon = st.sidebar.slider("Extra electrification demand by FY2046-47 (TWh)", 0.0, 800.0, float(P["addon_twh_2047"]), 10.0, key="addon")

st.sidebar.header("Population & urbanization")
demo_var = st.sidebar.selectbox("Demographic variant", list(DM.DEMO_VARIANTS), format_func=lambda k: DM.DEMO_VARIANTS[k]["label"], key="demo_var")
beta = st.sidebar.slider("Urbanization semi-elasticity (% generation per +1 pp urban share)", 0.0, 2.0,
                         DM.URBAN_SEMI_ELASTICITY_DEFAULT * 100, 0.1, key="beta") / 100
st.sidebar.caption("Central variant = official TG projection (to 2036) and leaves national generation unchanged: "
                   "the GDP path already embeds it. Variants hold per-capita income fixed (no GDP double counting).")

with st.sidebar.expander("FY2046-47 generation mix (assumption, % of domestic generation)"):
    m = P["mix_2047"]
    solar = st.slider("Solar", 0, 70, int(round(m["solar"] * 100)), key="mix_solar")
    wind = st.slider("Wind", 0, 40, int(round(m["wind"] * 100)), key="mix_wind")
    nuclear = st.slider("Nuclear", 0, 25, int(round(m["nuclear"] * 100)), key="mix_nuclear")
    hydro = st.slider("Hydro (>25 MW)", 0, 20, int(round(m["hydro"] * 100)), key="mix_hydro")
    gas = st.slider("Gas (+ minor diesel)", 0, 15, int(round(m["gas"] * 100)), key="mix_gas")
    other = st.slider("Other RE", 0, 10, int(round(m["other_re"] * 100)), key="mix_other")
    nonc = solar + wind + nuclear + hydro + gas + other
    coal = max(100 - nonc, 0)
    st.write(f"Coal & lignite (remainder): **{coal}%**")
mix_ov = {"coal": coal, "gas": gas, "nuclear": nuclear, "hydro": hydro, "solar": solar, "wind": wind, "other_re": other}
renorm = nonc > 100

st.sidebar.header("Conditional regional allocation (illustrative)")
use_req = st.sidebar.checkbox("EXPLORATORY: use electricity-requirement demand-location term", True, key="use_req",
                              help="Uses CEA energy REQUIREMENT shares (consumption side) only to locate demand for the transfer "
                                   "term - never as generation. Rule applicability awaits organizer confirmation; untick to remove.")
lam = st.sidebar.slider("Weight on generating near demand (lambda)", 0.0, 20.0, float(C.DEMAND_PROXIMITY_WEIGHT), 0.5, key="lam")
dsrc = st.sidebar.selectbox("Demand-location basis", list(allocation.DEMAND_BASES), format_func=lambda k: allocation.DEMAND_BASES[k], key="dsrc")
geo = st.sidebar.selectbox("Geography assumption", ["observed", "relaxed"],
                           format_func=lambda k: {"observed": "Anchored on observed generation (default)",
                                                  "relaxed": "Relaxed (no zero rules, no share caps)"}[k], key="geo")
hydro_pot = st.sidebar.checkbox("EXPLORATORY: strict CEA hydro-potential ceiling", True, key="hydro_pot",
                                help="Uses CEA hydro potential (MW) only as a dimensionless ratio to scale observed hydro "
                                     "generation into an indicative energy ceiling. Rule applicability awaits organizer confirmation.")
popw = st.sidebar.slider("Population weight in organizer proxy", 0.0, 1.0, float(C.POP_WEIGHT), 0.05, key="popw")
damp = st.sidebar.slider("Damping of per-capita income drift", 0.0, 1.0, 0.5, 0.05, key="damp")
show_pi = st.sidebar.checkbox("Show statistical intervals", True, key="show_pi")

overrides = (("gdp_growth_start", g0), ("gdp_growth_end", g1), ("elasticity_end", e1), ("addon_twh_2047", addon),
             ("mix_2047", tuple(sorted(mix_ov.items()))))
SC = run_scenario(scen_key, overrides, e0, (("variant", demo_var), ("beta", beta)))
lam_eff = lam if use_req else 0.0
dsrc_eff = dsrc if use_req else "organizer_proxy"   # requirement data fully removed when the toggle is off
AL, DIAG, RS = run_allocation(SC, lam_eff, dsrc_eff, popw, damp, geo, hydro_pot, beta)
INFEAS = allocation.infeasible_years(DIAG)
ALLOC_MODE = "strict hydro ceiling" if hydro_pot else "hydro ceiling OFF (unconstrained hydro geography)"
if len(INFEAS):
    # v1.2: the strict ceiling is never enlarged. Show an explicitly UNCONSTRAINED illustration instead.
    AL, DIAG_U, RS = run_allocation(SC, lam_eff, dsrc_eff, popw, damp, geo, False, beta)
    ALLOC_MODE = "UNCONSTRAINED fallback (hydro ceiling ignored) - NOT ceiling-compliant"

# ---------------------------------------------------------------------------
st.title("India electricity GENERATION to 2047 - national forecast and conditional regional projections")
st.caption("Metric: electricity **generated** (TWh = BU), never consumption or installed capacity. FY = Indian financial year "
           "(Apr-Mar), labelled by end year (2047 = FY2046-47). Headline = **domestic** generation; Bhutan imports shown separately.")
if len(INFEAS):
    r0 = INFEAS.iloc[INFEAS.fy_end_year.argmax()]
    st.error(f"INFEASIBLE under the indicative CEA hydro-potential ceiling for {len(INFEAS)} year(s) from "
             f"{fy(int(INFEAS.fy_end_year.min()))}: national hydro in {fy(int(r0.fy_end_year))} = {r0.hydro_required_twh:,.1f} TWh "
             f"vs ceiling {r0.hydro_ceiling_total_twh:,.1f} TWh. Regional charts below use an UNCONSTRAINED fallback "
             "(hydro ceiling ignored) that is NOT ceiling-compliant. Lower the hydro share to restore a compliant allocation.")
if renorm:
    rn = {k: v / nonc for k, v in mix_ov.items()}
    st.error(f"Mix sliders sum to {nonc}% (>100%). Coal set to 0 and the other shares RENORMALISED to: " +
             ", ".join(f"{SHORT[k]} {100*v:.1f}%" for k, v in rn.items() if v > 0))

h = SC[SC.fy_end_year == H].iloc[0]
rw = D["stat"][(D["stat"].model == "rw_drift") & (D["stat"].fy_end_year == H)].iloc[0]
nb = D["nat"].set_index("fy_end_year").loc[base_fy]
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Observed {fy(base_fy)} domestic generation", f"{nb.domestic_twh:,.1f} TWh",
          help=f"CEA total incl. Bhutan import = {nb.total_twh:,.3f} TWh; import {nb.bhutan_import_twh:,.3f} TWh")
c2.metric(f"{fy(H)} domestic generation - {C.SCENARIOS[scen_key]['label']}", f"{h.domestic_generation_twh:,.1f} TWh",
          help=f"+ assumed Bhutan imports {h.total_generation_twh - h.domestic_generation_twh:,.3f} TWh "
               f"= CEA-definition total {h.total_generation_twh:,.1f} TWh")
c3.metric(f"{fy(H)} statistical median (CEA-total basis)", f"{rw.point_twh:,.0f} TWh",
          help="RW-drift; model-based illustrative 95% interval "
               f"{rw.lo95:,.0f}-{rw.hi95:,.0f} TWh - long-horizon extrapolation, NOT empirically calibrated at 2047")
c4.metric(f"Non-fossil share {fy(H)} (assumed mix)", f"{100*h.non_fossil_share:.0f}%")
if h.provisional_flags:
    st.warning("Provisional plausibility flags (not feasibility proofs): " + h.provisional_flags)

tabs = st.tabs(["National forecast", "Population & urbanization", "Energy mix", "Regional (conditional)",
                "Model evaluation", "Data & provenance", "Assumptions & limitations"])

with tabs[0]:
    nat = D["nat"].set_index("fy_end_year")
    df = pd.DataFrame(index=range(2010, C.HORIZON_END + 1))
    df["Observed - CEA domestic generation (FY)"] = nat["domestic_twh"]
    for k in C.SCENARIOS:
        same = k == scen_key
        s = run_scenario(k, overrides if same else (), e0 if same else D["elas"]["eps0_trailing_ratio"],
                         (("variant", demo_var), ("beta", beta)) if same else ())
        col = f"Scenario {C.SCENARIOS[k]['label']} - domestic" + (" (your settings)" if same else " (defaults)")
        df[col] = s.set_index("fy_end_year")["domestic_generation_twh"]
        df.loc[base_fy, col] = nb.domestic_twh
    st.subheader("Scenario projections (assumption-driven) - domestic generation, TWh")
    st.line_chart(df)
    st.subheader("Independently fitted national statistical forecast (RW-drift; CEA-total basis incl. Bhutan imports)")
    st_ = D["stat"][D["stat"].model == "rw_drift"].set_index("fy_end_year")
    sf = pd.DataFrame(index=range(2010, C.HORIZON_END + 1))
    sf["Observed - CEA total generation"] = nat["total_twh"]
    sf["RW-drift median"] = st_["point_twh"]
    if show_pi:
        sf["Model-based 80% lower"] = st_["lo80"]
        sf["Model-based 80% upper"] = st_["hi80"]
        sf["Model-based 95% lower"] = st_["lo95"]
        sf["Model-based 95% upper"] = st_["hi95"]
    st.line_chart(sf)
    st.caption("Intervals are model-based. Rolling-origin backtests only cover 1-5 year horizons (CEA series 95% coverage: "
               f"{D['bt_cea'].set_index('model').loc['rw_drift','coverage95_pct']:.1f}%). Beyond FY2031 they are long-horizon "
               "extrapolations, NOT empirically calibrated. Scenario ranges are a separate, assumption-driven layer.")
    em = D["ember"].set_index("year")["electricity_generation"].loc[2000:]
    st.subheader("Ember calendar-year generation (incl. captive) - on its own calendar-year axis")
    st.line_chart(em.rename("Ember CY total generation (TWh)").to_frame())
    st.subheader("External plausibility check (NEP requirement is NOT generation)")
    st.dataframe(D["nep"].round(1))
    cols = ["fy_end_year", "gdp_growth", "implied_per_capita_gdp_growth", "elasticity", "addon_twh", "population_m", "urban_pct",
            "demographic_factor", "domestic_generation_twh", "imported_generation_twh" if "imported_generation_twh" in SC else "bhutan_import_twh",
            "total_generation_twh", "per_capita_domestic_generation_kwh", "non_fossil_share", "provisional_flags"]
    st.subheader("Selected scenario - yearly table")
    st.dataframe(SC[[c for c in cols if c in SC]].round(3))
    st.download_button("Download scenario table (CSV)", SC.to_csv(index=False), f"scenario_{scen_key}.csv")

with tabs[1]:
    st.subheader("Population and urbanization paths (official TG projection to 2036; extrapolated after)")
    npc = DM.national_path().set_index("fy_end_year")
    npv = DM.national_path(pop_growth_delta_pp=DM.DEMO_VARIANTS[demo_var]["pop_growth_delta_pp"],
                           urban_pace=DM.DEMO_VARIANTS[demo_var]["urban_pace"]).set_index("fy_end_year")
    st.line_chart(pd.DataFrame({"Population, central (million)": npc.population_m,
                                f"Population, {demo_var} (million)": npv.population_m}))
    st.line_chart(pd.DataFrame({"Urban share, central (%)": npc.urban_pct, f"Urban share, {demo_var} (%)": npv.urban_pct}))
    st.write(f"**Effect on {fy(H)} domestic generation ({C.SCENARIOS[scen_key]['label']}):** demographic factor "
             f"{h.demographic_factor:.3f} -> {h.domestic_generation_twh:,.1f} TWh; per-capita domestic generation "
             f"{h.per_capita_domestic_generation_kwh:,.0f} kWh/person.")
    dr = D["demo_reg"].pivot(index="fy_end_year", columns="region", values="pop_share")
    st.subheader("Regional population shares (drive the demand-location term of the allocation)")
    st.line_chart(dr)
    st.caption("Sources: Technical Group on Population Projections (NCP/MoHFW, July 2020) Tables 8-10. Values after 2036 and "
               "all variants are assumptions. The urbanization semi-elasticity is illustrative, not estimated.")

with tabs[2]:
    mx = D["mix"].pivot_table(index="fy_end_year", columns="source", values="twh").fillna(0)
    mx = mx.rename(columns={**SHORT, "res_unsplit": "RE (not split in CEA Growth Book)"})
    st.subheader("Historical national mix - observed (TWh, CEA utilities, domestic)")
    st.bar_chart(mx)
    st.caption("FY2017-FY2021: RE not split by source in the retrieved CEA table. FY2024-25: coal/gas split estimated "
               "(FY2023-24 ratio). FY2025-26: coal+lignite from CEA fuel-wise actuals; gas+diesel = thermal - coal - lignite.")
    pm = SC.set_index("fy_end_year")[[f"{k}_twh" for k in C.SOURCES]]
    pm.columns = [SHORT[k] for k in C.SOURCES]
    st.subheader(f"Projected national mix - {C.SCENARIOS[scen_key]['label']} (TWh; shares are ASSUMPTIONS, not optimised)")
    st.bar_chart(pm)
    comp = pd.DataFrame({
        f"{fy(base_fy)} observed share (%)": D["mix"][D["mix"].fy_end_year == base_fy].set_index("source")["share"].reindex(C.SOURCES) * 100,
        f"{fy(H)} assumed share (%)": pd.Series({k: h[f"share_{k}"] for k in C.SOURCES}) * 100,
    })
    comp.index = [LBL[k] for k in C.SOURCES]
    st.dataframe(comp.round(1))
    st.info("The national mix is a POLICY-SCENARIO ASSUMPTION, not the output of a cost, reliability or emissions "
            f"optimisation. Hydro in {fy(H)} uses {100*h.hydro_twh/D['hceil'].sum():.0f}% of the indicative CEA-potential "
            f"energy ceiling ({D['hceil'].sum():,.0f} TWh). Storage/flexibility needs for "
            f"{100*h.variable_re_share:.0f}% variable RE are not modelled.")

with tabs[3]:
    st.markdown(f"**Allocation mode:** {ALLOC_MODE}; demand-location term: "
                f"{'ON (exploratory, requirement-based)' if use_req else 'OFF'}.")
    st.info("Conditional regional projections = an illustrative, generation-conserving allocation of the national scenario "
            "(not independently fitted or backtested regional forecasts). It places the assumed national source totals across CEA regions "
            "close to observed generation geography and demand. Historical shares are NOT physical resource limits; the only "
            "source-backed resource check is the CEA hydro-potential ceiling.")
    region = st.selectbox("Region", C.REGIONS, format_func=lambda r: f"{C.REGION_NAMES[r]} ({r})", key="region")
    year = st.slider("Projection year (FY end)", base_fy + 1, C.HORIZON_END, H, key="year")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"{C.REGION_NAMES[region]} - observed (TWh)")
        rh = D["reg"][D["reg"].region == region].pivot_table(index="fy_end_year", columns="source", values="twh")
        rh = rh.rename(columns={"thermal": "Thermal (coal+gas+diesel)", **SHORT})
        st.bar_chart(rh)
    with col2:
        st.subheader(f"{C.REGION_NAMES[region]} - allocated (TWh)")
        rp = AL[AL.region == region].pivot_table(index="fy_end_year", columns="source", values="twh")[C.SOURCES]
        rp.columns = [SHORT[k] for k in C.SOURCES]
        st.bar_chart(rp)
    st.subheader(f"Regional comparison - {fy(year)}")
    piv = AL[AL.fy_end_year == year].pivot_table(index="region", columns="source", values="twh").reindex(C.REGIONS)[C.SOURCES]
    piv.columns = [SHORT[k] for k in C.SOURCES]
    st.bar_chart(piv)
    ry = RS[RS.fy_end_year == year].set_index("region").reindex(C.REGIONS)
    show = ry[["generation_twh", "share_of_national", "demand_proxy_share", "indicative_net_export_twh",
               "non_fossil_share", "variable_re_share", "dispatchable_share"]].copy()
    show.index = [C.REGION_NAMES[r] for r in show.index]
    st.dataframe(show.round(3))
    nat_y = SC.set_index("fy_end_year").loc[year, "domestic_generation_twh"]
    st.caption(f"Conservation: sum of regions = {ry.generation_twh.sum():,.3f} TWh; national domestic generation = "
               f"{nat_y:,.3f} TWh. 'Indicative net export' = generation located in the region minus its demand-location share "
               "x national generation; a signal of transmission need, not a power-flow result.")
    st.write("Strict-mode solve status by year: " + ", ".join(f"{k}: {v}" for k, v in DIAG.status.value_counts().items()))
    st.subheader("Hydro vs CEA-potential ceiling (selected year)")
    hy = AL[(AL.fy_end_year == year) & (AL.source == "hydro")].set_index("region")["twh"].reindex(C.REGIONS)
    st.dataframe(pd.DataFrame({"allocated_hydro_twh": hy, "indicative_ceiling_twh": D["hceil"],
                               "utilisation": hy / D["hceil"]}).round(3))
    st.subheader(f"Sensitivity of {fy(H)} regional results (precomputed, default scenarios)")
    sv = D["sens"][D["sens"].scenario == scen_key].pivot(index="case", columns="region", values="indicative_net_export_twh")
    st.dataframe(sv.round(1))
    st.subheader("Demand-location basis validation")
    st.dataframe(D["dpv"].round(4))

with tabs[4]:
    st.subheader("Rolling-origin backtests (expanding window, horizons 1-5 years)")
    st.dataframe(D["bt_cea"].round(2))
    st.dataframe(D["bt_emb"].round(2))
    st.line_chart(D["bt_cea_h"].pivot(index="h", columns="model", values="WAPE_pct"))
    st.write("GDP-elasticity engine, CONDITIONAL on realised GDP (oracle) - not an unconditional skill score:")
    st.dataframe(D["bt_gdp"].round(2))
    st.caption("RW-drift has the lowest WAPE on both series, but only marginally ahead of the CAGR baseline on CEA "
               "(see table). MAE/RMSE in TWh; WAPE = sum|error|/sum(actual); coverage = share of actuals inside intervals.")

with tabs[5]:
    st.subheader("Source manifest")
    st.dataframe(D["manifest"])
    c = D["checks"]
    st.subheader(f"Automated validation checks: {int(c.passed.sum())}/{len(c)} passed")
    st.dataframe(c)
    st.markdown(D["dq"])

with tabs[6]:
    st.markdown((C.REPORTS / "assumptions_and_limitations.md").read_text())
