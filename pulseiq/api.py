"""Read-only, aggregate-only API for five governed metrics.

Run with: uvicorn pulseiq.api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import hmac
import os
import re
import calendar
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
from fastapi import Depends, FastAPI, Header, HTTPException, Query

from .app_common import DB_PATH, ROOT

API_METRICS = {
    "M01": ("m01_headcount", "month-start"),
    "M04": ("m04_attrition_monthly", "month-start"),
    "M09": ("m09_payroll_cost", "month-start"),
    "M20": ("m20_dso", "month-end"),
    "M22": ("dashboard_task_completion_monthly", "month-start-rollup"),
}

app = FastAPI(
    title="PulseIQ Analytics API",
    version="1.0.0",
    description="Read-only aggregates from the governed PulseIQ metric layer. No employee-level endpoints are exposed.",
)


def _connect():
    if not DB_PATH.exists():
        data_dir=ROOT / "03_Data" / "csv"
        if not data_dir.exists():
            raise HTTPException(status_code=503, detail="Warehouse is not built and source data is unavailable.")
        try:
            import etl
            etl.run(data_dir=data_dir,db_path=DB_PATH)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Warehouse refresh failed: {type(exc).__name__}.") from exc
    return duckdb.connect(str(DB_PATH),read_only=True)


def check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    configured=os.environ.get("PULSEIQ_API_KEY","")
    required=os.environ.get("PULSEIQ_REQUIRE_LOGIN","0").strip()=="1"
    if required and not configured:
        raise HTTPException(status_code=503,detail="API key authentication is enabled but PULSEIQ_API_KEY is not configured.")
    if configured and (x_api_key is None or not hmac.compare_digest(x_api_key,configured)):
        raise HTTPException(status_code=401,detail="A valid API key is required.")
    if required and not configured:
        raise HTTPException(status_code=503,detail="API authentication is not configured.")


@app.get("/health", tags=["system"])
def health() -> dict[str, Any]:
    return {"status":"ok" if DB_PATH.exists() else "warehouse_missing","read_only":True}


@app.get("/api/metrics", tags=["metrics"], dependencies=[Depends(check_api_key)])
def list_metrics() -> dict[str, Any]:
    with _connect() as con:
        ids=list(API_METRICS)
        rows=con.execute(
            "SELECT metric_id,metric_name,business_definition,formula,source_table,grain,time_period,owner_team,unit,good_direction,caveat,minimum_group_size FROM metrics.metric_catalog WHERE metric_id IN (?,?,?,?,?) ORDER BY metric_id",
            ids,
        ).fetchdf()
        freshness=con.execute("SELECT data_cutoff,last_successful_refresh,status FROM metrics.dashboard_data_freshness").fetchdf()
    return {"metrics":rows.to_dict(orient="records"),"freshness":freshness.iloc[0].to_dict() if not freshness.empty else None,
            "privacy":"Aggregate metrics only; small groups follow the metric dictionary minimum size."}


@app.get("/api/metrics/{metric_id}", tags=["metrics"], dependencies=[Depends(check_api_key)])
def get_metric(
    metric_id: str,
    period: str = Query(...,description="Month in YYYY-MM format"),
    department_id: str = Query("ALL",description="ALL or an approved department identifier"),
) -> dict[str, Any]:
    metric_id=metric_id.upper()
    if metric_id not in API_METRICS:
        raise HTTPException(status_code=404,detail="Metric is not exposed by this API.")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])",period):
        raise HTTPException(status_code=422,detail="period must use YYYY-MM format.")
    try:
        y,m=map(int,period.split("-")); first=date(y,m,1)
        last=date(y,m,calendar.monthrange(y,m)[1])
    except ValueError as exc:
        raise HTTPException(status_code=422,detail="period is not a valid calendar month.") from exc
    view,grain=API_METRICS[metric_id]
    with _connect() as con:
        allowed={x[0] for x in con.execute("SELECT department_id FROM clean.dim_department").fetchall()}
        if department_id!="ALL" and department_id not in allowed:
            raise HTTPException(status_code=422,detail="Unknown department_id.")
        catalog=con.execute("SELECT metric_name,business_definition,formula,source_table,grain,owner_team,unit,good_direction,caveat,minimum_group_size FROM metrics.metric_catalog WHERE metric_id=?",[metric_id]).fetchone()
        if not catalog:
            raise HTTPException(status_code=503,detail="Metric catalog entry is missing.")
        if metric_id=="M20":
            row=con.execute(f"SELECT period,value FROM metrics.{view} WHERE period=?",[last]).fetchone()
        elif metric_id=="M22":
            row=con.execute(f"SELECT period,value FROM metrics.{view} WHERE period=? AND department_id=?",[first,department_id]).fetchone()
        else:
            row=con.execute(f"SELECT period,value FROM metrics.{view} WHERE period=? AND department_id=?",[first,department_id]).fetchone()
        freshness=con.execute("SELECT data_cutoff,last_successful_refresh,status FROM metrics.dashboard_data_freshness").fetchone()
    if not row:
        raise HTTPException(status_code=404,detail="No metric value is available for that period and scope.")
    keys=["metric_name","business_definition","formula","source_table","grain","owner_team","unit","good_direction","caveat","minimum_group_size"]
    definition=dict(zip(keys,catalog))
    return {"metric_id":metric_id,"metric":definition,"period":str(row[0]),"period_requested":period,
            "department_id":department_id,"value":row[1],"rollup_grain":grain,
            "data_cutoff":str(freshness[0]) if freshness and freshness[0] else None,
            "last_successful_refresh":str(freshness[1]) if freshness and freshness[1] else None,
            "freshness_status":freshness[2] if freshness else "unknown",
            "privacy":"Aggregate only; no employee-level data is returned."}
