# PulseIQ release notes

## 2026-10-22 · Live deployment and scheduled reporting

- Confirmed from the owner's browser screenshot that the deployed dashboard loads at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app).
- Added a monthly GitHub Actions workflow to rebuild the warehouse, run tests and acceptance checks, and publish the PDF/Excel pack as a downloadable artifact. It also runs on demand and when source/pipeline files change.
- Added automated access-control and seeded-issue disposition tests for salary-role permissions, department scopes, reversed leave dates and mismatched expense totals.
- The ETL now quarantines reversed-date leave and mismatched expense rows from clean metrics while preserving the raw source and DQ findings.
- Updated deployment, submission and acceptance documents. Production authentication is still pending in Streamlit Secrets; the supplied dataset remains a fixed snapshot through 2026-09-30.

## 2026-10-22 · GitHub release published

- Published the private `main` branch and annotated `phase-1` tag to [adityamergurwar/pulseiq](https://github.com/adityamergurwar/pulseiq).
- At initial publication, verified that the branch and peeled tag both resolved to commit `965d9f6`; the tag remains pinned there.
- Updated the deployment runbook, acceptance matrix, README and Phase 1 report to reflect the published release and the remaining hosted and owner actions.
- Added Streamlit-hosted secret lookup alongside environment variables on current `main`; all 8 automated tests and the local acceptance reconciliation pass.

## 2026-10-22 · Repeatable monthly workbook

- Added `scripts/build_monthly_excel.py` to generate the nine-sheet monthly Excel pack directly from governed metric, dashboard and audit views.
- Added a regression test for the workbook structure, reporting values, data-quality warning and reconciliation status.
- Rendered and reviewed all nine sheets; the export has no formula errors and its September 2026 headline values match the existing pack.
- The workbook keeps seeded raw-source findings visible. The data-quality gate remains `REVIEW REQUIRED` pending owner review.

## 2026-10-19 · Local completion candidate

- Added all 12 Streamlit analytics pages, five governed FastAPI metrics, metric lineage, validation results, monthly PDF/Excel packs and the board deck.
- Preserved source files and added explicit audit records for quarantines, load counts, SCD repair and the June 2026 payroll-ledger correction.
- Added a regression test for the headcount dashboard's prior-month query. The prior query repeats a department filter, so the call now binds all three parameters.
- Local test suite: 7 passed. Independent acceptance checks reconcile 18 payroll periods and 180 privacy-safe department-months.
- Source data cutoff: 2026-09-30. No overlap exists between forecast periods and actuals, so forecast error is not estimable.
- The private Git remote is configured locally and the `phase-1` tag is ready. GitHub authentication and the initial push remain outstanding. No production secret configuration, live URL, scheduled incoming data or recorded live demo is available in this workspace.
