"""Quality gates (v1.2). Run after `python run_all.py`:
    python quality_gates.py

Reports TWO separate verdicts:
  core_model_gates_passed     - data integrity, tests, conservation, strict hydro ceiling, cross-artefact agreement
  dashboard_real_runtime      - "VERIFIED" only if Streamlit is installed AND tests/test_dashboard_real.py ran and
                                passed in THIS invocation; otherwise "UNVERIFIED". The core verdict never implies it.
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pandas as pd

from src import allocation, config as C, demography as DM, scenarios
from src.integrity import sha256, verify_originals

EXPECTED_ORGANIZER_SHA256 = "f8f98adfc00457f3cd6033193722503fc481250d19ec37e0c692b35450d7bd4f"
EXPECTED_FAILED_CHECKS = {"PSAG-GR-2011"}

r: dict = {}
r["organizer_sha256"] = sha256(C.ORIGINAL_CSV)
r["organizer_sha256_ok"] = all(v["ok"] for v in verify_originals().values()) and r["organizer_sha256"] == EXPECTED_ORGANIZER_SHA256

p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rs"], capture_output=True, text=True)
r["pytest_summary"] = [l for l in p.stdout.strip().splitlines() if "passed" in l or "failed" in l][-1]
r["pytest_skips"] = [l for l in p.stdout.splitlines() if l.startswith("SKIPPED")]
r["pytest_ok"] = p.returncode == 0

chk = pd.read_csv(C.OUTPUTS / "validation_checks.csv")
failed = set(chk.loc[~chk.passed, "check_id"])
r["validation"] = f"{int(chk.passed.sum())}/{len(chk)} passed"
r["validation_failed_ids"] = sorted(failed)
r["validation_only_expected_failure"] = failed == EXPECTED_FAILED_CHECKS

cons = pd.read_csv(C.OUTPUTS / "allocation_conservation_checks.csv")
r["conservation_ok"] = bool(cons.passed.all())

# Strict hydro check against the ORIGINAL CEA-derived ceiling (never an enlarged bound)
hc = allocation.hydro_ceiling_twh()
al = pd.read_csv(C.OUTPUTS / "regional_allocation.csv")
h = al[al.source == "hydro"]
viol = float(np.max(h.twh.values - hc.reindex(h.region).values))
dg = pd.read_csv(C.OUTPUTS / "allocation_solver_diagnostics.csv")
r["default_allocation_statuses"] = dg.status.value_counts().to_dict()
r["default_hydro_max_excess_over_original_ceiling_twh"] = max(viol, 0.0)
r["default_hydro_within_original_ceiling"] = viol <= 1e-6 and set(dg.status) == {"solved"}
# Regression: UI-allowed 20% hydro must be reported infeasible, not "compliant"
sc20 = scenarios.project("central", overrides={"mix_2047": {"coal": 0.22, "gas": 0.02, "nuclear": 0.07, "hydro": 0.20,
                                                            "solar": 0.35, "wind": 0.12, "other_re": 0.02}})
_, d20 = allocation.allocate_scenario(sc20[sc20.fy_end_year == C.HEADLINE_FY_END])
r["hydro_20pct_case"] = {"status": d20.iloc[0].status, "required_twh": round(float(d20.iloc[0].hydro_required_twh), 3),
                         "original_ceiling_twh": round(float(d20.iloc[0].hydro_ceiling_total_twh), 3)}
r["hydro_20pct_flagged_infeasible"] = d20.iloc[0].status == "infeasible_under_indicative_hydro_ceiling"

sc = pd.read_csv(C.OUTPUTS / "national_scenarios.csv")
row = sc[(sc.scenario == "central") & (sc.fy_end_year == C.HEADLINE_FY_END)].iloc[0]
dom, imp, tot = round(row.domestic_generation_twh, 3), round(row.imported_generation_twh, 3), round(row.total_generation_twh, 3)
r["central_fy2047"] = {"domestic": dom, "imports": imp, "total": tot}
r["headline_preserved"] = (dom, imp, tot) == (5312.183, 7.804, 5319.987)
summary = (C.REPORTS / "results_summary.md").read_text()
r["summary_matches"] = f"{dom:,.3f}" in summary and f"{imp:,.3f}" in summary
deck = json.loads((C.ROOT / "presentation" / "deck_data.json").read_text())
r["deck_data_matches"] = abs(deck["headline_dom"]["central"] - row.domestic_generation_twh) < 1e-6
live = DM.apply_variant(scenarios.feasibility_flags(scenarios.project("central")), "central")
r["dashboard_code_path_matches"] = abs(live[live.fy_end_year == C.HEADLINE_FY_END].domestic_generation_twh.iloc[0]
                                       - row.domestic_generation_twh) < 1e-6
mix = pd.read_csv(C.DERIVED / "national_mix_fy.csv")
r["fy2026_fuel_split_value_types"] = sorted(set(mix[mix.fy_end_year == 2026].value_type))
r["fy2025_fuel_split_value_types"] = sorted(set(mix[(mix.fy_end_year == 2025) & mix.source.isin(["coal", "gas"])].value_type))

core_keys = ["organizer_sha256_ok", "pytest_ok", "validation_only_expected_failure", "conservation_ok",
             "default_hydro_within_original_ceiling", "hydro_20pct_flagged_infeasible", "headline_preserved",
             "summary_matches", "deck_data_matches", "dashboard_code_path_matches"]
r["core_model_gates_passed"] = all(bool(r[k]) for k in core_keys)

try:
    import streamlit  # noqa: F401
    have_st = True
except ImportError:
    have_st = False
real_skipped = any("test_dashboard_real" in l for l in r["pytest_skips"])
r["streamlit_installed"] = have_st
r["dashboard_real_runtime"] = "VERIFIED (AppTest passed in this run)" if (have_st and r["pytest_ok"] and not real_skipped) \
    else "UNVERIFIED - Streamlit not installed here; real AppTest skipped. Run DASHBOARD.md steps on a machine with Streamlit."
r["note"] = "core_model_gates_passed does NOT imply the dashboard ran under real Streamlit."

out = json.dumps(r, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
(C.OUTPUTS / "quality_gates.json").write_text(out)
print(out)
sys.exit(0 if r["core_model_gates_passed"] else 1)
