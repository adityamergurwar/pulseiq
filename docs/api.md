# PulseIQ metrics API

The FastAPI service exposes five governed, aggregate metrics. It returns the value, dictionary definition, formula, source, owner, data cutoff, last successful refresh and privacy statement. It does not expose employee rows.

## Public deployment

- Service: [pulseiq-metrics-api-fezs.onrender.com](https://pulseiq-metrics-api-fezs.onrender.com)
- Base URL: redirects browser visitors to the interactive OpenAPI documentation
- Health: [GET /health](https://pulseiq-metrics-api-fezs.onrender.com/health)
- Metric catalog: [GET /api/metrics](https://pulseiq-metrics-api-fezs.onrender.com/api/metrics)
- Interactive OpenAPI: [/docs](https://pulseiq-metrics-api-fezs.onrender.com/docs)

The Render free service may need a short cold-start delay after inactivity. The public release was checked on 19 November 2026: health returned HTTP 200, the catalog listed all five metrics, and M01, M04, M09, M20 and M22 returned governed September 2026 results with definitions, source, cutoff and freshness metadata.

## Start locally

```powershell
python etl.py
uvicorn pulseiq.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI interface.

## Endpoints

- `GET /health`
- `GET /api/metrics`
- `GET /api/metrics/{metric_id}?period=YYYY-MM&department_id=ALL`

The exposed metric IDs are M01 headcount, M04 monthly attrition, M09 employer payroll cost, M20 days sales outstanding and M22 task completion.

## Examples

```powershell
curl "http://127.0.0.1:8000/api/metrics/M01?period=2026-09&department_id=ALL"
curl "http://127.0.0.1:8000/api/metrics/M20?period=2026-09&department_id=ALL"
curl "https://pulseiq-metrics-api-fezs.onrender.com/api/metrics/M01?period=2026-09&department_id=ALL"
```

An M01 response includes this contract:

```json
{
  "metric_id": "M01",
  "period_requested": "2026-09",
  "department_id": "ALL",
  "value": 441,
  "metric": {
    "metric_name": "Headcount",
    "business_definition": "Active employees at month end",
    "source_table": "fact_headcount_monthly"
  },
  "data_cutoff": "2026-09-30",
  "freshness_status": "CURRENT",
  "privacy": "Aggregate only; no employee-level data is returned."
}
```

Unknown metric IDs, invalid months and unknown departments return HTTP 4xx responses. Set `PULSEIQ_API_KEY` in the service secret store to require the `X-API-Key` header. The repository includes `render.yaml` and `Dockerfile.api` for a second GitHub-backed service because Streamlit Community Cloud hosts the dashboard process only.

