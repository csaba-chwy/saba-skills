import base64
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from build_logs_events_graph_link import build_graph_link


REGIONAL_TRAFFIC_DQL = """timeseries requests = sum(dt.service.request.count, filter: { startsWith(service.name, "[prd]") and endsWith(service.name, "]agentic-commerce-orchestrator") }), by: { service.name }, interval: 15m, from: "2026-08-19T20:33:13Z", to: "2026-08-20T20:33:13Z", nonempty: true
| sort service.name asc"""


class BuildLogsEventsGraphLinkTest(unittest.TestCase):
    def test_builds_time_axis_bar_chart_for_regional_traffic(self) -> None:
        result = build_graph_link(
            "https://jql50548.apps.dynatrace.com/",
            REGIONAL_TRAFFIC_DQL,
        )
        parsed = urlsplit(result)
        decoded_dql = unquote(base64.b64decode(parsed.fragment).decode("utf-8"))
        params = parse_qs(parsed.query)

        self.assertEqual(parsed.netloc, "jql50548.apps.dynatrace.com")
        self.assertEqual(
            parsed.path,
            "/ui/apps/dynatrace.classic.logs.events/ui/logs-events",
        )
        self.assertEqual(params["advancedQueryMode"], ["true"])
        self.assertEqual(params["visualizationType"], ["barChart"])
        self.assertNotIn("visibleColumns", params)
        self.assertEqual(decoded_dql, REGIONAL_TRAFFIC_DQL)
        self.assertIn("interval: 15m", decoded_dql)
        self.assertNotIn("summarize", decoded_dql)
        self.assertNotIn("scalar: true", decoded_dql)

    def test_rejects_non_timeseries_dql(self) -> None:
        with self.assertRaisesRegex(ValueError, "must start with a timeseries"):
            build_graph_link(
                "https://example.apps.dynatrace.com",
                "fetch logs\n| limit 20",
            )

    def test_rejects_timeseries_without_explicit_interval(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit timeseries interval"):
            build_graph_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count)\n"
                "| fields timeframe, interval, requests",
            )

    def test_rejects_scalar_timeseries(self) -> None:
        with self.assertRaisesRegex(ValueError, "preserve native timeseries arrays"):
            build_graph_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count, scalar:true), "
                "interval:15m",
            )

    def test_rejects_summarized_timeseries(self) -> None:
        with self.assertRaisesRegex(ValueError, "preserve time buckets"):
            build_graph_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count), interval:15m\n"
                "| summarize requests=sum(arraySum(requests))",
            )

    def test_rejects_inline_graph_pipeline_commands(self) -> None:
        with self.assertRaisesRegex(ValueError, "pipeline command on its own line"):
            build_graph_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count), interval:15m "
                "| fields timeframe, requests",
            )


if __name__ == "__main__":
    unittest.main()
