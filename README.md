# Aura Workforce PulseIQ

PulseIQ is a workforce and finance analytics product for the fictional Zenith Nova Technologies dataset. It contains a repeatable DuckDB pipeline, an auditable clean layer, a star-schema warehouse, governed metrics, 12 Streamlit pages, a five-metric FastAPI service, validation evidence and monthly report builders.

All supplied people, companies and amounts are fictional training data. Source CSVs are retained as raw evidence. Invalid records are recorded with their source row and reason; derived outputs use the conformed or privacy-safe layer.

## Run locally

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python etl.py
streamlit run app.py
```

The app builds `pulseiq.duckdb` from `03_Data/csv/` on its first run if the file is absent. The same build can be run directly with `python etl.py`. A refresh replaces raw, clean, warehouse and metric tables while retaining ETL run and quarantine history.

Run the checks and the answer-key reconciliation:

```powershell
python -m unittest discover -s tests -v
python scripts/verify_acceptance.py
python scripts/verify_phase3.py
python scripts/verify_phase4.py
```

Run the metric API in another terminal:

```powershell
uvicorn pulseiq.api:app --host 127.0.0.1 --port 8000
```

The OpenAPI UI is at `http://127.0.0.1:8000/docs`. The API exposes M01, M04, M09, M20 and M22 with definitions, lineage, data cutoff and privacy metadata.

The dashboard is live at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app). The API is deployment-ready through `render.yaml` and `Dockerfile.api`; see [API deployment and examples](docs/api.md).

## Dashboards

The Streamlit app includes workforce, attendance and leave, attrition, team productivity, payroll and cost, budget and KPI targets, P&L and expenses, receivables and cash, department impact, forecasts and anomalies, executive scorecard, KPI builder, and data quality and lineage.

The local demo persona selector is a role simulation, not authentication. For a hosted deployment set `PULSEIQ_REQUIRE_LOGIN=1` and provide password hashes through `PULSEIQ_USERS_JSON` in the host environment or Streamlit secrets. See [deployment notes](docs/deployment.md); never commit secrets. `.streamlit/secrets.toml` is ignored by Git.

## Data and metric contracts

- `raw` retains the supplied CSV values.
- `clean` applies data-dictionary type/nullability rules, specialized contracts and row-level dispositions.
- `warehouse` holds conformed dimensions and facts, with employee history joined by `employee_key`.
- `metrics` owns M01-M28 and dashboard-safe aggregate views.
- `audit` records row counts, quarantine reasons, quality findings, relationship checks, corrections and ETL runs.

The supplied `data_contracts.csv` defines additional value/range/format rules for four feeds. The source dictionary provides schema and nullability checks for 297 columns across 23 operational dimension/fact tables. Unexpected columns are retained and logged for schema review. See [contract notes](docs/contract_notes.md), [star schema](docs/star_schema.md), [metric lineage](docs/lineage.md), and [quality results](docs/validation_results.md).

## P&L headline snapshot

The supplied workbook's `README` sheet lists data-volume headlines but does not contain revenue, expense or profit totals. This project README records the clean-ledger headline for the 18 supplied months (April 2025 through September 2026) so the dashboard has an explicit comparison point. It is calculated from active detail accounts only; group headings are excluded.

| P&L line | 18-month value |
|---|---:|
| Revenue (accounts 4001-4004) | INR 1,259,204,600.00 |
| Other income (account 4900) | INR 1,725,452.00 |
| Operating expenses (detail expense accounts) | INR 1,036,246,464.42 |
| Net profit | INR 224,683,587.58 |
| Operating margin (net profit / revenue) | 17.84% |

Revenue plus other income less operating expenses equals net profit. The monthly P&L views are independently reconciled to the supplied PQ-09 ledger answer key; see [Phase 3 validation](docs/phase3_validation.md).

## Phase 3: money and insight

Phase 3 adds a detail-account-safe P&L and expense analysis, client receivables and cash movement, a department-month impact view, review-labelled anomaly and forecast charts, and an eight-metric executive scorecard. The department comparison aggregates each source before joining and records the exact differences caused by privacy suppression and quarantined task rows. Client payment-speed averages include every client with a paid invoice; low sample counts remain visible.

`python scripts/verify_phase3.py` checks the task-specific totals against the supplied PQ-09 and PQ-13 keys, verifies ageing and client-day calculations, and records when forecast accuracy cannot be estimated. The data snapshot ends on 30 September 2026; a new source period is required to move the cutoff forward.

## Phase 4: release day

Phase 4 hardens the application for repeatable release: exact dependency pins, a Python 3.11 scheduled workflow, one-command PDF and Excel packs, a role-aware KPI explorer, a documented five-metric API, privacy break tests, clean-machine evidence, release notes and final submission artifacts. `python scripts/verify_phase4.py` checks the release configuration and produces `docs/phase4_validation.md`.

Four demo roles are available locally: `ADMIN`, `HR`, `MANAGER` and `EXECUTIVE`. Role scope and minimum-group suppression are applied before explorer results are displayed. The public training deployment contains aggregate fictional data; secrets belong only in the hosting platform's secret store. See [privacy and role break tests](docs/privacy_break_tests.md).

## Monthly management pack

The PDF report builder uses the latest observed month by default or accepts a month such as `2026-09`:

```powershell
python scripts/build_monthly_pack.py --month 2026-09
```

Build the companion Excel snapshot from governed metric and audit views with:

```powershell
python scripts/build_monthly_excel.py --month 2026-09
```

Both packs default to the latest observed workforce month when `--month` is omitted. The Excel file includes nine summary and supporting sheets. The September 2026 outputs label the data cutoff and source limitations. They do not present forecast values as actuals. A recurring hosted export still needs a host and a changing source feed.

## Container package

`Dockerfile` and `docker-compose.yml` package the warehouse, dashboard and API. The Compose setup requires production login secrets from the shell environment. See [deployment notes](docs/deployment.md).

## Scheduled refresh and monthly packs

`.github/workflows/monthly-refresh.yml` rebuilds the warehouse, runs the tests and acceptance checks, then creates a PDF and Excel pack. It runs monthly, on demand, and when source CSVs or pipeline code change. A source-data change on `main` also causes Streamlit Community Cloud to redeploy the app, which rebuilds the warehouse on cold start. The supplied dataset is a fixed training snapshot ending 2026-09-30; a scheduled run cannot advance that cutoff without a new source feed.

## Project evidence

- [Task acceptance matrix](docs/task_acceptance_matrix.md)
- [Phase 2 validation evidence](docs/phase2_validation.md)
- [Phase 1 report](docs/phase1_report.md)
- [Validation results](docs/validation_results.md)
- [Deployment runbook](docs/deployment.md)
- [Board demo script](docs/board_demo_script.md)
- [Phase 4 validation](docs/phase4_validation.md)
- [API guide](docs/api.md)
- [Release notes](RELEASE_NOTES.md)

## Local deliverables

- Phase 1 evidence report: `output/pdf/DataAnalytics_Aditya_Mergurwar_Phase1_Report.pdf`
- Phase 2 evidence report: `output/pdf/DataAnalytics_Aditya_Mergurwar_Phase2_Report.pdf`
- Phase 3 evidence report: `output/pdf/DataAnalytics_Aditya_Mergurwar_Phase3_Report.pdf`
- Phase 4 evidence report: `output/pdf/DataAnalytics_Aditya_Mergurwar_Phase4_Report.pdf`
- Consolidated final report: `output/pdf/DataAnalytics_Aditya_Mergurwar_Consolidated_Report.pdf`
- September management pack: `output/pdf/PulseIQ_Monthly_Pack_2026-09.pdf`
- Nine-sheet Excel snapshot: `outputs/pulseiq-monthly/PulseIQ_Monthly_Pack_2026-09.xlsx`
- Nine-slide board briefing: `output/pptx/PulseIQ_Board_Pack_September_2026.pptx`
- Live dashboard screenshot evidence: `output/evidence/PulseIQ_Live_Dashboard_2026-10-22.png`

## Release status

The [public pulseiq repository](https://github.com/adityamergurwar/pulseiq) contains all four phases. The Streamlit dashboard is deployed at [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app). The `v1.0.0`, `phase-4` and release-candidate tags identify the final and pre-release checkpoints. The fixed training snapshot ends on 2026-09-30; scheduled refreshes rebuild and validate the supplied data but require a new source feed to advance the cutoff. See the [acceptance matrix](docs/task_acceptance_matrix.md) and [deployment runbook](docs/deployment.md) for exact evidence.
