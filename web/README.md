# Live browser dashboard

Neutral public URL after GitHub Pages is enabled and deployed: https://sashank-810.github.io/CampusTrotters-INNOTHON-2026/

`web/dist/` is a static browser application, but it **recalculates** national scenarios and the constrained regional allocation on every input change. It does not select precomputed output rows. The port in `live_model.js` uses data exported by `web/export_live_inputs.py` from the existing Python v1.2 code and provenance sources. The deployed `docs/` directory is an exact copy of the browser assets.

Controls include scenario, fiscal year, CEA region, GDP growth path, elasticity, additional electrification, population/urbanization variant, urbanization effect, all seven source mix inputs, regional demand basis, demand alignment weight, geography caps, indicative hydro ceiling, population/GSDP weight and regional drift. Editing a non-coal source adjusts coal as the remainder; if non-coal entries exceed 100%, the model normalizes them and shows the entered sum. The hydro stress case correctly reports infeasibility and labels the displayed no-ceiling fallback. All regional allocations remain exploratory.

Rebuild after `python run_all.py`:

```bash
python web/export_live_inputs.py
node web/test_live_model.js
python -m http.server 8000 --directory web/dist
```

The test checks three national Python reference outputs, 15 regional reference totals, source conservation, changes to GDP and demographics, and a 20% hydro infeasibility case. The public browser application and its deployment must also be opened and exercised separately. The original organizer CSV is not included in static assets and remains unchanged under `data/original/`.
