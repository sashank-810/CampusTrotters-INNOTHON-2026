"""National electricity-GENERATION forecasting models and rolling-origin backtesting.

Target (primary): CEA total generation incl. RE (utilities), Indian FY, TWh
                  (`data/derived/national_generation_fy.csv`, FY2009-10..FY2024-25, n=16).
Target (secondary, longer history for backtesting): Ember total generation via OWID,
                  calendar year, TWh, 2000-2025 (n=26).

Models (all fitted on log generation; small-sample appropriate, fully explainable):
  A  trend_cagr     - trailing 10-year CAGR extrapolation (baseline; no interval)
  B1 loglinear_ols  - OLS of log(G) on time; OLS prediction interval (assumes iid errors)
  B2 rw_drift       - random walk with drift on log(G); analytic t-interval incl. drift uncertainty
  B3 holt_damped    - damped-trend exponential smoothing on log(G); residual-bootstrap interval
  C  gdp_elasticity - (scenario engine; backtested conditionally in scenarios.py)
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import config as C

LEVELS = (0.80, 0.95)


@dataclass
class Forecast:
    model: str
    years: np.ndarray
    point: np.ndarray
    lo: dict          # level -> array
    hi: dict


def _horizon_years(last_year: int, h: int) -> np.ndarray:
    return np.arange(last_year + 1, last_year + h + 1)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def trend_cagr(years, y, h, window=10) -> Forecast:
    k = min(window, len(y) - 1)
    g = (y[-1] / y[-1 - k]) ** (1 / k) - 1
    pt = y[-1] * (1 + g) ** np.arange(1, h + 1)
    return Forecast("trend_cagr", _horizon_years(years[-1], h), pt, {}, {})


def loglinear_ols(years, y, h) -> Forecast:
    x = years - years.mean()
    ly = np.log(y)
    X = np.column_stack([np.ones_like(x, dtype=float), x])
    beta, *_ = np.linalg.lstsq(X, ly, rcond=None)
    resid = ly - X @ beta
    n, p = X.shape
    s2 = resid @ resid / (n - p)
    xf = _horizon_years(years[-1], h) - years.mean()
    Xf = np.column_stack([np.ones_like(xf, dtype=float), xf])
    mu = Xf @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(s2 * (1 + np.einsum("ij,jk,ik->i", Xf, XtX_inv, Xf)))
    lo, hi = {}, {}
    for L in LEVELS:
        t = stats.t.ppf(0.5 + L / 2, n - p)
        lo[L], hi[L] = np.exp(mu - t * se), np.exp(mu + t * se)
    return Forecast("loglinear_ols", _horizon_years(years[-1], h), np.exp(mu), lo, hi)


def rw_drift(years, y, h) -> Forecast:
    d = np.diff(np.log(y))
    n = len(d)
    mu, sd = d.mean(), d.std(ddof=1)
    hh = np.arange(1, h + 1)
    centre = np.log(y[-1]) + hh * mu
    se = sd * np.sqrt(hh + hh ** 2 / n)          # process noise + drift-estimation uncertainty
    lo, hi = {}, {}
    for L in LEVELS:
        t = stats.t.ppf(0.5 + L / 2, n - 1)
        lo[L], hi[L] = np.exp(centre - t * se), np.exp(centre + t * se)
    # point = median of log-normal predictive (exp of mean log); documented choice
    return Forecast("rw_drift", _horizon_years(years[-1], h), np.exp(centre), lo, hi)


def _holt_filter(ly, a, b, phi):
    lvl, tr = ly[0], ly[1] - ly[0]
    errs = []
    for t in range(1, len(ly)):
        f = lvl + phi * tr
        e = ly[t] - f
        errs.append(e)
        new_lvl = f + a * e
        tr = phi * tr + a * b * e
        lvl = new_lvl
    return lvl, tr, np.array(errs)


def holt_damped(years, y, h, n_sims=2000, seed=C.RANDOM_SEED) -> Forecast:
    ly = np.log(y)

    def sse(p):
        return float(np.sum(_holt_filter(ly, *p)[2][1:] ** 2))   # skip first (init) error

    res = optimize.minimize(sse, x0=[0.5, 0.2, 0.9], method="L-BFGS-B",
                            bounds=[(0.05, 0.99), (0.01, 0.99), (0.80, 0.98)])
    a, b, phi = res.x
    lvl, tr, errs = _holt_filter(ly, a, b, phi)
    hh = np.arange(1, h + 1)
    damp = np.cumsum(phi ** hh)
    centre = lvl + damp * tr
    # residual bootstrap simulation of the state-space recursion
    rng = np.random.default_rng(seed)
    pool = errs[1:] - errs[1:].mean()
    sims = np.empty((n_sims, h))
    for i in range(n_sims):
        L_, T_ = lvl, tr
        for j in range(h):
            e = rng.choice(pool)
            f = L_ + phi * T_
            v = f + e
            L_ = f + a * e
            T_ = phi * T_ + a * b * e
            sims[i, j] = v
    lo, hi = {}, {}
    for L in LEVELS:
        lo[L] = np.exp(np.quantile(sims, 0.5 - L / 2, axis=0))
        hi[L] = np.exp(np.quantile(sims, 0.5 + L / 2, axis=0))
    fc = Forecast("holt_damped", _horizon_years(years[-1], h), np.exp(centre), lo, hi)
    fc.params = {"alpha": a, "beta": b, "phi": phi}  # type: ignore[attr-defined]
    return fc


MODELS = {"trend_cagr": trend_cagr, "loglinear_ols": loglinear_ols,
          "rw_drift": rw_drift, "holt_damped": holt_damped}


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------
def rolling_origin(series: pd.Series, min_train: int, max_h: int = 5, models=MODELS) -> pd.DataFrame:
    """Expanding-window rolling-origin evaluation. At origin T only data <= T are used."""
    years = series.index.values.astype(int)
    vals = series.values.astype(float)
    rows = []
    for i in range(min_train - 1, len(years) - 1):
        tr_y, tr_v = years[: i + 1], vals[: i + 1]
        h = min(max_h, len(years) - 1 - i)
        for name, fn in models.items():
            fc = fn(tr_y, tr_v, h)
            for j in range(h):
                actual = vals[i + 1 + j]
                row = {"model": name, "origin": int(tr_y[-1]), "target_year": int(fc.years[j]), "h": j + 1,
                       "forecast": fc.point[j], "actual": actual, "error": fc.point[j] - actual}
                for L in LEVELS:
                    if L in fc.lo:
                        row[f"lo{int(L*100)}"] = fc.lo[L][j]
                        row[f"hi{int(L*100)}"] = fc.hi[L][j]
                        row[f"in{int(L*100)}"] = fc.lo[L][j] <= actual <= fc.hi[L][j]
                rows.append(row)
    return pd.DataFrame(rows)


def score(bt: pd.DataFrame, by=("model", "h")) -> pd.DataFrame:
    rows = []
    for key, g in bt.groupby(list(by)):
        key = key if isinstance(key, tuple) else (key,)
        e = g["error"]
        out = dict(zip(by, key))
        out.update({"n": len(g), "MAE_TWh": e.abs().mean(), "RMSE_TWh": np.sqrt((e ** 2).mean()),
                    "WAPE_pct": 100 * e.abs().sum() / g["actual"].abs().sum(),
                    "MAPE_pct": 100 * (e.abs() / g["actual"]).mean(), "bias_TWh": e.mean()})
        for L in (80, 95):
            col = f"in{L}"
            has = col in g and g[col].notna().any()
            out[f"coverage{L}_pct"] = 100 * g[col].dropna().astype(float).mean() if has else np.nan
        rows.append(out)
    return pd.DataFrame(rows)


def load_targets() -> tuple[pd.Series, pd.Series]:
    nat = pd.read_csv(C.DERIVED / "national_generation_fy.csv")
    cea = nat.set_index("fy_end_year")["total_twh"].astype(float)
    emb = pd.read_csv(C.DERIVED / "ember_cy.csv")
    emb = emb[emb.year >= 2000].set_index("year")["electricity_generation"].astype(float)
    return cea, emb


def final_forecasts(series: pd.Series, horizon_end: int = C.HORIZON_END) -> pd.DataFrame:
    years = series.index.values.astype(int)
    vals = series.values.astype(float)
    h = horizon_end - years[-1]
    rows = []
    params = {}
    for name, fn in MODELS.items():
        fc = fn(years, vals, h)
        if hasattr(fc, "params"):
            params[name] = fc.params
        for j, yr in enumerate(fc.years):
            r = {"model": name, "fy_end_year": int(yr), "point_twh": fc.point[j]}
            for L in LEVELS:
                r[f"lo{int(L*100)}"] = fc.lo.get(L, [np.nan] * h)[j]
                r[f"hi{int(L*100)}"] = fc.hi.get(L, [np.nan] * h)[j]
            rows.append(r)
    out = pd.DataFrame(rows)
    out["value_type"] = "model_generated"
    h = out["fy_end_year"] - years[-1]
    out["interval_label"] = np.where(
        out["lo80"].isna(), "no interval (baseline)",
        np.where(h <= 5, "model-based interval; rolling-origin backtests cover horizons 1-5 (empirical coverage below nominal on CEA series)",
                 "model-based illustrative interval: long-horizon extrapolation, NOT empirically calibrated at this horizon"))
    out.attrs["params"] = params
    return out


def main() -> dict:
    cea, emb = load_targets()
    bt_cea = rolling_origin(cea, min_train=7)
    bt_emb = rolling_origin(emb, min_train=10)
    bt_cea.to_csv(C.OUTPUTS / "backtest_cea_fy_detail.csv", index=False)
    bt_emb.to_csv(C.OUTPUTS / "backtest_ember_cy_detail.csv", index=False)
    s_cea_h = score(bt_cea)
    s_emb_h = score(bt_emb)
    s_cea = score(bt_cea, by=("model",))
    s_emb = score(bt_emb, by=("model",))
    s_cea_h.to_csv(C.OUTPUTS / "backtest_cea_fy_by_horizon.csv", index=False)
    s_emb_h.to_csv(C.OUTPUTS / "backtest_ember_cy_by_horizon.csv", index=False)
    s_cea.to_csv(C.OUTPUTS / "backtest_cea_fy_summary.csv", index=False)
    s_emb.to_csv(C.OUTPUTS / "backtest_ember_cy_summary.csv", index=False)

    # Model selection rule (pre-declared): lowest mean WAPE across the two backtests among
    # models that provide an interval; ties -> simpler model.
    interval_models = ["loglinear_ols", "rw_drift", "holt_damped"]
    comb = (s_cea.set_index("model")["WAPE_pct"] + s_emb.set_index("model")["WAPE_pct"]) / 2
    selected = comb.loc[interval_models].idxmin()
    fc = final_forecasts(cea)
    fc["selected_statistical_model"] = fc["model"] == selected
    fc.to_csv(C.OUTPUTS / "national_forecast_statistical.csv", index=False)
    meta = {"selected_model": selected, "selection_rule": "min mean WAPE over CEA-FY and Ember-CY rolling-origin backtests among interval models",
            "mean_wape_pct": comb.round(3).to_dict(), "holt_params_full_sample": fc.attrs.get("params", {}),
            "cea_obs": len(cea), "ember_obs": len(emb)}
    (C.OUTPUTS / "forecast_meta.json").write_text(json.dumps(meta, indent=2, default=float))
    print(f"[forecast] backtests done; selected statistical model = {selected}")
    print(s_cea[["model", "n", "MAE_TWh", "RMSE_TWh", "WAPE_pct", "coverage80_pct", "coverage95_pct"]].round(2).to_string())
    return meta


if __name__ == "__main__":
    main()
