# Deployment runbook

## Hosting choice

| Option | Free-plan behavior | Data and service fit | Price note | Decision |
|---|---|---|---|---|
| Streamlit Community Cloud | Sleeps when idle and wakes on request | Direct GitHub deployment; suitable for the compact aggregate dashboard | Free | Chosen for the public dashboard |
| Render | Free web service can spin down; Docker and health checks supported | Hosts the separate FastAPI service; warehouse rebuilds from repository sources | Free tier selected; paid plans reduce sleeping | Chosen for the public metrics API |
| Self-hosted Docker | Behavior depends on the host | Runs dashboard, API and warehouse together with persistent volume | Infrastructure cost applies | Production option when uptime and private access matter |

Streamlit Community Cloud fits the current fictional training product because the checked-in sources and generated warehouse remain below the platform limit and occasional wake-up delay is acceptable. The repository publishes aggregate dashboard views and source training files; it does not publish credentials. `render.yaml` and `Dockerfile.api` package the API as a second GitHub-backed Render service because Streamlit hosts the dashboard process rather than a second FastAPI process.

## Refresh schedule

The GitHub Actions workflow runs at 06:17 UTC on the first day of each month, on demand, and whenever source or pipeline files change on `main`. It rebuilds the warehouse, runs the checks, creates PDF and Excel packs, and retains them as a 30-day workflow artifact. The fixed training source ends on 2026-09-30, so the workflow refreshes and verifies that snapshot until a new source file arrives.

## Current state

The public [adityamergurwar/pulseiq repository](https://github.com/adityamergurwar/pulseiq) publishes `main`, the four phase tags, `v1.0.0-rc1` and `v1.0.0`. The Streamlit Community Cloud dashboard is live at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app). The FastAPI service is live on Render at [pulseiq-metrics-api-fezs.onrender.com](https://pulseiq-metrics-api-fezs.onrender.com), and its five governed metrics were checked successfully on 19 November 2026. The current public dashboard is an aggregate fictional-data training release and displays the demo role simulator; it must not be represented as production authentication. The scheduled warehouse/report workflow is configured in `.github/workflows/monthly-refresh.yml`; a run can rebuild the fixed snapshot but cannot advance the cutoff without new source data.

## Remaining owner verification and submission actions

1. **Verify the public link from a physical phone and with another viewer.** The app is deployed at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app), but a physical-phone screenshot and an independent viewer's headcount check still need owner evidence.
2. **Complete the personal submission actions.** Confirm collaborator access for `fobesitech`, record the required face-and-screen walkthrough using `docs/board_demo_script.md`, upload it with link access enabled, and submit the final PDF through the programme form.

For a future private production deployment, enable `PULSEIQ_REQUIRE_LOGIN=1`, store `PULSEIQ_USERS_JSON` only in the host secret store and re-run the documented role break tests. The current public release is intentionally an aggregate fictional-data training product.

Streamlit Community Cloud monitors the connected GitHub repository and reflects pushed changes in the app. The app rebuilds its DuckDB warehouse from the checked-in CSV files when the database is absent; the scheduled workflow separately proves the repeatable pipeline and creates a downloadable report artifact. Neither mechanism can create new source data by itself.

## Local rehearsal

```powershell
python etl.py
python -m unittest discover -s tests -v
streamlit run app.py
uvicorn pulseiq.api:app --host 127.0.0.1 --port 8000
```

Production login is enabled only when `PULSEIQ_REQUIRE_LOGIN=1`. When the flag is absent, the sidebar says "Local role simulation" and the app is not authenticated.
