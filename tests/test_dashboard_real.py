"""REAL Streamlit runtime test (streamlit.testing.v1.AppTest) - no stub.

Skipped automatically where Streamlit is not installed (as in the build environment of v1.1).
On a machine with `pip install -r requirements.txt` this executes app/streamlit_app.py in the real
Streamlit script runner and exercises every scenario, demographic variant, demand basis, geography
mode, the hydro toggle, the >100% mix renormalisation path and the region/year selectors.
"""
import pytest
from pathlib import Path

st = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
TIMEOUT = 300


def _fresh():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def test_default_render_has_headline_metrics():
    at = _fresh()
    labels = [m.label for m in at.metric]
    assert len(labels) == 4 and any("domestic generation" in l for l in labels)


@pytest.mark.parametrize("scenario", ["conservative", "central", "accelerated"])
def test_each_scenario(scenario):
    at = _fresh()
    at.radio(key="scenario").set_value(scenario).run()
    _ok(at)


@pytest.mark.parametrize("variant", ["central", "low_pop", "high_pop", "slow_urban", "fast_urban"])
def test_each_demographic_variant(variant):
    at = _fresh()
    at.selectbox(key="demo_var").set_value(variant).run()
    _ok(at)


@pytest.mark.parametrize("basis", ["lgbr_plus_demographic_drift", "lgbr_plus_gsdp_drift", "lgbr_constant", "organizer_proxy"])
def test_each_demand_basis(basis):
    at = _fresh()
    at.selectbox(key="dsrc").set_value(basis).run()
    _ok(at)


def test_sliders_geography_hydro_and_region():
    at = _fresh()
    at.slider(key="g0").set_value(5.0).run(); _ok(at)
    at.slider(key="e1").set_value(0.6).run(); _ok(at)
    at.slider(key="beta").set_value(1.5).run(); _ok(at)
    at.slider(key="lam").set_value(10.0).run(); _ok(at)
    at.selectbox(key="geo").set_value("relaxed").run(); _ok(at)
    at.checkbox(key="hydro_pot").uncheck().run(); _ok(at)
    at.selectbox(key="region").set_value("NER").run(); _ok(at)
    at.slider(key="year").set_value(2035).run(); _ok(at)


def test_mix_over_100_shows_renormalisation_notice():
    at = _fresh()
    at.slider(key="mix_solar").set_value(70).run()
    at.slider(key="mix_wind").set_value(40).run()
    _ok(at)
    assert any("RENORMALISED" in e.value for e in at.error)


def test_hydro_20pct_shows_infeasible_not_compliant():
    at = _fresh()
    at.slider(key="mix_hydro").set_value(20).run()
    _ok(at)
    assert any("INFEASIBLE" in e.value for e in at.error)


def test_exploratory_toggles_off():
    at = _fresh()
    at.checkbox(key="use_req").uncheck().run(); _ok(at)
    at.checkbox(key="hydro_pot").uncheck().run(); _ok(at)
