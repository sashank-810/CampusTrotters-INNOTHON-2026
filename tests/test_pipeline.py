"""Automated tests: data integrity, transcription arithmetic, leakage-free backtesting,
model sanity, scenario accounting and allocation conservation.

Run:  python -m pytest -q
(`run_all.py` must have been executed first so outputs/ exists; the session fixture runs it.)
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import pytest

from src import allocation, config as C, forecast, scenarios
from src.integrity import verify_originals


@pytest.fixture(scope="session", autouse=True)
def pipeline():
    import run_all
    run_all.main()


# --- integrity -----------------------------------------------------------------
def test_original_hash_unchanged():
    res = verify_originals()
    assert all(v["ok"] for v in res.values())
    digest = hashlib.sha256(C.ORIGINAL_CSV.read_bytes()).hexdigest()
    assert digest == "f8f98adfc00457f3cd6033193722503fc481250d19ec37e0c692b35450d7bd4f"


def test_original_shape_and_no_capacity_in_targets():
    df = pd.read_csv(C.ORIGINAL_CSV)
    assert df.shape == (635, 10)
    nat = pd.read_csv(C.DERIVED / "national_generation_fy.csv")
    assert not any("Installed" in c or "capacity" in c.lower() for c in nat.columns)


def test_every_external_file_in_manifest():
    man = pd.read_csv(C.EXTERNAL / "SOURCE_MANIFEST.csv")
    listed = " ".join(man["files"].astype(str))
    for f in C.EXTERNAL.glob("*.csv"):
        if f.name == "SOURCE_MANIFEST.csv":
            continue
        assert f.name in listed, f"{f.name} missing from manifest"


# --- transcription validation ----------------------------------------------------
def test_validation_checks_only_known_source_inconsistency():
    chk = pd.read_csv(C.OUTPUTS / "validation_checks.csv")
    failed = set(chk.loc[~chk.passed, "check_id"])
    assert failed <= {"PSAG-GR-2011"}, failed       # documented source-internal inconsistency
    arith = chk[chk.kind == "arithmetic"]
    assert len(arith) > 100 and arith.passed.all()


def test_regional_history_reconciles_with_national():
    reg = pd.read_csv(C.DERIVED / "regional_generation_fy.csv")
    nat = pd.read_csv(C.DERIVED / "national_generation_fy.csv").set_index("fy_end_year")
    for y, g in reg.groupby("fy_end_year"):
        rel = (g.twh.sum() + nat.loc[y, "bhutan_import_twh"]) / nat.loc[y, "total_twh"] - 1
        assert abs(rel) < 0.005


# --- forecasting -------------------------------------------------------------------
def test_backtest_has_no_leakage():
    bt = pd.read_csv(C.OUTPUTS / "backtest_cea_fy_detail.csv")
    assert (bt.target_year > bt.origin).all()
    assert (bt.target_year - bt.origin == bt.h).all()


def test_models_reproduce_known_series():
    years = np.arange(2000, 2020)
    y = 100 * 1.05 ** (years - 2000)
    for name, fn in forecast.MODELS.items():
        fc = fn(years, y, 3)
        assert np.allclose(fc.point, 100 * 1.05 ** np.arange(20, 23), rtol=0.02), name


def test_prediction_intervals_ordered():
    fc = pd.read_csv(C.OUTPUTS / "national_forecast_statistical.csv")
    d = fc[fc.model != "trend_cagr"]
    assert (d.lo95 <= d.lo80).all() and (d.lo80 <= d.point_twh).all()
    assert (d.point_twh <= d.hi80).all() and (d.hi80 <= d.hi95).all()


def test_metrics_computed_not_hardcoded():
    bt = pd.read_csv(C.OUTPUTS / "backtest_cea_fy_detail.csv")
    s = pd.read_csv(C.OUTPUTS / "backtest_cea_fy_summary.csv").set_index("model")
    for m, g in bt.groupby("model"):
        wape = 100 * g.error.abs().sum() / g.actual.sum()
        assert np.isclose(wape, s.loc[m, "WAPE_pct"])


# --- scenarios -----------------------------------------------------------------------
def test_scenario_shares_sum_to_one_and_nonnegative():
    sc = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
    shares = sc[[f"share_{k}" for k in C.SOURCES]]
    assert np.allclose(shares.sum(axis=1), 1.0)
    assert (shares >= 0).all().all()
    twh = sc[[f"{k}_twh" for k in C.SOURCES]].sum(axis=1)
    assert np.allclose(twh, sc.domestic_generation_twh)


def test_scenario_ordering_and_sensitivity():
    c = scenarios.project("central")
    hi = scenarios.project("central", overrides={"gdp_growth_end": 0.06})
    assert (hi.total_generation_twh.values >= c.total_generation_twh.values - 1e-9).all()
    sc = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
    y = sc[sc.fy_end_year == C.HEADLINE_FY_END].set_index("scenario").total_generation_twh
    assert y["conservative"] < y["central"] <= y["accelerated"]


# --- allocation ----------------------------------------------------------------------
def test_allocation_conserves_energy():
    chk = pd.read_csv(C.OUTPUTS / "allocation_conservation_checks.csv")
    assert chk.passed.all()
    al = pd.read_csv(C.OUTPUTS / "regional_allocation.csv")
    assert (al.twh >= 0).all()


def test_zero_resource_rule_respected():
    al = pd.read_csv(C.OUTPUTS / "regional_allocation.csv")
    z = al[al.region.isin(["ER", "NER"]) & al.source.isin(["wind", "nuclear"])]
    assert np.allclose(z.twh, 0.0)


def test_allocation_with_extreme_lambda_still_conserves():
    sc = scenarios.project("accelerated").head(3)
    al, diag = allocation.allocate_scenario(sc, lam=1000.0, demand_source="organizer_proxy")
    for (s, y), g in al.groupby(["scenario", "fy_end_year"]):
        row = sc[sc.fy_end_year == y].iloc[0]
        assert np.isclose(g.twh.sum(), row.domestic_generation_twh)
    assert diag.success.all()
