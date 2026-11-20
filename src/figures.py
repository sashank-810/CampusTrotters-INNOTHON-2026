"""Static figures (PNG) for the report and presentation. Generated only from outputs/ files."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config as C  # noqa: E402

# Validated categorical palette (fixed order; colour follows entity, never rank)
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SOURCE_COLORS = dict(zip(C.SOURCES, SLOTS))
SCEN_COLORS = {"conservative": SLOTS[0], "central": SLOTS[1], "accelerated": SLOTS[2]}
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
FIG = C.ROOT / "reports" / "figures"


def _style(ax, title, ylabel):
    ax.set_facecolor(SURF)
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold")
    ax.set_ylabel(ylabel, color=INK2)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK2)


def national(out):
    nat = pd.read_csv(C.DERIVED / "national_generation_fy.csv")
    emb = pd.read_csv(C.DERIVED / "ember_cy.csv")
    fc = pd.read_csv(C.OUTPUTS / "national_forecast_statistical.csv")
    sc = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
    rw = fc[fc.model == "rw_drift"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), facecolor=SURF)
    ax = axes[0]
    nudges = {"conservative": -10, "central": -4, "accelerated": 8}
    for s, col in SCEN_COLORS.items():
        d = sc[sc.scenario == s]
        x = np.r_[C.BASE_FY_END, d.fy_end_year]
        y = np.r_[nat.set_index("fy_end_year").loc[C.BASE_FY_END, "domestic_twh"], d.domestic_generation_twh]
        ax.plot(x, y, color=col, lw=2.2, label=f"Scenario: {C.SCENARIOS[s]['label']}")
        yh = d.set_index("fy_end_year").loc[C.HEADLINE_FY_END, "domestic_generation_twh"]
        ax.plot([C.HEADLINE_FY_END], [yh], marker="o", ms=5, color=col)
        ax.annotate(f"{yh:,.0f} (FY47)", (C.HEADLINE_FY_END, yh), xytext=(14, nudges[s]), textcoords="offset points",
                    color=INK2, fontsize=8, va="center")
    ax.plot(nat.fy_end_year, nat.total_twh, color=MUTED, lw=1.4, label="Observed: CEA total incl. Bhutan imports")
    dm = nat.dropna(subset=["domestic_twh"])
    ax.plot(dm.fy_end_year, dm.domestic_twh, color=INK, lw=0, marker="o", ms=4,
            label="Observed: CEA domestic (years with import data)")
    ax.axvline(C.BASE_FY_END + 0.5, color=MUTED, lw=0.8, ls=":")
    _style(ax, "A. Scenarios - DOMESTIC generation (excl. Bhutan imports)", "TWh per year")
    ax.set_xlabel("FY end year (2047 = FY2046-47)", color=INK2)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.set_xlim(2009, 2052)
    ax = axes[1]
    ax.fill_between(rw.fy_end_year, rw.lo95, rw.hi95, color="#e2e1dc", lw=0, label="Model-based 95% interval*")
    ax.fill_between(rw.fy_end_year, rw.lo80, rw.hi80, color="#c9c8c1", lw=0, label="Model-based 80% interval*")
    ax.plot(rw.fy_end_year, rw.point_twh, color=INK2, lw=1.6, ls="--", label="RW-drift median")
    ax.plot(nat.fy_end_year, nat.total_twh, color=INK, lw=2.4, marker="o", ms=3.5, label="Observed: CEA total (incl. imports)")
    ax.axvspan(C.BASE_FY_END + 5.5, C.HORIZON_END + 0.5, color="#f3f2ee", lw=0, zorder=0)
    ax.text(C.BASE_FY_END + 6, 600, "beyond backtested horizon (>5 yr)", fontsize=8, color=INK2)
    _style(ax, "B. Statistical model - CEA total basis", "TWh per year")
    ax.set_xlabel("FY end year", color=INK2)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.set_ylim(0, None)
    fig.text(0.01, 0.005, "*Intervals: rolling-origin backtests cover 1-5 yr horizons only (CEA 95% coverage 82.5%); longer horizons are "
             "illustrative extrapolations, not empirically calibrated. Scenario ranges are assumption-driven and separate.",
             fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out / "fig1_national_forecast.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURF)
    e = emb[emb.year >= 2000]
    ax.plot(e.year, e.electricity_generation, color=MUTED, lw=1.8, marker="o", ms=3, label="Ember total generation (calendar year, incl. captive)")
    _style(ax, "Ember generation on its own calendar-year axis", "TWh")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig1b_ember_calendar_year.png", dpi=160)
    plt.close(fig)


def demography_fig(out):
    d = pd.read_csv(C.OUTPUTS / "demography_sensitivity.csv")
    d = d[d.scenario == "central"].copy()
    d["lab"] = d.demographic_variant + np.where(d.demographic_variant.isin(["slow_urban", "fast_urban"]),
                                               " (beta=" + (d.urban_semi_elasticity_per_pp * 100).round(1).astype(str) + "%/pp)", "")
    d = d.sort_values("change_vs_central_twh")
    fig, ax = plt.subplots(figsize=(9, 4.4), facecolor=SURF)
    cols = [SLOTS[0] if v < 0 else SLOTS[1] for v in d.change_vs_central_twh]
    ax.barh(d.lab, d.change_vs_central_twh, color=cols, edgecolor=SURF)
    for i, v in enumerate(d.change_vs_central_twh):
        ax.text(v + (8 if v >= 0 else -8), i, f"{v:+,.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=8, color=INK2)
    ax.axvline(0, color=MUTED, lw=1)
    _style(ax, "Demographic sensitivity, central scenario FY2046-47", "")
    ax.set_xlabel("Change in domestic generation vs central demographic path (TWh)", color=INK2)
    ax.set_xlim(d.change_vs_central_twh.min() - 120, d.change_vs_central_twh.max() + 120)
    fig.tight_layout()
    fig.savefig(out / "fig6_demography_sensitivity.png", dpi=160)
    plt.close(fig)


def hydro_fig(out):
    h = pd.read_csv(C.OUTPUTS / "hydro_potential_check.csv")
    h = h[h.scenario == "central"]
    v10 = h[h.case.str.startswith("v1.0")].set_index("region").reindex(C.REGIONS)
    v11 = h[h.case.str.startswith("v1.1")].set_index("region").reindex(C.REGIONS)
    x = np.arange(len(C.REGIONS))
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=SURF)
    ax.bar(x - 0.2, v10.hydro_twh, 0.38, color=SLOTS[1], edgecolor=SURF, label="v1.0 allocation (no ceiling)")
    ax.bar(x + 0.2, v11.hydro_twh, 0.38, color=SLOTS[0], edgecolor=SURF, label="v1.1 allocation (with ceiling)")
    ax.scatter(x, v11.cea_potential_ceiling_twh, marker="_", s=900, color=INK, lw=2.5, label="Indicative CEA-potential ceiling", zorder=3)
    ax.set_xticks(x, [C.REGION_NAMES[r] for r in C.REGIONS])
    _style(ax, "Hydro, central FY2046-47: allocation vs CEA-potential energy ceiling", "TWh")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig7_hydro_potential_check.png", dpi=160)
    plt.close(fig)


def backtest(out):
    a = pd.read_csv(C.OUTPUTS / "backtest_cea_fy_by_horizon.csv")
    b = pd.read_csv(C.OUTPUTS / "backtest_ember_cy_by_horizon.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=SURF, sharey=True)
    names = {"trend_cagr": "A trend CAGR", "loglinear_ols": "B1 log-linear OLS", "rw_drift": "B2 RW + drift",
             "holt_damped": "B3 damped Holt"}
    for ax, df, t in [(axes[0], a, "CEA FY total (n=17)"), (axes[1], b, "Ember CY total (n=26)")]:
        for i, m in enumerate(names):
            d = df[df.model == m]
            ax.plot(d.h, d.WAPE_pct, color=SLOTS[i], lw=2, marker="o", ms=5, label=names[m])
        _style(ax, f"Rolling-origin WAPE - {t}", "WAPE (%)")
        ax.set_xlabel("Forecast horizon (years)", color=INK2)
        ax.set_xticks([1, 2, 3, 4, 5])
    axes[0].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig2_backtest_wape.png", dpi=160)
    plt.close(fig)


def mix(out):
    m = pd.read_csv(C.DERIVED / "national_mix_fy.csv")
    sc = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
    base = m[m.fy_end_year == C.BASE_FY_END].set_index("source")["share"]
    cols = {"FY2025-26\n(observed*)": base}
    for s in C.SCENARIOS:
        r = sc[(sc.scenario == s) & (sc.fy_end_year == C.HEADLINE_FY_END)].iloc[0]
        cols[f"FY2046-47\n{C.SCENARIOS[s]['label']}"] = pd.Series({k: r[f"share_{k}"] for k in C.SOURCES})
    df = pd.DataFrame(cols).reindex(C.SOURCES).fillna(0) * 100
    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=SURF)
    bottom = np.zeros(df.shape[1])
    for k in C.SOURCES:
        ax.bar(df.columns, df.loc[k], bottom=bottom, color=SOURCE_COLORS[k], edgecolor=SURF, lw=2, width=0.6,
               label=C.SOURCE_LABELS[k])
        for j, v in enumerate(df.loc[k]):
            if v >= 4:
                ax.text(j, bottom[j] + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=8, color="white")
        bottom += df.loc[k].values
    _style(ax, "National generation mix (shares of domestic generation)", "% of TWh generated")
    ax.legend(fontsize=7.5, frameon=False, bbox_to_anchor=(1.0, 1), loc="upper left")
    ax.text(0, -0.18, "*FY2025-26 coal+lignite = CEA fuel-wise actuals; gas = thermal minus coal/lignite. FY2046-47 shares are scenario ASSUMPTIONS.",
            transform=ax.transAxes, fontsize=7.5, color=INK2)
    fig.tight_layout()
    fig.savefig(out / "fig3_national_mix.png", dpi=160)
    plt.close(fig)


def regional(out):
    reg = pd.read_csv(C.DERIVED / "regional_generation_fy.csv")
    al = pd.read_csv(C.OUTPUTS / "regional_allocation.csv")
    obs = reg[reg.fy_end_year == C.BASE_FY_END].copy()
    th = obs[obs.source == "thermal"].set_index("region")["twh"]
    obs_p = obs[obs.source != "thermal"].pivot(index="region", columns="source", values="twh")
    obs_p["coal"] = th          # observed thermal shown in coal colour slot, labelled
    obs_p["gas"] = 0.0
    fut = al[(al.scenario == "central") & (al.fy_end_year == C.HEADLINE_FY_END)].pivot(index="region", columns="source", values="twh")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), facecolor=SURF, sharey=True)
    for ax, df, t in [(axes[0], obs_p, "FY2025-26 observed (thermal = coal+gas+diesel)"),
                      (axes[1], fut, "FY2046-47 central (illustrative allocation)")]:
        df = df.reindex(C.REGIONS)[C.SOURCES].fillna(0)
        bottom = np.zeros(len(df))
        for k in C.SOURCES:
            ax.bar([C.REGION_NAMES[r] for r in df.index], df[k], bottom=bottom, color=SOURCE_COLORS[k],
                   edgecolor=SURF, lw=1.5, width=0.62, label=C.SOURCE_LABELS[k])
            bottom += df[k].values
        for j, v in enumerate(bottom):
            ax.text(j, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8, color=INK2)
        _style(ax, t, "TWh generated in region")
        ax.tick_params(axis="x", labelsize=8)
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8, frameon=False, loc="lower center", ncol=4)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(out / "fig4_regional_mix.png", dpi=160)
    plt.close(fig)


def transfers(out):
    s = pd.read_csv(C.OUTPUTS / "regional_summary.csv")
    d = s[s.fy_end_year == C.HEADLINE_FY_END]
    fig, ax = plt.subplots(figsize=(9, 4), facecolor=SURF)
    w = 0.26
    x = np.arange(len(C.REGIONS))
    for i, sc in enumerate(C.SCENARIOS):
        v = d[d.scenario == sc].set_index("region").reindex(C.REGIONS)["indicative_net_export_twh"]
        ax.bar(x + (i - 1) * w, v, width=w, color=SCEN_COLORS[sc], edgecolor=SURF, lw=1, label=C.SCENARIOS[sc]["label"])
    ax.axhline(0, color=MUTED, lw=1)
    ax.set_xticks(x, [C.REGION_NAMES[r] for r in C.REGIONS])
    _style(ax, "Indicative net inter-regional transfer, FY2046-47 (illustrative allocation)",
           "TWh (+ exporter / - importer)")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig5_transfers.png", dpi=160)
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (national, backtest, mix, regional, transfers, demography_fig, hydro_fig):
        f(FIG)
    print(f"[figures] written to {FIG}")


if __name__ == "__main__":
    main()
