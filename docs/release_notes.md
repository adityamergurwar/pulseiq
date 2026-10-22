# PulseIQ release notes

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
- Release remains local. No remote repository, production secret configuration, live URL, scheduled incoming data or recorded live demo is available in this workspace.
