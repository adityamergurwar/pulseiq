# Deployment runbook

## Current state

The app is packaged for Streamlit Community Cloud or another Python host. The private repository target is [adityamergurwar/pulseiq](https://github.com/adityamergurwar/pulseiq), and the initial push is pending. No hosting account is connected in this workspace. Do not treat a localhost URL as a public deployment. The included demo roles are simulations and must not be used as production authentication.

## Before publishing

1. Create the private `pulseiq` repository and push the reviewed project.
2. Choose the host, connect the repository and set the app entry point to `app.py`.
3. Install the packages in `requirements.txt`; the app builds the local DuckDB warehouse from the checked-in CSV source files on cold start.
4. In the host's secret manager, set `PULSEIQ_REQUIRE_LOGIN=1` and `PULSEIQ_USERS_JSON` to JSON records with `role`, optional `department_id` / `team_id`, and PBKDF2-SHA256 `password_salt_hex` plus `password_pbkdf2_hex` values. Generate a hash with `python scripts/hash_password.py --help`; do not place real passwords in the repository.
5. Confirm salary detail is restricted to ADMIN/HR roles, managers are scoped to their team, predicted risk remains grouped, and minimum-group rules apply.
6. Review the critical raw-data findings and their clean-layer handling in `docs/validation_results.md` before publication. The DQ page intentionally shows `REVIEW REQUIRED` while the supplied raw rows retain seeded critical findings.
7. Once a host and changing source-feed process exist, configure a schedule there to rebuild the warehouse and re-run tests. The current 29 CSV extracts are a fixed training snapshot, so scheduling a rebuild alone does not advance the data cutoff.
8. Test the live link from a phone and with a viewer who has not seen the project. Record the final five-minute walkthrough after a live URL exists.

## Local rehearsal

```powershell
python etl.py
python -m unittest discover -s tests -v
streamlit run app.py
uvicorn pulseiq.api:app --host 127.0.0.1 --port 8000
```

Production login is enabled only when `PULSEIQ_REQUIRE_LOGIN=1`. When the flag is absent, the sidebar says "Local role simulation" and the app is not authenticated.
