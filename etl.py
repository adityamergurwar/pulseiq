"""One-command, rerunnable PulseIQ data build with row-level audit evidence."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from pulseiq.metrics import create_metric_views
from pulseiq.quality import run_quality_checks

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "03_Data" / "csv"
DB = Path(__import__("os").environ.get("PULSEIQ_DB_PATH", ROOT / "pulseiq.duckdb"))

CONTRACT_FEEDS = {
    "fact_anomaly": "AI anomaly results (fact_anomaly)",
    "fact_attrition_risk": "AI attrition risk (fact_attrition_risk)",
    "fact_forecast": "AI forecast (fact_forecast)",
    "fact_task": "Task board (fact_task)",
}
PRIMARY_KEYS = {
    "dim_account": ["account_code"], "dim_client": ["client_id"], "dim_date": ["date_key"],
    "dim_department": ["department_id"], "dim_employee": ["employee_key"],
    "dim_leave_type": ["leave_type_code"], "dim_location": ["work_location"],
    "dim_role": ["role_id"], "dim_sprint": ["sprint_id"], "dim_team": ["team_id"],
    "dim_vendor": ["vendor_id"], "fact_anomaly": ["result_id"],
    "fact_attendance_monthly": ["attendance_fact_id"], "fact_attrition_risk": ["prediction_id"],
    "fact_expense": ["expense_id"], "fact_forecast": ["forecast_id"],
    "fact_headcount_monthly": ["date_key", "department_id"],
    "fact_invoice_payment": ["payment_id"], "fact_invoice": ["invoice_id"],
    "fact_leave": ["leave_request_id"], "fact_ledger": ["line_id"],
    "fact_payroll": ["payroll_item_id"], "fact_task": ["task_id"],
}
WAREHOUSE_TABLES = sorted((*PRIMARY_KEYS.keys(),))


def qid(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return isinstance(value, str) and not value.strip()


def serializable(value: Any) -> Any:
    if is_blank(value):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def load_contracts(data_dir: Path = DATA) -> dict[str, list[dict[str, str]]]:
    output: dict[str, list[dict[str, str]]] = {}
    with (data_dir / "data_contracts.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            output.setdefault(row["feed"], []).append(row)
    return output


def _expected_type(kind: str) -> str:
    kind = str(kind).strip().lower()
    if kind == "integer":
        return "integer"
    if kind == "decimal":
        return "decimal"
    if kind == "date":
        return "date"
    if kind == "timestamp":
        return "timestamp"
    return "text"


def _valid_type(value: Any, kind: str) -> bool:
    kind = _expected_type(kind)
    if kind == "text":
        return True
    if kind == "integer":
        try:
            return float(value).is_integer()
        except (ValueError, TypeError, OverflowError):
            return False
    if kind == "decimal":
        try:
            float(value)
            return True
        except (ValueError, TypeError, OverflowError):
            return False
    if kind == "date":
        if isinstance(value, (date, datetime, pd.Timestamp)):
            return True
        try:
            datetime.fromisoformat(str(value)[:10])
            return True
        except ValueError:
            return False
    if kind == "timestamp":
        if isinstance(value, (datetime, pd.Timestamp)):
            return True
        try:
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    return True


def _contract_issues(table: str, row: dict[str, Any], columns: list[str], contracts: dict) -> list[str]:
    feed = CONTRACT_FEEDS.get(table)
    rules = contracts.get(feed, []) if feed else []
    issues: list[str] = []
    for spec in rules:
        col = spec["column_name"]
        targets = [f"top_reason_{i}" for i in (1, 2, 3)] if col == "top_reason_1..3" else [col]
        for target in targets:
            if target not in columns:
                issues.append(f"missing contract column {target}")
                continue
            value = row.get(target)
            blank = is_blank(value)
            nullable = str(spec["nullable"]).strip().lower() in {"yes", "y", "true", "1"}
            if blank:
                if not nullable:
                    issues.append(f"{target} is required")
                continue
            kind = spec["data_type"].strip().lower()
            if not _valid_type(value, kind):
                issues.append(f"{target} violates {spec['data_type']}")
                continue
            rule = spec["rule_or_allowed_values"].strip()
            low_rule = rule.lower()
            sval = str(value).strip()
            if low_rule == "0 to 1" and not 0 <= float(value) <= 1:
                issues.append(f"{target} must be between 0 and 1")
            elif low_rule.startswith(">= 0") and float(value) < 0:
                issues.append(f"{target} must be >= 0")
            elif "<= forecast_value" in low_rule and float(value) > float(row["forecast_value"]):
                issues.append(f"{target} exceeds forecast_value")
            elif ">= forecast_value" in low_rule and float(value) < float(row["forecast_value"]):
                issues.append(f"{target} below forecast_value")
            elif low_rule in {"y or n", "y/n"} and sval not in {"Y", "N"}:
                issues.append(f"{target} must be Y or N")
            elif "|" in rule and not low_rule.startswith(("exists in", "month end")):
                allowed = {part.strip() for part in rule.split("|")}
                if sval not in allowed:
                    issues.append(f"{target} not in allowed values")
            elif "an-nnnn" in low_rule and not re.fullmatch(r"AN-\d{4}", sval):
                issues.append(f"{target} must match AN-nnnn")
            elif "ar-nnnn" in low_rule and not re.fullmatch(r"AR-\d{4}", sval):
                issues.append(f"{target} must match AR-nnnn")
            elif "fc-nnnn" in low_rule and not re.fullmatch(r"FC-\d{4}", sval):
                issues.append(f"{target} must match FC-nnnn")
            elif "task-nnnnn" in low_rule and not re.fullmatch(r"TASK-\d{5}", sval):
                issues.append(f"{target} must match TASK-nnnnn")
            elif low_rule.startswith("1,2,3,5") and int(float(value)) not in {1, 2, 3, 5, 8, 13}:
                issues.append(f"{target} must be a Fibonacci story point")
            elif low_rule == "p1..p4" and sval not in {"P1", "P2", "P3", "P4"}:
                issues.append(f"{target} must be P1 to P4")
    if table == "fact_task":
        created, started, completed, status = (row.get(c) for c in ("created_date", "started_date", "completed_date", "status"))
        if not any(is_blank(v) for v in (created, started)) and created > started:
            issues.append("created_date must not follow started_date")
        if is_blank(started) and status != "To Do":
            issues.append("started_date may be blank only for To Do")
        if status == "Done" and is_blank(completed):
            issues.append("completed_date is required for Done tasks")
        if not any(is_blank(v) for v in (started, completed)) and completed < started:
            issues.append("completed_date must not precede started_date")
    return list(dict.fromkeys(issues))


def _read_dictionary(con) -> dict[str, dict[str, dict[str, Any]]]:
    if not con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='raw' AND table_name='data_dictionary'").fetchone()[0]:
        return {}
    rows = con.execute("SELECT sheet,\"column\",data_type FROM raw.data_dictionary").fetchall()
    output: dict[str, dict[str, dict[str, Any]]] = {}
    for sheet, column, kind in rows:
        required = False
        if con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='raw' AND table_name=?",[sheet]).fetchone()[0]:
            actual_nulls=con.execute(f"SELECT COUNT(*) FROM raw.{qid(sheet)} WHERE {qid(column)} IS NULL").fetchone()[0]
            required = actual_nulls == 0
        output.setdefault(sheet, {})[column] = {"data_type": kind, "required": required}
    return output


def _row_schema_issues(row: dict[str, Any], specs: dict[str, dict[str, Any]]) -> list[str]:
    issues = []
    for column, spec in specs.items():
        value = row.get(column)
        if is_blank(value):
            if spec["required"]:
                issues.append(f"{column} is required by the source dictionary")
            continue
        if not _valid_type(value, spec["data_type"]):
            issues.append(f"{column} violates source type {spec['data_type']}")
    return issues


def _schema_contracts(con, dictionary: dict[str, dict[str, dict[str, Any]]], source_columns: dict[str, list[str]]) -> None:
    con.execute("""CREATE OR REPLACE TABLE audit.schema_contract_results(
      table_name VARCHAR,column_name VARCHAR,expected_type VARCHAR,actual_type VARCHAR,
      nullable_expected BOOLEAN,actual_nulls BIGINT,status VARCHAR,detail VARCHAR)""")
    out=[]
    for table, specs in dictionary.items():
        if table not in source_columns or table not in PRIMARY_KEYS:
            continue
        actual_cols = set(source_columns[table])
        desc = {r[0]: r[1] for r in con.execute(f"DESCRIBE raw.{qid(table)}").fetchall()}
        missing = set(specs) - actual_cols
        for col, spec in specs.items():
            if col not in desc:
                out.append((table,col,str(spec['data_type']),None,not spec['required'],None,'FAIL','Expected column is absent'))
                continue
            nulls = int(con.execute(f"SELECT COUNT(*) FROM raw.{qid(table)} WHERE {qid(col)} IS NULL").fetchone()[0])
            status = 'PASS'
            detail = ''
            if spec['required'] and nulls:
                status,detail='FAIL',f'{nulls} null values in a required column'
            kind = _expected_type(spec['data_type'])
            cast_type = {'text':'VARCHAR','integer':'BIGINT','decimal':'DOUBLE','date':'DATE','timestamp':'TIMESTAMP'}[kind]
            value_sql = f"NULLIF(TRIM(CAST({qid(col)} AS VARCHAR)),'')"
            if kind == 'integer':
                invalid_expr=f"TRY_CAST({value_sql} AS DOUBLE) IS NULL OR TRY_CAST({value_sql} AS DOUBLE)<>FLOOR(TRY_CAST({value_sql} AS DOUBLE))"
            else:
                invalid_expr=f"TRY_CAST({value_sql} AS {cast_type}) IS NULL"
            invalid=int(con.execute(f"SELECT COUNT(*) FROM raw.{qid(table)} WHERE {value_sql} IS NOT NULL AND ({invalid_expr})").fetchone()[0]) if kind!='text' else 0
            if invalid:
                status = 'WARN' if status != 'FAIL' else status
                detail = (detail+'; ' if detail else '')+f'{invalid} nonblank values fail {spec["data_type"]} parsing; rows are quarantined'
            out.append((table,col,str(spec['data_type']),str(desc[col]),not spec['required'],nulls,status,detail))
        for col in sorted(actual_cols-set(specs)):
            out.append((table,col,None,str(desc[col]),True,None,'WARN','Unexpected column retained in raw/clean; review schema drift'))
    if out:
        con.executemany("INSERT INTO audit.schema_contract_results VALUES (?,?,?,?,?,?,?,?)",out)


def _create_audit_tables(con) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw; CREATE SCHEMA IF NOT EXISTS clean; CREATE SCHEMA IF NOT EXISTS warehouse; CREATE SCHEMA IF NOT EXISTS metrics; CREATE SCHEMA IF NOT EXISTS audit")
    con.execute("""CREATE TABLE IF NOT EXISTS audit.quarantine(
      run_id VARCHAR,source_table VARCHAR,source_row BIGINT,row_json JSON,reason VARCHAR)""")
    con.execute("""CREATE TABLE IF NOT EXISTS audit.etl_run_log(
      run_id VARCHAR,started_at TIMESTAMPTZ,finished_at TIMESTAMPTZ,status VARCHAR,error VARCHAR)""")


def _add_unknown_employee(con) -> None:
    cols = [r[0] for r in con.execute("DESCRIBE warehouse.dim_employee").fetchall()]
    types = {r[0]: r[1] for r in con.execute("DESCRIBE warehouse.dim_employee").fetchall()}
    values=[]
    for col in cols:
        if col == "employee_key": values.append("-1")
        elif col == "employee_id": values.append("'UNKNOWN'")
        elif col == "full_name": values.append("'Unknown employee'")
        elif col == "valid_from": values.append("DATE '1900-01-01'")
        elif col == "valid_to": values.append("DATE '9999-12-31'")
        elif col == "is_current": values.append("'Y'")
        elif col == "employment_status": values.append("'Unknown'")
        elif col == "employment_type": values.append("'Unknown'")
        elif col == "work_mode": values.append("'Unknown'")
        elif types[col] in {"VARCHAR", "JSON"}: values.append("NULL")
        else: values.append("NULL")
    con.execute(f"INSERT INTO warehouse.dim_employee ({','.join(map(qid,cols))}) VALUES ({','.join(values)})")


def _extend_forecast_calendar(con) -> None:
    last_key = int(con.execute("SELECT MAX(forecast_month_key) FROM clean.fact_forecast").fetchone()[0])
    max_date = con.execute("SELECT MAX(date) FROM warehouse.dim_date").fetchone()[0]
    if max_date is None:
        return
    # Add calendar dates only when forecast keys require them. Source dimensions stay unchanged.
    max_needed = con.execute("SELECT MAX(forecast_month_key) FROM clean.fact_forecast").fetchone()[0]
    if max_needed is None:
        return
    needed_date = datetime.strptime(str(max_needed), "%Y%m%d").date()
    if needed_date <= max_date:
        return
    con.execute("""INSERT INTO warehouse.dim_date
      SELECT CAST(d AS DATE) AS date,CAST(strftime(d,'%Y%m%d') AS BIGINT) AS date_key,
        year(d) AS year,quarter(d) AS quarter,month(d) AS month_number,
        strftime(d,'%B') AS month_name,strftime(d,'%Y-%m') AS year_month,
        weekofyear(d) AS week_of_year,strftime(d,'%A') AS day_of_week,
        CASE WHEN dayofweek(d) IN (0,6) THEN 'Y' ELSE 'N' END AS is_weekend,
        'N' AS is_holiday,CASE WHEN dayofweek(d) IN (0,6) THEN 'N' ELSE 'Y' END AS is_working_day,
        CASE WHEN month(d)>=4 THEN 'FY'||year(d)||'-'||right(CAST(year(d)+1 AS VARCHAR),2)
             ELSE 'FY'||(year(d)-1)||'-'||right(CAST(year(d) AS VARCHAR),2) END AS financial_year,
        'Q'||CAST(CASE WHEN month(d)>=4 THEN ((month(d)-4)//3)+1 ELSE ((month(d)+8)//3)+1 END AS VARCHAR) AS fiscal_quarter,
        ((month(d)+8)%12)+1 AS fiscal_month_number,
        CASE WHEN d=last_day(d) THEN 'Y' ELSE 'N' END AS is_month_end,
        CAST(date_trunc('month',d) AS DATE) AS month_start_date,last_day(d) AS month_end_date
      FROM generate_series(?::DATE,?::DATE,INTERVAL 1 DAY) g(d)
      WHERE CAST(strftime(d,'%Y%m%d') AS BIGINT) NOT IN (SELECT date_key FROM warehouse.dim_date)""", [max_date + pd.Timedelta(days=1), needed_date])


def build_warehouse(con) -> None:
    for table, keys in PRIMARY_KEYS.items():
        if not con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='clean' AND table_name=?",[table]).fetchone()[0]:
            continue
        desc = con.execute(f"DESCRIBE clean.{qid(table)}").fetchall()
        definitions = ",".join(f"{qid(c)} {typ}" for c,typ,*_ in desc)
        key_sql = ",".join(qid(k) for k in keys)
        con.execute(f"CREATE OR REPLACE TABLE warehouse.{qid(table)} ({definitions},PRIMARY KEY ({key_sql}))")
        con.execute(f"INSERT INTO warehouse.{qid(table)} SELECT * FROM clean.{qid(table)}")

    # The supplied ledger has one explicitly identified, balanced payroll posting
    # that is overstated by INR 18,450 on both sides of the journal entry.
    # Correct it in the conformed warehouse and retain raw.fact_ledger unchanged.
    corrections = [
        ("JL-005614", "debit", 19891524.18, 19873074.18,
         "DQ-04: reduce the D01 salary debit by INR 18,450; raw ledger retained."),
        ("JL-005614", "signed_amount_debit_positive", 19891524.18, 19873074.18,
         "DQ-04: reduce the D01 salary debit by INR 18,450; raw ledger retained."),
        ("JL-005643", "credit", 47061928.45, 47043478.45,
         "DQ-04: reduce the offsetting payroll payable credit by INR 18,450; raw ledger retained."),
        ("JL-005643", "signed_amount_debit_positive", -47061928.45, -47043478.45,
         "DQ-04: reduce the offsetting payroll payable credit by INR 18,450; raw ledger retained."),
    ]
    for line_id, field, source_value, corrected_value, _ in corrections:
        actual = con.execute(f"SELECT {qid(field)} FROM raw.fact_ledger WHERE line_id=?", [line_id]).fetchall()
        if len(actual) != 1 or abs(float(actual[0][0])-source_value)>0.005:
            raise RuntimeError(f"Ledger correction precondition failed for {line_id}.{field}; inspect source drift")
    con.execute("""CREATE OR REPLACE TABLE audit.ledger_corrections(
      line_id VARCHAR,field_name VARCHAR,source_value DOUBLE,corrected_value DOUBLE,reason VARCHAR)""")
    con.executemany("INSERT INTO audit.ledger_corrections VALUES (?,?,?,?,?)",corrections)
    con.execute("""UPDATE warehouse.fact_ledger SET debit=debit-18450.00,
      signed_amount_debit_positive=signed_amount_debit_positive-18450.00 WHERE line_id='JL-005614'""")
    con.execute("""UPDATE warehouse.fact_ledger SET credit=credit-18450.00,
      signed_amount_debit_positive=signed_amount_debit_positive+18450.00 WHERE line_id='JL-005643'""")

    # Preserve source effective dates in clean and record the deterministic SCD repair in warehouse.
    con.execute("""CREATE OR REPLACE TABLE audit.scd_repairs AS
      WITH versions AS (
        SELECT employee_key,employee_id,valid_to,
          LEAD(valid_from) OVER(PARTITION BY employee_id ORDER BY valid_from,employee_key) AS next_valid_from
        FROM clean.dim_employee
      ) SELECT employee_key,employee_id,valid_to AS source_valid_to,
        CAST(next_valid_from-INTERVAL 1 DAY AS DATE) AS repaired_valid_to,
        'Closed overlap one day before the next effective version; clean source retained.' AS reason
      FROM versions WHERE next_valid_from IS NOT NULL AND valid_to>=next_valid_from""")
    con.execute("""UPDATE warehouse.dim_employee AS e SET valid_to=r.repaired_valid_to
      FROM audit.scd_repairs r WHERE e.employee_key=r.employee_key""")

    _add_unknown_employee(con)
    for table in ("fact_payroll", "fact_attendance_monthly", "fact_leave", "fact_attrition_risk"):
        if con.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='warehouse' AND table_name='{table}'").fetchone()[0]:
            con.execute(f"""UPDATE warehouse.{table} AS f SET employee_key=-1
              WHERE NOT EXISTS(SELECT 1 FROM warehouse.dim_employee e WHERE e.employee_key=f.employee_key)""")
    if con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='warehouse' AND table_name='fact_task'").fetchone()[0]:
        con.execute("ALTER TABLE warehouse.fact_task ADD COLUMN employee_key BIGINT")
        con.execute("""UPDATE warehouse.fact_task AS t SET employee_key=COALESCE((
          SELECT e.employee_key FROM warehouse.dim_employee e
          WHERE e.employee_id=t.assignee_employee_id AND e.employee_id<>'UNKNOWN'
            AND e.valid_from<=COALESCE(t.completed_date,t.started_date,t.created_date)
            AND e.valid_to>=COALESCE(t.completed_date,t.started_date,t.created_date)
          ORDER BY e.valid_from DESC,e.employee_key DESC LIMIT 1),-1)""")
    if con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='warehouse' AND table_name='fact_anomaly'").fetchone()[0]:
        con.execute("ALTER TABLE warehouse.fact_anomaly ADD COLUMN employee_key BIGINT")
        con.execute("""UPDATE warehouse.fact_anomaly AS a SET employee_key=COALESCE((
          SELECT e.employee_key FROM warehouse.dim_employee e
          WHERE e.employee_id=a.employee_id AND e.employee_id<>'UNKNOWN'
            AND e.valid_from<=last_day(a.period) AND e.valid_to>=last_day(a.period)
          ORDER BY e.valid_from DESC,e.employee_key DESC LIMIT 1),-1)""")
    _extend_forecast_calendar(con)
    con.execute("""CREATE OR REPLACE VIEW audit.payroll_ledger_reconciliation_clean AS
      WITH p AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) AS period,SUM(employer_cost) AS payroll_cost
                 FROM clean.fact_payroll GROUP BY 1),
      l AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
                 SUM(signed_amount_debit_positive) AS ledger_payroll_cost FROM warehouse.fact_ledger
          WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5005 GROUP BY 1)
      SELECT COALESCE(p.period,l.period) AS period,p.payroll_cost,l.ledger_payroll_cost,
        COALESCE(p.payroll_cost,0)-COALESCE(l.ledger_payroll_cost,0) AS difference,
        CASE WHEN ABS(COALESCE(p.payroll_cost,0)-COALESCE(l.ledger_payroll_cost,0))<=0.01 THEN 'PASS' ELSE 'FAIL' END AS status
      FROM p FULL OUTER JOIN l USING(period)""")

    joins = [
      ("fact_payroll","employee_key","dim_employee","employee_key"),("fact_payroll","date_key","dim_date","date_key"),("fact_payroll","department_id","dim_department","department_id"),("fact_payroll","role_id","dim_role","role_id"),
      ("fact_attendance_monthly","employee_key","dim_employee","employee_key"),("fact_attendance_monthly","date_key","dim_date","date_key"),("fact_attendance_monthly","department_id","dim_department","department_id"),
      ("fact_leave","employee_key","dim_employee","employee_key"),("fact_leave","leave_type_code","dim_leave_type","leave_type_code"),("fact_leave","start_date_key","dim_date","date_key"),("fact_leave","end_date_key","dim_date","date_key"),
      ("fact_headcount_monthly","department_id","dim_department","department_id"),("fact_headcount_monthly","date_key","dim_date","date_key"),
      ("fact_ledger","account_code","dim_account","account_code"),("fact_ledger","cost_center_department_id","dim_department","department_id"),("fact_ledger","date_key","dim_date","date_key"),
      ("fact_invoice","client_id","dim_client","client_id"),("fact_invoice","service_line_account","dim_account","account_code"),("fact_invoice","invoice_date_key","dim_date","date_key"),
      ("fact_invoice_payment","invoice_id","fact_invoice","invoice_id"),("fact_invoice_payment","payment_date_key","dim_date","date_key"),
      ("fact_expense","vendor_id","dim_vendor","vendor_id"),("fact_expense","category_account","dim_account","account_code"),("fact_expense","department_id","dim_department","department_id"),("fact_expense","expense_date_key","dim_date","date_key"),
      ("fact_task","team_id","dim_team","team_id"),("fact_task","sprint_id","dim_sprint","sprint_id"),("fact_task","employee_key","dim_employee","employee_key"),
      ("fact_anomaly","employee_key","dim_employee","employee_key"),("fact_anomaly","period_key","dim_date","date_key"),
      ("fact_attrition_risk","employee_key","dim_employee","employee_key"),("fact_attrition_risk","department_id","dim_department","department_id"),("fact_attrition_risk","as_of_date_key","dim_date","date_key"),
      ("fact_forecast","department_id","dim_department","department_id"),("fact_forecast","forecast_month_key","dim_date","date_key"),
    ]
    out=[]
    for fact,fk,dim,dk in joins:
        special = f" AND f.{qid(fk)}<>'ALL'" if fact=='fact_forecast' and fk=='department_id' else ""
        query=f"""SELECT COUNT(*) FROM warehouse.{qid(fact)} f LEFT JOIN warehouse.{qid(dim)} d
          ON f.{qid(fk)}=d.{qid(dk)} WHERE f.{qid(fk)} IS NOT NULL AND d.{qid(dk)} IS NULL{special}"""
        count=int(con.execute(query).fetchone()[0])
        out.append((fact,f"{fk} -> {dim}.{dk}",count,"No unmatched keys" if count==0 else "unresolved; see row-level result"))
    con.execute("""CREATE OR REPLACE TABLE audit.orphan_results(
      fact_table VARCHAR,relationship VARCHAR,orphan_rows BIGINT,disposition VARCHAR)""")
    con.executemany("INSERT INTO audit.orphan_results VALUES (?,?,?,?)",out)


def run(data_dir: Path = DATA, db_path: Path = DB, fail_on_critical: bool = False) -> int:
    if not data_dir.exists():
        raise FileNotFoundError(f"Expected CSV bundle at {data_dir}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    con = duckdb.connect(str(db_path))
    _create_audit_tables(con)
    con.execute("INSERT INTO audit.etl_run_log(run_id,started_at,status) VALUES (?,?, 'RUNNING')", [run_id,started])
    try:
        contracts = load_contracts(data_dir)
        source_files = sorted(data_dir.glob("*.csv"))
        if not source_files:
            raise FileNotFoundError(f"No CSV files found in {data_dir}")
        source_columns: dict[str,list[str]] = {}
        for path in source_files:
            table = path.stem
            con.execute(f"CREATE OR REPLACE TABLE raw.{qid(table)} AS SELECT * FROM read_csv_auto(?,header=true,all_varchar=false,sample_size=-1)", [str(path)])
            source_columns[table] = [r[0] for r in con.execute(f"DESCRIBE raw.{qid(table)}").fetchall()]

        dictionary = _read_dictionary(con)
        _schema_contracts(con,dictionary,source_columns)
        for row in con.execute("SELECT table_name,column_name,status,detail FROM audit.schema_contract_results WHERE status='FAIL'").fetchall():
            raise RuntimeError(f"Schema contract failed for {row[0]}.{row[1]}: {row[3]}")

        payroll_employee_ids={str(x[0]) for x in con.execute("SELECT employee_id FROM raw.dim_employee").fetchall()}
        employee_exit_dates={int(k):v for k,v in con.execute("SELECT employee_key,exit_date FROM raw.dim_employee WHERE exit_date IS NOT NULL").fetchall()}
        seen_payroll_runs=set()
        con.execute("CREATE OR REPLACE TABLE audit.load_summary(run_id VARCHAR,table_name VARCHAR,rows_in BIGINT,rows_passed BIGINT,rows_quarantined BIGINT,run_at TIMESTAMPTZ)")
        load_rows=[]
        for path in source_files:
            table=path.stem
            cols=source_columns[table]
            rows=con.execute(f"SELECT * FROM raw.{qid(table)}").fetchdf().to_dict("records")
            specs=dictionary.get(table,{})
            pk=PRIMARY_KEYS.get(table,[])
            seen=set(); passed_ids=[]; rejected=[]
            for row_no,row in enumerate(rows,1):
                issues=_row_schema_issues(row,specs)
                issues.extend(_contract_issues(table,row,cols,contracts))
                if table=="fact_payroll":
                    employee_id=str(row.get("employee_id")) if not is_blank(row.get("employee_id")) else ""
                    if employee_id not in payroll_employee_ids:
                        issues.append(f"employee_id {employee_id or '<blank>'} has no matching dim_employee row")
                    run_key=(employee_id,str(row.get("run_id")))
                    if run_key in seen_payroll_runs:
                        issues.append(f"duplicate employee_id/run_id payroll row {run_key}")
                    else:
                        seen_payroll_runs.add(run_key)
                if table=="fact_attendance_monthly":
                    employee_key=row.get("employee_key")
                    period_end=row.get("period_end_date")
                    exit_date=employee_exit_dates.get(int(employee_key)) if not is_blank(employee_key) else None
                    if exit_date is not None and not is_blank(period_end):
                        period_start=date(period_end.year,period_end.month,1)
                        exit_month=date(exit_date.year,exit_date.month,1)
                        if period_start>exit_month:
                            issues.append(f"attendance period {period_start} begins after employee exit month {exit_month}")
                if pk:
                    key=tuple(serializable(row.get(c)) for c in pk)
                    if key in seen:
                        issues.append(f"duplicate primary key {key}")
                    else:
                        seen.add(key)
                if issues:
                    rejected.append((row_no,row,"; ".join(dict.fromkeys(issues))))
                else:
                    passed_ids.append(row_no)
            if rejected:
                con.register("_accepted_rows",pd.DataFrame({"source_row":passed_ids}))
                col_list=','.join(f"r.{qid(c)}" for c in cols)
                con.execute(f"""CREATE OR REPLACE TABLE clean.{qid(table)} AS
                  WITH numbered AS (SELECT *,ROW_NUMBER() OVER() AS _source_row FROM raw.{qid(table)})
                  SELECT {col_list} FROM numbered r JOIN _accepted_rows p ON r._source_row=p.source_row""")
                con.unregister("_accepted_rows")
            else:
                con.execute(f"CREATE OR REPLACE TABLE clean.{qid(table)} AS SELECT * FROM raw.{qid(table)}")
            for row_no,row,reason in rejected:
                safe={key:serializable(value) for key,value in row.items()}
                con.execute("INSERT INTO audit.quarantine VALUES (?,?,?,?,?)",[run_id,table,row_no,json.dumps(safe,default=str),reason])
            load_rows.append((run_id,table,len(rows),len(passed_ids),len(rejected),started))
        if load_rows:
            con.executemany("INSERT INTO audit.load_summary VALUES (?,?,?,?,?,?)",load_rows)

        build_warehouse(con)
        create_metric_views(con)
        con.execute("UPDATE audit.etl_run_log SET finished_at=?,status='SUCCESS' WHERE run_id=?",[datetime.now(timezone.utc),run_id])
        dq=run_quality_checks(con,run_id)
        con.execute("CREATE OR REPLACE VIEW audit.release_gate AS SELECT CASE WHEN COUNT(*) FILTER(WHERE status='FAIL')=0 THEN 'PASS' ELSE 'REVIEW REQUIRED' END AS status, COUNT(*) FILTER(WHERE status='FAIL') AS critical_checks_failed FROM audit.dq_results WHERE run_id=(SELECT run_id FROM audit.dq_results ORDER BY run_at DESC LIMIT 1)")

        print("table                              rows_in   passed   quarantined   reconcile")
        for _,table,rows_in,passed,quarantined,_ in load_rows:
            status='OK' if rows_in==passed+quarantined else 'ERROR'
            print(f"{table:<34} {rows_in:>8} {passed:>8} {quarantined:>13}   {status}")
        print("\nData-quality summary (known source issues are retained and listed)")
        print("check_id  table_name                         status  affected groups/rows")
        for item in dq:
            print(f"{item['check_id']:<9} {item['table_name']:<35} {item['status']:<7} {item['bad_rows']}")
        print("\nWarehouse relationship audit")
        for fact,relationship,orphans,disposition in con.execute("SELECT * FROM audit.orphan_results ORDER BY fact_table,relationship").fetchall():
            print(f"{fact}.{relationship}: {orphans} orphans ({disposition})")
        print(f"\nRelease gate: {con.execute('SELECT status FROM audit.release_gate').fetchone()[0]}")
        print(f"Database: {db_path}")
        critical=int(con.execute("SELECT COUNT(*) FROM audit.dq_results WHERE run_id=? AND severity='Critical' AND status='FAIL'",[run_id]).fetchone()[0])
        con.close()
        if fail_on_critical and critical:
            raise SystemExit(f"{critical} critical DQ check(s) failed; see audit.dq_check_details")
        return 0
    except Exception as error:
        try:
            con.execute("UPDATE audit.etl_run_log SET finished_at=?,status='FAILED',error=? WHERE run_id=?",[datetime.now(timezone.utc),str(error),run_id])
            con.close()
        except Exception:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Refresh PulseIQ raw, clean, warehouse, metrics and quality layers")
    parser.add_argument("--data-dir",type=Path,default=DATA)
    parser.add_argument("--db",type=Path,default=DB)
    parser.add_argument("--fail-on-critical",action="store_true",help="return a failing exit code when critical source-quality checks have findings")
    args=parser.parse_args(argv)
    return run(args.data_dir,args.db,args.fail_on_critical)


if __name__ == "__main__":
    sys.exit(main())
