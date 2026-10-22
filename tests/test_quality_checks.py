"""Each DQ query is seeded with an isolated, synthetic bad row and must catch it."""
import unittest
import duckdb

from pulseiq.quality import CHECKS


def fixture(check_id):
    c=duckdb.connect(":memory:")
    for schema in ["raw","audit","metrics","clean","warehouse"]:
        c.execute(f"CREATE SCHEMA {schema}")
    setups={
      "DQ-C01": [
        "CREATE TABLE raw.fact_payroll(period_end_date DATE,employer_cost DOUBLE)",
        "INSERT INTO raw.fact_payroll VALUES ('2026-01-31',100)",
        "CREATE TABLE raw.fact_ledger(entry_date DATE,account_code VARCHAR,signed_amount_debit_positive DOUBLE)",
        "INSERT INTO raw.fact_ledger VALUES ('2026-01-02','5001',90)"],
      "DQ-C02": ["CREATE TABLE raw.fact_ledger(entry_id VARCHAR,debit DOUBLE,credit DOUBLE)","INSERT INTO raw.fact_ledger VALUES ('JE-1',10,0)"],
      "DQ-C03": ["CREATE TABLE raw.fact_payroll(employee_id VARCHAR,run_id VARCHAR)","INSERT INTO raw.fact_payroll VALUES ('E1','R1'),('E1','R1')"],
      "DQ-C04": ["CREATE TABLE raw.fact_payroll(payroll_item_id VARCHAR,employee_id VARCHAR)","INSERT INTO raw.fact_payroll VALUES ('P1','MISSING')","CREATE TABLE raw.dim_employee(employee_id VARCHAR)"],
      "DQ-C05": ["CREATE TABLE raw.fact_attendance_monthly(attendance_fact_id VARCHAR,employee_key BIGINT,period_end_date DATE)","INSERT INTO raw.fact_attendance_monthly VALUES ('A1',1,'2026-03-31')","CREATE TABLE raw.dim_employee(employee_key BIGINT,exit_date DATE)","INSERT INTO raw.dim_employee VALUES (1,'2026-01-15')"],
      "DQ-C06": ["CREATE TABLE raw.fact_attendance_monthly(attendance_fact_id VARCHAR,employee_id VARCHAR,period_end_date DATE,unpaid_absence_days DOUBLE)","INSERT INTO raw.fact_attendance_monthly VALUES ('A1','E1','2026-01-31',1)","CREATE TABLE raw.fact_payroll(employee_id VARCHAR,period_end_date DATE,lop_days DOUBLE)"],
      "DQ-C07": ["CREATE TABLE raw.fact_invoice(invoice_id VARCHAR,total_amount DOUBLE,amount_paid DOUBLE,balance_due DOUBLE)","INSERT INTO raw.fact_invoice VALUES ('I1',100,101,-1)"],
      "DQ-C08": ["CREATE TABLE raw.fact_expense(expense_id VARCHAR,total_amount DOUBLE,amount_excl_gst DOUBLE,gst_amount DOUBLE)","INSERT INTO raw.fact_expense VALUES ('X1',151,100,50)"],
      "DQ-C09": ["CREATE TABLE raw.fact_task(task_id VARCHAR,status VARCHAR,started_date DATE,completed_date DATE)","INSERT INTO raw.fact_task VALUES ('T1','Done','2026-01-10','2026-01-09')"],
      "DQ-C10": ["CREATE TABLE raw.fact_leave(leave_request_id VARCHAR,start_date DATE,end_date DATE)","INSERT INTO raw.fact_leave VALUES ('L1','2026-01-10','2026-01-09')"],
      "DQ-C11": ["CREATE TABLE raw.fact_attrition_risk(prediction_id VARCHAR,as_of_date DATE)","INSERT INTO raw.fact_attrition_risk VALUES ('R1','2025-01-01'),('R2','2026-01-01')"],
      "DQ-C12": ["CREATE TABLE raw.dim_employee(employee_id VARCHAR,employee_key BIGINT,valid_from DATE,valid_to DATE)","INSERT INTO raw.dim_employee VALUES ('E1',1,'2020-01-01','2021-01-10'),('E1',2,'2021-01-01','2022-01-01')"],
      "DQ-C13": ["CREATE TABLE audit.etl_run_log(status VARCHAR,finished_at TIMESTAMPTZ)","INSERT INTO audit.etl_run_log VALUES ('SUCCESS',TIMESTAMPTZ '2020-01-01 00:00:00+00')"],
      "DQ-C14": [
        "CREATE TABLE metrics.metric_catalog(metric_id VARCHAR,minimum_group_size INTEGER)",
        "INSERT INTO metrics.metric_catalog VALUES ('M01',5),('M04',10),('M07',5),('M27',10)",
        "CREATE TABLE metrics.m01_headcount(period DATE,department_id VARCHAR)","INSERT INTO metrics.m01_headcount VALUES ('2026-01-31','D01')",
        "CREATE TABLE metrics.m04_attrition_monthly(period DATE,department_id VARCHAR)",
        "CREATE TABLE metrics.m07_gross_pay(period DATE,department_id VARCHAR)",
        "CREATE TABLE metrics.m27_high_risk_share(period DATE,department_id VARCHAR)",
        "CREATE TABLE clean.fact_headcount_monthly(month_start_date DATE,department_id VARCHAR,headcount_end INTEGER,headcount_start INTEGER)",
        "INSERT INTO clean.fact_headcount_monthly VALUES ('2026-01-31','D01',2,2)",
        "CREATE TABLE clean.fact_payroll(period_end_date DATE,employee_id VARCHAR,employee_key BIGINT)",
        "CREATE TABLE warehouse.dim_employee(employee_key BIGINT,department_id VARCHAR)",
        "CREATE TABLE clean.fact_attrition_risk(as_of_date DATE,department_id VARCHAR,employee_id VARCHAR)",
      ],
    }
    for sql in setups[check_id]: c.execute(sql)
    check=next(row for row in CHECKS if row[0]==check_id)
    return c,check[4]


class QualityInjectionTests(unittest.TestCase):
    def test_all_fourteen_queries_catch_a_seeded_bad_row(self):
        self.assertEqual(len(CHECKS),14)
        for check_id,*_ in CHECKS:
            with self.subTest(check_id=check_id):
                con,sql=fixture(check_id)
                try:
                    rows=con.execute(sql).fetchall()
                    self.assertGreater(len(rows),0,f"{check_id} did not detect its injected issue")
                finally:
                    con.close()


if __name__=="__main__": unittest.main(verbosity=2)
