# Deployment runbook

## Current state

The private [adityamergurwar/pulseiq repository](https://github.com/adityamergurwar/pulseiq) has a published `main` branch and annotated `phase-1` tag; the tag marks commit `965d9f6` (2026-10-22). The current `main` includes support for Streamlit-hosted secrets. The Streamlit app is packaged for Community Cloud or another Python host, but no hosting account is connected and there is no public URL. Do not treat a localhost URL as a public deployment. The included demo roles are simulations and must not be used as production authentication.

## Remaining go-live and submission actions

1. In the chosen host, connect the published repository, select branch `main`, and set the app entry point to `app.py`. For Streamlit Community Cloud, the private repository must be authorized in its GitHub connection.
2. Install the packages in `requirements.txt`; the app builds the DuckDB warehouse from the checked-in CSV source files on cold start.
3. In the host's secret manager, set `PULSEIQ_REQUIRE_LOGIN` to `"1"` and `PULSEIQ_USERS_JSON` to JSON records with `role`, optional `department_id` / `team_id`, and PBKDF2-SHA256 `password_salt_hex` plus `password_pbkdf2_hex` values. Generate a hash with `python scripts/hash_password.py --help`; do not place real passwords in the repository. For Streamlit Community Cloud, add those keys to its Secrets setting; the app reads both host environment variables and Streamlit secrets. A local `.streamlit/secrets.toml` is ignored by Git and must never be committed.
4. Confirm salary detail is restricted to ADMIN/HR roles, managers are scoped to their team, predicted risk remains grouped, and minimum-group rules apply.
5. Review the critical raw-data findings and their clean-layer handling in `docs/validation_results.md` before publication. The DQ page intentionally shows `REVIEW REQUIRED` while the supplied raw rows retain seeded critical findings.
6. Add the required GitHub collaborator `fobesitech` with the access level specified by the project owner/playbook.
7. Once a host and changing source-feed process exist, configure a schedule there to rebuild the warehouse and re-run tests. The current 29 CSV extracts are a fixed training snapshot, so scheduling a rebuild alone does not advance the data cutoff.
8. Test the live link from a phone and with a viewer who has not seen the project. Record the final five-minute walkthrough after a live URL exists, confirm the personal learning reflection, and upload the required files to the programme.

## Local rehearsal

```powershell
python etl.py
python -m unittest discover -s tests -v
streamlit run app.py
uvicorn pulseiq.api:app --host 127.0.0.1 --port 8000
```

Production login is enabled only when `PULSEIQ_REQUIRE_LOGIN=1`. When the flag is absent, the sidebar says "Local role simulation" and the app is not authenticated.
