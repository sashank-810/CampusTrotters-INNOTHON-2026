# Public dashboard

Live URL: https://campustrotters-innothon-2026.stormyboot512.chatgpt.site

This responsive static page selects **precomputed** national scenario, year and regional allocation rows exported from the verified Python v1.2 pipeline. It does not recalculate arbitrary inputs in the browser. The full `app/streamlit_app.py` recomputes custom sliders using the same `src/` model code and passed 17 real Streamlit AppTest cases.

Rebuild the page data after `python run_all.py` with `python web/export_static_data.py`. Serve `web/dist/` as static files, for example `python -m http.server 8000 --directory web/dist`. The published Site was checked with central/accelerated scenarios, a 2035 year selection and a North-Eastern region selection; its tab and table values changed consistently.

The raw organizer CSV is not shipped as a static asset. It remains in `data/original/` with its upstream MIT license and immutable SHA-256.
