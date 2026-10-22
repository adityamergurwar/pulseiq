import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from pulseiq.app_common import config_value, prior_month_headcount, query_df


class DashboardQueryTests(unittest.TestCase):
    def test_config_value_reads_streamlit_secrets_and_environment_takes_precedence(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(st, "secrets", {"PULSEIQ_REQUIRE_LOGIN": "1"}):
            self.assertEqual(config_value("PULSEIQ_REQUIRE_LOGIN", "0"), "1")
            self.assertEqual(config_value("MISSING_SETTING", "fallback"), "fallback")

        with patch.dict("os.environ", {"PULSEIQ_REQUIRE_LOGIN": "0"}), patch.object(st, "secrets", {"PULSEIQ_REQUIRE_LOGIN": "1"}):
            self.assertEqual(config_value("PULSEIQ_REQUIRE_LOGIN", "1"), "0")

    def test_prior_month_headcount_binds_both_department_filters(self):
        latest = query_df("SELECT MAX(period) FROM metrics.m01_headcount").iloc[0, 0]
        self.assertIsNotNone(latest)
        selected_period = latest.date() if hasattr(latest, "date") else date.fromisoformat(str(latest))

        for department_id in ("ALL", "D01"):
            with self.subTest(department_id=department_id):
                result = prior_month_headcount(department_id, selected_period)
                self.assertEqual(len(result), 1)
                self.assertIsNotNone(result.iloc[0]["value"])
                self.assertGreater(float(result.iloc[0]["value"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
