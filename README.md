# Aura Workforce PulseIQ

PulseIQ is a workforce and finance analytics product for the fictional Zenith Nova Technologies dataset. It contains a repeatable DuckDB pipeline, an auditable clean layer, a star-schema warehouse, 28 governed metrics, 12 Streamlit pages, a five-metric FastAPI service, validation evidence and monthly report builders.

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
```

Run the metric API in another terminal:

```powershell
uvicorn pulseiq.api:app --host 127.0.0.1 --port 8000
```

The OpenAPI UI is at `http://127.0.0.1:8000/docs`. The API exposes M01, M04, M09, M20 and M22 with definitions, lineage, data cutoff and privacy metadata.

## Dashboards

The Streamlit app includes workforce, attendance and leave, attrition, team productivity, payroll and cost, budget and KPI targets, P&L and expenses, receivables and cash, department impact, forecasts and anomalies, executive scorecard, KPI builder, and data quality and lineage.

The local demo persona selector is a role simulation, not authentication. For a hosted deployment set `PULSEIQ_REQUIRE_LOGIN=1` and provide password hashes through the host secret `PULSEIQ_USERS_JSON`. See [deployment notes](docs/deployment.md); never commit secrets.

## Data and metric contracts

- `raw` retains the supplied CSV values.
- `clean` applies data-dictionary type/nullability rules, specialized contracts and row-level dispositions.
- `warehouse` holds conformed dimensions and facts, with employee history joined by `employee_key`.
- `metrics` owns M01-M28 and dashboard-safe aggregate views.
- `audit` records row counts, quarantine reasons, quality findings, relationship checks, corrections and ETL runs.

The supplied `data_contracts.csv` defines additional value/range/format rules for four feeds. The source dictionary provides schema and nullability checks for 297 columns across 23 operational dimension/fact tables. Unexpected columns are retained and logged for schema review. See [contract notes](docs/contract_notes.md), [star schema](docs/star_schema.md), [metric lineage](docs/lineage.md), and [quality results](docs/validation_results.md).

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

## Project evidence

- [Task acceptance matrix](docs/task_acceptance_matrix.md)
- [Phase 1 report](docs/phase1_report.md)
- [Validation results](docs/validation_results.md)
- [Deployment runbook](docs/deployment.md)
- [Board demo script](docs/board_demo_script.md)
- [Release notes](docs/release_notes.md)

## Local deliverables

- Phase 1 evidence report: `output/pdf/DataAnalytics_Aditya_Mergurwar_Phase1_Report.pdf`
- September management pack: `output/pdf/PulseIQ_Monthly_Pack_2026-09.pdf`
- Nine-sheet Excel snapshot: `outputs/pulseiq-monthly/PulseIQ_Monthly_Pack_2026-09.xlsx`
- Nine-slide board briefing: `output/pptx/PulseIQ_Board_Pack_September_2026.pptx`

## Release status

The project runs locally and the local acceptance checks pass. The requested private [pulseiq repository](https://github.com/adityamergurwar/pulseiq) is the publication target; its push and `phase-1` tag are pending. There is no public dashboard URL, hosted refresh schedule, or recorded demo yet. Public release also requires an owner to review the seeded raw-data findings and configure production login secrets. The exact items still needing the project owner's account or personal input are listed in the acceptance matrix.
