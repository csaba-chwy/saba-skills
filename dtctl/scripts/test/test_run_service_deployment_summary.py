import json
import subprocess
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from run_service_deployment_summary import (
    execute_deployment_summary,
    render_markdown,
)


class FakeRunner:
    def __init__(self, *, empty: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.empty = empty

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
        records = []
        if not self.empty:
            records = [
                {
                    "service.name": "[prd][use1]sf-item",
                    "primary_tags.version": "0.180.0",
                    "timeframe": {
                        "start": "2026-08-20T11:50:00.000000000Z",
                        "end": "2026-08-20T12:15:00.000000000Z",
                    },
                    "interval": "300000000000",
                    "requests": [None, None, 41, 120, 98],
                },
                {
                    "service.name": "[prd][use2]sf-item",
                    "primary_tags.version": "0.180.0",
                    "timeframe": {
                        "start": "2026-08-20T11:50:00.000000000Z",
                        "end": "2026-08-20T12:15:00.000000000Z",
                    },
                    "interval": "300000000000",
                    "requests": [None, None, None, 67, 111],
                },
            ]
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps({"records": records}), stderr=""
        )


class RunServiceDeploymentSummaryTest(unittest.TestCase):
    def test_reports_first_version_traffic_per_region(self) -> None:
        runner = FakeRunner()
        summary = execute_deployment_summary(
            environment="prd",
            service="sf-item",
            version="0.180.0",
            lookback="14d",
            end_time="2026-08-31T12:00:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=runner,
        )
        markdown = render_markdown(summary)

        queries = [command for command in runner.commands if "query" in command]
        self.assertEqual(len(queries), 1)
        self.assertIn('primary_tags.version == "0.180.0"', queries[0][4])
        self.assertEqual(
            summary.observations[0].first_bucket_start,
            "2026-08-20T12:00:00Z",
        )
        self.assertEqual(
            summary.observations[1].first_bucket_start,
            "2026-08-20T12:05:00Z",
        )
        self.assertIn("Treat different regional boundaries separately", markdown)
        self.assertIn("visualizationType=barChart", markdown)

    def test_empty_result_does_not_claim_version_was_not_deployed(self) -> None:
        summary = execute_deployment_summary(
            environment="prd",
            service="sf-item",
            version="0.180.0",
            end_time="2026-08-31T12:00:00Z",
            environ={"DTCTL_PROD_ENVIRONMENT": "https://prod.example.com"},
            runner=FakeRunner(empty=True),
        )

        markdown = render_markdown(summary)
        self.assertEqual(summary.observations, ())
        self.assertIn("does not prove", markdown)
        self.assertNotIn("was not deployed", markdown)


if __name__ == "__main__":
    unittest.main()
