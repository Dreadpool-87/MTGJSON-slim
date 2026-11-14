"""Static safety contract for independently released JSON without touching SQLite latest."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/json-weekly.yml"


class JsonWeeklyWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text()

    def test_follows_successful_trusted_main_sqlite_workflow_not_clock_delay(self):
        self.assertIn('  workflow_run:', self.source)
        self.assertIn('workflows: ["Verify MTGJSON slim"]', self.source)
        self.assertIn('types: [completed]', self.source)
        self.assertIn('branches: [main]', self.source)
        self.assertNotIn("cron: '20 7 * * 2'", self.source)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.source)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", self.source)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", self.source)
        self.assertIn("github.event.workflow_run.event == 'schedule'", self.source)
        self.assertIn("mtgjson-slim-json-", self.source)

    def test_no_publication_on_pr_and_write_only_publish_job(self):
        self.assertIn("  pull_request:", self.source)
        start, publish = self.source.split("\n  publish:\n", 1)
        self.assertNotRegex(start, r"(?m)^\s*contents: write\s*$")
        self.assertIn("    permissions:\n      contents: write", publish)
        self.assertIn("github.ref == 'refs/heads/main'", publish)
        self.assertIn("needs.real-data.outputs.publish == 'true'", publish)
        self.assertIn("JSON_PUBLICATION_ENABLED:", start)

    def test_source_from_both_official_formats_and_cross_audit_required(self):
        self.assertIn("python slim.py download", self.source)
        self.assertIn("python slim_json.py download", self.source)
        self.assertIn("python scripts/audit_json_field_selection.py", self.source)
        self.assertIn("python scripts/audit_json_sqlite.py", self.source)
        self.assertIn("python scripts/json_release_plan.py", self.source)
        self.assertIn("json-manifest.json", self.source)

    def test_validated_published_sqlite_required_twice(self):
        self.assertIn("Require already published, matching, validated SQLite Release", self.source)
        self.assertIn("Recheck published SQLite dependency immediately before JSON publishing", self.source)
        self.assertEqual(self.source.count("scripts/require_published_sqlite.py \\"), 4)
        self.assertIn("output-json/sqlite-manifest.json", self.source)
        self.assertIn("candidate/sqlite-manifest.json", self.source)
        self.assertIn("evidence/sqlite-publication-gate.json", self.source)
        self.assertIn("sqlite-release-publish-gate.json", self.source)
        self.assertIn("gh release download", self.source)
        self.assertIn("sqlite-public/release.json", self.source)

    def test_only_small_compressed_candidate_transferred(self):
        after = self.source.split("Transfer only compressed JSON when approved and changed", 1)[1]
        before_publish = after.split("\n  publish:", 1)[0]
        self.assertIn("output-json/*.json.xz", before_publish)
        self.assertIn("output-json/json-manifest.json", before_publish)
        self.assertNotIn("output-json/*.json\n", before_publish)
        self.assertIn("retention-days: 1", before_publish)

    def test_draft_first_and_json_not_latest_sqlite(self):
        self.assertIn("python scripts/rehydrate_json.py", self.source)
        self.assertIn("python scripts/package_json_formats.py", self.source)
        self.assertIn("gh release create", self.source)
        self.assertIn("--draft --latest=false", self.source)
        self.assertIn("gh release edit", self.source)
        self.assertIn("--draft=false --latest=false", self.source)
        self.assertIn("json-slim-$date-$fp", self.source)
        self.assertIn("json-manifest.json", self.source)


if __name__ == "__main__":
    unittest.main()
