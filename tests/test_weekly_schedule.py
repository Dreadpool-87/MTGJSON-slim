"""Regression checks for the intentionally non-publishing weekly verification schedule."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"
README = ROOT / "README.md"


class WeeklyVerificationScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")

    def test_tuesday_seven_belgian_local_time_with_dst(self):
        self.assertRegex(
            self.workflow,
            r"(?m)^  schedule:\n    - cron: '0 7 \* \* 2'\n      timezone: 'Europe/Brussels'$",
        )
        self.assertEqual(
            len(re.findall(r"(?m)^    - cron:", self.workflow)), 1,
            "The workflow should have only one automatic weekly schedule",
        )

    def test_manual_and_pull_request_events_retained(self):
        self.assertIn("  workflow_dispatch:", self.workflow)
        self.assertIn("  pull_request:", self.workflow)
        self.assertIn(
            "if: github.event_name == 'workflow_dispatch' || github.event_name == 'schedule'",
            self.workflow,
        )
        self.assertIn("    needs: tests", self.workflow)

    def test_reports_only_and_read_only_permissions(self):
        self.assertIn("  contents: read", self.workflow)
        self.assertNotRegex(self.workflow, r"(?m)^\s*contents:\s*write\s*$")
        reports = self.workflow.split("      - name: Retain reports only\n", 1)
        self.assertEqual(len(reports), 2)
        self.assertIn("retention-days: 14", reports[1])
        self.assertIn("output/validation.json", reports[1])
        self.assertIn("output/source-inventory.json", reports[1])
        self.assertNotIn(".sqlite", reports[1])
        self.assertNotIn("gh release", self.workflow)
        self.assertNotIn("action-gh-release", self.workflow)
        self.assertNotIn("schedule: 'daily'", self.workflow)

    def test_readme_discloses_real_weekly_behavior(self):
        self.assertIn("Tuesday at 07:00", self.readme)
        self.assertIn("Europe/Brussels", self.readme)
        self.assertIn("one official download and one complete build per week", self.readme)
        self.assertIn("not** uploaded, released, committed or published", self.readme)


if __name__ == "__main__":
    unittest.main()
