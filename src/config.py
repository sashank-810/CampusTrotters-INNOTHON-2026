"""Central configuration: paths, region mappings, technology classes, scenario assumptions.

Every numerical ASSUMPTION used by the models lives in this file (or is a dashboard
control that defaults to a value here) so that it can be audited in one place.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ORIGINAL = DATA / "original" / "organizer_renewable_india_dataset"
ORIGINAL_CSV = ORIGINAL / "renewable_energy_dataset.csv"
ORIGINAL_SHA256 = ORIGINAL / "SHA256SUMS"
EXTERNAL = DATA / "external"
DERIVED = DATA / "derived"
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"

# Units: 1 MU = 1 GWh = 0.001 TWh ; 1 BU = 1 TWh
MU_PER_TWH = 1000.0

# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------
REGIONS = ["NR", "WR", "SR", "ER", "NER"]
REGION_NAMES = {
    "NR": "Northern", "WR": "Western", "SR": "Southern",
    "ER": "Eastern", "NER": "North-Eastern",
}
DGR_REGION_TO_CODE = {
    "Northern": "NR", "Western": "WR", "Southern": "SR",
    "Eastern": "ER", "North Eastern": "NER",
}

# Organizer state names -> CEA grid region (CEA convention used in all generation reports:
# Rajasthan in NR; Chhattisgarh & MP in WR; A&N and Sikkim in ER).
STATE_TO_CEA_REGION = {
    "Chandigarh": "NR", "Delhi": "NR", "Haryana": "NR", "Himachal Pradesh": "NR",
    "Jammu And Kashmir": "NR", "Punjab": "NR", "Rajasthan": "NR",
    "Uttar Pradesh": "NR", "Uttarakhand": "NR",
    "Chhattisgarh": "WR", "Goa": "WR", "Gujarat": "WR", "Madhya Pradesh": "WR",
    "Maharashtra": "WR",
    "Andhra Pradesh": "SR", "Karnataka": "SR", "Kerala": "SR", "Lakshadweep": "SR",
    "Puducherry": "SR", "Tamil Nadu": "SR", "Telangana": "SR",
    "Andaman And Nicobar Islands": "ER", "Bihar": "ER", "Jharkhand": "ER",
    "Odisha": "ER", "Sikkim": "ER", "West Bengal": "ER",
    "Arunachal Pradesh": "NER", "Assam": "NER", "Manipur": "NER", "Meghalaya": "NER",
    "Mizoram": "NER", "Nagaland": "NER", "Tripura": "NER",
}

# ---------------------------------------------------------------------------
# Technology classes used in the strategy (generation, not capacity)
# ---------------------------------------------------------------------------
SOURCES = ["coal", "gas", "nuclear", "hydro", "solar", "wind", "other_re"]
SOURCE_LABELS = {
    "coal": "Coal & lignite", "gas": "Gas + minor diesel", "nuclear": "Nuclear",
    "hydro": "Hydro (>25 MW)", "solar": "Solar", "wind": "Wind",
    "other_re": "Other RE (biomass, bagasse, small hydro, waste-to-energy)",
}
FOSSIL = ["coal", "gas"]
NON_FOSSIL = ["nuclear", "hydro", "solar", "wind", "other_re"]
VARIABLE_RE = ["solar", "wind"]
DISPATCHABLE = ["coal", "gas", "nuclear", "hydro", "other_re"]

# Mapping of CEA RE report categories to strategy classes
RE_SOURCE_MAP = {
    "Solar": "solar", "Wind": "wind", "Biomass": "other_re", "Bagasse": "other_re",
    "Small Hydro": "other_re", "Others": "other_re",
}

# ---------------------------------------------------------------------------
# Forecast set-up
# ---------------------------------------------------------------------------
BASE_FY_END = 2026          # FY2025-26 = last complete observed FY
HORIZON_END = 2048          # FY2047-48 (covers calendar 2047); headline reported for FY2046-47 too
HEADLINE_FY_END = 2047      # FY2046-47 ("FY47") - see mentor question on year definition
BACKTEST_HORIZONS = [1, 2, 3, 4, 5]
RANDOM_SEED = 20261117

# ---------------------------------------------------------------------------
# Scenario assumptions (ASSUMPTIONS - not data). Rationale in reports/methodology.md
# ---------------------------------------------------------------------------
SCENARIOS = {
    "conservative": {
        "label": "Conservative",
        # real GDP growth path: (start rate FY26, rate reached by FY2047)
        "gdp_growth_start": 0.060, "gdp_growth_end": 0.045,
        # generation-GDP elasticity: starts at historical estimate, moves linearly to this by FY2047
        "elasticity_end": 0.70,
        # extra electrification demand not captured by GDP elasticity (TWh in FY2047; linear ramp from FY2028)
        "addon_twh_2047": 0.0,
        # 2047 domestic generation shares (must sum to 1)
        "mix_2047": {"coal": 0.52, "gas": 0.02, "nuclear": 0.05, "hydro": 0.07,
                      "solar": 0.23, "wind": 0.09, "other_re": 0.02},
    },
    "central": {
        "label": "Central",
        "gdp_growth_start": 0.070, "gdp_growth_end": 0.050,
        "elasticity_end": 0.80,
        "addon_twh_2047": 0.0,
        "mix_2047": {"coal": 0.35, "gas": 0.02, "nuclear": 0.07, "hydro": 0.07,
                      "solar": 0.35, "wind": 0.12, "other_re": 0.02},
    },
    "accelerated": {
        "label": "Accelerated transition",
        "gdp_growth_start": 0.070, "gdp_growth_end": 0.050,
        "elasticity_end": 0.80,
        # Green-hydrogen electrolysis: 5 Mt/yr x 52.5 kWh/kg = 262.5 TWh (illustrative, see methodology)
        "addon_twh_2047": 262.5,
        "mix_2047": {"coal": 0.18, "gas": 0.02, "nuclear": 0.10, "hydro": 0.08,
                      "solar": 0.44, "wind": 0.15, "other_re": 0.03},
    },
}
ADDON_RAMP_START = 2028

# Cross-border imports (Bhutan hydro) deducted from the published CEA total to obtain
# domestic generation in projection years (ASSUMPTION: held at FY2025-26 observed DGR level).
BHUTAN_IMPORT_TWH_DEFAULT = 7.80403

# ---------------------------------------------------------------------------
# Regional allocation (illustrative preferences & data-derived feasibility rules)
# ---------------------------------------------------------------------------
# Weight on staying close to the observed (resource-revealed) regional geography of each source.
GEOGRAPHY_WEIGHTS = {"coal": 3.0, "gas": 3.0, "nuclear": 10.0, "hydro": 10.0,
                     "solar": 1.0, "wind": 2.0, "other_re": 3.0}
# Max multiple of a region's observed share of a source that it may hold in a projection year.
SHARE_CAP_MULTIPLIER = {"coal": 1.25, "gas": 1.5, "nuclear": 1.6, "hydro": 1.2,
                        "solar": 2.0, "wind": 1.5, "other_re": 1.5}
# Weight on generating close to the demand proxy (reduces inter-regional transfer need).
DEMAND_PROXIMITY_WEIGHT = 1.0
# Demand proxy = POP_WEIGHT * population share + (1-POP_WEIGHT) * nominal GSDP share (organizer data).
POP_WEIGHT = 0.5
# Regions with zero observed generation of a source FY2021-22..FY2024-25 are held at zero
# (wind in ER/NER; nuclear in ER/NER) - data-derived rule, flagged provisional.
