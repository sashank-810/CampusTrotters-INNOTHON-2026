# Assumptions, limitations and value-type legend

## Value types used in every derived/output table
| value_type | Meaning |
|---|---|
| `organizer_original_plus_derived_columns` | organizer values unchanged + added mapping columns |
| `external_observed` | reported by CEA / MoP / Ember (see `source_id`) |
| `derived` / `derived_PSAG_minus_GrowthBook` | arithmetic on observed values (documented formula) |
| `estimated_split` | not reported; estimated with a stated ratio (FY2024-25 coal vs gas only, as of v1.1) |
| `derived_residual` | difference of two observed official values (FY2025-26 gas+diesel = thermal − coal − lignite) |
| `external_projection` / `extrapolated_assumption` | official population projection (to 2036) / our extrapolation beyond 2036 |
| `zero_not_printed_in_source` | region/source not printed in a CEA table; treated as 0 |
| `model_generated` / `scenario_projection` | output of a model or scenario assumption — never an observation |

## Key assumptions (all editable in `src/config.py` and, where meaningful, in the dashboard)
1. **Target definition:** CEA/MoP total generation incl. RE (utilities) — includes Bhutan imports (~0.4%), excludes
   captive plants. **Headline = domestic generation** = CEA total − Bhutan imports (imports held at the FY2025-26 level,
   7.804 TWh, and reported separately).
2. **"2047" = FY2046-47**; projections also provided for FY2047-48.
3. **GDP growth paths** and **elasticity end-points** per scenario (methodology §4). The starting elasticity (0.922) is
   estimated, not assumed.
4. **Accelerated-transition add-on** of 262.5 TWh by FY2046-47 is an illustrative green-hydrogen electrolysis load
   (5 Mt/yr × 52.5 kWh/kg). Both inputs are assumptions to be refined with mentors.
5. **2047 generation mixes** are policy-scenario assumptions, not optimisation outputs.
6. **Regional coal vs gas split** of thermal follows the regional thermal geography (no regional gas data retrieved).
7. **FY2024-25 national coal vs gas split** uses the FY2023-24 Growth-Book ratio (FY2025-26 now uses published CEA actuals).
8. **Regional geography caps, zero rules and weights** are illustrative assumptions anchored on observed generation —
   NOT physical resource limits. Hydro is additionally capped by the indicative CEA-potential energy ceiling (exploratory,
   strict: settings above it are reported infeasible, never rescaled). Regional outputs are conditional allocations,
   not independently fitted regional forecasts.
11. **Rule ambiguity (unresolved):** the problem statement restricts installed capacity and energy consumption for forecasting
   or comparison. Two secondary inputs may fall under it — CEA hydro potential (MW, used as a ratio) and CEA requirement
   shares (demand location). Both are optional toggles labelled exploratory; organizer confirmation is pending.
9. **Demand location** (only for the transfer term) = CEA LGBR FY2024-25 actual requirement shares, drifted by TG regional
   population and urban-share projections and organizer per-capita GSDP trends (damping 0.5).
10. **Demography:** TG projections to 2036; extrapolation to 2047; variants ±0.2 pp/yr population growth and ½×/2× urbanization
    pace; urbanization semi-elasticity β = 0.5%/pp (illustrative, not estimated).

## Limitations
* Only 17 annual national observations (FY basis) and 5 years of regional source-level history.
* No hourly / seasonal dispatch, storage, reserve-margin or transmission power-flow model: reliability is indicated
  by dispatchable / variable-RE shares only, and all feasibility flags are **provisional**.
* Solar/wind/land and nuclear-site potentials not yet imported; only hydro has a source-backed ceiling. The national mix
  is a stipulated scenario assumption, not an optimised mix.
* Regional outputs are allocations of national projections, not separately fitted regional forecasts; no state-level output.
* Statistical intervals are model-based; backtests cover only 1-5 year horizons (CEA 95% coverage 82.5%). The FY2046-47
  interval is a long-horizon extrapolation, NOT empirically calibrated.
* PDF tables were transcribed via automated text extraction; arithmetic checks guard against errors but the original
  PDFs should be spot-checked by the team before final submission.
* FY2025-26 total (1,847.913 BU) is confirmed in the May-2026 MoP *Power Sector at a Glance* edition (resolves the v1.0
  'deleted' file-name caveat).
* NPCIL Annual Report 2025-26 and NITI ICED pages could not be read here; FY2025-26 fuel split taken from CEA 18-column reports.
* TG population projections were read from a mirror PDF (India totals cross-checked with MoSPI); three NER state totals
  are derived from urban persons ÷ urban %. Projections pre-date Census 2027.
* IMF growth figures were taken from a secondary news report, not the IMF database.
* The organizer dataset contains XGBoost-imputed values (unflagged), nominal GSDP, an undocumented Year basis, and
  is missing Ladakh and DNH&DD.
* The screening-stage 5,900 TWh figure was consumption-based and is **not** used as a target or calibration point.
