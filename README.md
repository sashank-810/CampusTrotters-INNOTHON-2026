# CampusTrotters — India Electricity Generation to 2047

**ExxonMobil INNOTHON 2026 final submission · v1.4**

**Public interactive dashboard:** https://campustrotters-innothon-2026.vercel.app/ — deployed on Vercel and tested in a public browser. The source served there is in `docs/`; see [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md) for deployment details.

The browser dashboard recalculates GDP, elasticity, electrification, demographics, source mix, demand location, geography and hydro sensitivity directly in the browser. Its baseline was compared to the v1.2 Python model across three scenarios and 15 regional totals. The full Python Streamlit application remains in `app/streamlit_app.py`; `web/` contains the browser port and its test. The seven-slide final presentation is `presentation/CampusTrotters_INNOTHON2026_FINAL_v1_4.pptx` and links to the public dashboard.

The public dashboard's v1.5 presentation uses a plain-language research layout. A production browser check confirmed that Conservative changes domestic FY2046–47 generation to 4,435 TWh and Reset restores the 5,312 TWh central case.

v1.4 packages and patches v1.2 without modifying its source archive or the organizer CSV; see **`CHANGELOG.md`** and **`DASHBOARD.md`**.

Reproducible final prototype: national scenarios and conditional regional allocations of electricity
**generated** (TWh = BU) to FY2047-48, an illustrative regional generation strategy, validation evidence and an
interactive Streamlit dashboard. Capacity and consumption are never used as the forecast metric.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_all.py                    # rebuilds derived data, audit, models, figures, reports (~6 s; no network needed)
python -m pytest -q                  # 48 passed on Python 3.12 with real Streamlit 1.67
python quality_gates.py              # core-model gates + SEPARATE dashboard_real_runtime status -> outputs/quality_gates.json
streamlit run app/streamlit_app.py   # dashboard at http://localhost:8501
```
Optional – rebuild the slides: `python presentation/export_deck_data.py && node presentation/build_deck.js`
(needs Node + `pptxgenjs`). The v1.2 deck is `presentation/INNOTHON2026_midpoint_presentation_v1_2.pptx`; earlier decks are in
`presentation/archive_v1_0/` and `presentation/archive_v1_1/`.

**Headline (central, FY2046-47):** 5,312.18 TWh generated domestically + 7.80 TWh assumed Bhutan imports = 5,319.99 TWh
CEA-definition total. The national statistical forecast is independently fitted and backtested; regional results are
*conditional projections* from an illustrative, generation-conserving allocation, not a physical-feasibility proof.

## Repository map
| Path | Contents |
|---|---|
| `data/original/organizer_renewable_india_dataset/` | Organizer base-truth CSV **byte-identical** to GitHub commit `89d5ef7`, upstream README/LICENSE, `SHA256SUMS` |
| `data/external/` | Supplementary official data (CEA, MoP, NPP; Ember via OWID) + **`SOURCE_MANIFEST.csv`** (URL, retrieval date, period, unit, method, verification, limitations) |
| `data/derived/` | Reproducible joins/mappings (generated; every row has `value_type` and `source_id`) |
| `src/` | `integrity` (hash guard) · `prepare` (derived tables + 186 checks) · `audit` (data-quality report) · `forecast` (models + rolling-origin backtests) · `scenarios` (GDP-elasticity scenarios + mix) · `demography` (TG population/urbanization; variants) · `allocation` (illustrative SciPy allocation, hydro ceiling, sensitivity) · `figures` · `report` · `config` (all assumptions) |
| `app/streamlit_app.py` | Dashboard |
| `outputs/` | All model outputs, backtest scores, solver diagnostics, validation results, `run_log.json` |
| `reports/` | `methodology.md`, `results_summary.md` (auto-generated numbers), `data_quality_report.md` (auto), `assumptions_and_limitations.md`, `mentor_questions.md`, `figures/` |
| `presentation/` | Midpoint deck (`.pptx` + `.pdf`), generator script and exported deck data |
| `tests/` | pytest suite; `test_dashboard_real.py` = real Streamlit AppTest (skips if Streamlit absent); `tests/stubs/streamlit.py` = stand-in used only by the stub smoke test |

## What is observed, estimated or modelled
* **Observed:** CEA/MoP total generation FY2009-10..FY2025-26; CEA regional conventional (FY2020-21..FY2025-26) and
  RE generation by source (FY2021-22..FY2025-26); Ember calendar-year generation; organizer population/GSDP.
* **Estimated (flagged):** FY2024-25 national coal vs gas split; some historical Bhutan-import values.
* **Derived residual:** FY2025-26 gas+diesel = CEA thermal − coal − lignite (coal and lignite are published actuals).
* **Projections / assumptions:** TG population & urban share to 2036 (official projection), extrapolated to 2047.
* **Model-generated:** everything in `outputs/` beginning with `national_`, `regional_`, `allocation_`.

## Verification status (v1.4 final build)
* `python run_all.py`, `python -m pytest -q` (**48 passed**) and `python quality_gates.py`
  (`core_model_gates_passed: true`, `dashboard_real_runtime: VERIFIED`) ran with Python 3.12 and Streamlit 1.67.
  The original organizer SHA-256 is unchanged; exactly one documented source check fails (`PSAG-GR-2011`).
* Real Streamlit AppTest passed 17 cases, including hydro infeasibility, renormalisation and all scenario and regional controls. The browser model was independently compared to Python reference outputs with `node web/test_live_model.js`. On the public Vercel URL, central FY2046–47 displayed 5,312 TWh domestic; changing initial GDP growth from 7% to 8% displayed 5,795 TWh; changing hydro to 20% showed the 1,062 versus 480 TWh infeasibility warning and a labelled regional fallback; Reset restored the baseline.
* Official PDFs were read by automated text extraction; arithmetic checks guard the transcription. Spot-check a few values.

See `reports/methodology.md` for the method and `reports/mentor_questions.md` for open questions.
