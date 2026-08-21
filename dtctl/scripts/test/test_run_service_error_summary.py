import json
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from run_service_error_summary import (
    build_failure_analysis_link,
    execute_error_summary,
    render_markdown,
)


class FakeRunner:
    def __init__(self, *, failures: bool = True) -> None:
        self.commands: list[list[str]] = []
        self.failures = failures

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
        dql = command[4]
        if "by: { service.name, dt.entity.service, failed }" in dql:
            failure_counts = (6_255, 58_866) if self.failures else (0, 0)
            records = [
                {
                    "service.name": "[prd][use1]sf-item",
                    "dt.entity.service": "SERVICE-4D3CC297F58610EF",
                    "failed": False,
                    "requests": 29_230_240 - failure_counts[0],
                },
                {
                    "service.name": "[prd][use2]sf-item",
                    "dt.entity.service": "SERVICE-EFAECFC53A8BEA4E",
                    "failed": False,
                    "requests": 51_440_704 - failure_counts[1],
                },
            ]
            records.extend(
                {
                    "service.name": f"[prd][{region}]sf-item",
                    "dt.entity.service": entity_id,
                    "failed": True,
                    "requests": failures,
                }
                for region, entity_id, failures in (
                    ("use1", "SERVICE-4D3CC297F58610EF", failure_counts[0]),
                    ("use2", "SERVICE-EFAECFC53A8BEA4E", failure_counts[1]),
                )
                if failures
            )
            if not self.failures:
                records.append(
                    {
                        "service.name": None,
                        "dt.entity.service": None,
                        "failed": None,
                        "requests": None,
                    }
                )
        else:
            records = [
                {
                    "endpoint.name": "query ChewyApiPartNumber__item__0",
                    "http.response.status_code": None,
                    "failures": 50_779,
                },
                {
                    "endpoint.name": "POST /error",
                    "http.response.status_code": "500",
                    "failures": 363,
                },
            ]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"records": records}),
            stderr="",
        )


class NullServiceNameRunner(FakeRunner):
    def __call__(self, command, timeout):
        completed = super().__call__(command, timeout)
        if "query" not in command:
            return completed
        dql = command[4]
        if dql.startswith("fetch spans"):
            records = [
                {
                    "k8s.workload.name": (
                        "[prd][use1]agentic-commerce-orchestrator"
                    ),
                    "dt.entity.service": "SERVICE-880DA3BBFCFE8E87",
                    "service.name": None,
                },
                {
                    "k8s.workload.name": (
                        "[prd][use2]agentic-commerce-orchestrator"
                    ),
                    "dt.entity.service": "SERVICE-26EF4F42398F4D91",
                    "service.name": None,
                },
            ]
        elif "startsWith(service.name" in dql:
            records = []
        elif "by: { service.name, dt.entity.service, failed }" in dql:
            records = [
                {
                    "service.name": None,
                    "dt.entity.service": "SERVICE-880DA3BBFCFE8E87",
                    "failed": False,
                    "requests": 739,
                },
                {
                    "service.name": None,
                    "dt.entity.service": "SERVICE-26EF4F42398F4D91",
                    "failed": False,
                    "requests": 613,
                },
            ]
        else:
            raise AssertionError(f"unexpected query: {dql}")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"records": records}),
            stderr="",
        )


class RunServiceErrorSummaryTest(unittest.TestCase):
    def test_runs_two_metric_queries_and_renders_native_drilldowns(self) -> None:
        runner = FakeRunner()
        summary = execute_error_summary(
            environment="prd",
            service="sf-item",
            lookback="1d",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(summary)

        query_commands = [command for command in runner.commands if "query" in command]
        self.assertEqual(len(query_commands), 2)
        self.assertIn("65,121 / 80,670,944", markdown)
        self.assertIn("query ChewyApiPartNumber__item__0", markdown)
        self.assertIn("HTTP 500", markdown)
        self.assertEqual(markdown.count("open native Failure Analysis"), 2)
        self.assertIn("view-service-failure-analysis", markdown)
        self.assertIn("visualizationType=table", markdown)

    def test_skips_breakdown_query_when_no_failures_exist(self) -> None:
        runner = FakeRunner(failures=False)
        summary = execute_error_summary(
            environment="prd",
            service="sf-item",
            lookback="1h",
            end_time="2026-08-20T22:24:02Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )

        query_commands = [command for command in runner.commands if "query" in command]
        self.assertEqual(len(query_commands), 1)
        self.assertEqual(summary.failures, 0)
        self.assertEqual(summary.top_errors, ())
        self.assertIn("endpoint ranking was skipped", render_markdown(summary))

    def test_falls_back_from_null_service_name_to_span_entity_ids(self) -> None:
        runner = NullServiceNameRunner()
        summary = execute_error_summary(
            environment="prd",
            service="agentic-commerce-orchestrator",
            lookback="1d",
            end_time="2026-08-21T12:15:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(summary)
        query_commands = [command for command in runner.commands if "query" in command]

        self.assertEqual(len(query_commands), 3)
        self.assertTrue(query_commands[1][4].startswith("fetch spans"))
        self.assertIn(
            'from:"2026-08-21T12:00:00Z"',
            query_commands[1][4],
        )
        self.assertIn("--default-scan-limit-gbytes", query_commands[1])
        self.assertIn(
            'dt.entity.service == "SERVICE-880DA3BBFCFE8E87"',
            query_commands[2][4],
        )
        self.assertNotIn("startsWith(service.name", query_commands[2][4])
        self.assertIn("1,352", markdown)
        self.assertIn("[prd][use1]agentic-commerce-orchestrator", markdown)
        self.assertIn("[prd][use2]agentic-commerce-orchestrator", markdown)

    def test_failure_analysis_link_contains_entity_and_absolute_window(self) -> None:
        result = build_failure_analysis_link(
            "https://prod.example.com/",
            "SERVICE-4D3CC297F58610EF",
            start="2026-08-19T22:24:02Z",
            end="2026-08-20T22:24:02Z",
        )
        parsed = urlsplit(result)
        payload = json.loads(unquote(parsed.fragment))

        self.assertEqual(parsed.netloc, "prod.example.com")
        self.assertIn(
            "/ui/intent/dynatrace.services/view-service-failure-analysis",
            parsed.path,
        )
        self.assertEqual(
            payload,
            {
                "dt.entity.service": "SERVICE-4D3CC297F58610EF",
                "dt.timeframe": {
                    "from": "2026-08-19T22:24:02Z",
                    "to": "2026-08-20T22:24:02Z",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
