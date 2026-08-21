import subprocess
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from build_service_rundown_query import (
    build_rundown_query,
    build_scalar_rundown_query,
    build_service_error_totals_query,
    build_top_service_errors_query,
)
from build_logs_events_graph_link import build_graph_link


class BuildServiceRundownQueryTest(unittest.TestCase):
    def test_builds_default_health_timeline(self) -> None:
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

    def test_builds_request_only_timeline_for_focused_question(self) -> None:
        result = build_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T21:37:11Z",
            end="2026-08-20T21:37:11Z",
            metrics=("requests",),
        )

        self.assertIn("requests = sum(dt.service.request.count)", result)
        self.assertIn("fields timeframe, interval, requests", result)
        self.assertNotIn("failed_requests", result)
        self.assertNotIn("response_time", result)

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

    def test_cli_limits_query_to_selected_metric(self) -> None:
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
                "--metric",
                "requests",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("fields timeframe, interval, requests", result.stdout)
        self.assertNotIn("failed_requests", result.stdout)
        self.assertNotIn("response_time", result.stdout)

    def test_rundown_query_is_accepted_by_time_axis_graph_link(self) -> None:
        dql = build_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T21:37:11Z",
            end="2026-08-20T21:37:11Z",
        )

        result = build_graph_link(
            "https://example.apps.dynatrace.com",
            dql,
        )

        self.assertIn("visualizationType=barChart", result)

    def test_builds_scalar_rundown_for_table_output(self) -> None:
        result = build_scalar_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
        )

        self.assertIn(
            "requests = sum(dt.service.request.count, scalar: true)", result
        )
        self.assertIn("default: 0, scalar: true", result)
        self.assertIn("latency_p95_ms = latency_p95_us / 1000.0", result)
        self.assertIn(
            "fields requests, failed_requests, error_rate, latency_p95_ms", result
        )

    def test_scalar_query_fetches_only_the_requested_measure(self) -> None:
        requests = build_scalar_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
            metrics=("requests",),
        )
        error_rate = build_scalar_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
            metrics=("error-rate",),
        )

        self.assertIn("fields requests", requests)
        self.assertNotIn("failed_requests", requests)
        self.assertNotIn("response_time", requests)
        self.assertIn("requests = sum", error_rate)
        self.assertIn("failed_requests = sum", error_rate)
        self.assertIn("fields error_rate", error_rate)
        self.assertNotIn("response_time", error_rate)

    def test_scalar_query_supports_requested_latency_percentile(self) -> None:
        result = build_scalar_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
            metrics=("latency",),
            latency_percentile=99,
        )

        self.assertIn("response_time, 99, scalar: true", result)
        self.assertIn("fields latency_p99_ms", result)
        self.assertNotIn("request.count", result)

    def test_scalar_failure_query_keeps_request_metric_presence(self) -> None:
        result = build_scalar_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
            metrics=("failures",),
        )

        self.assertIn(
            "metric_presence = sum(dt.service.request.count, scalar: true)", result
        )
        self.assertIn("fields failed_requests, metric_presence", result)

    def test_scalar_error_rate_exposes_existing_request_input_as_presence(self) -> None:
        result = build_scalar_rundown_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
            metrics=("error-rate",),
        )

        self.assertIn("metric_presence = requests", result)
        self.assertIn("fields error_rate, metric_presence", result)

    def test_builds_service_error_totals_by_deployment(self) -> None:
        result = build_service_error_totals_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
        )

        self.assertIn("scalar: true", result)
        self.assertIn("by: { service.name, dt.entity.service, failed }", result)
        self.assertIn(
            "fields service.name, dt.entity.service, failed, requests", result
        )

    def test_builds_ranked_service_error_breakdown(self) -> None:
        result = build_top_service_errors_query(
            environment="stg",
            service="checkout-b",
            start="2026-08-20T20:00:00Z",
            end="2026-08-20T21:00:00Z",
            limit=7,
        )

        self.assertIn("by: { endpoint.name, http.response.status_code }", result)
        self.assertIn("filter failures > 0", result)
        self.assertIn("sort failures desc, endpoint.name asc", result)
        self.assertTrue(result.endswith("| limit 7"))

    def test_rejects_oversized_error_breakdown(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 20"):
            build_top_service_errors_query(
                environment="prd",
                service="sf-item",
                start="2026-08-19T22:24:02Z",
                end="2026-08-20T22:24:02Z",
                limit=21,
            )


if __name__ == "__main__":
    unittest.main()
