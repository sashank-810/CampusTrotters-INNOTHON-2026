"""v1.2 regression tests: the CEA hydro ceiling is never enlarged; infeasibility is structured;
strict-mode compliance is checked against the ORIGINAL ceiling; quality-gate expectations."""
import numpy as np
import pandas as pd

from src import allocation, config as C, scenarios

MIX_HYDRO_20 = {"coal": 0.22, "gas": 0.02, "nuclear": 0.07, "hydro": 0.20, "solar": 0.35, "wind": 0.12, "other_re": 0.02}


def test_ui_max_hydro_20pct_is_reported_infeasible():
    sc = scenarios.project("central", overrides={"mix_2047": MIX_HYDRO_20})
    al, dg = allocation.allocate_scenario(sc)
    r = dg[dg.fy_end_year == C.HEADLINE_FY_END].iloc[0]
    assert r.status == "infeasible_under_indicative_hydro_ceiling" and not r.success
    assert round(r.hydro_required_twh, 1) == 1062.4 and round(r.hydro_ceiling_total_twh, 1) == 480.4
    assert al[al.fy_end_year == C.HEADLINE_FY_END].empty          # no allocation published for infeasible years
    # every year that WAS solved respects the original regional ceilings
    hc = allocation.hydro_ceiling_twh()
    h = al[al.source == "hydro"]
    assert (h.twh.values <= hc.reindex(h.region).values * (1 + 1e-9)).all()


def test_unconstrained_mode_is_labelled_not_compliant():
    sc = scenarios.project("central", overrides={"mix_2047": MIX_HYDRO_20})
    al, dg = allocation.allocate_scenario(sc, use_hydro_potential=False)
    assert dg.success.all() and set(dg.status) == {"solved"}
    assert al.value_type.str.contains("OFF").all()
    hc = allocation.hydro_ceiling_twh()
    h = al[(al.source == "hydro") & (al.fy_end_year == C.HEADLINE_FY_END)].set_index("region").twh
    assert (h > hc).any()                                          # proves it is NOT ceiling-compliant


def test_default_outputs_strictly_within_original_ceiling():
    dg = pd.read_csv(C.OUTPUTS / "allocation_solver_diagnostics.csv")
    assert set(dg.status) == {"solved"}
    assert (dg.max_hydro_ceiling_violation_twh.fillna(0) < 1e-6).all()
    al = pd.read_csv(C.OUTPUTS / "regional_allocation.csv")
    hc = allocation.hydro_ceiling_twh()
    h = al[al.source == "hydro"]
    assert (h.twh.values <= hc.reindex(h.region).values * (1 + 1e-9)).all()


def test_default_headline_preserved():
    sc = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
    r = sc[(sc.scenario == "central") & (sc.fy_end_year == C.HEADLINE_FY_END)].iloc[0]
    assert (round(r.domestic_generation_twh, 3), round(r.imported_generation_twh, 3), round(r.total_generation_twh, 3)) == \
        (5312.183, 7.804, 5319.987)


def test_only_expected_source_check_fails():
    chk = pd.read_csv(C.OUTPUTS / "validation_checks.csv")
    assert set(chk.loc[~chk.passed, "check_id"]) == {"PSAG-GR-2011"}


def test_feasible_high_hydro_just_below_ceiling_solves():
    sc = scenarios.project("central", overrides={"mix_2047": {**MIX_HYDRO_20, "hydro": 0.085, "coal": 0.335}})
    al, dg = allocation.allocate_scenario(sc[sc.fy_end_year == C.HEADLINE_FY_END])
    assert dg.iloc[0].status == "solved" and dg.iloc[0].max_hydro_ceiling_violation_twh < 1e-6
