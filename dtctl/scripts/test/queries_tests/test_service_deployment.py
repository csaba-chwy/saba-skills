import subprocess
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from queries.service_deployment import build_service_deployment_query


class BuildServiceDeploymentQueryTest(unittest.TestCase):
    def test_builds_exact_version_request_timeline(self) -> None:
        result = build_service_deployment_query(
            environment="prd",
            service="sf-item",
            version="0.180.0",
            start="2026-08-17T12:00:00Z",
            end="2026-08-31T12:00:00Z",
        )

        self.assertIn("dt.service.request.count", result)
        self.assertIn("by: { service.name, primary_tags.version }", result)
        self.assertIn('primary_tags.version == "0.180.0"', result)
        self.assertIn('startsWith(service.name, "[prd]")', result)
        self.assertIn("interval: 5m", result)
        self.assertNotIn("scalar: true", result)

    def test_rejects_dql_injection_in_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact tag value"):
            build_service_deployment_query(
                environment="prd",
                service="sf-item",
                version='0.180.0" or true',
                start="2026-08-17T12:00:00Z",
                end="2026-08-31T12:00:00Z",
            )

    def test_cli_prints_query(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SRC_DIR / "queries" / "service_deployment.py"),
                "--environment",
                "stg",
                "--service",
                "checkout-b",
                "--version",
                "v2.4.1-rc.1",
                "--from-time",
                "2026-08-30T12:00:00Z",
                "--to-time",
                "2026-08-31T12:00:00Z",
                "--interval",
                "1m",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn('primary_tags.version == "v2.4.1-rc.1"', result.stdout)
        self.assertIn("interval: 1m", result.stdout)


if __name__ == "__main__":
    unittest.main()
