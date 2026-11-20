# Publish the live dashboard on Vercel

Repository: https://github.com/sashank-810/CampusTrotters-INNOTHON-2026

The deployment-ready static application is in `docs/`. It recomputes national and regional results in the browser; the Streamlit/Python version remains in `app/` for reproducibility.

## Vercel project settings

1. Connect Vercel to the GitHub account that owns this repository.
2. In Vercel, choose **Add New → Project**, then import `sashank-810/CampusTrotters-INNOTHON-2026`.
3. Set **Root Directory** to `docs`. Select **Other** as framework preset. Leave build command and output directory at their static defaults; do not run the Python pipeline during deployment.
4. Deploy the `main` branch. Copy the actual Production Domain shown by Vercel (usually a `vercel.app` address). Do not infer a URL from the project name.
5. Open the public URL in a signed-out browser. Check the central FY2046–47 domestic value around **5,312 TWh**, change GDP growth and confirm the figure changes, set Hydro to **20%** and confirm the indicative-ceiling infeasibility warning, then reset.
6. Replace deployment-pending text in `README.md` and the seven-slide deck with the verified Production Domain before submitting.

The browser baseline is checked against v1.2 Python outputs by `node web/test_live_model.js`. The original organizer dataset is never sent to static hosting; only derived model inputs in `docs/model_inputs.json` are published. Regional physical feasibility and long-horizon statistical calibration remain unproven.
