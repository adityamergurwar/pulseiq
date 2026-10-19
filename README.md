# Aura Workforce PulseIQ · Phase 1

Foundation project for the fictional Zenith Nova workforce dataset. The project keeps the supplied CSVs as immutable bronze inputs, validates contracted feeds, builds clean and warehouse schemas, records quarantines and runs a quality report.

## Quick start

Python 3.11+ is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python etl.py
streamlit run app.py
```

The pipeline reads `03_Data/csv/`, creates `pulseiq.duckdb`, and prints row reconciliation and 14 DQ checks. It is safe to rerun: source tables and derived layers are replaced as a complete refresh; the quarantine and run logs retain audit history. Contract rules are present for `fact_anomaly`, `fact_attrition_risk`, `fact_forecast`, and `fact_task`; other feed contracts will be added when the source contract sheet provides them. The ETL applies supplied type, requiredness, allowed-value, range and identifier-format rules, and fails on missing contracted columns. Unexpected source columns are currently retained in raw/clean and surfaced for review rather than dropped.

## Data layers

- `raw`: exact CSV import; treated as immutable source evidence.
- `clean`: contract-passing rows. Failed contracted rows are preserved in `audit.quarantine` with source row and a reason.
- `warehouse`: source dimensions and facts, retaining `employee_key` so department history is interpreted as of the relevant month.
- `metrics`: 28 governed `mNN_*` views, dashboard views and `metric_catalog`.
- `audit`: `load_summary`, `dq_results`, `orphan_results`, `quarantine`, and ETL run log.

## Notes and evidence

- [Star schema and join map](docs/star_schema.md)
- [Contract notes for three tables](docs/contract_notes.md)
- [Quality checks and decisions](docs/data_quality.md)
- [Phase 1 report draft](docs/phase1_report.md)

The report draft intentionally leaves your name, repository URL, tag, screenshots, and personal learning reflection as placeholders. The supplied starter's workbook README/data dictionary is distributed as `03_Data/PulseIQ_Dataset.xlsx`; the CSV extracts and dictionaries are included in the repository for convenient use.

## Scope and known limits

The current source `data_contracts.csv` defines only four feed contracts. Several DQ catalog rules refer to names from an earlier schema; `etl.py` maps the 14 checks to the actual delivered columns and records their bad-row counts. `DQ-C01` is a reconciliation count, and `DQ-C13` evaluates the latest run log. Finance and dashboard outputs should be reviewed against the official validation key after each task is completed.

No GitHub repository is created or published from this local workspace. Once you create the private `pulseiq` repository, add its URL and your identity to the report, then push and tag the finished work. The validation-vault answer files have not yet been consulted; compare them after a successful pipeline run as the vault directs.
