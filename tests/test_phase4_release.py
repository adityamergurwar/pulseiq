import unittest
from pathlib import Path

import duckdb
import pandas as pd

from scripts.build_monthly_pack import budget_chart, re_full_month

ROOT = Path(__file__).resolve().parents[1]


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

    def test_final_challenge_overdue_share_reconciles(self):
        with duckdb.connect(str(ROOT / "pulseiq.duckdb"), read_only=True) as con:
            metric = con.execute(
                "SELECT period,value FROM metrics.m29_overdue_receivables_share ORDER BY period DESC LIMIT 1"
            ).fetchone()
            expected = con.execute(
                """SELECT as_of_date,
                    100.0*SUM(CASE WHEN ageing_bucket<>'Not due' THEN balance ELSE 0 END)/SUM(balance)
                    FROM metrics.dashboard_receivables_asof
                    WHERE as_of_date=(SELECT MAX(as_of_date) FROM metrics.dashboard_receivables_asof)
                    GROUP BY 1"""
            ).fetchone()
        self.assertEqual(metric[0], expected[0])
        self.assertAlmostEqual(float(metric[1]), float(expected[1]), places=8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
