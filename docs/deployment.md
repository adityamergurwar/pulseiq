# Deployment runbook

## Current state

The private [adityamergurwar/pulseiq repository](https://github.com/adityamergurwar/pulseiq) has a published `main` branch and annotated `phase-1` tag; the tag marks commit `965d9f6` (2026-10-22). The Streamlit Community Cloud app is deployed at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app); the user supplied a browser screenshot showing the dashboard loaded there on 2026-10-22. The screenshot still showed the **Demo persona** control, so production authentication is not confirmed. The current code can read Streamlit-hosted secrets. The scheduled warehouse/report workflow is configured in `.github/workflows/monthly-refresh.yml`, but its first hosted run has not yet been observed. The included demo roles are simulations and must not be used as production authentication.

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
