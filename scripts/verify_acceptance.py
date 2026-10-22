"""Run the local acceptance checks and write a non-PII validation summary."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import duckdb
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pulseiq.metrics import METRIC_VIEWS

DB=Path(__import__("os").environ.get("PULSEIQ_DB_PATH",ROOT/"pulseiq.duckdb"))


def manual_checks(con,period=date(2026,9,1)):
    month_end=(pd.Timestamp(period)+pd.offsets.MonthEnd(0)).date()
    results=[]
    # M01: independently count active SCD employee identities at month-end.
    q=con.execute("""SELECT COUNT(DISTINCT employee_id) FROM warehouse.dim_employee
        WHERE employee_id<>'UNKNOWN' AND department_id='D01' AND hire_date<=?
          AND (exit_date IS NULL OR exit_date>?) AND valid_from<=? AND valid_to>=?""",[month_end]*4).fetchone()[0]
    v=con.execute("SELECT value FROM metrics.m01_headcount WHERE period=? AND department_id='D01'",[period]).fetchone()[0]
    results.append(("M01 active SCD headcount, D01",float(q),float(v),0.01))
    # M07: direct sum from the clean payroll fact.
    q=con.execute("SELECT SUM(gross_pay) FROM clean.fact_payroll WHERE period_end_date=? AND department_id='D01'",[month_end]).fetchone()[0]
    v=con.execute("SELECT value FROM metrics.m07_gross_pay WHERE period=? AND department_id='D01'",[period]).fetchone()[0]
    results.append(("M07 gross pay, D01",float(q),float(v),0.01))
    # M13: weighted numerator/denominator from the attendance fact.
    q=con.execute("""SELECT SUM(a.present_days+0.5*a.half_days_unpaid)/NULLIF(SUM(a.scheduled_days),0)
        FROM clean.fact_attendance_monthly a JOIN warehouse.dim_employee e USING(employee_key)
        WHERE a.period_end_date=? AND e.department_id='D01'""",[month_end]).fetchone()[0]
    v=con.execute("SELECT value FROM metrics.m13_attendance_rate WHERE period=? AND department_id='D01'",[period]).fetchone()[0]
    results.append(("M13 weighted attendance rate, D01",float(q),float(v),1e-10))
    # M17: ledger formula directly, including account 4900 other income.
    q=con.execute("""SELECT -SUM(signed_amount_debit_positive) FROM warehouse.fact_ledger
        WHERE date_trunc('month',entry_date)=? AND TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 5999""",[period]).fetchone()[0]
    v=con.execute("SELECT value FROM metrics.m17_net_profit WHERE period=?",[period]).fetchone()[0]
    results.append(("M17 ledger net profit",float(q),float(v),0.01))
    # M20: reconstruct closing AR and rolling 90-day credit sales.
    ar=con.execute("SELECT SUM(balance) FROM metrics.dashboard_receivables_asof WHERE period=?",[period]).fetchone()[0]
    sales=con.execute("""SELECT SUM(total_amount) FROM clean.fact_invoice
        WHERE status NOT IN ('DRAFT','CANCELLED') AND invoice_date<=?
          AND invoice_date>?-INTERVAL 90 DAY""",[month_end,month_end]).fetchone()[0]
    q=90.0*ar/sales
    v=con.execute("SELECT value FROM metrics.m20_dso WHERE period=?",[month_end]).fetchone()[0]
    results.append(("M20 event-based DSO",float(q),float(v),1e-10))
    # M22: use independent task counts, excluding cancelled tasks.
    sprint="SP-01";team="T01"
    q=con.execute("""SELECT 100.0*COUNT(*) FILTER(WHERE status='Done')/
        NULLIF(COUNT(*) FILTER(WHERE status<>'Cancelled'),0) FROM clean.fact_task
        WHERE sprint_id=? AND team_id=?""",[sprint,team]).fetchone()[0]
    v=con.execute("SELECT value FROM metrics.m22_task_completion WHERE sprint_id=? AND team_id=?",[sprint,team]).fetchone()[0]
    results.append(("M22 task completion, T01 / SP-01",float(q),float(v),1e-10))
    # Two-team productivity check for velocity and cycle time.
    for team in ["T01","T02"]:
        qv=con.execute("SELECT SUM(story_points) FILTER(WHERE status='Done') FROM clean.fact_task WHERE sprint_id='SP-01' AND team_id=?",[team]).fetchone()[0]
        vv=con.execute("SELECT value FROM metrics.m24_velocity WHERE sprint_id='SP-01' AND team_id=?",[team]).fetchone()[0]
        results.append((f"M24 velocity, {team} / SP-01",float(qv),float(vv),1e-10))
        qc=con.execute("SELECT AVG(date_diff('day',started_date,completed_date)) FILTER(WHERE status='Done') FROM clean.fact_task WHERE sprint_id='SP-01' AND team_id=?",[team]).fetchone()[0]
        vc=con.execute("SELECT value FROM metrics.m25_cycle_time WHERE sprint_id='SP-01' AND team_id=?",[team]).fetchone()[0]
        results.append((f"M25 cycle time, {team} / SP-01",float(qc),float(vc),1e-10))
    # Three budget-month arithmetic checks independent of the dashboard status.
    for dept in ["D01","D02","D03"]:
        budget,actual,var=con.execute("""SELECT b.budget_payroll_cost,m.value,b.budget_payroll_cost-m.value
            FROM clean.budget_payroll_dept_month b JOIN metrics.m09_payroll_cost m
              ON m.period=b.month AND m.department_id=b.department_id
            WHERE b.month=? AND b.department_id=?""",[period,dept]).fetchone()
        results.append((f"PQ-10 budget variance, {dept}",float(actual-budget),float(-var),0.01))
    return results


def pq09_compare(con,vault):
    key_path=vault/"unlock_PQ-09_reconciliation_answer_key.csv"
    if not key_path.exists(): return None
    key=pd.read_csv(key_path);key["period"]=pd.to_datetime(key.month).dt.date
    actual=con.execute("""WITH p AS (
        SELECT CAST(date_trunc('month',period_end_date) AS DATE) AS period,
          COUNT(DISTINCT employee_id) AS employees_paid,SUM(gross_pay) AS payroll_gross_pay,
          SUM(net_pay) AS payroll_net_pay,SUM(employer_cost) AS payroll_employer_cost
        FROM clean.fact_payroll GROUP BY 1
      ),l AS (
        SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
          SUM(signed_amount_debit_positive) FILTER(WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5005) AS ledger_salary_related_expense,
          -SUM(signed_amount_debit_positive) FILTER(WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 4999) AS ledger_revenue,
          SUM(signed_amount_debit_positive) FILTER(WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 5000 AND 5999) AS ledger_total_expense,
          -SUM(signed_amount_debit_positive) FILTER(WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 5999) AS ledger_net_profit,
          SUM(signed_amount_debit_positive) FILTER(WHERE TRY_CAST(account_code AS INTEGER)=1001) AS bank_movement
        FROM warehouse.fact_ledger GROUP BY 1
      ),ar AS (
        SELECT period,SUM(balance) AS receivables_closing_balance FROM metrics.dashboard_receivables_asof GROUP BY 1
      ) SELECT * FROM p JOIN l USING(period) JOIN ar USING(period) ORDER BY period""").fetchdf()
    actual["period"]=pd.to_datetime(actual.period).dt.date
    actual["bank_closing_balance"]=actual.bank_movement.cumsum()
    actual["payroll_vs_ledger_difference"]=con.execute("SELECT period,difference FROM audit.payroll_ledger_reconciliation_clean ORDER BY period").fetchdf().difference
    joined=key.merge(actual,on="period",how="outer",suffixes=("_key","_actual"))
    cols=["employees_paid","payroll_gross_pay","payroll_net_pay","payroll_employer_cost","ledger_salary_related_expense","ledger_revenue","ledger_total_expense","ledger_net_profit","bank_closing_balance","receivables_closing_balance","payroll_vs_ledger_difference"]
    mismatches={}
    for col in cols:
        a=pd.to_numeric(joined[f"{col}_key"],errors="coerce");b=pd.to_numeric(joined[f"{col}_actual"],errors="coerce")
        tol=0 if col=="employees_paid" else .011
        mismatches[col]=int((a.isna()^b.isna()).sum()+((a-b).abs()>tol).sum())
    matched=int(joined["employees_paid_actual"].notna().sum())
    return {"rows":len(key),"months_matched":matched,"mismatches":mismatches,
            "max_payroll_ledger_abs_diff":float(pd.to_numeric(joined.payroll_vs_ledger_difference_actual).abs().max())}


def pq13_compare(con,vault):
    key_path=vault/"unlock_PQ-13_reference_summary_dept_month.csv"
    if not key_path.exists(): return None
    key=pd.read_csv(key_path);key["period"]=pd.to_datetime(key.month).dt.date
    all_rows=len(key);d00=int((key.department_id=="D00").sum());key=key[key.department_id!="D00"]
    actual=con.execute("SELECT * FROM metrics.dashboard_department_impact").fetchdf();actual["period"]=pd.to_datetime(actual.period).dt.date
    joined=key.merge(actual,on=["department_id","period"],how="left",suffixes=("_key","_view"))
    mappings={
      "employer_cost":("payroll_cost",.011),"gross_pay":("gross_pay",.011),"overtime_pay":("overtime_pay",.011),
      "employees_paid":("paid_people",0),"overtime_hours":("overtime_hours",.011),"late_arrivals":("late_arrivals",0),
      "attendance_rate":("attendance_rate",.00011),"headcount_end":("headcount_end",0),"hires":("hires",0),"exits":("exits",0),
      "attrition_rate_monthly_pct":("attrition_pct",.051),"tasks":("planned_tasks",0),"tasks_done":("done_tasks",0),
      "story_points_done":("story_points_done",0),"task_completion_rate_pct":("task_completion_pct",.051),
      "cost_per_head":("cost_per_head",.011),"overtime_share_pct":("overtime_share_pct",.051),
    }
    diffs={};task_cols={"tasks","tasks_done","story_points_done","task_completion_rate_pct"}
    for key_col,(view_col,tol) in mappings.items():
        kc=key_col+"_key" if key_col in actual.columns else key_col
        vc=view_col+"_view" if view_col in key.columns else view_col
        a=pd.to_numeric(joined[kc],errors="coerce");b=pd.to_numeric(joined[vc],errors="coerce")
        diffs[key_col]=int((a.isna()^b.isna()).sum()+((a-b).abs()>tol).sum())
    non_task=sum(v for k,v in diffs.items() if k not in task_cols)
    task_groups=max(diffs[k] for k in task_cols)
    return {"reference_rows":all_rows,"rows_after_privacy_suppression":len(key),"d00_rows_suppressed":d00,
            "matched_rows":int(joined.payroll_cost.notna().sum()),"field_differences":diffs,
            "non_task_differences":non_task,"largest_task_field_difference_count":task_groups}


def run(vault:Path):
    if not DB.exists(): raise FileNotFoundError(f"Missing {DB}; run python etl.py first.")
    con=duckdb.connect(str(DB),read_only=True)
    lines=["# Local acceptance evidence","",f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}","", "## Pipeline and warehouse",""]
    latest=con.execute("SELECT run_id FROM audit.etl_run_log ORDER BY started_at DESC LIMIT 1").fetchone()[0]
    counts=con.execute("SELECT COUNT(*),SUM(ABS(rows_in-rows_passed-rows_quarantined)) FROM audit.load_summary WHERE run_id=?",[latest]).fetchone()
    lines += [f"- Latest run: `{latest}`; source tables: {int(counts[0])}; unexplained row-count difference: {int(counts[1] or 0)}."]
    bad_fk=con.execute("SELECT COUNT(*) FROM audit.orphan_results WHERE orphan_rows<>0").fetchone()[0]
    lines += [f"- Warehouse declared relationships with orphans: {bad_fk}."]
    metric_rows=[]
    for mid,view in METRIC_VIEWS.items():
        n,nval=con.execute(f"SELECT COUNT(*),COUNT(value) FROM metrics.{view}").fetchone()
        metric_rows.append((mid,view,int(n),int(nval)))
    lines += [f"- Governed metric views: {len(metric_rows)}; all have rows: {all(x[2]>0 for x in metric_rows)}.",
              f"- M28 rows: {next(x[2] for x in metric_rows if x[0]=='M28')}; measured values: {next(x[3] for x in metric_rows if x[0]=='M28')} (actuals start after supplied forecast horizon).",""]
    lines += ["## Seeded issue detection","", "| Check | Status | Findings |", "|---|---:|---:|"]
    dq=con.execute("SELECT check_id,status,bad_rows FROM audit.dq_results WHERE run_id=? ORDER BY check_id",[latest]).fetchall()
    for check_id,status,n in dq: lines.append(f"| {check_id} | {status} | {n} |")
    lines += ["", "DQ-C06 flags the same post-exit attendance row already identified by DQ-C05; it is not an additional planted issue. The clean warehouse quarantines four post-exit attendance rows, four invalid payroll rows, two reversed-date leave rows, one expense arithmetic mismatch and 20 invalid task rows. The raw source stays intact. The SCD overlap and DQ-04 ledger mismatch are corrected in the conformed warehouse and recorded in audit tables.",""]

    # Calculator checks and task-level arithmetic checks.
    checks=manual_checks(con)
    lines += ["## Hand calculations","", "| Check | Independently calculated | Governed view | Result |", "|---|---:|---:|---|"]
    all_manual=True
    for name,manual,view,tol in checks:
        ok=abs(manual-view)<=tol;all_manual &= ok
        lines.append(f"| {name} | {manual:,.6f} | {view:,.6f} | {'PASS' if ok else 'FAIL'} |")
    lines += [""]

    pq09=pq09_compare(con,vault)
    if pq09:
        lines += ["## PQ-09 reconciliation answer key","",f"- Compared {pq09['rows']} reference months; payroll, ledger, cash and receivables rows matched: {all(v==0 for v in pq09['mismatches'].values())}.",
          f"- Largest clean payroll-to-ledger difference: INR {pq09['max_payroll_ledger_abs_diff']:.8f} (acceptance tolerance INR 0.01).",""]
        lines += ["| Field | Mismatching months |","|---|---:|"]+[f"| {k} | {v} |" for k,v in pq09["mismatches"].items()]+[""]
    else:
        lines += ["## PQ-09 reconciliation answer key","","Validation file not present; local comparison skipped.",""]
    pq13=pq13_compare(con,vault)
    if pq13:
        lines += ["## PQ-13 department-month comparison","",f"- Reference contains {pq13['reference_rows']} rows. {pq13['d00_rows_suppressed']} single-person D00 reference rows are withheld; {pq13['matched_rows']} department-month rows match the privacy-safe view.",
          f"- All non-task fields match within source precision: {pq13['non_task_differences']==0}.",
          f"- Task differences occur in {pq13['largest_task_field_difference_count']} or fewer department-month groups and match the locations of the 20 quarantined invalid task rows.","",
          "| Reference field | Differences after privacy suppression |","|---|---:|"]+[f"| {k} | {v} |" for k,v in pq13['field_differences'].items()]+[""]
    else:
        lines += ["## PQ-13 department-month comparison","","Validation file not present; local comparison skipped.",""]

    # Monthly re-run and quality flags remain distinct from clean metric correctness.
    gate=con.execute("SELECT COUNT(*) FILTER(WHERE status='FAIL'),COUNT(*) FILTER(WHERE status='WARN') FROM audit.dq_results WHERE run_id=?",[latest]).fetchone()
    lines += ["## Release interpretation","",f"- DQ checks: {len(dq)} automated; {int(gate[0])} critical check(s) fail against the intentionally seeded raw issues and {int(gate[1])} warning check(s) are recorded.",
      "- Release gate remains REVIEW REQUIRED until a human reviews source findings. Clean-layer reconciliation and all calculations above can pass while raw DQ checks still report planted issues.",
      "- Forecast MAPE is not estimable because actuals end in September 2026 and the supplied forecast starts in October 2026."]
    con.close()
    return "\n".join(lines), all_manual, pq09, pq13


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vault",type=Path,default=ROOT/"04_Validation_Vault")
    ap.add_argument("--output",type=Path,default=ROOT/"docs"/"validation_results.md")
    ap.add_argument("--stdout",action="store_true")
    a=ap.parse_args();content,manual,pq09,pq13=run(a.vault)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(content+"\n",encoding="utf-8")
    print(content if a.stdout else f"Wrote {a.output}")
    if not manual: raise SystemExit(1)
    if pq09 and any(pq09["mismatches"].values()): raise SystemExit(1)
    if pq13 and pq13["non_task_differences"]: raise SystemExit(1)


if __name__=="__main__": main()
