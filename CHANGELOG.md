# CHANGELOG

## v1.8 — 20 Nov 2026 (judge-facing dashboard copy)
* Removed internal version and checksum text from the public dashboard. Kept the original dataset integrity hash and detailed checks in the repository.
* Reworded the provenance view for readers and linked it to the repository for deeper verification.
* Hidden routine success status; infeasibility and invalid-input warnings remain visible. Verified the live central view, provenance view and hydro warning.

## v1.6 — 20 Nov 2026 (accelerated scenario input fix)
* Allowed fractional TWh in the browser's extra-electrification input. The accelerated scenario uses 262.5 TWh, which the former whole-number step falsely rejected.
* Verified the public Accelerated transition view at FY2046–47: 5,575 TWh domestic, 5,582 TWh CEA-definition total, 80% non-fossil, and five regional allocations summing to 5,574.7 TWh.

## v1.5 — 20 Nov 2026 (dashboard presentation)
* Reworked the public browser dashboard into a calmer research layout with plain-language headings, larger labels and controls, and clearer notes on observed versus modelled results.
* Kept the v1.2 equations, assumptions and source data unchanged. Rechecked the browser reference scenarios and conservation tests; independently exercised scenario switching and Reset on the production Vercel URL.

## v1.4 — 20 Nov 2026 (interactive public deployment)
* Ported the v1.2 national and regional calculations to the static browser application in `docs/`, with live controls and reference comparisons in `node web/test_live_model.js`.
* Fixed the initial elasticity numeric field to accept the precise fitted value; the prior step restriction prevented rendering in production.
* Deployed and exercised the neutral public Vercel URL, including GDP sensitivity, hydro infeasibility and reset. Direct deployment is not yet GitHub-connected.
* Updated the seven-slide final deck's hyperlink to the public URL in a versioned v1.4 copy. Original data and previous deck versions remain untouched.

## v1.3 — 20 Nov 2026 (CampusTrotters final submission)
* Preserved the original v1.2 ZIP and original organizer CSV (SHA-256 `f8f98adfc00457f3cd6033193722503fc481250d19ec37e0c692b35450d7bd4f`).
* Fixed `tests/test_dashboard_real.py` to use an absolute app path, which recent Streamlit AppTest resolves correctly.
* Installed real Streamlit 1.67, reproduced `python run_all.py` and verified **48 passed**, with 17 real dashboard test cases and no skipped tests. Quality gates: core model passed, dashboard runtime VERIFIED, 185/186 source checks passed (documented `PSAG-GR-2011` exception).
* Published and browser-tested a public static dashboard driven by precomputed v1.2 outputs. It offers scenario, year, region and provenance views; custom recomputation remains in the tested Streamlit app.
* Built a separate seven-slide CampusTrotters final deck, with observed data, assumptions, scenario outcomes, conditional allocations, backtesting and feasibility limits explicitly separated.
* Remaining limitations: regional predictive calibration, physical resource/dispatch/transmission feasibility and organizer clarification of secondary capacity/requirement inputs.

## v1.2 — 17 Nov 2026 (targeted patch after the v1.1 independent audit)
v1.1 ZIP (`INNOTHON2026_IISc_midpoint_v1_1.zip`, SHA-256 `22553730…53b90d`) and v1.0 ZIP preserved unchanged. Organizer CSV
unchanged (SHA-256 `f8f98adf…bd4f`). Default national and regional results are numerically unchanged from v1.1.

* **Hydro infeasibility fixed (P1).** `allocation.solve_year` no longer enlarges the CEA-derived hydro ceiling. When the
  assumed national hydro exceeds the summed ceiling, the year returns `status = infeasible_under_indicative_hydro_ceiling`,
  `success = False` and no allocation rows. Every solved year is checked against the ORIGINAL ceiling
  (`max_hydro_ceiling_violation_twh`). Reproduced audit case: central, 20% hydro → 1,062.437 TWh required vs 480.363 TWh
  ceiling → infeasible (FY2036-37 onward).
* **Dashboard:** in that case it shows an error and an explicitly labelled UNCONSTRAINED fallback ("NOT ceiling-compliant")
  instead of crashing or implying compliance. Both secondary inputs are optional toggles labelled EXPLORATORY: the strict hydro
  ceiling (capacity ratio) and the requirement-based demand-location term. When the latter is off, requirement data are removed
  entirely (λ = 0; organizer proxy for transfers).
* **Terminology:** "independently fitted national statistical forecast" vs "conditional regional projections (illustrative
  allocation)"; national mixes are "ASSUMPTIONS, not optimised"; gas labelled "gas + minor diesel" (FY2025-26 = thermal residual;
  FY2024-25 split still estimated).
* **Quality gates:** `quality_gates.py` now reports `core_model_gates_passed` and a SEPARATE `dashboard_real_runtime`
  ("UNVERIFIED" unless Streamlit is installed and the real AppTest ran and passed in that invocation). It requires that exactly
  `PSAG-GR-2011` fails, checks hydro against the original ceiling, and runs the 20%-hydro regression case.
* **Tests:** 31 pass + 1 real-Streamlit module skipped (new `tests/test_v12.py`; stub smoke tests for the 20%-hydro and
  toggles-off paths; real AppTest cases added for both).
* **Sensitivity:** new case "No capacity- or consumption-derived inputs (hydro ceiling OFF, λ = 0)".
* **Slides:** `INNOTHON2026_midpoint_presentation_v1_2.pptx` — terminology, gas label, exploratory/strict hydro note, rule
  question, larger chart fonts; no screenshot (dashboard not run).

### Unresolved after v1.2
* **Real Streamlit runtime UNVERIFIED** — `pip install` failed again in the build environment (no package index). No screenshot.
* Rule-scope question on capacity-ratio and requirement-based secondary inputs is open (mentor Q4).
* Regional outputs are allocations, not independently backtested regional forecasts; no state level.
* No solar/wind/land/nuclear-site, dispatch, storage or transmission constraints; national mix not optimised.
* FY2024-25 coal/gas split estimated; NPCIL/NITI pages not read directly.


## v1.1 — 17 Nov 2026 (patch of v1.0 after independent technical audit)
v1.0 ZIP (`INNOTHON2026_IISc_midpoint.zip`, SHA-256 `76cb0b26…5908022`) is preserved unchanged. Organizer CSV unchanged
(SHA-256 `f8f98adf…bd4f`, re-verified on every load and by tests).

### Data (supplementary only; organizer data untouched)
* **FY2025-26 fuel split now published, not estimated.** Coal + lignite = CEA 18-column Sub-Report 11 actuals
  (1,250,338.80 + 30,330.01 GWh = 1,280.669 TWh, `external_observed`); gas + diesel = Sub-Report 1 thermal − coal − lignite
  = 26.462 TWh (`derived_residual`). Replaces the v1.0 estimate (1,275.611 / 31.226 TWh). FY2024-25 split remains estimated.
  NPCIL Annual Report 2025-26 and NITI ICED could not be read in the build environment (server error / chart-only page);
  the residual matches the audit's reported NITI/NPCIL value (26.46 BU).
* **Population & urbanization:** Technical Group on Population Projections (NCP/MoHFW 2020) Tables 8–10, 2021–2036, all
  states/UTs (`tg_population_projections_2021_2036.csv`; 3 NER totals derived from urban persons ÷ urban %).
* **Hydro resource potential:** CEA region-wise hydro potential as on 31.10.2023 (`cea_hydro_potential_region_20231031.csv`).
* FY2025-26 total (1,847.913 BU) confirmed in MoP PSAG May-2026 edition (resolves "deleted" file-name caveat).
* 10 new validation checks (186 total; 185 pass; same documented source inconsistency).

### Models
* **New `src/demography.py`:** national and regional population/urban paths; demographic variants (±0.2 pp/yr population
  growth, ½×/2× urbanization pace, urbanization semi-elasticity β); central variant leaves generation unchanged (no GDP
  double counting; tested). Scenario outputs now include population, urban %, implied per-capita GDP growth and per-capita
  generation. New outputs: `demography_*.csv`.
* **National accounting:** `imported_generation_twh` added; headline everywhere = **domestic** generation
  (central FY2046-47 **5,312.183 TWh**) with **7.804 TWh** assumed Bhutan imports reported separately (CEA-definition
  total 5,319.987 TWh). National totals are numerically unchanged from v1.0.
* **Statistical intervals:** every forecast row carries `interval_label`; beyond 5-year horizons labelled "model-based
  illustrative interval: long-horizon extrapolation, NOT empirically calibrated".
* **Regional allocation reframed** as an *illustrative, generation-conserving allocation*. New: CEA hydro-potential energy
  ceiling (default on), "relaxed" geography mode, demographic demand-location drift (new default basis), sensitivity table
  (`allocation_sensitivity.csv`), hydro check (`hydro_potential_check.csv`). **Regional results changed:** v1.0 hydro
  exceeded the ceiling in NR/WR/SR/ER; v1.1 shifts hydro to NER (central FY47: 86 vs 17 TWh).
* Scenario flags: hydro share of CEA-potential ceiling (accelerated uses 93%).
* `value_type` added to `regional_summary.csv`, sensitivity and check outputs.

### Dashboard
* Headline metrics show domestic generation; imports in tooltips; statistical chart separated from scenario chart; Ember
  shown on its own calendar-year axis; explicit renormalisation notice when mix sliders exceed 100%; new
  Population & urbanization tab; demographic variant, β, geography mode and hydro-ceiling controls; hydro check and
  sensitivity tables; all widgets keyed.
* **New real-runtime test** `tests/test_dashboard_real.py` (Streamlit `AppTest`, no stub) covering all scenarios, variants,
  demand bases, geography/hydro toggles, sliders and the >100% mix path. **Skipped in the build environment because
  Streamlit could not be installed (no package index).** The stub smoke test is kept and relabelled as such.

### Slides & docs
* Deck regenerated as `INNOTHON2026_midpoint_presentation_v1_1.pptx` (v1.0 deck kept): domestic headline + imports,
  "illustrative allocation" wording, softened FY2025-26 causality, Ember CY footnote, "marginally lowest WAPE",
  uncertainty labels, new demography and hydro-check slides, live-demo slide (no screenshot — see unresolved issues).
* Methodology, assumptions, mentor questions (Q4, Q12–Q14) updated; `DASHBOARD.md` added.

### Unresolved
* Real Streamlit run and screenshot not performed here (see DASHBOARD.md for the 3-command check).
* NPCIL/NITI pages not read directly; FY2024-25 coal/gas split still estimated.
* No solar/wind/land/nuclear-site potentials; national mix not optimised; no dispatch/storage/transmission model.
* "2047" definition, captive scope and the use of capacity-type resource potentials await organizer confirmation.
