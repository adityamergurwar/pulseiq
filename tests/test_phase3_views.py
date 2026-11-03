import unittest
from pathlib import Path

import duckdb

from pulseiq.app_common import DB_PATH


class Phase3ViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Path(DB_PATH).exists():
            raise unittest.SkipTest("Run python etl.py to build the warehouse first.")
        cls.con = duckdb.connect(str(DB_PATH), read_only=True)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "con", None):
            cls.con.close()

    def test_pnl_uses_detail_accounts_and_balances_each_month(self):
        rows = self.con.execute(
            """WITH detail AS (
                 SELECT CAST(date_trunc('month',l.entry_date) AS DATE) AS period,
                   SUM(CASE WHEN a.account_type='INCOME'
                             AND TRY_CAST(a.account_code AS INTEGER) BETWEEN 4001 AND 4004
                            THEN -l.signed_amount_debit_positive ELSE 0 END) AS revenue,
                   SUM(CASE WHEN a.account_type='EXPENSE'
                            THEN l.signed_amount_debit_positive ELSE 0 END) AS expenses,
                   SUM(CASE WHEN a.account_type='INCOME'
                             AND TRY_CAST(a.account_code AS INTEGER)=4900
                            THEN -l.signed_amount_debit_positive ELSE 0 END) AS other_income
                 FROM warehouse.fact_ledger l
                 JOIN clean.dim_account a ON TRY_CAST(l.account_code AS INTEGER)=a.account_code
                 WHERE a.statement='Profit & Loss' AND a.is_group='N' AND a.is_active='Y'
                 GROUP BY 1
               )
               SELECT v.period, v.revenue-d.revenue, v.expenses-d.expenses,
                      v.other_income-d.other_income, v.reconciliation_difference
               FROM metrics.dashboard_pnl_monthly v JOIN detail d USING(period)
               ORDER BY v.period"""
        ).fetchall()
        self.assertEqual(len(rows), 18)
        for period, revenue_diff, expense_diff, income_diff, tie_out in rows:
            with self.subTest(period=period):
                self.assertAlmostEqual(revenue_diff, 0, places=2)
                self.assertAlmostEqual(expense_diff, 0, places=2)
                self.assertAlmostEqual(income_diff, 0, places=2)
                self.assertAlmostEqual(tie_out, 0, places=2)
        view_sql = self.con.execute(
            "SELECT sql FROM duckdb_views() WHERE schema_name='metrics' AND view_name='dashboard_pnl_monthly'"
        ).fetchone()[0].lower().replace(" ", "")
        self.assertIn("a.is_group='n'", view_sql)

    def test_pnl_account_mix_is_detail_only_and_reconciles_to_pnl_lines(self):
        rows = self.con.execute(
            """SELECT p.period,
                      p.revenue-SUM(m.amount) FILTER(WHERE m.account_type='INCOME') AS revenue_diff,
                      p.expenses-SUM(m.amount) FILTER(WHERE m.account_type='EXPENSE') AS expense_diff
               FROM metrics.dashboard_pnl_monthly p
               JOIN metrics.dashboard_pnl_account_mix m USING(period)
               GROUP BY p.period,p.revenue,p.expenses ORDER BY p.period"""
        ).fetchall()
        self.assertEqual(len(rows), 18)
        for period, revenue_diff, expense_diff in rows:
            with self.subTest(period=period):
                self.assertAlmostEqual(revenue_diff, 0, places=2)
                self.assertAlmostEqual(expense_diff, 0, places=2)

    def test_expense_category_and_vendor_views_match_the_expense_register(self):
        category_mismatches = self.con.execute(
            """WITH expected AS (
                 SELECT CAST(date_trunc('month',e.expense_date) AS DATE) AS period,
                        a.account_name, SUM(e.total_amount) AS spend
                 FROM clean.fact_expense e JOIN clean.dim_account a
                   ON e.category_account=a.account_code
                 WHERE a.account_type='EXPENSE' AND a.is_group='N' AND a.is_active='Y'
                 GROUP BY 1,2
               ), actual AS (
                 SELECT period,account_name,SUM(spend) AS spend
                 FROM metrics.dashboard_expense_category GROUP BY 1,2
               )
               SELECT COUNT(*) FROM expected e FULL JOIN actual a USING(period,account_name)
               WHERE e.spend IS NULL OR a.spend IS NULL OR ABS(e.spend-a.spend)>0.01"""
        ).fetchone()[0]
        vendor_mismatches = self.con.execute(
            """WITH expected AS (
                 SELECT CAST(date_trunc('month',e.expense_date) AS DATE) AS period,
                        v.vendor_name, SUM(e.total_amount) AS spend
                 FROM clean.fact_expense e JOIN clean.dim_vendor v USING(vendor_id)
                 GROUP BY 1,2
               ), actual AS (
                 SELECT period,vendor_name,SUM(spend) AS spend
                 FROM metrics.dashboard_vendor_spend GROUP BY 1,2
               )
               SELECT COUNT(*) FROM expected e FULL JOIN actual a USING(period,vendor_name)
               WHERE e.spend IS NULL OR a.spend IS NULL OR ABS(e.spend-a.spend)>0.01"""
        ).fetchone()[0]
        self.assertEqual(category_mismatches, 0)
        self.assertEqual(vendor_mismatches, 0)

    def test_current_receivables_use_only_open_statuses_and_ageing_reconciles(self):
        invalid_statuses = self.con.execute(
            """SELECT COUNT(*) FROM metrics.dashboard_receivables
               WHERE status NOT IN ('SENT','OVERDUE','PARTIALLY_PAID')"""
        ).fetchone()[0]
        totals = self.con.execute(
            """SELECT SUM(balance) AS total,
                      SUM(balance) FILTER(WHERE ageing_bucket='Not due') AS not_due,
                      SUM(balance) FILTER(WHERE ageing_bucket='0-30 days') AS d30,
                      SUM(balance) FILTER(WHERE ageing_bucket='31-60 days') AS d60,
                      SUM(balance) FILTER(WHERE ageing_bucket='61-90 days') AS d90,
                      SUM(balance) FILTER(WHERE ageing_bucket='90+ days') AS d90_plus
               FROM metrics.dashboard_receivables"""
        ).fetchone()
        self.assertEqual(invalid_statuses, 0)
        self.assertAlmostEqual(totals[0], sum(value or 0 for value in totals[1:]), places=2)
        buckets = {
            row[0]
            for row in self.con.execute(
                "SELECT DISTINCT ageing_bucket FROM metrics.dashboard_receivables"
            ).fetchall()
        }
        self.assertTrue(buckets <= {"Not due", "0-30 days", "31-60 days", "61-90 days", "90+ days"})
        self.assertGreater(totals[0], 0)

    def test_days_to_pay_are_client_averages_and_cash_movements_balance(self):
        mismatches = self.con.execute(
            """WITH expected AS (
                 SELECT client_id, AVG(days_to_pay) AS days
                 FROM clean.fact_invoice
                 WHERE status='PAID' AND days_to_pay IS NOT NULL
                 GROUP BY 1
               )
               SELECT COUNT(*) FROM expected e FULL JOIN metrics.dashboard_client_collection v USING(client_id)
               WHERE e.client_id IS NULL OR v.client_id IS NULL OR ABS(e.days-v.average_days_to_pay)>0.000001"""
        ).fetchone()[0]
        cash_mismatches = self.con.execute(
            """SELECT COUNT(*) FROM metrics.dashboard_cash_movement
               WHERE ABS(net_movement-(cash_in-cash_out))>0.01"""
        ).fetchone()[0]
        self.assertEqual(mismatches, 0)
        expected_clients = self.con.execute(
            """SELECT COUNT(DISTINCT client_id) FROM clean.fact_invoice
               WHERE status='PAID' AND days_to_pay IS NOT NULL"""
        ).fetchone()[0]
        actual_clients = self.con.execute("SELECT COUNT(*) FROM metrics.dashboard_client_collection").fetchone()[0]
        self.assertEqual(actual_clients, expected_clients)
        self.assertEqual(cash_mismatches, 0)
        self.assertGreater(
            self.con.execute("SELECT COUNT(*) FROM metrics.dashboard_overdue_by_client").fetchone()[0],
            0,
        )

    def test_department_impact_is_unique_at_department_month_grain(self):
        duplicates = self.con.execute(
            """SELECT COUNT(*) FROM (
                 SELECT period,department_id,COUNT(*) AS rows
                 FROM metrics.dashboard_department_impact
                 GROUP BY 1,2 HAVING COUNT(*)<>1
               )"""
        ).fetchone()[0]
        missing_fields = self.con.execute(
            """SELECT COUNT(*) FROM metrics.dashboard_department_impact
               WHERE overtime_pay IS NULL OR leave_days_per_head IS NULL"""
        ).fetchone()[0]
        self.assertEqual(duplicates, 0)
        self.assertEqual(missing_fields, 0)

    def test_forecast_error_only_exists_when_actuals_overlap(self):
        overlaps = self.con.execute(
            """SELECT COUNT(*) FROM metrics.dashboard_forecast
               WHERE actual_value IS NOT NULL"""
        ).fetchone()[0]
        self.assertEqual(overlaps, 0)

    def test_eight_scorecard_metrics_are_dictionary_metrics_and_queryable(self):
        views = [
            ("M01", "m01_headcount", "2026-09-01"),
            ("M04", "m04_attrition_monthly", "2026-09-01"),
            ("M09", "m09_payroll_cost", "2026-09-01"),
            ("M13", "m13_attendance_rate", "2026-09-01"),
            ("M16", "m16_revenue", "2026-09-01"),
            ("M18", "m18_operating_margin", "2026-09-01"),
            ("M20", "m20_dso", "2026-09-30"),
        ]
        dictionary_ids = {
            row[0] for row in self.con.execute("SELECT metric_id FROM clean.metric_dictionary").fetchall()
        }
        for metric_id, view, period in views:
            with self.subTest(metric_id=metric_id):
                self.assertIn(metric_id, dictionary_ids)
                self.assertIsNotNone(
                    self.con.execute(
                        f"SELECT value FROM metrics.{view} WHERE period=CAST(? AS DATE)"
                        + (" AND department_id='ALL'" if metric_id not in {"M16", "M18", "M20"} else ""),
                        [period],
                    ).fetchone()
                )
        task_value = self.con.execute(
            "SELECT value FROM metrics.dashboard_task_completion_monthly WHERE period=DATE '2026-09-01' AND department_id='ALL'"
        ).fetchone()
        self.assertIsNotNone(task_value)
        self.assertIn("M22", dictionary_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
