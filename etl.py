"""Repeatable PulseIQ load, contract validation, warehouse build and DQ run."""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "03_Data" / "csv"
DB = ROOT / "pulseiq.duckdb"
CONTRACT_FEEDS = {
    "fact_anomaly": "AI anomaly results (fact_anomaly)",
    "fact_attrition_risk": "AI attrition risk (fact_attrition_risk)",
    "fact_forecast": "AI forecast (fact_forecast)",
    "fact_task": "Task board (fact_task)",
}


def qid(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def load_contracts():
    contracts = {}
    with (DATA / "data_contracts.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            contracts.setdefault(row["feed"], []).append(row)
    return contracts


def validate_table(table: str, rows: list[dict], columns: list[str], contracts: dict):
    feed = CONTRACT_FEEDS.get(table)
    rules = {r["column_name"]: r for r in contracts.get(feed, [])} if feed else {}
    if not rules:
        return rows, []
    reasons, passed = [], []
    for n, row in enumerate(rows, start=1):
        issues = []
        for col, spec in rules.items():
            if col not in columns and ".." not in col:
                issues.append(f"missing contract column {col}"); continue
            targets = [f"top_reason_{i}" for i in (1, 2, 3)] if col == "top_reason_1..3" else [col]
            for target in targets:
                val = row.get(target)
                blank = val is None or str(val).strip() == ""
                if blank and spec["nullable"].lower() == "no":
                    issues.append(f"{target} is required"); continue
                if blank: continue
                typ = spec["data_type"].lower()
                try:
                    if typ in ("int", "integer"):
                        if not float(val).is_integer(): raise ValueError("not integral")
                        int(float(val))
                    elif "decimal" in typ or typ in ("float", "numeric"):
                        float(val)
                    elif typ == "date":
                        datetime.fromisoformat(str(val)[:10])
                    elif typ == "timestamp":
                        datetime.fromisoformat(str(val).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    issues.append(f"{target} violates {spec['data_type']}"); continue
                rule = spec["rule_or_allowed_values"].lower()
                if "0 to 1" in rule and not 0 <= float(val) <= 1: issues.append(f"{target} must be between 0 and 1")
                elif rule.startswith(">= 0") and float(val) < 0: issues.append(f"{target} must be >= 0")
                elif rule.startswith("<= forecast_value") and float(val) > float(row["forecast_value"]): issues.append(f"{target} exceeds forecast_value")
                elif rule.startswith(">= forecast_value") and float(val) < float(row["forecast_value"]): issues.append(f"{target} below forecast_value")
                elif " | " in rule and rule.split(" | ")[0] not in ("Y", "N"):
                    allowed = {x.strip() for x in re.split(r"\s*\|\s*", spec["rule_or_allowed_values"]) if x.strip()}
                    if str(val) not in allowed and not rule.startswith("exists in") and not rule.startswith("month end"):
                        issues.append(f"{target} not in allowed values")
                elif "an-nnnn" in rule and not re.fullmatch(r"AN-\d{4}", str(val)): issues.append(f"{target} must match AN-nnnn")
                elif "ar-nnnn" in rule and not re.fullmatch(r"AR-\d{4}", str(val)): issues.append(f"{target} must match AR-nnnn")
                elif "fc-nnnn" in rule and not re.fullmatch(r"FC-\d{4}", str(val)): issues.append(f"{target} must match FC-nnnn")
                elif "task-nnnnn" in rule and not re.fullmatch(r"TASK-\d{5}", str(val)): issues.append(f"{target} must match TASK-nnnnn")
                elif rule == "y or n" and str(val) not in {"Y", "N"}: issues.append(f"{target} must be Y or N")
                elif rule.startswith("1,2,3,5") and int(float(val)) not in {1,2,3,5,8,13}: issues.append(f"{target} must be a Fibonacci story point")
                elif rule == "p1..p4" and str(val) not in {"P1","P2","P3","P4"}: issues.append(f"{target} must be P1 to P4")
        if table == "fact_task":
            if row.get("started_date") and row.get("created_date") and row["created_date"] > row["started_date"]: issues.append("created_date must not follow started_date")
            if row.get("started_date") in (None, "") and row.get("status") != "To Do": issues.append("started_date may be blank only for To Do")
            if row.get("status") == "Done" and not row.get("completed_date"): issues.append("completed_date is required for Done tasks")
            if row.get("started_date") and row.get("completed_date") and row["completed_date"] < row["started_date"]: issues.append("completed_date must not precede started_date")
        if issues: reasons.append((n, row, "; ".join(issues)))
        else: passed.append(row)
    # Uniqueness is a feed-level promise for the declared identifier.
    unique_cols = [c for c, spec in rules.items() if "unique" in spec["rule_or_allowed_values"].lower()]
    passed_ids = {id(row) for row in passed}
    unique_reasons = {}
    for col in unique_cols:
        seen = set()
        for n, row in enumerate(rows, start=1):
            val = row.get(col)
            if val in seen and id(row) in passed_ids:
                unique_reasons.setdefault(n, []).append(f"{col} duplicates {val}")
            seen.add(val)
    for n, row in enumerate(rows, start=1):
        if n in unique_reasons: reasons.append((n, row, "; ".join(unique_reasons[n])))
    if unique_reasons:
        duplicate_ids = {id(rows[n-1]) for n in unique_reasons}
        passed = [row for row in passed if id(row) not in duplicate_ids]
    return passed, reasons


def build_views(con):
    # Governed views follow the supplied metric dictionary and expose a consistent date/department grain when defined.
    sql = {
      "m01_headcount": "SELECT month_start_date, department_id, headcount_end AS value FROM clean.fact_headcount_monthly WHERE headcount_end>=5 UNION ALL SELECT month_start_date, 'ALL' AS department_id, SUM(headcount_end) AS value FROM clean.fact_headcount_monthly GROUP BY 1",
      "m02_hires": "SELECT h.month_start_date, h.department_id, h.hires AS value FROM clean.fact_headcount_monthly h WHERE h.headcount_end>=5 UNION ALL SELECT month_start_date, 'ALL' AS department_id, SUM(hires) AS value FROM clean.fact_headcount_monthly GROUP BY 1",
      "m03_exits": "SELECT h.month_start_date, h.department_id, h.exits AS value FROM clean.fact_headcount_monthly h WHERE h.headcount_end>=5 UNION ALL SELECT month_start_date, 'ALL' AS department_id, SUM(exits) AS value FROM clean.fact_headcount_monthly GROUP BY 1",
      "m04_attrition_monthly": "SELECT month_start_date, department_id, attrition_rate_monthly_pct AS value FROM clean.fact_headcount_monthly WHERE headcount_end>=10 UNION ALL SELECT month_start_date, 'ALL' AS department_id, 100.0*SUM(exits)/NULLIF(SUM(headcount_start),0) AS value FROM clean.fact_headcount_monthly GROUP BY 1",
      "m05_attrition_rolling_12m": "SELECT month_start_date, department_id, 100.0 * SUM(exits) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) / NULLIF(AVG(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW),0) AS value FROM clean.fact_headcount_monthly QUALIFY AVG(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)>=10",
      "m06_voluntary_attrition": "SELECT month_start_date, department_id, 100.0 * SUM(voluntary_exits) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) / NULLIF(AVG(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW),0) AS value FROM clean.fact_headcount_monthly QUALIFY AVG(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)>=10",
      "m07_gross_pay": "SELECT period_end_date AS month, department_id, SUM(gross_pay) AS value FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m08_net_pay": "SELECT period_end_date AS month, department_id, SUM(net_pay) AS value FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m09_payroll_cost": "SELECT period_end_date AS month, department_id, SUM(employer_cost) AS value FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m10_cost_per_head": "SELECT period_end_date AS month, department_id, SUM(employer_cost)/NULLIF(COUNT(DISTINCT employee_id),0) AS value FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m11_overtime_share": "SELECT period_end_date AS month, department_id, 100.0*SUM(overtime_pay)/NULLIF(SUM(employer_cost),0) AS value FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m12_variable_pay_share": "SELECT period_end_date AS month, department_id, 100.0*SUM(variable_pay)/NULLIF(SUM(gross_pay),0) AS value FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m13_attendance_rate": "SELECT period_end_date AS month, department_id, (SUM(present_days)+0.5*SUM(half_days_unpaid))/NULLIF(SUM(scheduled_days),0) AS value FROM clean.fact_attendance_monthly GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m14_late_arrival_rate": "SELECT period_end_date AS month, department_id, SUM(late_arrivals)/NULLIF(SUM(present_days),0) AS value FROM clean.fact_attendance_monthly GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m15_lop_days": "SELECT period_end_date AS month, department_id, SUM(lop_days) AS value FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id)>=5",
      "m16_revenue": "SELECT CAST(date_trunc('month',entry_date) AS DATE) AS month, -SUM(signed_amount_debit_positive) AS value FROM clean.fact_ledger WHERE account_code BETWEEN '4001' AND '4004' GROUP BY 1",
      "m17_net_profit": "SELECT CAST(date_trunc('month',entry_date) AS DATE) AS month, -SUM(signed_amount_debit_positive) AS value FROM clean.fact_ledger WHERE account_code LIKE '4%' OR account_code LIKE '5%' GROUP BY 1",
      "m18_operating_margin": "SELECT CAST(date_trunc('month',entry_date) AS DATE) AS month, -100.0*SUM(CASE WHEN account_code LIKE '4%' OR account_code LIKE '5%' THEN signed_amount_debit_positive ELSE 0 END)/NULLIF(-SUM(CASE WHEN account_code BETWEEN '4001' AND '4004' THEN signed_amount_debit_positive ELSE 0 END),0) AS value FROM clean.fact_ledger GROUP BY 1",
      "m19_payroll_pct_revenue": "SELECT p.month, 100.0*p.cost/NULLIF(r.revenue,0) AS value FROM (SELECT CAST(date_trunc('month',entry_date) AS DATE) month, -SUM(signed_amount_debit_positive) cost FROM clean.fact_ledger WHERE account_code BETWEEN '5001' AND '5005' GROUP BY 1) p JOIN (SELECT CAST(date_trunc('month',entry_date) AS DATE) month, -SUM(signed_amount_debit_positive) revenue FROM clean.fact_ledger WHERE account_code BETWEEN '4001' AND '4004' GROUP BY 1) r USING(month)",
      "m20_dso": "WITH months AS (SELECT month_end_date AS month FROM clean.dim_date WHERE is_month_end='Y' GROUP BY 1), ar AS (SELECT m.month, SUM(GREATEST(i.total_amount-COALESCE((SELECT SUM(p.amount) FROM clean.fact_invoice_payment p WHERE p.invoice_id=i.invoice_id AND p.payment_date<=m.month),0),0)) AS receivables FROM months m JOIN clean.fact_invoice i ON i.invoice_date<=m.month AND i.status NOT IN ('DRAFT','CANCELLED') GROUP BY 1), sales AS (SELECT m.month, SUM(i.total_amount) AS sales_90d FROM months m JOIN clean.fact_invoice i ON i.invoice_date<=m.month AND i.invoice_date>m.month-INTERVAL 90 DAY AND i.status NOT IN ('DRAFT','CANCELLED') GROUP BY 1) SELECT ar.month, 90.0*ar.receivables/NULLIF(sales.sales_90d,0) AS value FROM ar JOIN sales USING(month)",
      "m21_overdue_receivables": "WITH months AS (SELECT month_end_date AS month FROM clean.dim_date WHERE is_month_end='Y' GROUP BY 1) SELECT m.month, SUM(GREATEST(i.total_amount-COALESCE((SELECT SUM(p.amount) FROM clean.fact_invoice_payment p WHERE p.invoice_id=i.invoice_id AND p.payment_date<=m.month),0),0)) AS value FROM months m JOIN clean.fact_invoice i ON i.due_date<m.month AND i.invoice_date<=m.month AND i.status NOT IN ('DRAFT','CANCELLED') GROUP BY 1",
      "m22_task_completion": "SELECT s.sprint_id, t.team_id, 100.0*COUNT(*) FILTER(WHERE t.status='Done')/NULLIF(COUNT(*) FILTER(WHERE t.status!='Cancelled'),0) AS value FROM clean.fact_task t JOIN clean.dim_sprint s USING(sprint_id) GROUP BY 1,2 HAVING COUNT(*) FILTER(WHERE t.status!='Cancelled')>=5",
      "m23_on_time_delivery": "SELECT sprint_id, team_id, 100.0*COUNT(*) FILTER(WHERE completed_on_time='Y')/NULLIF(COUNT(*) FILTER(WHERE status='Done'),0) AS value FROM clean.fact_task GROUP BY 1,2 HAVING COUNT(*) FILTER(WHERE status='Done')>=5",
      "m24_velocity": "SELECT sprint_id, team_id, SUM(story_points) FILTER(WHERE status='Done') AS value FROM clean.fact_task GROUP BY 1,2",
      "m25_cycle_time": "SELECT sprint_id, team_id, AVG(cycle_time_days) FILTER(WHERE status='Done') AS value FROM clean.fact_task GROUP BY 1,2 HAVING COUNT(*) FILTER(WHERE status='Done')>=5",
       "m26_anomaly_flag_rate": "SELECT source_dataset, CAST(date_trunc('month',period) AS DATE) AS month, 100.0*AVG(CASE WHEN flagged='Y' THEN 1.0 ELSE 0 END) AS value FROM clean.fact_anomaly GROUP BY 1,2",
      "m27_high_risk_share": "SELECT department_id, 100.0*AVG(CASE WHEN risk_band='High' THEN 1.0 ELSE 0 END) AS value FROM clean.fact_attrition_risk GROUP BY 1 HAVING COUNT(DISTINCT employee_id)>=10",
      "m28_forecast_error": "SELECT f.department_id, f.forecast_month, AVG(CASE WHEN f.metric='headcount_end' THEN ABS(f.forecast_value-h.headcount_end)/NULLIF(h.headcount_end,0) ELSE ABS(f.forecast_value-h.attrition_rate_monthly_pct)/NULLIF(h.attrition_rate_monthly_pct,0) END)*100 AS value FROM clean.fact_forecast f JOIN clean.fact_headcount_monthly h ON f.department_id=h.department_id AND f.forecast_month=h.month_start_date GROUP BY 1,2",
    }
    for name, query in sql.items():
        con.execute(f"CREATE OR REPLACE VIEW metrics.{name} AS {query}")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_department_mix AS
        SELECT h.month_start_date, h.department_id, d.department_name, h.headcount_end AS value
        FROM clean.fact_headcount_monthly h JOIN clean.dim_department d USING(department_id)
        WHERE h.department_id <> 'D00' AND h.headcount_end >= 5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_location_tier AS
        WITH snapshot AS (SELECT month_start_date, CAST(month_start_date + INTERVAL 1 MONTH - INTERVAL 1 DAY AS DATE) month_end FROM clean.fact_headcount_monthly GROUP BY 1), people AS (
          SELECT s.month_start_date,e.department_id,e.employee_id,l.city_tier AS label FROM snapshot s JOIN clean.dim_employee e ON CAST(e.valid_from AS DATE)<=s.month_end AND CAST(e.valid_to AS DATE)>=s.month_end JOIN clean.dim_location l ON l.work_location=e.work_location WHERE e.department_id<>'D00')
        SELECT month_start_date,department_id,label,COUNT(DISTINCT employee_id) value FROM people GROUP BY 1,2,3 HAVING COUNT(DISTINCT employee_id)>=5
        UNION ALL SELECT month_start_date,'ALL' AS department_id,label,COUNT(DISTINCT employee_id) value FROM people GROUP BY 1,3 HAVING COUNT(DISTINCT employee_id)>=5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_work_mode AS
        WITH snapshot AS (SELECT month_start_date, CAST(month_start_date + INTERVAL 1 MONTH - INTERVAL 1 DAY AS DATE) month_end FROM clean.fact_headcount_monthly GROUP BY 1), people AS (
          SELECT s.month_start_date,e.department_id,e.employee_id,e.work_mode AS label FROM snapshot s JOIN clean.dim_employee e ON CAST(e.valid_from AS DATE)<=s.month_end AND CAST(e.valid_to AS DATE)>=s.month_end WHERE e.department_id<>'D00')
        SELECT month_start_date,department_id,label,COUNT(DISTINCT employee_id) value FROM people GROUP BY 1,2,3 HAVING COUNT(DISTINCT employee_id)>=5
        UNION ALL SELECT month_start_date,'ALL' AS department_id,label,COUNT(DISTINCT employee_id) value FROM people GROUP BY 1,3 HAVING COUNT(DISTINCT employee_id)>=5""")
    con.execute("CREATE OR REPLACE VIEW metrics.metric_catalog AS SELECT metric_id, metric_name, business_definition, source_table, owner_team, minimum_group_size FROM raw.metric_dictionary")
    return sql


def run():
    if not DATA.exists(): raise FileNotFoundError(f"Expected CSV bundle at {DATA}")
    con = duckdb.connect(str(DB))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw; CREATE SCHEMA IF NOT EXISTS clean; CREATE SCHEMA IF NOT EXISTS warehouse; CREATE SCHEMA IF NOT EXISTS metrics; CREATE SCHEMA IF NOT EXISTS audit")
    contracts = load_contracts()
    results = []
    run_id = datetime.now(timezone.utc).isoformat()
    for path in sorted(DATA.glob("*.csv")):
        table = path.stem
        if table == "data_contracts":
            con.execute(f"CREATE OR REPLACE TABLE raw.{qid(table)} AS SELECT * FROM read_csv_auto(?, header=true)", [str(path)])
            continue
        con.execute(f"CREATE OR REPLACE TABLE raw.{qid(table)} AS SELECT * FROM read_csv_auto(?, header=true, all_varchar=false)", [str(path)])
        rows = con.execute(f"SELECT * FROM raw.{qid(table)}").fetchdf().to_dict("records")
        columns = [r[0] for r in con.execute(f"DESCRIBE raw.{qid(table)}").fetchall()]
        feed = CONTRACT_FEEDS.get(table)
        if feed:
            expected = {r["column_name"] for r in contracts.get(feed, []) if ".." not in r["column_name"]}
            if "top_reason_1..3" in {r["column_name"] for r in contracts.get(feed, [])}:
                expected.update({"top_reason_1", "top_reason_2", "top_reason_3"})
            missing = sorted(expected - set(columns))
            if missing: raise RuntimeError(f"{table} is missing contracted columns: {', '.join(missing)}")
        passed, rejected = validate_table(table, rows, columns, contracts)
        if feed:
            contracted_columns = {r["column_name"] for r in contracts.get(feed, []) if ".." not in r["column_name"]}
            if "top_reason_1..3" in {r["column_name"] for r in contracts.get(feed, [])}:
                contracted_columns.update({"top_reason_1", "top_reason_2", "top_reason_3"})
            unexpected = sorted(set(columns) - contracted_columns)
            if unexpected: print(f"WARNING {table}: unexpected columns retained for review: {', '.join(unexpected)}")
        fk_specs = {
            "fact_task": [("team_id","dim_team","team_id"),("sprint_id","dim_sprint","sprint_id"),("assignee_employee_id","dim_employee","employee_id")],
            "fact_attrition_risk": [("employee_id","dim_employee","employee_id"),("department_id","dim_department","department_id")],
            "fact_forecast": [("department_id","dim_department","department_id")],
            "fact_anomaly": [("employee_id","dim_employee","employee_id")],
        }
        fk_columns = fk_specs.get(table, [])
        if fk_columns:
            pass_ids = {id(row) for row in passed}
            fk_bad = []
            new_passed = []
            known_by_column = {}
            for col, dim_table, dim_col in fk_columns:
                known = {str(v[0]) for v in con.execute(f"SELECT {qid(dim_col)} FROM raw.{qid(dim_table)}").fetchall()}
                if table == "fact_forecast" and col == "department_id": known.add("ALL")
                known_by_column[col] = (known, dim_table, dim_col)
            sprint_ends = {}
            if table == "fact_task":
                sprint_ends = {str(sid): str(end)[:10] for sid,end in con.execute("SELECT sprint_id,end_date FROM raw.dim_sprint").fetchall()}
            for row_no, row in enumerate(rows, start=1):
                if id(row) not in pass_ids: continue
                missing = [(col, dim_table, dim_col) for col,(known,dim_table,dim_col) in known_by_column.items() if str(row.get(col)) not in known]
                if missing:
                    col, dim_table, dim_col = missing[0]
                    fk_bad.append((row_no,row,f"{col} {row.get(col)} has no match in {dim_table}.{dim_col}"))
                elif table == "fact_task" and str(row.get("due_date"))[:10] != sprint_ends.get(str(row.get("sprint_id"))):
                    fk_bad.append((row_no,row,"due_date must match the sprint end date"))
                else: new_passed.append(row)
            rejected.extend(fk_bad)
            passed=new_passed
        # All tables are materialized to clean; contract failures are excluded. Uncontracted tables pass through unchanged.
        con.execute(f"CREATE OR REPLACE TABLE clean.{qid(table)} AS SELECT * FROM raw.{qid(table)}")
        if rejected:
            con.register("_passed_rows", __import__('pandas').DataFrame(passed, columns=columns))
            con.execute(f"CREATE OR REPLACE TABLE clean.{qid(table)} AS SELECT * FROM _passed_rows")
            con.unregister("_passed_rows")
        for row_no, row, reason in rejected:
            con.execute("INSERT INTO audit.quarantine SELECT ?, ?, ?, ?, ?", [run_id, table, row_no, json.dumps(row, default=str), reason]) if con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='audit' AND table_name='quarantine'").fetchone()[0] else con.execute("CREATE TABLE audit.quarantine(run_id VARCHAR, source_table VARCHAR, source_row BIGINT, row_json JSON, reason VARCHAR)")
            if con.execute("SELECT COUNT(*) FROM audit.quarantine WHERE run_id=? AND source_table=? AND source_row=?", [run_id,table,row_no]).fetchone()[0] == 0:
                con.execute("INSERT INTO audit.quarantine VALUES (?, ?, ?, ?, ?)", [run_id, table, row_no, json.dumps(row, default=str), reason])
        results.append((table, len(rows), len(passed), len(rejected)))
    con.execute("CREATE TABLE IF NOT EXISTS audit.quarantine(run_id VARCHAR, source_table VARCHAR, source_row BIGINT, row_json JSON, reason VARCHAR)")
    con.execute("CREATE OR REPLACE TABLE audit.load_summary AS SELECT * FROM (VALUES " + ",".join("(?,?,?,?)" for _ in results) + ") t(table_name, rows_in, rows_passed, rows_quarantined)", [v for row in results for v in row])
    # Star-schema base: preserve source keys, and retain employee surrogate history for month-correct joins.
    primary_keys = {
      "dim_account": ["account_code"], "dim_client": ["client_id"], "dim_date": ["date_key"],
      "dim_department": ["department_id"], "dim_employee": ["employee_key"], "dim_leave_type": ["leave_type_code"],
      "dim_location": ["work_location"], "dim_role": ["role_id"], "dim_sprint": ["sprint_id"],
      "dim_team": ["team_id"], "dim_vendor": ["vendor_id"], "fact_anomaly": ["result_id"],
      "fact_attendance_monthly": ["attendance_fact_id"], "fact_attrition_risk": ["prediction_id"],
      "fact_expense": ["expense_id"], "fact_forecast": ["forecast_id"],
      "fact_headcount_monthly": ["date_key", "department_id"], "fact_invoice_payment": ["payment_id"],
      "fact_invoice": ["invoice_id"], "fact_leave": ["leave_request_id"], "fact_ledger": ["line_id"],
      "fact_payroll": ["payroll_item_id"], "fact_task": ["task_id"],
    }
    for t in [p.stem for p in DATA.glob("dim_*.csv")] + [p.stem for p in DATA.glob("fact_*.csv")]:
        desc = con.execute(f"DESCRIBE clean.{qid(t)}").fetchall()
        cols = ", ".join(f"{qid(col[0])} {col[1]}" for col in desc)
        pk = ", ".join(qid(col) for col in primary_keys[t])
        con.execute(f"CREATE OR REPLACE TABLE warehouse.{qid(t)} ({cols}, PRIMARY KEY ({pk}))")
        con.execute(f"INSERT INTO warehouse.{qid(t)} SELECT * FROM clean.{qid(t)}")
    build_views(con)
    joins = [
      ("fact_payroll","employee_key","dim_employee","employee_key"),("fact_payroll","date_key","dim_date","date_key"),("fact_payroll","department_id","dim_department","department_id"),("fact_payroll","role_id","dim_role","role_id"),
      ("fact_attendance_monthly","employee_key","dim_employee","employee_key"),("fact_attendance_monthly","date_key","dim_date","date_key"),("fact_attendance_monthly","department_id","dim_department","department_id"),
      ("fact_leave","employee_key","dim_employee","employee_key"),("fact_leave","leave_type_code","dim_leave_type","leave_type_code"),("fact_leave","start_date_key","dim_date","date_key"),("fact_leave","end_date_key","dim_date","date_key"),
      ("fact_headcount_monthly","department_id","dim_department","department_id"),("fact_headcount_monthly","date_key","dim_date","date_key"),
      ("fact_ledger","account_code","dim_account","account_code"),("fact_ledger","cost_center_department_id","dim_department","department_id"),("fact_ledger","date_key","dim_date","date_key"),
      ("fact_invoice","client_id","dim_client","client_id"),("fact_invoice","service_line_account","dim_account","account_code"),("fact_invoice","invoice_date_key","dim_date","date_key"),
      ("fact_invoice_payment","invoice_id","fact_invoice","invoice_id"),("fact_invoice_payment","payment_date_key","dim_date","date_key"),
      ("fact_expense","vendor_id","dim_vendor","vendor_id"),("fact_expense","category_account","dim_account","account_code"),("fact_expense","department_id","dim_department","department_id"),("fact_expense","expense_date_key","dim_date","date_key"),
      ("fact_task","team_id","dim_team","team_id"),("fact_task","sprint_id","dim_sprint","sprint_id"),("fact_task","assignee_employee_id","dim_employee","employee_id"),
      ("fact_anomaly","employee_id","dim_employee","employee_id"),("fact_anomaly","period_key","dim_date","date_key"),
      ("fact_attrition_risk","employee_key","dim_employee","employee_key"),("fact_attrition_risk","department_id","dim_department","department_id"),("fact_attrition_risk","as_of_date_key","dim_date","date_key"),
      ("fact_forecast","department_id","dim_department","department_id"),("fact_forecast","forecast_month_key","dim_date","date_key"),
    ]
    orphan_rows=[]
    for fact, fk, dim, dk in joins:
        special_scope = f" AND f.{qid(fk)} <> 'ALL'" if fact == "fact_forecast" and fk == "department_id" else ""
        query=f"SELECT COUNT(*) FROM clean.{qid(fact)} f LEFT JOIN clean.{qid(dim)} d ON f.{qid(fk)}=d.{qid(dk)} WHERE f.{qid(fk)} IS NOT NULL AND d.{qid(dk)} IS NULL{special_scope}"
        count=int(con.execute(query).fetchone()[0])
        orphan_rows.append((fact,f"{fk} -> {dim}.{dk}",count))
    con.execute("CREATE OR REPLACE TABLE audit.orphan_results(fact_table VARCHAR, relationship VARCHAR, orphan_rows BIGINT)")
    con.executemany("INSERT INTO audit.orphan_results VALUES (?,?,?)",orphan_rows)
    # 14 quality checks, implemented against actual bundle fields.
    checks = [
      ("DQ-C01","Payroll equals ledger","Critical","WITH p AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) m,SUM(employer_cost) v FROM clean.fact_payroll GROUP BY 1), l AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) m,-SUM(signed_amount_debit_positive) v FROM clean.fact_ledger WHERE account_code BETWEEN '5001' AND '5005' GROUP BY 1) SELECT COUNT(*) FROM p FULL OUTER JOIN l USING(m) WHERE ABS(COALESCE(p.v,0)-COALESCE(l.v,0))>0.01"),
      ("DQ-C02","Ledger balanced","Critical","SELECT COUNT(*) FROM (SELECT entry_id FROM clean.fact_ledger GROUP BY entry_id HAVING ABS(SUM(debit)-SUM(credit))>0.005)"),
      ("DQ-C03","Unique payroll rows","Critical","SELECT COUNT(*) FROM (SELECT employee_id,date_key FROM clean.fact_payroll GROUP BY 1,2 HAVING COUNT(*)>1)"),
      ("DQ-C04","No orphan employees","Critical","SELECT COUNT(*) FROM clean.fact_payroll p LEFT JOIN clean.dim_employee d USING(employee_id) WHERE d.employee_id IS NULL"),
      ("DQ-C05","No attendance after exit","Warning","SELECT COUNT(*) FROM clean.fact_attendance_monthly a JOIN clean.dim_employee d ON a.employee_key=d.employee_key WHERE d.exit_date IS NOT NULL AND a.period_end_date>CAST(d.exit_date AS DATE)"),
      ("DQ-C06","Unpaid leave deducted","Warning","SELECT COUNT(*) FROM (SELECT a.employee_id,a.period_end_date FROM clean.fact_attendance_monthly a LEFT JOIN clean.fact_payroll p USING(employee_id,period_end_date) WHERE a.unpaid_absence_days>0 AND COALESCE(p.lop_days,0)=0)"),
      ("DQ-C07","Invoice arithmetic","Warning","SELECT COUNT(*) FROM clean.fact_invoice WHERE amount_paid>total_amount OR balance_due<0"),
      ("DQ-C08","Expense arithmetic","Warning","SELECT COUNT(*) FROM clean.fact_expense WHERE ABS(total_amount-(amount_excl_gst+gst_amount))>0.01"),
      ("DQ-C09","Task dates sensible","Warning","SELECT COUNT(*) FROM clean.fact_task WHERE completed_date<started_date OR (status='Done' AND completed_date IS NULL)"),
      ("DQ-C10","Leave dates sensible","Warning","SELECT COUNT(*) FROM clean.fact_leave WHERE end_date<start_date"),
      ("DQ-C11","AI feeds are fresh","Warning","SELECT COUNT(*) FROM clean.fact_attrition_risk WHERE as_of_date < (SELECT MAX(as_of_date) FROM clean.fact_attrition_risk)-INTERVAL 7 DAY"),
      ("DQ-C12","Dimension history does not overlap","Critical","SELECT COUNT(*) FROM clean.dim_employee a JOIN clean.dim_employee b ON a.employee_id=b.employee_id AND a.employee_key<b.employee_key AND a.valid_to>=b.valid_from"),
      ("DQ-C13","Pipeline freshness","Critical","SELECT COUNT(*) FROM audit.etl_run_log WHERE finished_at < now()-INTERVAL 24 HOUR"),
      ("DQ-C14","Minimum group size","Critical","SELECT COUNT(*) FROM (SELECT value FROM metrics.dashboard_department_mix WHERE value<5 UNION ALL SELECT value FROM metrics.dashboard_location_tier WHERE value<5 UNION ALL SELECT value FROM metrics.dashboard_work_mode WHERE value<5)"),
    ]
    con.execute("CREATE TABLE IF NOT EXISTS audit.etl_run_log(finished_at TIMESTAMPTZ)")
    con.execute("INSERT INTO audit.etl_run_log VALUES (now())")
    out=[]
    for cid,name,severity,query in checks:
        bad=int(con.execute(query).fetchone()[0]); out.append((cid,name,severity,bad,"PASS" if bad==0 else ("FAIL" if severity=="Critical" else "WARN"),datetime.now(timezone.utc).isoformat()))
    con.execute("CREATE OR REPLACE TABLE audit.dq_results(check_id VARCHAR, check_name VARCHAR, severity VARCHAR, bad_rows BIGINT, status VARCHAR, run_at TIMESTAMPTZ)")
    con.executemany("INSERT INTO audit.dq_results VALUES (?,?,?,?,?,?)",out)
    print("table                         rows_in  passed  quarantined")
    for table,ins,passed,bad in results: print(f"{table:<30} {ins:>7} {passed:>7} {bad:>12}")
    print("\nDQ summary")
    for row in con.execute("SELECT check_id,check_name,bad_rows,status FROM audit.dq_results ORDER BY check_id").fetchall(): print(f"{row[0]} {row[1]}: {row[3]} ({row[2]} bad rows)")
    print("\nWarehouse orphan audit")
    for row in con.execute("SELECT fact_table, relationship, orphan_rows FROM audit.orphan_results WHERE orphan_rows>0 ORDER BY fact_table, relationship").fetchall(): print(f"{row[0]} {row[1]}: {row[2]} orphan rows")
    if not con.execute("SELECT COUNT(*) FROM audit.orphan_results WHERE orphan_rows>0").fetchone()[0]: print("No orphan keys found.")
    critical_failures = con.execute("SELECT COUNT(*) FROM audit.dq_results WHERE severity='Critical' AND status='FAIL'").fetchone()[0]
    print(f"\nDatabase: {DB}")
    con.close()
    if critical_failures: raise SystemExit(f"Load completed with {critical_failures} critical DQ failure(s); review audit.dq_results before release.")


if __name__ == "__main__":
    run()
