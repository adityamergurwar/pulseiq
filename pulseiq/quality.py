"""Run the supplied fourteen checks as row-level, auditable DQ results."""
from __future__ import annotations

from datetime import datetime, timezone


CHECKS = [
    ("DQ-C01", "Payroll equals ledger", "fact_payroll + fact_ledger", "Critical", """
      WITH p AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) AS period,SUM(employer_cost) AS amount
                 FROM raw.fact_payroll GROUP BY 1),
      l AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
                   SUM(signed_amount_debit_positive) AS amount FROM raw.fact_ledger
            WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5005 GROUP BY 1)
      SELECT COALESCE(CAST(p.period AS VARCHAR),CAST(l.period AS VARCHAR)) AS record_key,
             'Payroll='||ROUND(COALESCE(p.amount,0),2)||'; ledger='||ROUND(COALESCE(l.amount,0),2) AS detail
      FROM p FULL OUTER JOIN l USING(period) WHERE ABS(COALESCE(p.amount,0)-COALESCE(l.amount,0))>0.01"""),
    ("DQ-C02", "Ledger entries balance", "fact_ledger", "Critical", """
      SELECT entry_id AS record_key,'debits='||ROUND(SUM(debit),2)||'; credits='||ROUND(SUM(credit),2) AS detail
      FROM raw.fact_ledger GROUP BY entry_id HAVING ABS(SUM(debit)-SUM(credit))>0.005"""),
    ("DQ-C03", "No duplicate employee payroll month", "fact_payroll", "Critical", """
      SELECT employee_id||'|'||run_id AS record_key,
             'payroll lines='||COUNT(*) AS detail FROM raw.fact_payroll
      GROUP BY employee_id,run_id HAVING COUNT(*)>1"""),
    ("DQ-C04", "Payroll employees resolve to a person", "fact_payroll", "Critical", """
      SELECT p.payroll_item_id AS record_key,'employee_id='||p.employee_id AS detail
      FROM raw.fact_payroll p LEFT JOIN raw.dim_employee e USING(employee_id)
      WHERE e.employee_id IS NULL"""),
    ("DQ-C05", "Attendance does not follow employee exit", "fact_attendance_monthly", "Warning", """
      SELECT a.attendance_fact_id AS record_key,'period='||CAST(a.period_end_date AS VARCHAR)||
        '; exit='||CAST(e.exit_date AS VARCHAR) AS detail
      FROM raw.fact_attendance_monthly a JOIN raw.dim_employee e ON e.employee_key=a.employee_key
      WHERE e.exit_date IS NOT NULL
        AND date_trunc('month',a.period_end_date)>date_trunc('month',CAST(e.exit_date AS DATE))"""),
    ("DQ-C06", "Unpaid absence has payroll LOP", "fact_attendance_monthly + fact_payroll", "Warning", """
      SELECT a.attendance_fact_id AS record_key,'employee='||a.employee_id||'; absence='||a.unpaid_absence_days AS detail
      FROM raw.fact_attendance_monthly a LEFT JOIN raw.fact_payroll p
        ON p.employee_id=a.employee_id AND p.period_end_date=a.period_end_date
      WHERE a.unpaid_absence_days>0 AND COALESCE(p.lop_days,0)=0"""),
    ("DQ-C07", "Invoice amounts reconcile", "fact_invoice", "Warning", """
      SELECT invoice_id AS record_key,'total='||total_amount||'; paid='||amount_paid||'; balance='||balance_due AS detail
      FROM raw.fact_invoice WHERE amount_paid>total_amount OR balance_due<0"""),
    ("DQ-C08", "Expense total reconciles to tax components", "fact_expense", "Warning", """
      SELECT expense_id AS record_key,'total='||total_amount||'; components='||(amount_excl_gst+gst_amount) AS detail
      FROM raw.fact_expense WHERE ABS(total_amount-(amount_excl_gst+gst_amount))>0.01"""),
    ("DQ-C09", "Task dates match status", "fact_task", "Warning", """
      SELECT task_id AS record_key,'status='||status||'; started='||COALESCE(CAST(started_date AS VARCHAR),'blank')||
        '; completed='||COALESCE(CAST(completed_date AS VARCHAR),'blank') AS detail
      FROM raw.fact_task WHERE (completed_date<started_date) OR
        (status='Done' AND completed_date IS NULL) OR (status='Done' AND started_date IS NULL)"""),
    ("DQ-C10", "Leave end date is not before start date", "fact_leave", "Warning", """
      SELECT leave_request_id AS record_key,'start='||CAST(start_date AS VARCHAR)||'; end='||CAST(end_date AS VARCHAR) AS detail
      FROM raw.fact_leave WHERE end_date<start_date"""),
    ("DQ-C11", "Attrition-risk batch is current", "fact_attrition_risk", "Warning", """
      WITH latest AS (SELECT MAX(as_of_date) AS as_of_date FROM raw.fact_attrition_risk)
      SELECT r.prediction_id AS record_key,'as_of_date='||CAST(r.as_of_date AS VARCHAR)||
        '; latest='||CAST(latest.as_of_date AS VARCHAR) AS detail
      FROM raw.fact_attrition_risk r,latest WHERE r.as_of_date<latest.as_of_date-INTERVAL 7 DAY"""),
    ("DQ-C12", "Employee effective dates do not overlap", "dim_employee", "Critical", """
      SELECT a.employee_id||'|'||a.employee_key||'|'||b.employee_key AS record_key,
             'valid_to='||CAST(a.valid_to AS VARCHAR)||'; next_valid_from='||CAST(b.valid_from AS VARCHAR) AS detail
      FROM raw.dim_employee a JOIN raw.dim_employee b
        ON a.employee_id=b.employee_id AND a.employee_key<b.employee_key
       AND a.valid_from<=b.valid_to AND b.valid_from<=a.valid_to"""),
    ("DQ-C13", "Most recent successful ETL is under 24 hours old", "audit.etl_run_log", "Critical", """
      SELECT CAST(MAX(finished_at) AS VARCHAR) AS record_key,
             'latest successful refresh is stale' AS detail FROM audit.etl_run_log WHERE status='SUCCESS'
      HAVING MAX(finished_at)<now()-INTERVAL 24 HOUR OR MAX(finished_at) IS NULL"""),
    ("DQ-C14", "Minimum group size is respected", "metrics.*", "Critical", """
      WITH exposures AS (
        SELECT 'M01' AS metric_id,CAST(m.period AS VARCHAR) AS period,m.department_id AS group_key,
               h.headcount_end AS group_size FROM metrics.m01_headcount m
          JOIN clean.fact_headcount_monthly h ON h.month_start_date=m.period AND h.department_id=m.department_id
          WHERE m.department_id<>'ALL'
        UNION ALL
        SELECT 'M04',CAST(m.period AS VARCHAR),m.department_id,h.headcount_start FROM metrics.m04_attrition_monthly m
          JOIN clean.fact_headcount_monthly h ON h.month_start_date=m.period AND h.department_id=m.department_id
          WHERE m.department_id<>'ALL'
        UNION ALL
        SELECT 'M07',CAST(m.period AS VARCHAR),m.department_id,COUNT(DISTINCT p.employee_id)
          FROM metrics.m07_gross_pay m JOIN clean.fact_payroll p ON p.period_end_date=m.period
          JOIN warehouse.dim_employee e ON e.employee_key=p.employee_key AND e.department_id=m.department_id
          WHERE m.department_id<>'ALL' GROUP BY 1,2,3
        UNION ALL
        SELECT 'M27',CAST(m.period AS VARCHAR),m.department_id,COUNT(DISTINCT r.employee_id)
          FROM metrics.m27_high_risk_share m JOIN clean.fact_attrition_risk r
            ON r.as_of_date=m.period AND r.department_id=m.department_id GROUP BY 1,2,3
      ) SELECT metric_id||'|'||period||'|'||group_key AS record_key,
               'exposed group size='||group_size||'; minimum='||minimum_group_size AS detail
        FROM exposures JOIN metrics.metric_catalog USING(metric_id)
        WHERE minimum_group_size IS NOT NULL AND group_size<minimum_group_size"""),
]


def run_quality_checks(con, run_id: str) -> list[dict]:
    """Persist bad-row detail and a manager-readable result for every check."""
    con.execute("""CREATE TABLE IF NOT EXISTS audit.dq_results(
      run_id VARCHAR,check_id VARCHAR,check_name VARCHAR,table_name VARCHAR,severity VARCHAR,
      bad_rows BIGINT,status VARCHAR,run_at TIMESTAMPTZ)""")
    con.execute("""CREATE TABLE IF NOT EXISTS audit.dq_check_details(
      run_id VARCHAR,check_id VARCHAR,table_name VARCHAR,record_key VARCHAR,detail VARCHAR)""")
    con.execute("DELETE FROM audit.dq_results WHERE run_id=?", [run_id])
    con.execute("DELETE FROM audit.dq_check_details WHERE run_id=?", [run_id])
    output=[]
    for check_id,name,table_name,severity,query in CHECKS:
        details=con.execute(query).fetchall()
        bad=len(details)
        status="PASS" if bad==0 else ("FAIL" if severity=="Critical" else "WARN")
        output.append({"check_id":check_id,"check_name":name,"table_name":table_name,
                       "severity":severity,"bad_rows":bad,"status":status})
        con.executemany("INSERT INTO audit.dq_results VALUES (?,?,?,?,?,?,?,?)",[
            (run_id,check_id,name,table_name,severity,bad,status,datetime.now(timezone.utc))])
        if details:
            con.executemany("INSERT INTO audit.dq_check_details VALUES (?,?,?,?,?)",[
                (run_id,check_id,table_name,str(key),str(detail)) for key,detail in details])
    con.execute("""CREATE OR REPLACE VIEW audit.dq_summary AS
        SELECT status,COUNT(*) AS checks,SUM(bad_rows) AS affected_records
        FROM audit.dq_results WHERE run_id=(SELECT run_id FROM audit.dq_results ORDER BY run_at DESC LIMIT 1) GROUP BY status""")
    return output
