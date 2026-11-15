"""Workflow safety regression checks for owner-enabled release, weekly build and validation."""
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
        self.assertIn('  push:', self.workflow)
        self.assertIn("      - '.github/workflows/verify.yml'", self.workflow)
        self.assertIn("github.event_name == 'push'", self.workflow)
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)
        self.assertIn('python slim.py download --directory downloads --report evidence/download.json', self.workflow)
        self.assertIn('python slim.py build --archive downloads/AllPrintings.sqlite.xz', self.workflow)
        self.assertNotIn('previous_upstream_sha256', self.workflow)
        self.assertNotIn('--previous-sha256', self.workflow)

    def test_only_release_job_has_write_and_is_main_only(self):
        self.assertIn('permissions:\n  contents: read', self.workflow)
        before, release = self.workflow.split('\n  publish:\n', 1)
        self.assertNotRegex(before, r'(?m)^\s*contents: write\s*$')
        self.assertIn('    permissions:\n      contents: write', release)
        self.assertIn("github.ref == 'refs/heads/main'", release)
        self.assertNotIn('MTGJSON_PUBLIC_DISTRIBUTION_APPROVED', self.workflow)
        self.assertIn("PUBLICATION_ENABLED: 'true'", self.workflow)
        self.assertIn('needs.real-data.outputs.publish', release)
        self.assertIn('gh release create', release)
        self.assertIn('--draft', release)
        self.assertIn('gh release edit', release)
        self.assertIn('--draft=false --latest', release)
        self.assertIn('MTGJSON_LICENSE.txt', release)
        self.assertIn('-eq 10', release)
        self.assertIn('scripts/package_extra_formats.py --package candidate', release)
        self.assertIn('"candidate/$zst"', release)
        self.assertIn('"candidate/$zip"', release)
        self.assertIn('--title "MTGJSON-slim — $source_date"', release)
        self.assertNotIn('--title "MTGJSON slim $RELEASE_TAG"', release)

    def test_only_changed_validated_packages_are_transferred(self):
        self.assertIn("steps.release_plan.outputs.publish == 'true'", self.workflow)
        self.assertIn("needs.real-data.outputs.publish == 'true'", self.workflow)
        self.assertIn('python scripts/release_plan.py --package output', self.workflow)
        self.assertIn('scripts/release_plan.py --package output --disabled', self.workflow)
        self.assertIn('output/*.sqlite', self.workflow)
        self.assertIn('output/*.sqlite.xz', self.workflow)
        self.assertIn('retention-days: 1', self.workflow)
        self.assertIn('retention-days: 14', self.workflow)

    def test_readme_truthfully_describes_published_release_and_attribution(self):
        """The landing page stays concise; operational guarantees live in linked guides."""
        readme = self.readme
        development = (ROOT / 'docs/DEVELOPMENT.md').read_text(encoding='utf-8')
        usage = (ROOT / 'docs/USAGE.md').read_text(encoding='utf-8')
        notices = (ROOT / 'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8')
        json_audit = (ROOT / 'docs/JSON_DIRECT_SOURCE_PREVIEW.md').read_text(encoding='utf-8')

        self.assertLessEqual(len(readme.split()), 800, 'README should be a short entrypoint')
        self.assertLessEqual(len(readme.splitlines()), 100)
        for link in ('docs/USAGE.md', 'docs/DEVELOPMENT.md',
                     'docs/PROFILE_2_3_DATA_INVENTORY.md', 'THIRD_PARTY_NOTICES.md'):
            self.assertIn(link, readme)
        for family in ('AllPrintings SQLite', 'AllPrintings JSON', 'AtomicCards JSON'):
            self.assertIn(family, readme)
        self.assertIn('https://github.com/Dreadpool-87/MTGJSON-slim/releases', readme)
        self.assertIn('Tuesday **07:00 Europe/Brussels**', development)
        self.assertIn('Settings → Pages', development)
        for flag in ('PUBLICATION_ENABLED', 'JSON_PUBLICATION_ENABLED',
                     'ATOMIC_PUBLICATION_ENABLED'):
            self.assertIn(flag, development)
        self.assertIn('10 assets', development)
        self.assertIn('every', development.lower())
        self.assertIn('SHA-256', usage)
        self.assertIn('https://mtgjson.com/license/', notices)
        self.assertIn('not affiliated with MTGJSON', readme)
        self.assertIn('src="https://mtgjson.com/images/assets/logo-mtgjson.svg"', readme)
        self.assertIn('alt="MTGJSON logo"', readme)
        self.assertIn('Current status: published', json_audit)
        self.assertNotIn('Status: separate preview only.', json_audit)


if __name__ == '__main__':
    unittest.main()
