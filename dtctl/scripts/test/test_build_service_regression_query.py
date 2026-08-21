import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from build_service_regression_query import build_service_regression_query


class BuildServiceRegressionQueryTest(unittest.TestCase):
    def test_builds_one_before_after_query(self) -> None:
        result = build_service_regression_query(
            environment="prd",
            service="sf-item",
            before_start="2026-08-20T11:25:00Z",
            before_end="2026-08-20T11:55:00Z",
            after_start="2026-08-20T12:05:00Z",
            after_end="2026-08-20T12:35:00Z",
        )

        self.assertEqual(result.count("timeseries {"), 2)
        self.assertEqual(result.count("dt.service.request.count"), 4)
        self.assertEqual(result.count("dt.service.request.response_time"), 2)
        self.assertEqual(result.count("| append ["), 1)
        self.assertIn('comparison_window = "before"', result)
        self.assertIn('comparison_window = "after"', result)
        self.assertIn('startsWith(service.name, "[prd]")', result)

    def test_rejects_reversed_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "end must be later"):
            build_service_regression_query(
                environment="prd",
                service="sf-item",
                before_start="2026-08-20T12:00:00Z",
                before_end="2026-08-20T11:00:00Z",
                after_start="2026-08-20T12:05:00Z",
                after_end="2026-08-20T12:35:00Z",
            )


if __name__ == "__main__":
    unittest.main()
