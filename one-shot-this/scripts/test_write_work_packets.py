#!/usr/bin/env python3
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


WRITE_SCRIPT = Path(__file__).with_name("write_work_packets.py")
SPAWN_SCRIPT = Path(__file__).with_name("spawn_tmux_worktrees.sh")


class WriteWorkPacketsTest(unittest.TestCase):
    def run_writer(self, plan):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        plan_path = root / "plan.json"
        output_dir = root / "packets"
        plan_path.write_text(json.dumps(plan))
        result = subprocess.run(
            [str(WRITE_SCRIPT), str(plan_path), str(output_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result, output_dir

    def test_preserves_jira_contract_and_delivery_evidence(self):
        plan = {
            "jira_key": "SHOP-123",
            "jira_url": "https://jira.example.com/browse/SHOP-123",
            "issue_type": "Story",
            "summary": "Publish checkout state",
            "description": "Publish the final state without changing checkout ownership.",
            "acceptance_criteria": ["Publish state after a successful checkout"],
            "cross_repo_steps": ["Deploy the producer before the consumer"],
            "dependency_links": ["https://jira.example.com/browse/SHOP-100"],
            "repos": [
                {
                    "name": "checkout-api",
                    "branch_suffix": "SHOP-123-checkout-state",
                    "why_impacted": "Owns the checkout state transition.",
                    "steps": ["Publish the state event"],
                    "tests": ["Run the checkout integration test"],
                    "observability": ["Count bounded publish outcomes"],
                    "rollout_notes": ["Deploy behind the existing flag"],
                }
            ],
        }

        result, output_dir = self.run_writer(plan)

        self.assertEqual(result.returncode, 0, result.stderr)
        packet = (output_dir / "checkout-api.md").read_text()
        self.assertIn("[SHOP-123](https://jira.example.com/browse/SHOP-123)", packet)
        self.assertIn("Publish state after a successful checkout", packet)
        self.assertIn("Count bounded publish outcomes", packet)
        self.assertIn("Deploy the producer before the consumer", packet)
        self.assertIn("https://jira.example.com/browse/SHOP-100", packet)
        self.assertIn("Approve push + draft PR + Jira link", packet)

    def test_rejects_a_plan_without_full_jira_url(self):
        plan = {
            "jira_key": "SHOP-123",
            "summary": "Publish checkout state",
            "description": "Publish the final state.",
            "acceptance_criteria": ["Publish the state"],
            "repos": [{"name": "checkout-api", "why_impacted": "Owns the change."}],
        }

        result, _ = self.run_writer(plan)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires non-empty jira_url", result.stderr)

    def test_single_repo_plan_stays_in_the_current_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan_path = root / "plan.json"
            packets_dir = root / "packets"
            packets_dir.mkdir()
            plan_path.write_text(json.dumps({"repos": [{"name": "checkout-api"}]}))

            result = subprocess.run(
                [str(SPAWN_SCRIPT), "SHOP-123", str(plan_path), str(packets_dir)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("implemented in the current Codex session", result.stderr)


if __name__ == "__main__":
    unittest.main()
