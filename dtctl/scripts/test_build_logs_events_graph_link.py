import base64
import unittest
from urllib.parse import parse_qs, unquote, urlsplit

from build_logs_events_graph_link import build_graph_link


REGIONAL_TRAFFIC_DQL = """timeseries requests = sum(dt.service.request.count, filter: { startsWith(service.name, "[prd]") and endsWith(service.name, "]agentic-commerce-orchestrator") }), by: { service.name }, interval: 15m, from: "2026-08-19T20:33:13Z", to: "2026-08-20T20:33:13Z", nonempty: true
| fields timeframe, interval, service.name, requests
| sort service.name asc"""


class BuildLogsEventsGraphLinkTest(unittest.TestCase):
    def test_builds_line_chart_for_regional_traffic_prompt(self) -> None:
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
        self.assertEqual(params["visualizationType"], ["lineChart"])
        self.assertNotIn("visibleColumns", params)
        self.assertEqual(decoded_dql, REGIONAL_TRAFFIC_DQL)
        self.assertIn("interval: 15m", decoded_dql)
        self.assertIn("service.name, requests", decoded_dql)

    def test_rejects_non_timeseries_dql(self) -> None:
        with self.assertRaisesRegex(ValueError, "must start with a timeseries"):
            build_graph_link(
                "https://example.apps.dynatrace.com",
                "fetch logs\n| limit 20",
            )


if __name__ == "__main__":
    unittest.main()
