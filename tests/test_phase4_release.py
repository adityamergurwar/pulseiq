import unittest

import pandas as pd

from scripts.build_monthly_pack import budget_chart, re_full_month


class Phase4ReleaseTests(unittest.TestCase):
    def test_month_argument_contract(self):
        self.assertTrue(re_full_month("2026-09"))
        self.assertFalse(re_full_month("2026-13"))
        self.assertFalse(re_full_month("Sep-2026"))

    def test_new_department_does_not_break_monthly_chart(self):
        frame = pd.DataFrame(
            [
                {
                    "department_id": "D99",
                    "budget_cost": 1_000_000.0,
                    "actual_cost": 1_050_000.0,
                    "variance": 50_000.0,
                    "variance_pct": 5.0,
                    "status": "Amber",
                }
            ]
        )
        drawing = budget_chart(frame)
        chart = next(node for node in drawing.contents if hasattr(node, "categoryAxis"))
        self.assertEqual(chart.categoryAxis.categoryNames, ["D99"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
