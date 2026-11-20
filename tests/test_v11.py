"""v1.1 tests: accounting split, published FY2025-26 fuel split, demography, hydro ceiling, labels."""
import numpy as np
import pandas as pd

from src import allocation, config as C, demography as DM, scenarios


def test_domestic_plus_imports_equals_total():
    sc = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
    assert np.allclose(sc.domestic_generation_twh + sc.imported_generation_twh, sc.total_generation_twh)
    c = sc[(sc.scenario == "central") & (sc.fy_end_year == C.HEADLINE_FY_END)].iloc[0]
    assert round(c.domestic_generation_twh, 2) == 5312.18 and round(c.imported_generation_twh, 3) == 7.804


def test_fy2026_fuel_split_is_published_not_estimated():
    m = pd.read_csv(C.DERIVED / "national_mix_fy.csv")
    r = m[m.fy_end_year == 2026].set_index("source")
    assert r.loc["coal", "value_type"] == "external_observed"
    assert np.isclose(r.loc["coal", "twh"], (1250338.80 + 30330.01) / 1000)
    assert r.loc["gas", "value_type"] == "derived_residual"
    assert np.isclose(r.loc["gas", "twh"], (1307130.61 - 1250338.80 - 30330.01) / 1000)
    assert "estimated_split" not in set(r.value_type)


def test_central_demography_leaves_generation_unchanged():
    base = scenarios.project("central")
    v = DM.apply_variant(base, "central")
    assert np.allclose(base.domestic_generation_twh, v.domestic_generation_twh)


def test_population_variants_move_generation_in_expected_direction():
    base = scenarios.project("central")
    lo = DM.apply_variant(base, "low_pop").domestic_generation_twh.iloc[-1]
    hi = DM.apply_variant(base, "high_pop").domestic_generation_twh.iloc[-1]
    c = base.domestic_generation_twh.iloc[-1]
    assert lo < c < hi
    fast = DM.apply_variant(base, "fast_urban", urban_semi_elasticity=0.01).domestic_generation_twh.iloc[-1]
    assert fast > c


def test_tg_projection_reproduced_at_anchor_years():
    p = DM.national_path().set_index("fy_end_year")
    assert np.isclose(p.loc[2036, "population_m"], 1522.288)
    assert np.isclose(p.loc[2036, "urban_pct"], 39.06)
    rp = DM.regional_paths()
    assert np.allclose(rp.groupby("fy_end_year").pop_share.sum(), 1.0)


def test_default_allocation_respects_hydro_ceiling():
    al = pd.read_csv(C.OUTPUTS / "regional_allocation.csv")
    hc = allocation.hydro_ceiling_twh()
    h = al[al.source == "hydro"]
    assert (h.apply(lambda r: r.twh <= hc[r.region] * (1 + 1e-6), axis=1)).all()


def test_regional_summary_has_value_type_and_interval_labels():
    assert "value_type" in pd.read_csv(C.OUTPUTS / "regional_summary.csv").columns
    f = pd.read_csv(C.OUTPUTS / "national_forecast_statistical.csv")
    lab = f[(f.model == "rw_drift") & (f.fy_end_year == C.HEADLINE_FY_END)].interval_label.iloc[0]
    assert "NOT empirically calibrated" in lab


def test_relaxed_geography_still_conserves():
    sc = scenarios.project("accelerated")
    sc = sc[sc.fy_end_year == C.HEADLINE_FY_END]
    al, dg = allocation.allocate_scenario(sc, geography_mode="relaxed")
    assert dg.success.all() and np.isclose(al.twh.sum(), sc.domestic_generation_twh.iloc[0]) and (al.twh >= 0).all()
