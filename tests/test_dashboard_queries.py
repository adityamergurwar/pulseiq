import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from pulseiq.app_common import (
    company_metric_for_period,
    config_value,
    prior_month_headcount,
    quarantine_summary_for_run,
    query_df,
)


class DashboardQueryTests(unittest.TestCase):
    def test_config_value_reads_streamlit_secrets_and_environment_takes_precedence(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(st, "secrets", {"PULSEIQ_REQUIRE_LOGIN": "1"}):
            self.assertEqual(config_value("PULSEIQ_REQUIRE_LOGIN", "0"), "1")
            self.assertEqual(config_value("MISSING_SETTING", "fallback"), "fallback")

        with patch.dict("os.environ", {"PULSEIQ_REQUIRE_LOGIN": "0"}), patch.object(st, "secrets", {"PULSEIQ_REQUIRE_LOGIN": "1"}):
            self.assertEqual(config_value("PULSEIQ_REQUIRE_LOGIN", "1"), "0")

    def test_dashboard_queries_bind_scopes_and_match_warehouse_columns(self):
        latest = query_df("SELECT MAX(period) FROM metrics.m01_headcount").iloc[0, 0]
        self.assertIsNotNone(latest)
        selected_period = latest.date() if hasattr(latest, "date") else date.fromisoformat(str(latest))

        for department_id in ("ALL", "D01"):
            with self.subTest(department_id=department_id):
                result = prior_month_headcount(department_id, selected_period)
                self.assertEqual(len(result), 1)
                self.assertIsNotNone(result.iloc[0]["value"])
                self.assertGreater(float(result.iloc[0]["value"]), 0)

        scorecard_views = (
            "metrics.m01_headcount",
            "metrics.m04_attrition_monthly",
            "metrics.m13_attendance_rate",
            "metrics.m11_overtime_share",
            "metrics.m09_payroll_cost",
            "metrics.m16_revenue",
            "metrics.m18_operating_margin",
            "metrics.dashboard_task_completion_monthly",
        )
        for view in scorecard_views:
            with self.subTest(scorecard_view=view):
                result = company_metric_for_period(view, selected_period)
                self.assertEqual(list(result.columns), ["value"])
                self.assertEqual(len(result), 1)

        latest_run = query_df(
            "SELECT run_id FROM audit.etl_run_log ORDER BY started_at DESC LIMIT 1"
        ).iloc[0, 0]
        quarantine = quarantine_summary_for_run(str(latest_run))
        self.assertGreater(len(quarantine), 0)
        self.assertEqual(
            list(quarantine.columns), ["table_name", "reason", "rows"]
        )
        self.assertIn("fact_payroll", set(quarantine.table_name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
