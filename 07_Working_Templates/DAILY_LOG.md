# Daily Log

**Date:** 2026-10-19
**Done today:** Fixed the workforce prior-month query binding and added its regression test; six tests and local acceptance checks pass. Built and reviewed the September PDF and Excel packs, the Phase 1 evidence report and the nine-slide board deck. Updated lineage, quality, deployment and submission documentation.
**Doing next:** Authenticate and push the private repository and `phase-1` tag. Then review seeded raw-data findings, configure hosting secrets, and complete the live deployment and walkthrough.
**Blocked by:** No Git remote or hosting account is configured in this workspace; no public URL is available.
**One thing learned:** A repeated SQL filter needs a bound value for each placeholder, and a regression test should exercise the real query with both company and department scopes.

---

## 2026-10-22 · Deployment follow-up

**Done today:** Confirmed from the owner's browser screenshot that `https://pulseiq-workforce.streamlit.app` loads the dashboard. Added salary-role and department-scope tests, configured a monthly warehouse/report workflow, and updated the acceptance and deployment status documents.
**Doing next:** Save the generated ADMIN login record in Streamlit Secrets, verify production roles, run the GitHub Actions workflow, and complete the phone/viewer checks and final recording.
**Blocked by:** The secret value is known only in the owner's terminal and must be entered in Streamlit's secret manager. Phone testing, collaborator invitation, learning reflection and programme upload require the owner's account or participation.
**Learning note (owner to confirm):** A deployed dashboard is not production-authenticated until the host has the login flag and password-hash user map configured.
