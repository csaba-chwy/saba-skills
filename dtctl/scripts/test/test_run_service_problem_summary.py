import json
import subprocess
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from run_service_problem_summary import execute_problem_summary, render_markdown


class FakeRunner:
    def __init__(self, *, entities: bool = True) -> None:
        self.commands: list[list[str]] = []
        self.entities = entities

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
                stdout="Auth type: OAuth\nAccess token: valid for 30m\n",
                stderr="",
            )
        dql = command[4]
        if dql.startswith("timeseries"):
            records = (
                [
                    {
                        "service.name": "[prd][use1]sf-item",
                        "dt.entity.service": "SERVICE-4D3CC297F58610EF",
                        "requests": 1200,
                    }
                ]
                if self.entities
                else []
            )
        else:
            records = [
                {
                    "event.start": "2026-08-20T10:00:00Z",
                    "event.end": None,
                    "display_id": "P-12345",
                    "event.name": "Failure rate increase",
                    "event.category": "ERROR",
                    "event.status": "ACTIVE",
                    "dt.davis.affected_users_count": 12,
                    "root_cause_entity_id": "SERVICE-4D3CC297F58610EF",
                    "root_cause_entity_name": "[prd][use1]sf-item",
                    "affected_entity_count": "3",
                }
            ]
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps({"records": records}), stderr=""
        )


class RunServiceProblemSummaryTest(unittest.TestCase):
    def test_runs_entity_and_problem_queries_and_renders_root_cause(self) -> None:
        runner = FakeRunner()
        summary = execute_problem_summary(
            environment="prd",
            service="sf-item",
            lookback="1d",
            end_time="2026-08-20T12:00:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(summary)

        queries = [command for command in runner.commands if "query" in command]
        self.assertEqual(len(queries), 2)
        self.assertIn("--default-scan-limit-gbytes", queries[1])
        self.assertIn("P-12345", markdown)
        self.assertIn("1 active", markdown)
        self.assertIn("Davis root cause", markdown)
        self.assertIn("visualizationType=table", markdown)

    def test_skips_tenant_wide_problem_query_without_service_entities(self) -> None:
        runner = FakeRunner(entities=False)
        summary = execute_problem_summary(
            environment="prd",
            service="sf-item",
            lookback="1h",
            end_time="2026-08-20T12:00:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )

        queries = [command for command in runner.commands if "query" in command]
        self.assertEqual(len(queries), 1)
        self.assertTrue(summary.problem_query_skipped)
        self.assertIn("skipped to avoid a tenant-wide scan", render_markdown(summary))


if __name__ == "__main__":
    unittest.main()
