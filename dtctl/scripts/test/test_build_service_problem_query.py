import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from build_service_problem_query import (
    build_service_entities_query,
    build_service_problems_query,
)


class BuildServiceProblemQueryTest(unittest.TestCase):
    def test_builds_bounded_entity_resolution_query(self) -> None:
        result = build_service_entities_query(
            environment="prd",
            service="sf-item",
            start="2026-08-19T12:00:00Z",
            end="2026-08-20T12:00:00Z",
        )

        self.assertIn("dt.service.request.count", result)
        self.assertIn("dt.entity.service", result)
        self.assertIn('startsWith(service.name, "[prd]")', result)
        self.assertIn("| limit 20", result)

    def test_builds_deduplicated_active_problem_query(self) -> None:
        result = build_service_problems_query(
            entity_ids=(
                "SERVICE-4D3CC297F58610EF",
                "SERVICE-EFAECFC53A8BEA4E",
            ),
            start="2026-08-19T12:00:00Z",
            end="2026-08-20T12:00:00Z",
            status="active",
            limit=5,
        )

        self.assertIn("fetch dt.davis.problems", result)
        self.assertIn('event.status == "ACTIVE"', result)
        self.assertIn("matchesValue(affected_entity_ids", result)
        self.assertIn("or in(root_cause_entity_id", result)
        self.assertIn('"SERVICE-4D3CC297F58610EF"', result)
        self.assertIn("| dedup display_id", result)
        self.assertTrue(result.endswith("| limit 5"))

    def test_rejects_invalid_entity_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid Dynatrace service entity ID"):
            build_service_problems_query(
                entity_ids=("SERVICE-not-valid",),
                start="2026-08-19T12:00:00Z",
                end="2026-08-20T12:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
