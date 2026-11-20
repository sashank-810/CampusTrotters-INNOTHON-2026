"""Minimal headless stand-in for `streamlit`, used ONLY by tests/test_dashboard_smoke.py to execute
the dashboard script top-to-bottom where the real package is unavailable. Widgets return their
default values; charts/tables record what they were given so the test can inspect them."""
import pandas as pd

CALLS = []
OVERRIDES = {}   # widget key -> value, lets tests drive non-default settings


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, name):
        return getattr(_module, name)


def _record(kind):
    def f(*args, **kwargs):
        CALLS.append((kind, args, kwargs))
        if kind.endswith("chart") or kind == "dataframe":
            data = args[0] if args else kwargs.get("data")
            assert isinstance(data, pd.DataFrame), f"{kind} expects a DataFrame"
            assert len(data) > 0, f"{kind} got empty data"
        return None
    return f


def cache_data(func=None, **kw):
    return func if func else (lambda f: f)


def set_page_config(**kw): pass
def radio(label, options, index=0, **kw): return OVERRIDES.get(kw.get("key"), list(options)[index])
def selectbox(label, options, index=0, **kw): return OVERRIDES.get(kw.get("key"), list(options)[index])
def slider(label, min_value=None, max_value=None, value=None, step=None, **kw): return OVERRIDES.get(kw.get("key"), value)
def checkbox(label, value=False, **kw): return OVERRIDES.get(kw.get("key"), value)
def columns(n, **kw): return [_Ctx() for _ in range(n if isinstance(n, int) else len(n))]
def tabs(names): return [_Ctx() for _ in names]
def expander(*a, **k): return _Ctx()


for _k in ["line_chart", "bar_chart", "area_chart", "dataframe", "metric", "title", "caption", "header",
           "subheader", "write", "markdown", "warning", "error", "info", "download_button"]:
    globals()[_k] = _record(_k)

import sys as _sys  # noqa: E402
_module = _sys.modules[__name__]
sidebar = _Ctx()
