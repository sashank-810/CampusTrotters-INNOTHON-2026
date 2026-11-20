"""Extract India rows from the Our World in Data energy dataset (Ember-based generation).

The full OWID file (~9 MB) is not shipped; this script documents how the shipped
extract `data/external/owid_ember_india_generation_cy.csv` was produced.

Usage:
    python -m src.extract_owid /path/to/owid-energy-data.csv
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "owid_ember_india_generation_cy.csv"

COLUMNS = [
    "year", "electricity_generation", "electricity_demand", "net_elec_imports",
    "coal_electricity", "gas_electricity", "oil_electricity", "hydro_electricity",
    "nuclear_electricity", "solar_electricity", "wind_electricity",
    "biofuel_electricity", "other_renewable_exc_biofuel_electricity",
    "population", "gdp",
]


def main(src: str) -> None:
    src_path = Path(src)
    digest = hashlib.sha256(src_path.read_bytes()).hexdigest()
    df = pd.read_csv(src_path)
    india = df.loc[df["country"] == "India", [c for c in COLUMNS if c in df.columns]]
    india = india[india["year"] >= 1990].copy()
    india.insert(0, "country", "India")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    india.to_csv(OUT, index=False)
    (OUT.with_suffix(".provenance.txt")).write_text(
        "Extracted from owid-energy-data.csv\n"
        f"source_sha256={digest}\n"
        "owid_repo_commit=f8de88a4f6f9cab44f1cf606047cbd6c4414042c\n"
        "units: generation/demand/imports in TWh (calendar year); gdp in 2011 international $ (Maddison), population persons\n"
        "generation source per OWID codebook: Ember Yearly Electricity Data (2026); Energy Institute Statistical Review (2025)\n"
    )
    print(f"wrote {OUT} rows={len(india)} sha256(source)={digest}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "owid-energy-data.csv")
