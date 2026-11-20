# Public Vercel deployment

Production URL: **https://campustrotters-innothon-2026.vercel.app/**

Repository: https://github.com/sashank-810/CampusTrotters-INNOTHON-2026

The static browser application in `docs/` was deployed directly to Vercel and independently exercised in a public browser on 20 Nov 2026. It recomputes national and regional results on parameter changes. The full Streamlit/Python application remains in `app/` for reproducibility.

The Vercel project is currently **directly deployed**, not connected to GitHub: a GitHub push does not automatically redeploy it. For future changes, connect the project to this repository in Vercel (Root Directory `docs`, Framework Preset `Other`, no Python build step) once the Vercel account's GitHub Login Connection has been enabled, or manually redeploy the five static assets in `docs/` together. Verify the production alias after each deployment. The project is public, with Vercel deployment protection disabled for this submission.

## Public verification

* Central FY2046–47: **5,312 TWh domestic** and **5,320 TWh CEA-definition total**.
* Change initial GDP growth from 7% to 8%: domestic headline changes to **5,795 TWh** (total **5,803 TWh**); Reset returns to baseline.
* Set hydro share to 20%: the dashboard warns that **1,062 TWh** is required against an indicative **480 TWh** ceiling. Regional strategy explicitly labels the no-ceiling fallback; it does not claim that the constrained allocation is feasible.

The browser baseline is checked against v1.2 Python outputs by `node web/test_live_model.js`. The original organizer dataset is never sent to static hosting; only derived model inputs in `docs/model_inputs.json` are published. Regional physical feasibility and long-horizon statistical calibration remain unproven.
