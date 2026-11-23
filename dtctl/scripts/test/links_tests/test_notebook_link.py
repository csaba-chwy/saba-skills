import json
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote_plus, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from links.notebook_link import build_link


class BuildNotebookTableLinkTest(unittest.TestCase):
    def test_encodes_exact_multiline_dql_as_notebooks_table(self) -> None:
        dql = (
            "fetch logs, from:\"2026-08-20T20:00:00Z\", to:\"2026-08-20T20:05:00Z\"\n"
            "| filter loglevel == \"ERROR\"\n"
            "| fields timestamp, loglevel\n"
            "| limit 20"
        )

        result = build_link("https://test.apps.dynatrace.com/", dql, title="Logs")
        parsed = urlsplit(result)

        self.assertEqual(parsed.netloc, "test.apps.dynatrace.com")
        self.assertEqual(parsed.path, "/ui/intent/dynatrace.notebooks/view-query")
        self.assertEqual(
            json.loads(unquote_plus(parsed.fragment)),
            {
                "dt.query": dql,
                "title": "Logs",
                "visualization": "table",
                "visualizationSettings": {"autoSelectVisualization": False},
            },
        )

    def test_normalizes_line_endings_and_rejects_invalid_input(self) -> None:
        result = build_link(
            "https://example.apps.dynatrace.com",
            "fetch spans\r\n| limit 20\r\n",
            title="Spans",
        )
        decoded_dql = json.loads(unquote_plus(urlsplit(result).fragment))["dt.query"]

        self.assertEqual(decoded_dql, "fetch spans\n| limit 20")
        with self.assertRaisesRegex(ValueError, "absolute https URL"):
            build_link("http://example.com", "fetch logs", title="Logs")
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            build_link("https://example.com", "\n", title="Logs")

    def test_rejects_inline_pipeline_commands(self) -> None:
        with self.assertRaisesRegex(ValueError, "pipeline command on its own line"):
            build_link(
                "https://example.apps.dynatrace.com",
                "fetch logs | filter loglevel == \"ERROR\" | limit 20",
                title="Logs",
            )

    def test_allows_pipe_characters_inside_quoted_values(self) -> None:
        dql = (
            "fetch logs\n"
            "| filter contains(content, \"left | right\")\n"
            "| limit 20"
        )

        result = build_link("https://example.apps.dynatrace.com", dql, title="Logs")
        decoded_dql = json.loads(unquote_plus(urlsplit(result).fragment))["dt.query"]

        self.assertEqual(decoded_dql, dql)


REGIONAL_TRAFFIC_DQL = """timeseries requests = sum(dt.service.request.count, filter: { startsWith(service.name, "[prd]") and endsWith(service.name, "]agentic-commerce-orchestrator") }), by: { service.name }, interval: 15m, from: "2026-08-19T20:33:13Z", to: "2026-08-20T20:33:13Z", nonempty: true
| sort service.name asc"""


class BuildNotebookLineChartLinkTest(unittest.TestCase):
    def test_encodes_notebooks_line_chart_for_regional_traffic(self) -> None:
        result = build_link(
            "https://test.apps.dynatrace.com/",
            REGIONAL_TRAFFIC_DQL,
            title="Requests per 15m by region",
            line_chart=True,
        )
        parsed = urlsplit(result)

        self.assertEqual(parsed.path, "/ui/intent/dynatrace.notebooks/view-query")
        self.assertEqual(
            json.loads(unquote_plus(parsed.fragment)),
            {
                "dt.query": REGIONAL_TRAFFIC_DQL,
                "title": "Requests per 15m by region",
                "visualization": "lineChart",
                "visualizationSettings": {"autoSelectVisualization": False},
            },
        )

    def test_rejects_non_timeseries_dql(self) -> None:
        with self.assertRaisesRegex(ValueError, "must start with a timeseries"):
            build_link(
                "https://example.apps.dynatrace.com",
                "fetch logs\n| limit 20",
                title="Requests per 15m",
                line_chart=True,
            )

    def test_rejects_timeseries_without_explicit_interval(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit timeseries interval"):
            build_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count)\n"
                "| fields timeframe, interval, requests",
                title="Requests per 15m",
                line_chart=True,
            )

    def test_rejects_scalar_timeseries(self) -> None:
        with self.assertRaisesRegex(ValueError, "preserve native timeseries arrays"):
            build_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count, scalar:true), "
                "interval:15m",
                title="Requests per 15m",
                line_chart=True,
            )

    def test_rejects_summarized_timeseries(self) -> None:
        with self.assertRaisesRegex(ValueError, "preserve time buckets"):
            build_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count), interval:15m\n"
                "| summarize requests=sum(arraySum(requests))",
                title="Requests per 15m",
                line_chart=True,
            )

    def test_rejects_inline_graph_pipeline_commands(self) -> None:
        with self.assertRaisesRegex(ValueError, "pipeline command on its own line"):
            build_link(
                "https://example.apps.dynatrace.com",
                "timeseries requests=sum(dt.service.request.count), interval:15m "
                "| fields timeframe, requests",
                title="Requests per 15m",
                line_chart=True,
            )


if __name__ == "__main__":
    unittest.main()
