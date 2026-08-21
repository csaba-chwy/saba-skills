import json
import subprocess
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from run_service_regression import (
    execute_regression_check,
    render_markdown,
    resolve_comparison_windows,
)


class FakeRunner:
    def __init__(self, *, regressed: bool = True, no_data: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.regressed = regressed
        self.no_data = no_data

    def __call__(self, command, timeout):
        self.commands.append(list(command))
        if command[1:3] == ["config", "describe-context"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    "Environment: https://prod.example.com\n"
                    "Safety Level: readonly\n"
                ),
                stderr="",
            )
        if command[1:4] == ["--context", "prod", "auth"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="Auth type: OAuth\nRefresh token: present\n",
                stderr="",
            )
        if self.no_data:
            records = [
                {
                    "comparison_window": label,
                    "requests": None,
                    "failed_requests": 0,
                    "latency_p95_ms": None,
                }
                for label in ("before", "after")
            ]
            return subprocess.CompletedProcess(
                command, 0, stdout=json.dumps({"records": records}), stderr=""
            )
        after = (
            {
                "comparison_window": "after",
                "requests": 600,
                "failed_requests": 24,
                "error_rate": 4.0,
                "latency_p95_ms": 450.0,
            }
            if self.regressed
            else {
                "comparison_window": "after",
                "requests": 980,
                "failed_requests": 5,
                "error_rate": 0.51,
                "latency_p95_ms": 205.0,
            }
        )
        records = [
            {
                "comparison_window": "before",
                "requests": 1000,
                "failed_requests": 5,
                "error_rate": 0.5,
                "latency_p95_ms": 200.0,
            },
            after,
        ]
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps({"records": records}), stderr=""
        )


class RunServiceRegressionTest(unittest.TestCase):
    def test_resolves_guarded_equal_windows(self) -> None:
        result = resolve_comparison_windows(
            "2026-08-20T12:00:00Z", window="30m", guard="5m"
        )

        self.assertEqual(result.before_start, "2026-08-20T11:25:00Z")
        self.assertEqual(result.before_end, "2026-08-20T11:55:00Z")
        self.assertEqual(result.after_start, "2026-08-20T12:05:00Z")
        self.assertEqual(result.after_end, "2026-08-20T12:35:00Z")

    def test_runs_one_comparison_query_and_reports_thresholds(self) -> None:
        runner = FakeRunner()
        summary = execute_regression_check(
            environment="prd",
            service="sf-item",
            change_time="2026-08-20T12:00:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(summary)

        queries = [command for command in runner.commands if "query" in command]
        self.assertEqual(len(queries), 1)
        self.assertIn("| append [", queries[0][4])
        self.assertTrue(summary.regression_detected)
        self.assertIn("Regression detected", markdown)
        self.assertIn("error rate increased", markdown)
        self.assertIn("request volume dropped", markdown)
        self.assertIn("visualizationType=table", markdown)

    def test_stops_cleanly_when_thresholds_are_not_exceeded(self) -> None:
        summary = execute_regression_check(
            environment="prd",
            service="sf-item",
            change_time="2026-08-20T12:00:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=FakeRunner(regressed=False),
        )

        self.assertFalse(summary.regression_detected)
        self.assertIn("Stop here", render_markdown(summary))

    def test_rejects_guard_that_consumes_the_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "guard must be shorter"):
            resolve_comparison_windows(
                "2026-08-20T12:00:00Z", window="5m", guard="5m"
            )

    def test_reports_insufficient_data_without_claiming_no_regression(self) -> None:
        summary = execute_regression_check(
            environment="prd",
            service="sf-item",
            change_time="2026-08-20T12:00:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=FakeRunner(no_data=True),
        )

        markdown = render_markdown(summary)
        self.assertTrue(summary.insufficient_data)
        self.assertIn("Insufficient data", markdown)
        self.assertNotIn("No regression detected", markdown)


if __name__ == "__main__":
    unittest.main()
