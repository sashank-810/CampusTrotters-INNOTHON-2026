"""STUB-based smoke test (NOT a real Streamlit run): executes app/streamlit_app.py with the
headless stand-in `tests/stubs/streamlit.py`, verifying that the script's data logic runs end to end
and that every chart/table receives non-empty data. Real-runtime testing is in
tests/test_dashboard_real.py (Streamlit AppTest), which runs wherever Streamlit is installed."""
import importlib
import runpy
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_runs_headless(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tests" / "stubs"))
    sys.modules.pop("streamlit", None)
    stub = importlib.import_module("streamlit")
    assert "stubs" in stub.__file__
    stub.CALLS.clear()
    runpy.run_path(str(ROOT / "app" / "streamlit_app.py"), run_name="__main__")
    kinds = [c[0] for c in stub.CALLS]
    assert kinds.count("line_chart") >= 2 and kinds.count("bar_chart") >= 4 and kinds.count("dataframe") >= 8
    assert kinds.count("metric") == 4
    # national chart contains observed + scenario + statistical series
    nat_chart = next(c for c in stub.CALLS if c[0] == "line_chart")[1][0]
    assert any(col.startswith("Observed - CEA domestic") for col in nat_chart.columns)
    assert any(col.startswith("Scenario Central - domestic") for col in nat_chart.columns)
    sys.modules.pop("streamlit", None)


def _run_stub(monkeypatch, overrides):
    monkeypatch.syspath_prepend(str(ROOT / "tests" / "stubs"))
    sys.modules.pop("streamlit", None)
    stub = importlib.import_module("streamlit")
    stub.CALLS.clear()
    stub.OVERRIDES.clear()
    stub.OVERRIDES.update(overrides)
    try:
        runpy.run_path(str(ROOT / "app" / "streamlit_app.py"), run_name="__main__")
        return list(stub.CALLS)
    finally:
        stub.OVERRIDES.clear()
        sys.modules.pop("streamlit", None)


def test_stub_hydro_20pct_reports_infeasible_without_crash(monkeypatch):
    calls = _run_stub(monkeypatch, {"mix_hydro": 20})
    errs = [c[1][0] for c in calls if c[0] == "error"]
    assert any("INFEASIBLE under the indicative CEA hydro-potential ceiling" in e for e in errs)
    assert any("ALLOC" in str(c) or "UNCONSTRAINED" in str(c) for c in calls)


def test_stub_requirement_term_off_runs(monkeypatch):
    calls = _run_stub(monkeypatch, {"use_req": False, "hydro_pot": False})
    assert any(c[0] == "metric" for c in calls)
