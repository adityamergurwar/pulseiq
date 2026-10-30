import unittest
from pathlib import Path

import duckdb

from pulseiq.app_common import DB_PATH


class Phase2ViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Path(DB_PATH).exists():
            raise unittest.SkipTest("Run python etl.py to build the warehouse first.")
        cls.con = duckdb.connect(str(DB_PATH), read_only=True)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "con", None):
            cls.con.close()

    def test_attendance_metric_uses_weighted_scheduled_day_denominator(self):
        manual = self.con.execute(
            """SELECT SUM(a.present_days+0.5*a.half_days_unpaid)/NULLIF(SUM(a.scheduled_days),0)
               FROM clean.fact_attendance_monthly a
               JOIN warehouse.dim_employee e USING(employee_key)
               WHERE a.period_end_date=DATE '2026-09-30' AND e.department_id='D01'"""
        ).fetchone()[0]
        governed = self.con.execute(
            "SELECT value FROM metrics.m13_attendance_rate WHERE period=DATE '2026-09-01' AND department_id='D01'"
        ).fetchone()[0]
        self.assertAlmostEqual(manual, governed, places=10)

    def test_calendar_and_leave_type_views_have_month_context_and_privacy_floor(self):
        january = self.con.execute(
            "SELECT public_holiday_count,long_weekend_holiday_count FROM metrics.dashboard_calendar_monthly WHERE period=DATE '2026-01-01'"
        ).fetchone()
        self.assertEqual(january, (3, 1))
        low_group = self.con.execute(
            "SELECT COUNT(*) FROM metrics.dashboard_leave_type_monthly WHERE people<5 OR leave_days<0"
        ).fetchone()[0]
        rows = self.con.execute("SELECT COUNT(*) FROM metrics.dashboard_leave_type_monthly").fetchone()[0]
        self.assertEqual(low_group, 0)
        self.assertGreater(rows, 0)

    def test_company_attrition_exit_split_matches_governed_metrics(self):
        mismatches = self.con.execute(
            """SELECT COUNT(*) FROM metrics.dashboard_attrition_company a
               JOIN metrics.m03_exits e ON e.period=a.period AND e.department_id='ALL'
               JOIN metrics.m04_attrition_monthly r ON r.period=a.period AND r.department_id='ALL'
               WHERE a.exits<>e.value OR ABS(a.attrition_pct-r.value)>1e-10
                  OR a.voluntary_exits<0 OR a.voluntary_exits>a.exits"""
        ).fetchone()[0]
        self.assertEqual(mismatches, 0)
        for view in ("dashboard_exit_tenure", "dashboard_exit_reasons"):
            low_groups = self.con.execute(
                f"SELECT COUNT(*) FROM metrics.{view} WHERE exits<5"
            ).fetchone()[0]
            self.assertEqual(low_groups, 0, view)
        low_risk_groups = self.con.execute(
            "SELECT COUNT(*) FROM metrics.dashboard_predicted_risk_company WHERE people<10"
        ).fetchone()[0]
        self.assertEqual(low_risk_groups, 0)

    def test_team_productivity_metrics_match_independent_team_sprint_calculations(self):
        teams, sprints = self.con.execute(
            "SELECT COUNT(DISTINCT team_id),COUNT(DISTINCT sprint_id) FROM clean.fact_task"
        ).fetchone()
        self.assertEqual((teams, sprints), (16, 38))
        for team in ("T01", "T02"):
            manual = self.con.execute(
                """SELECT
                     100.0*COUNT(*) FILTER(WHERE status='Done')/NULLIF(COUNT(*) FILTER(WHERE status<>'Cancelled'),0),
                     100.0*COUNT(*) FILTER(WHERE status='Done' AND completed_on_time='Y')/NULLIF(COUNT(*) FILTER(WHERE status='Done'),0),
                     SUM(story_points) FILTER(WHERE status='Done'),
                     AVG(date_diff('day',started_date,completed_date)) FILTER(WHERE status='Done')
                   FROM clean.fact_task WHERE sprint_id='SP-01' AND team_id=?""",
                [team],
            ).fetchone()
            governed = self.con.execute(
                """SELECT c.value,o.value,v.value,t.value
                   FROM metrics.m22_task_completion c
                   JOIN metrics.m23_on_time_delivery o USING(sprint_id,team_id)
                   JOIN metrics.m24_velocity v USING(sprint_id,team_id)
                   JOIN metrics.m25_cycle_time t USING(sprint_id,team_id)
                   WHERE c.sprint_id='SP-01' AND c.team_id=?""",
                [team],
            ).fetchone()
            for actual, expected in zip(manual, governed):
                self.assertAlmostEqual(actual, expected, places=10, msg=team)

    def test_budget_variance_and_target_status_follow_documented_direction(self):
        bad_variance = self.con.execute(
            """SELECT COUNT(*) FROM metrics.dashboard_budget_actuals
               WHERE ABS(variance-(actual_cost-budget_cost))>0.01"""
        ).fetchone()[0]
        bad_targets = self.con.execute(
            """SELECT COUNT(*) FROM metrics.dashboard_kpi_targets
               WHERE status<>CASE WHEN actual_value IS NULL THEN 'NO DATA'
                                  WHEN (direction='Higher is better' AND actual_value>=target_value)
                                      OR (direction='Lower is better' AND actual_value<=target_value)
                                  THEN 'GREEN' ELSE 'RED' END"""
        ).fetchone()[0]
        self.assertEqual(bad_variance, 0)
        self.assertEqual(bad_targets, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
