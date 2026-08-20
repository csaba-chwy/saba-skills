import base64
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from build_logs_events_link import build_link


class BuildLogsEventsLinkTest(unittest.TestCase):
    def test_matches_logs_and_events_advanced_mode_example(self) -> None:
        dql = (
            "fetch logs //, scanLimitGBytes: 500, samplingRatio: 1000\n"
            "| sort timestamp desc"
        )

        result = build_link("https://dlg34900.apps.dynatrace.com/", dql)
        parsed = urlsplit(result)
        decoded_dql = unquote(base64.b64decode(parsed.fragment).decode("utf-8"))
        params = parse_qs(parsed.query)

        self.assertEqual(
            parsed.path,
            "/ui/apps/dynatrace.classic.logs.events/ui/logs-events",
        )
        self.assertEqual(params["advancedQueryMode"], ["true"])
        self.assertEqual(params["visualizationType"], ["table"])
        self.assertEqual(
            params["visibleColumns"],
            ["timestamp", "status", "content"],
        )
        self.assertEqual(
            parsed.fragment,
            "ZmV0Y2glMjBsb2dzJTIwJTJGJTJGJTJDJTIwc2NhbkxpbWl0R0J5dGVzJTNBJTIwNTAw"
            "JTJDJTIwc2FtcGxpbmdSYXRpbyUzQSUyMDEwMDAlMEElN0MlMjBzb3J0JTIwdGltZXN0"
            "YW1wJTIwZGVzYw==",
        )
        self.assertEqual(decoded_dql, dql)
        self.assertIn("\n| sort", decoded_dql)

    def test_normalizes_line_endings_and_rejects_invalid_input(self) -> None:
        result = build_link(
            "https://example.apps.dynatrace.com",
            "fetch spans\r\n| limit 20\r\n",
        )
        decoded_dql = unquote(
            base64.b64decode(urlsplit(result).fragment).decode("utf-8")
        )

        self.assertEqual(decoded_dql, "fetch spans\n| limit 20")
        with self.assertRaisesRegex(ValueError, "absolute https URL"):
            build_link("http://example.com", "fetch logs")
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            build_link("https://example.com", "\n")

    def test_rejects_inline_pipeline_commands(self) -> None:
        with self.assertRaisesRegex(ValueError, "pipeline command on its own line"):
            build_link(
                "https://example.apps.dynatrace.com",
                "fetch logs | filter loglevel == \"ERROR\" | limit 20",
            )

    def test_allows_pipe_characters_inside_quoted_values(self) -> None:
        dql = (
            "fetch logs\n"
            "| filter contains(content, \"left | right\")\n"
            "| limit 20"
        )

        result = build_link("https://example.apps.dynatrace.com", dql)
        decoded_dql = unquote(
            base64.b64decode(urlsplit(result).fragment).decode("utf-8")
        )

        self.assertEqual(decoded_dql, dql)


if __name__ == "__main__":
    unittest.main()
