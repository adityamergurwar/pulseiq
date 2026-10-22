import unittest
from fastapi import HTTPException

from pulseiq.api import API_METRICS, app, get_metric, list_metrics


class AnalyticsApiTests(unittest.TestCase):
    def test_openapi_contains_five_governed_metrics(self):
        self.assertEqual(set(API_METRICS),{"M01","M04","M09","M20","M22"})
        schema=app.openapi()
        self.assertIn("/api/metrics/{metric_id}",schema["paths"])
        self.assertIn("/api/metrics",schema["paths"])

    def test_metric_response_includes_definition_lineage_and_freshness(self):
        result=get_metric("M01","2026-09","ALL")
        self.assertEqual(result["metric_id"],"M01")
        self.assertGreater(result["value"],0)
        self.assertIn("formula",result["metric"])
        self.assertIn("source_table",result["metric"])
        self.assertIn("owner_team",result["metric"])
        self.assertIn("data_cutoff",result)
        self.assertIn("privacy",result)

    def test_metric_metadata_endpoint_returns_five(self):
        result=list_metrics()
        self.assertEqual(len(result["metrics"]),5)
        self.assertTrue(result["freshness"])

    def test_unknown_metric_and_bad_period_are_rejected(self):
        with self.assertRaises(HTTPException): get_metric("M99","2026-09","ALL")
        with self.assertRaises(HTTPException): get_metric("M01","2026-13","ALL")


if __name__=="__main__": unittest.main(verbosity=2)
