# Deployment runbook

## Hosting choice

| Option | Free-plan behavior | Data and service fit | Price note | Decision |
|---|---|---|---|---|
| Streamlit Community Cloud | Sleeps when idle and wakes on request | Direct GitHub deployment; suitable for the compact aggregate dashboard | Free | Chosen for the public dashboard |
| Render | Free web service can spin down; Docker and health checks supported | Suitable for the separate FastAPI service; warehouse rebuilds from repository sources | Free tier available; paid plans reduce sleeping | Deployment-ready API option |
| Self-hosted Docker | Behavior depends on the host | Runs dashboard, API and warehouse together with persistent volume | Infrastructure cost applies | Production option when uptime and private access matter |

Streamlit Community Cloud fits the current fictional training product because the checked-in sources and generated warehouse remain below the platform limit and occasional wake-up delay is acceptable. The repository publishes aggregate dashboard views and source training files; it does not publish credentials. `render.yaml` and `Dockerfile.api` package the API as a second GitHub-backed service because Streamlit hosts the dashboard process rather than a second FastAPI process.

## Refresh schedule

The GitHub Actions workflow runs at 06:17 UTC on the first day of each month, on demand, and whenever source or pipeline files change on `main`. It rebuilds the warehouse, runs the checks, creates PDF and Excel packs, and retains them as a 30-day workflow artifact. The fixed training source ends on 2026-09-30, so the workflow refreshes and verifies that snapshot until a new source file arrives.

## Current state

The public [adityamergurwar/pulseiq repository](https://github.com/adityamergurwar/pulseiq) has a published `main` branch and annotated `phase-1` tag; the tag marks commit `965d9f6` (2026-10-22). The Streamlit Community Cloud app is deployed at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app); the user supplied a browser screenshot showing the dashboard loaded there on 2026-10-22. The screenshot still showed the **Demo persona** control, so production authentication is not confirmed. The current code can read Streamlit-hosted secrets. The scheduled warehouse/report workflow is configured in `.github/workflows/monthly-refresh.yml`, but its first hosted run has not yet been observed. The included demo roles are simulations and must not be used as production authentication.

## Remaining go-live and submission actions

1. **Set production login secrets in the Streamlit app.** Open the live app, select **Manage app → Settings → Secrets**, and set `PULSEIQ_REQUIRE_LOGIN = "1"` plus `PULSEIQ_USERS_JSON` to the complete JSON record generated locally. The user has generated an ADMIN record; saving it and confirming the login form are still outstanding. Never put the password or JSON record in this repository or chat. Add separate HR, manager and executive records with scoped `department_id`/`team_id` values if those roles will be used in production.
2. **Verify role behavior after login is enabled.** Confirm only ADMIN/HR can see salary-level detail, manager and HR views stay scoped, executive view is company-level, predicted attrition risk stays grouped, and minimum-group suppression is applied. Local unit coverage checks salary access and role scopes.
3. **Run the scheduled workflow once on GitHub.** `.github/workflows/monthly-refresh.yml` rebuilds the warehouse, runs tests and acceptance checks, and uploads the latest PDF/Excel pack. It runs monthly, on demand, and when source/pipeline files change. The repository currently has a fixed training snapshot ending 2026-09-30; the workflow can rebuild and validate it, but a genuinely newer cutoff requires an incoming source feed.
4. **Review data-quality dispositions.** `docs/data_quality.md` maps all 11 planted issue categories to their check, finding count and clean-layer handling. The DQ dashboard intentionally keeps raw source findings visible; do not change the raw rows to make the checks appear green.
5. **Verify the public link from a phone and with another viewer.** The app is deployed at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app), but the current evidence only confirms it loaded in the owner's browser.
6. **Complete repository and submission actions.** Invite the required GitHub collaborator `fobesitech`, record the five-minute live walkthrough using `docs/board_demo_script.md`, confirm the learning reflection in the owner's own words, and upload the required report to the programme site.

Streamlit Community Cloud monitors the connected GitHub repository and reflects pushed changes in the app. The app rebuilds its DuckDB warehouse from the checked-in CSV files when the database is absent; the scheduled workflow separately proves the repeatable pipeline and creates a downloadable report artifact. Neither mechanism can create new source data by itself.

## Local rehearsal

```powershell
python etl.py
python -m unittest discover -s tests -v
streamlit run app.py
uvicorn pulseiq.api:app --host 127.0.0.1 --port 8000
```

Production login is enabled only when `PULSEIQ_REQUIRE_LOGIN=1`. When the flag is absent, the sidebar says "Local role simulation" and the app is not authenticated.
