# Technical Methodology — India Electricity Generation to 2047 (v1.2)
IISc Bengaluru team · ExxonMobil INNOTHON 2026 · Midpoint (18 Nov 2026)

All numbers come from code (`python run_all.py`) and are collected in `reports/results_summary.md` (auto-generated).
Changes since v1.0 are listed in `CHANGELOG.md`.

**One-line characterisation.** A generation-only, auditable prototype: an **independently fitted, backtested national statistical
forecast**; an assumption-driven national scenario engine (GDP, elasticity, demographic *sensitivity*, electrification);
and **conditional regional projections** — an *illustrative, generation-conserving allocation* of the national scenario,
not independently fitted or backtested regional forecasts. One exploratory resource check (hydro) is applied strictly. Organizer data are preserved
byte-for-byte.

## 1. Problem framing and accounting
* **Quantity:** annual electricity **generated** (TWh = BU). Not consumption, not installed capacity.
* **Headline = domestic generation** (generated inside India). CEA/MoP "total generation" also contains Bhutan
  imports (7.804 TWh in FY2025-26); projections hold imports at that level and report them **separately**:
  domestic + imports = CEA-definition total.
* **Horizon:** to FY2047-48; headline **FY2046-47** (labelled 2047; mentor Q1). Indian FY, labelled by end year.

## 2. Data
| Role | Dataset | Basis |
|---|---|---|
| Base truth (organizer) | `renewable_energy_dataset.csv` | preserved byte-identical; SHA-256 verified on every load |
| Forecast target | MoP *Power Sector at a Glance* total generation FY2009-10..FY2025-26 (n = 17); FY2025-26 confirmed in the May-2026 edition | FY, utilities, incl. Bhutan imports |
| National mix | CEA Growth Book (FY2016-17..FY2023-24); CEA DGR + RE reports; **FY2025-26 coal+lignite from CEA 18-column fuel-wise actuals (Sub-Report 11)**, gas+diesel = Sub-Report 1 thermal − coal − lignite | FY |
| Regional history | CEA DGR (FY2020-21..FY2025-26) + CEA RE reports (FY2021-22..FY2025-26) | FY, region × source |
| Population & urbanization | **Technical Group on Population Projections (NCP/MoHFW, 2020)** Tables 8-10, states 2021-2036 | 1 March, projection |
| Hydro resource | **CEA region-wise hydro potential (31.10.2023)**: exploitable identified vs developed | resource check |
| Long history / backtest | Ember via OWID (CY 2000-2025) + Maddison real GDP | CY, incl. captive |
| Demand location (transfer term only) | CEA LGBR 2025-26 actual requirement FY2024-25 | consumption side, never used as generation |

Provenance: `data/external/SOURCE_MANIFEST.csv` (18 entries). **186 automated checks** (185 pass; the one failure is
a source-internal inconsistency in the published FY2010-11 growth rate, documented). NPCIL's 2025-26 annual report
and NITI's ICED page could not be read in this environment; the CEA 18-column reports were used instead, and the
resulting FY2025-26 gas+diesel residual (26.46 TWh) matches the figure the independent audit reported from those sources.

## 3. Statistical models (national, CEA-total basis)
Trend CAGR (A), log-linear OLS (B1), random walk with drift (B2), damped Holt (B3), all on log generation; expanding-
window rolling-origin backtests at horizons 1-5 on CEA FY (40 pairs) and Ember CY (70 pairs); MAE, RMSE, WAPE and
interval coverage. **B2 has the lowest WAPE on both series, but only marginally ahead of the CAGR baseline on the CEA
series** (5.37% vs 5.45%). Its nominal 95% interval covered 82.5% of CEA outcomes at horizons ≤ 5 years.
**The FY2046-47 interval (3,640–8,215 TWh) is a model-based illustrative extrapolation, not empirically calibrated at
a 21-year horizon.** Every interval row in `outputs/national_forecast_statistical.csv` carries an `interval_label`.

## 4. Scenario engine (Model C) — national totals
G_t = G_{t−1}·(1+g_t)^{ε_t} + add-on_t; ε₀ = 0.922 estimated (Ember vs Maddison, 2013-2022), declining to an assumed
end value. Conditional backtest (realised GDP as oracle): WAPE 2.35% vs 4.50% for B2 — conditional, not unconditional skill.

| | Conservative | Central | Accelerated transition |
|---|---|---|---|
| Real GDP growth FY27 → FY47 | 6.0% → 4.5% | 7.0% → 5.0% | 7.0% → 5.0% |
| Elasticity ε₀ → FY47 | 0.922 → 0.70 | 0.922 → 0.80 | 0.922 → 0.80 |
| Extra electrification by FY47 | 0 | 0 | 262.5 TWh (illustrative green-H₂ load) |
| FY47 mix coal/gas/nuc/hydro/solar/wind/other (%) | 52/2/5/7/23/9/2 | 35/2/7/7/35/12/2 | 18/2/10/8/44/15/3 |

**The national mix is a stipulated policy-scenario assumption, not an optimisation output** (no cost, reliability or
emissions optimisation yet). Supporting checks, all reported as flags rather than proofs:
* hydro: the assumed FY47 hydro uses 65% / 77% / 93% of the all-India CEA-potential energy ceiling (480 TWh) in the
  three scenarios — the accelerated case is close to the identified resource;
* solar/wind: variable-RE share > 30% in every scenario → storage/flexibility not modelled (flagged);
* nuclear: > 5× FY2025-26 output in central/accelerated → sustained build-out required (flagged);
* coal: conservative case > 1.5× FY2025-26 (emissions/coal-supply implications, flagged).

## 5. Population growth and urbanization (new in v1.1)
* **Data:** TG projections — India 1,425.9 M (2026) → 1,522.3 M (2036); urban share 36.0% → 39.1%; state values summed
  to CEA regions. 2037-2047: extrapolated (population growth rate continues its TG decline; urban share continues the
  2031-36 increment) → 1,576 M and 42.4% in FY2046-47 (**assumption**).
* **No GDP double counting:** the scenario GDP path is interpreted as already containing the central TG population path,
  so the central demographic variant leaves generation unchanged (tested). Outputs report population, urban share,
  implied per-capita GDP growth and per-capita generation (central FY47: 3,370 kWh/person domestic).
* **Variants (sensitivity):** population growth ±0.2 pp/yr after FY2026; urbanization at half/double TG pace. Variants
  hold per-capita income and per-capita generation fixed, plus an **assumed** urbanization semi-elasticity β
  (default 0.5% generation per percentage point of urban share; tested 0, 0.5, 2.0). Central FY47 effects: population
  −218/+227 TWh; urbanization −85/+169 TWh at β = 0.5%, up to −338/+677 TWh at β = 2%.
* **Regional effect:** the demand-location shares in the allocation's transfer term now drift with TG regional
  population shares and urban shares, plus organizer per-capita GSDP trends (GSDP share ÷ population share), so
  population and income are separated.

## 6. Conditional regional projections: illustrative allocation (convex QP, SciPy SLSQP)
* **Hard:** Σ_r x[r,k] = assumed national total of source k (so Σ regions = national domestic generation, Σ sources =
  regional total); x ≥ 0.
* **Illustrative geography assumptions anchored on observed generation — not physical resource limits:** zero for
  region-source pairs never observed (wind, nuclear in ER/NER); caps at a multiple of observed regional share; existing
  hydro/nuclear output as floors. A "relaxed" mode removes the zero rules and caps (dashboard + sensitivity table).
* **Exploratory resource check (default on, strict since v1.2):** regional hydro ≤ observed mean hydro generation × (CEA exploitable
  potential ÷ developed capacity). This is an energy ceiling; the CEA MW figures are used only as a dimensionless ratio
  (assumes new sites yield like existing ones; mentor Q4). Result: the v1.0 allocation exceeded this ceiling in four
  regions; v1.1 moves hydro to the North-Eastern region (86 TWh central vs 17 TWh in v1.0), which becomes a hydro exporter.
* **Strict infeasibility handling (v1.2):** if the assumed national hydro exceeds the summed ceiling (480.4 TWh), the year is
  returned as `infeasible_under_indicative_hydro_ceiling` with no allocation — the ceiling is never enlarged. Example: central
  with a 20% hydro share needs 1,062.4 TWh in FY2046-47 and is infeasible from FY2036-37. The dashboard then shows an error
  and an explicitly labelled UNCONSTRAINED fallback that is not ceiling-compliant. Compliance is checked against the original
  ceiling in tests and `quality_gates.py`.
* **Objective (illustrative preferences):** closeness to observed geography + λ × closeness to demand location. The
  demand-location term uses CEA electricity-requirement shares (consumption side) and is **exploratory**: a dashboard toggle
  removes it entirely (λ = 0 and organizer population/GSDP proxy for transfers), and a sensitivity case runs with neither
  capacity- nor consumption-derived inputs.
* **Sensitivity** (`outputs/allocation_sensitivity.csv`): v1.0 settings, relaxed geography, organizer proxy, λ = 0/10,
  β = 0/2%. Regional totals move by up to ~80 TWh and transfers change sign in some regions — conclusions about
  individual regions are therefore indicative.

## 7. Uncertainty — three layers, never merged
(i) statistical model-based intervals (calibrated only to 5-year horizons); (ii) scenario and demographic ranges
(assumption-driven); (iii) data uncertainty (FY2024-25 estimated coal/gas split, transcription, provisional CEA values).

## 8. Limitations
No hourly/seasonal dispatch, storage or transmission-flow model; solar/wind/land and nuclear-site potentials not imported;
regional coal vs gas split unavailable; captive generation outside the target; regional results are allocations of national
projections, not separately fitted regional forecasts; no state-level output.
