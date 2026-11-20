# CampusTrotters final verification — 20 November 2026

## Reproduction

- `python run_all.py`: completed with 186 validation checks (185 passed; documented PSAG-GR-2011 source inconsistency).
- `python -m pytest -q`: **48 passed**, including **17 real Streamlit AppTest cases**, no skips. See `outputs/test_results_final.txt`.
- `python quality_gates.py`: `core_model_gates_passed=true`, `dashboard_real_runtime=VERIFIED`. See `outputs/quality_gates.json`.
- Original organizer CSV SHA-256: `f8f98adfc00457f3cd6033193722503fc481250d19ec37e0c692b35450d7bd4f`. The original v1.2 ZIP is not modified.
- The static export passed 66/66 national-to-regional accounting comparisons and matched the published site's data JSON byte-for-byte.
- Browser verification of the public site: central headline 5,312 TWh; accelerated 5,575 TWh; the 2035 North-Eastern selection changed regional output and mix. Public URL: https://campustrotters-innothon-2026.stormyboot512.chatgpt.site

## Independent numerical cross-checks

| Quantity | Reproduced value |
|---|---:|
| Central FY2046–47 domestic generation | 5,312.183 TWh |
| Assumed Bhutan imports | 7.804 TWh |
| CEA-definition total | 5,319.987 TWh |
| Conservative / accelerated domestic | 4,434.575 / 5,574.683 TWh |
| Five central regional allocations summed | 5,312.183 TWh |
| Default region-year allocations solved | 66/66 |
| Hydro 20% stress requirement / original indicative ceiling | 1,062.437 / 480.363 TWh; infeasible |
| RW-drift CEA FY WAPE / Ember CY WAPE | 5.37% / 4.25%, horizons 1–5 |

## Distinctions and open issues

Observed generation comes from CEA/MoP, with an independent Ember comparison. The FY2024–25 coal/gas split and some historical imports are estimates. National scenarios, demographic variants and fuel shares depend on assumptions. Regional outputs are conditional allocations, not independently calibrated forecasts. The optional hydro ceiling uses capacity ratios and the optional demand-location term uses electricity-requirement shares; organizer approval of these secondary uses is unresolved. There is no verified regional resource, siting, transmission, dispatch or storage feasibility model. The statistical 2047 interval extrapolates beyond validated horizons and is not calibrated at 21 years.

The public web page selects precomputed outputs; the real Streamlit app in the same repository recomputes user-defined model controls.
