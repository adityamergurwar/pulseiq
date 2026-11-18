# PulseIQ release notes

## v1.0.0 · Phase 4 release

### Included

- Reproducible DuckDB warehouse with raw evidence, clean dispositions, conformed facts and governed metric views.
- Twelve-page Streamlit application covering workforce, people, delivery, payroll, budget, P&L, receivables, department impact, AI signals, executive scorecard, KPI exploration and data quality.
- One-command monthly PDF and Excel packs for any available reporting month.
- Five-metric FastAPI service with definitions, source, freshness and privacy metadata, plus OpenAPI documentation and a Render deployment blueprint.
- Role-aware KPI exploration for ADMIN, HR, MANAGER and EXECUTIVE, including department/team scope and minimum-group suppression.
- Nine-slide board pack, Phase 4 report, consolidated report, validation evidence and a five-minute demonstration script.
- Exact direct dependency pins and a Python 3.11 GitHub Actions schedule for rebuild, tests, validation and report artifacts.

### Validation

- 28 automated tests pass in an isolated virtual environment.
- Phase 3 verifier passes 12/12 groups; Phase 4 verifier passes 11/11 groups.
- Eighteen monthly payroll/ledger periods reconcile within INR 0.01; declared warehouse relationship orphans are zero.
- A fictional D99 department fixture proves the budget view discovers a new department without code changes.

### Operational boundaries

- The supplied fictional source snapshot ends on 30 September 2026. A refresh cannot create later actuals without a new source feed.
- Forecast accuracy is unavailable until actual data overlaps the supplied forecast horizon.
- Raw quality findings remain visible because the training data intentionally contains defects; conformed metrics use documented corrections or quarantines.
- Production password hashes must be configured in the hosting secret store. No credential is stored in the repository.
- The API blueprint is deployment-ready; the actual public API URL depends on the selected hosting account.
- The screen-and-face demonstration and programme-form upload are owner actions; `docs/board_demo_script.md` supplies the recording flow.

## v1.0.0-rc1 · Release candidate

- Added exact dependency pins, supported GitHub Action versions, clean-machine validation, scheduled report generation, API deployment files, privacy break tests and the Phase 4 release verifier.
