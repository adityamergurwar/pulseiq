import unittest

from etl import _contract_issues


class SeededIssueDispositionTests(unittest.TestCase):
    def test_reversed_leave_and_expense_rows_are_quarantined(self):
        leave = {
            "leave_request_id": "LR-002286",
            "start_date": "2026-02-10",
            "end_date": "2026-02-09",
            "days": 1,
        }
        leave_issues = _contract_issues("fact_leave", leave, list(leave), {})
        self.assertIn("end_date precedes start_date; leave row quarantined", leave_issues)

        expense = {
            "expense_id": "EXP-00371",
            "total_amount": 1500.0,
            "amount_excl_gst": 1000.0,
            "gst_amount": 0.0,
        }
        expense_issues = _contract_issues("fact_expense", expense, list(expense), {})
        self.assertIn(
            "total_amount does not equal amount_excl_gst + gst_amount; expense row quarantined",
            expense_issues,
        )

    def test_valid_leave_and_expense_rows_are_not_quarantined(self):
        leave = {"start_date": "2026-02-09", "end_date": "2026-02-10", "days": 2}
        expense = {"total_amount": 118.0, "amount_excl_gst": 100.0, "gst_amount": 18.0}
        self.assertEqual(_contract_issues("fact_leave", leave, list(leave), {}), [])
        self.assertEqual(_contract_issues("fact_expense", expense, list(expense), {}), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
