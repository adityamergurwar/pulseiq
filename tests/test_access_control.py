import unittest
from unittest.mock import patch

import pandas as pd

from pulseiq import app_common


class AccessControlTests(unittest.TestCase):
    def test_salary_level_access_is_limited_to_admin_and_hr(self):
        self.assertTrue(app_common.can_view_salary({"role": "ADMIN"}))
        self.assertTrue(app_common.can_view_salary({"role": "HR"}))
        self.assertFalse(app_common.can_view_salary({"role": "MANAGER"}))
        self.assertFalse(app_common.can_view_salary({"role": "EXECUTIVE"}))

    def test_manager_and_hr_cannot_widen_their_department_scope(self):
        for role in ("MANAGER", "HR"):
            with self.subTest(role=role):
                user = {"role": role, "department_id": "D01", "team_id": "T01"}
                self.assertEqual(app_common.visible_departments(user), ["D01"])
                clause, params = app_common.scoped_dept_clause(user, "D02")
                self.assertEqual(clause, "= ?")
                self.assertEqual(params, ["D01"])

    def test_executive_is_company_scoped_and_admin_can_choose_departments(self):
        executive = {"role": "EXECUTIVE", "department_id": "D01"}
        self.assertEqual(app_common.visible_departments(executive), ["ALL"])
        self.assertEqual(app_common.scoped_dept_clause(executive, "D02"), ("= ?", ["ALL"]))

        with patch.object(app_common, "query_df", return_value=pd.DataFrame({"department_id": ["D01", "D02"]})):
            admin = {"role": "ADMIN"}
            self.assertEqual(app_common.visible_departments(admin), ["ALL", "D01", "D02"])
            self.assertEqual(app_common.visible_departments(admin, include_all=False), ["D01", "D02"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
