import base64
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from run_service_rundown import execute_rundown, render_markdown, resolve_window


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command, timeout):
        self.commands.append(list(command))
        if command[1:3] == ["config", "describe-context"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    "Environment:  https://prod.example.com\n"
                    "Safety Level: readonly\n"
                ),
                stderr="",
            )
        if command[1:4] == ["--context", "prod", "auth"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    "Auth type: OAuth\n"
                    "Access token: expired\n"
                    "Refresh token: present\n"
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "records": [
                        {
                            "requests": 81_320_208,
                            "failed_requests": 63_604,
                            "error_rate": 0.07821426133095971,
                            "latency_p95_ms": 7.200360277845569,
                        }
                    ]
                }
            ),
            stderr="",
        )


class EmptyMetricRunner(FakeRunner):
    def __init__(self, *, logs=(), spans=()) -> None:
        super().__init__()
        self.logs = list(logs)
        self.spans = list(spans)

    def __call__(self, command, timeout):
        completed = super().__call__(command, timeout)
        if "query" not in command:
            return completed
        dql = command[4]
        if dql.startswith("timeseries"):
            records = []
        elif dql.startswith("fetch logs"):
            records = self.logs
        elif dql.startswith("fetch spans"):
            records = self.spans
        else:
            raise AssertionError(f"unexpected query: {dql}")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"records": records}),
            stderr="",
        )


class RunServiceRundownTest(unittest.TestCase):
    def test_resolves_exact_absolute_window(self) -> None:
        start, end = resolve_window(
            "1d", now=datetime(2026, 8, 20, 22, 24, 2, tzinfo=timezone.utc)
        )

        self.assertEqual(start, "2026-08-19T22:24:02Z")
        self.assertEqual(end, "2026-08-20T22:24:02Z")

    def test_runs_one_query_and_renders_ready_markdown(self) -> None:
        runner = FakeRunner()
        result = execute_rundown(
            environment="prd",
            service="sf-item",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(result)

        query_commands = [command for command in runner.commands if "query" in command]
        self.assertEqual(len(query_commands), 1)
        self.assertIn("--fetch-timeout-seconds", query_commands[0])
        self.assertIn("81,320,208", markdown)
        self.assertIn("63,604", markdown)
        self.assertIn("0.0782%", markdown)
        self.assertIn("7.20 ms", markdown)
        self.assertIn("visualizationType=table", markdown)
        self.assertNotIn("barChart", markdown)
        linked_dql = unquote(
            base64.b64decode(urlsplit(result.link).fragment).decode("utf-8")
        )
        self.assertIn('from: "2026-08-19T22:24:02Z"', linked_dql)
        self.assertIn('to: "2026-08-20T22:24:02Z"', linked_dql)
        self.assertIn("scalar: true", linked_dql)

    def test_focused_request_question_omits_unrequested_metrics(self) -> None:
        runner = FakeRunner()
        result = execute_rundown(
            environment="prd",
            service="sf-item",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
            metrics=("requests",),
        )
        markdown = render_markdown(result)
        query = next(command[4] for command in runner.commands if "query" in command)

        self.assertIn("Requests: **81,320,208**", markdown)
        self.assertNotIn("Failed requests", markdown)
        self.assertNotIn("Error rate", markdown)
        self.assertNotIn("latency", markdown)
        self.assertNotIn("failed_requests", query)
        self.assertNotIn("response_time", query)

    def test_focused_p99_question_uses_requested_percentile(self) -> None:
        runner = FakeRunner()

        def p99_runner(command, timeout):
            completed = runner(command, timeout)
            if "query" not in command:
                return completed
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"records": [{"latency_p99_ms": 12.5}]}),
                stderr="",
            )

        result = execute_rundown(
            environment="prd",
            service="sf-item",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=p99_runner,
            metrics=("latency",),
            latency_percentile=99,
        )
        markdown = render_markdown(result)

        self.assertIn("p99 latency: **12.50 ms**", markdown)
        self.assertNotIn("Requests", markdown)

    def test_empty_service_metrics_fall_back_to_application_logs(self) -> None:
        runner = EmptyMetricRunner(
            logs=(
                {
                    "k8s.workload.name": "[prd][use1]agentic-commerce-orchestrator",
                    "timestamp": "2026-08-20T22:23:58Z",
                },
                {
                    "k8s.workload.name": "[prd][use1]agentic-commerce-orchestrator",
                    "timestamp": "2026-08-20T22:23:57Z",
                },
            )
        )

        result = execute_rundown(
            environment="prd",
            service="agentic-commerce-orchestrator",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(result)
        query_commands = [command for command in runner.commands if "query" in command]

        self.assertEqual(len(query_commands), 2)
        self.assertTrue(query_commands[1][4].startswith("fetch logs"))
        self.assertIn(
            'log.source == "agentic-commerce-orchestrator"', query_commands[1][4]
        )
        self.assertIn('env == "prd"', query_commands[1][4])
        self.assertIn(
            'startsWith(k8s.workload.name, "[prd][")', query_commands[1][4]
        )
        self.assertIn("--default-scan-limit-gbytes", query_commands[1])
        self.assertIn("standard service metrics unavailable", markdown)
        self.assertIn("Application telemetry is present", markdown)
        self.assertIn("[prd][use1]agentic-commerce-orchestrator", markdown)
        self.assertIn(
            "does not mean the application or workload does not exist", markdown
        )

    def test_null_only_scalar_record_uses_application_fallback(self) -> None:
        class NullMetricRunner(EmptyMetricRunner):
            def __call__(self, command, timeout):
                completed = super().__call__(command, timeout)
                if "query" in command and command[4].startswith("timeseries"):
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout=json.dumps(
                            {
                                "records": [
                                    {
                                        "requests": None,
                                        "failed_requests": 0,
                                        "error_rate": 0.0,
                                        "latency_p95_ms": None,
                                    }
                                ]
                            }
                        ),
                        stderr="",
                    )
                return completed

        runner = NullMetricRunner(
            logs=(
                {
                    "k8s.workload.name": "[prd][use1]agentic-commerce-orchestrator",
                    "timestamp": "2026-08-20T22:23:58Z",
                },
            )
        )

        result = execute_rundown(
            environment="prd",
            service="agentic-commerce-orchestrator",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )

        self.assertIn("Application telemetry is present", render_markdown(result))

    def test_empty_log_fallback_checks_exact_application_spans(self) -> None:
        runner = EmptyMetricRunner(
            spans=(
                {
                    "k8s.workload.name": "[prd][use1]agentic-commerce-orchestrator",
                    "start_time": "2026-08-20T22:23:57Z",
                },
            )
        )

        result = execute_rundown(
            environment="prd",
            service="agentic-commerce-orchestrator",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(result)
        query_commands = [command for command in runner.commands if "query" in command]

        self.assertEqual(len(query_commands), 3)
        self.assertTrue(query_commands[2][4].startswith("fetch spans"))
        self.assertIn(
            'endsWith(k8s.workload.name, "]agentic-commerce-orchestrator")',
            query_commands[2][4],
        )
        self.assertIn("Spans: **1** sample record", markdown)

    def test_empty_bounded_discovery_is_explicitly_inconclusive(self) -> None:
        runner = EmptyMetricRunner()

        result = execute_rundown(
            environment="prd",
            service="agentic-commerce-orchestrator",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(result)

        self.assertIn("That result is inconclusive", markdown)
        self.assertIn("before making an existence claim", markdown)
        self.assertNotIn("service does not exist", markdown.lower())


if __name__ == "__main__":
    unittest.main()
