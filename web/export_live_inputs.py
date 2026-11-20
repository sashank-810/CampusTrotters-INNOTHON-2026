"""Export immutable model inputs for the browser implementation.

The organizer CSV is read only; this writes a derived JSON copy with source
labels, observed generation references, and assumption defaults.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import allocation as A, config as C, demography as DM, scenarios


def records(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    return df.astype(object).where(pd.notna(df), None).to_dict("records")


def export() -> dict:
    rho, base = A.reference_shares()
    lgbr = A.demand_shares("lgbr_constant")
    proxy = pd.read_csv(C.DERIVED / "demand_proxy_region_year.csv")
    proxy = proxy[proxy.year == 2024].set_index("region").reindex(C.REGIONS)
    data = {
        "version": "v1.4 browser model, sourced from v1.2 Python pipeline",
        "regions": C.REGIONS, "sources": C.SOURCES,
        "base_fy_end": C.BASE_FY_END, "horizon_end": C.HORIZON_END,
        "headline_fy_end": C.HEADLINE_FY_END,
        "addon_ramp_start": C.ADDON_RAMP_START,
        "bhutan_import_twh": C.BHUTAN_IMPORT_TWH_DEFAULT,
        "base": scenarios.base_year_values(),
        "eps0": scenarios.elasticity_estimates()["eps0_trailing_ratio"],
        "scenarios": C.SCENARIOS,
        "weights": C.GEOGRAPHY_WEIGHTS, "caps": C.SHARE_CAP_MULTIPLIER,
        "rho": rho.to_dict(orient="index"),
        "observed_base": base.to_dict(orient="index"),
        "hydro_ceiling": A.hydro_ceiling_twh().to_dict(),
        "demand_lgbr": lgbr.to_dict(),
        "demand_proxy_2024": proxy[["pop_share", "gsdp_share"]].to_dict(orient="index"),
        "gsdp_slopes": A.gsdp_share_slopes().to_dict(),
        "pc_slopes": DM.organizer_per_capita_gsdp_slopes().to_dict(),
        "national_demography": records(C.OUTPUTS / "demography_national_path.csv"),
        "regional_demography": records(C.OUTPUTS / "demography_regional_paths.csv"),
        "history": records(C.DERIVED / "national_generation_fy.csv"),
        "statistical": records(C.OUTPUTS / "national_forecast_statistical.csv"),
        "validation": records(C.OUTPUTS / "validation_checks.csv"),
    }
    target = ROOT / "web" / "dist" / "model_inputs.json"
    target.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = export()
    print(f"Exported {len(d['national_demography'])} national and "
          f"{len(d['regional_demography'])} regional demographic rows.")
