"""Workflow safety regression checks: weekly rebuild, semantic release and rights gate."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'verify.yml'
README = ROOT / 'README.md'


class WeeklyReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text()
        cls.readme = README.read_text()

    def test_tuesday_seven_local_time_with_dst_and_single_cron(self):
        self.assertRegex(
            self.workflow,
            r"(?m)^  schedule:\n    - cron: '0 7 \* \* 2'\n      timezone: 'Europe/Brussels'$")
        self.assertEqual(len(re.findall(r'(?m)^    - cron:', self.workflow)), 1)

    def test_always_rebuilds_without_prior_sha_skip(self):
        self.assertIn('  workflow_dispatch:', self.workflow)
        self.assertIn('  pull_request:', self.workflow)
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)
        self.assertIn('python slim.py download --directory downloads --report evidence/download.json', self.workflow)
        self.assertIn('python slim.py build --archive downloads/AllPrintings.sqlite.xz', self.workflow)
        self.assertNotIn('previous_upstream_sha256', self.workflow)
        self.assertNotIn('--previous-sha256', self.workflow)

    def test_only_release_job_has_write_and_rights_gate(self):
        self.assertIn('permissions:\n  contents: read', self.workflow)
        before, release = self.workflow.split('\n  publish:\n', 1)
        self.assertNotRegex(before, r'(?m)^\s*contents: write\s*$')
        self.assertIn('    permissions:\n      contents: write', release)
        self.assertIn("vars.MTGJSON_PUBLIC_DISTRIBUTION_APPROVED == 'true'", release)
        self.assertIn('needs.real-data.outputs.publish', release)
        self.assertIn('gh release create', release)
        self.assertIn('--draft', release)
        self.assertIn('gh release edit', release)
        self.assertIn('--draft=false --latest', release)
        self.assertIn('MTGJSON_LICENSE.txt', release)
        self.assertIn('-eq 6', release)

    def test_only_changed_approved_packages_are_transferred(self):
        self.assertIn("steps.release_plan.outputs.publish == 'true'", self.workflow)
        self.assertIn("vars.MTGJSON_PUBLIC_DISTRIBUTION_APPROVED == 'true'", self.workflow)
        self.assertIn('scripts/release_plan.py --package output --disabled', self.workflow)
        self.assertIn('output/*.sqlite', self.workflow)
        self.assertIn('output/*.sqlite.xz', self.workflow)
        self.assertIn('retention-days: 1', self.workflow)
        self.assertIn('retention-days: 14', self.workflow)

    def test_readme_truthfully_states_release_gate(self):
        self.assertIn('Tuesday at 07:00', self.readme)
        self.assertIn('Europe/Brussels', self.readme)
        self.assertIn('MTGJSON_PUBLIC_DISTRIBUTION_APPROVED', self.readme)
        self.assertIn('every scheduled run', self.readme)


if __name__ == '__main__':
    unittest.main()
