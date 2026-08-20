import subprocess
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from build_service_rundown_query import build_rundown_query


class BuildServiceRundownQueryTest(unittest.TestCase):
    def test_builds_default_three_metric_timeline(self) -> None:
        result = build_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T21:37:11Z",
            end="2026-08-20T21:37:11Z",
        )

        self.assertTrue(result.startswith("timeseries {\n"))
        self.assertIn("requests = sum(dt.service.request.count)", result)
        self.assertIn("filter: { failed == true }, default: 0", result)
        self.assertIn(
            "latency_p95_us = percentile(dt.service.request.response_time, 95)",
            result,
        )
        self.assertIn(
            "error_rate = if(requests[] > 0, "
            "100.0 * failed_requests[] / requests[], else: 0.0)",
            result,
        )
        self.assertIn("latency_p95_ms = latency_p95_us[] / 1000.0", result)
        self.assertIn('startsWith(service.name, "[prd]")', result)
        self.assertIn('endsWith(service.name, "]sf-item")', result)
        self.assertNotIn("by: {", result)

    def test_adapts_grouping_filter_interval_and_percentile(self) -> None:
        result = build_rundown_query(
            environment="stg",
            service="checkout-b",
            start="2026-08-20T20:00:00Z",
            end="2026-08-20T21:00:00Z",
            interval="5m",
            group_by=("service.name", "endpoint.name"),
            additional_filters=('endpoint.name == "GET /api/checkout"',),
            latency_percentile=99,
        )

        self.assertIn("interval: 5m, by: { service.name, endpoint.name }", result)
        self.assertIn('and endpoint.name == "GET /api/checkout"', result)
        self.assertIn("latency_p99_ms", result)
        self.assertIn(
            "fields timeframe, interval, service.name, endpoint.name, requests",
            result,
        )

    def test_rejects_pipeline_in_additional_filter(self) -> None:
        with self.assertRaisesRegex(ValueError, "pipeline-free"):
            build_rundown_query(
                environment="prd",
                service="sf-item",
                start="2026-08-19T21:37:11Z",
                end="2026-08-20T21:37:11Z",
                additional_filters=("failed == true | limit 1",),
            )

    def test_rejects_relative_or_reversed_timeframes(self) -> None:
        with self.assertRaisesRegex(ValueError, "RFC 3339"):
            build_rundown_query(
                environment="prd",
                service="sf-item",
                start="now()-24h",
                end="2026-08-20T21:37:11Z",
            )
        with self.assertRaisesRegex(ValueError, "later than start"):
            build_rundown_query(
                environment="prd",
                service="sf-item",
                start="2026-08-20T21:37:11Z",
                end="2026-08-19T21:37:11Z",
            )

    def test_cli_prints_query(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SRC_DIR / "build_service_rundown_query.py"),
                "--environment",
                "prd",
                "--service",
                "sf-item",
                "--from-time",
                "2026-08-19T21:37:11Z",
                "--to-time",
                "2026-08-20T21:37:11Z",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("timeseries {", result.stdout)
        self.assertIn("latency_p95_ms", result.stdout)


if __name__ == "__main__":
    unittest.main()
