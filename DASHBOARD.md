# Running and verifying the dashboard (real Streamlit)

Final v1.4 verification: Streamlit 1.67 and all 17 real AppTest cases passed in the submission environment. The Python suite passed 48 tests. The neutral GitHub Pages address, once deployed and independently opened, is https://sashank-810.github.io/CampusTrotters-INNOTHON-2026/ . Its controls recalculate results with a browser port of the Python national and allocation model; `node web/test_live_model.js` checks baseline agreement.

To rerun the Python app:

```bash
pip install -r requirements.txt
python run_all.py
python -m pytest -q tests/test_dashboard_real.py   # REAL Streamlit runtime (AppTest): all scenarios, variants, toggles
streamlit run app/streamlit_app.py                 # opens http://localhost:8501
```

Expected: `test_dashboard_real.py` reports 17 passes. Then `python quality_gates.py` reports `dashboard_real_runtime: VERIFIED`.

## Demo path for judges (≈2 minutes)
1. Headline cards: domestic FY2046-47 generation (central ≈ 5,312 TWh); hover for imports and CEA total.
2. Sidebar → Scenario: switch Conservative / Central / Accelerated.
3. Sidebar → Demographic variant: "High population growth" → headline moves by ≈ +227 TWh (central).
4. Population & urbanization tab: TG paths and regional population shares.
5. Regional allocation tab → Region "North-Eastern": hydro vs CEA-potential ceiling; sensitivity table.
6. Data & provenance tab: source manifest and 186 validation checks.
7. Robustness demo: set Hydro to 20% in the mix expander → red INFEASIBLE banner; charts switch to a labelled UNCONSTRAINED fallback.

## Screenshot for the deck
After `streamlit run`, capture the "National forecast" tab and save it as `presentation/dashboard_screenshot.png`, then
re-run `node presentation/build_deck.js` — the deck inserts it automatically on the live-demo slide if the file exists.
