"""Static download-site checks without a browser or external dependencies."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'docs' / 'index.html'


class Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.format_values = []
        self.json_values = []
        self.atomic_values = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'input':
            name = attrs.get('name')
            if name == 'format':
                self.format_values.append(attrs.get('value'))
            if name == 'json-format':
                self.json_values.append(attrs.get('value'))
            if name == 'atomic-format':
                self.atomic_values.append(attrs.get('value'))


class DownloadSiteTests(unittest.TestCase):
    def test_sqlite_selector_behaviour_with_incomplete_releases(self):
        result = subprocess.run(['node', '--test', str(ROOT / 'tests/test_download_site_behavior.js')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @classmethod
    def setUpClass(cls):
        cls.html = SITE.read_text(encoding='utf-8')
        cls.script = (ROOT / 'docs/release-downloads.js').read_text(encoding='utf-8')
        cls.parser = Inputs()
        cls.parser.feed(cls.html)

    def test_matching_json_atomic_selector_behaviour(self):
        result = subprocess.run(['node', '--test', str(ROOT / 'tests/test_download_site_ui.js')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_error_states_in_all_json_panels(self):
        result = subprocess.run(['node', '--test', str(ROOT / 'tests/test_download_site_errors.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_honest_static_fallback_and_verification_scope(self):
        self.assertNotIn('Not yet published', self.html)
        self.assertNotIn('#why-does-a-slim-version-exist', self.html)
        self.assertIn('#choose-a-dataset', self.html)
        self.assertIn('## Choose a dataset', (ROOT / 'README.md').read_text())
        self.assertIn('<noscript>', self.html)
        self.assertIn('JavaScript is disabled; availability has not been checked', self.html)
        self.assertIn('does not download or hash files in your browser', self.html)
        self.assertIn('less commit/runtime/provenance metadata', self.html)
        self.assertIn('AtomicCards Slim — Card Lookup', self.html)
        self.assertIn('contracts/atomic-b1.json', self.html)
        self.assertIn('At build time', self.html)

    def test_allprintings_uncompressed_label_is_not_duplicated(self):
        self.assertIn('JSON · Uncompressed', self.html)
        self.assertNotIn('JSON JSON · Uncompressed', self.html)

    def test_four_clear_database_choices(self):
        self.assertEqual(set(self.parser.format_values), {'sqlite', 'xz', 'zst', 'zip'})
        self.assertEqual(len(self.parser.format_values), 4)
        for family in ('json', 'atomic'):
            values = getattr(self.parser, family + '_values')
            self.assertEqual(values, ['xz', 'zst', 'zip', 'raw'])

    def test_shared_api_and_real_download_links(self):
        self.assertIn('src="release-downloads.js" defer', self.html)
        self.assertEqual(self.script.count('await fetch('), 1)
        self.assertIn("'?per_page=100'", self.script)
        self.assertNotIn('/releases/latest', self.script)
        self.assertIn("asset.name + '.sha256'", self.script)
        self.assertIn('if (!response.ok)', self.script)
        result = subprocess.run(['node', '--test', str(ROOT / 'tests/test_release_api.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mobile_accessibility_and_attribution(self):
        self.assertIn('name="viewport"', self.html)
        self.assertIn('@media (max-width: 620px)', self.html)
        for family in ('sqlite', 'json', 'atomic'):
            self.assertIn(family + '-release', self.parser.ids)
            self.assertIn(family + '-manifest', self.parser.ids)
        self.assertIn('for files and manifests', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('name="format"', self.html)
        self.assertIn('https://mtgjson.com/images/assets/logo-mtgjson.svg', self.html)
        self.assertIn('Not affiliated with or endorsed', self.html)
        self.assertIn('id="download"', self.html)
        self.assertIn('id="checksum"', self.html)
        for family in ('json', 'atomic'):
            for suffix in ('download', 'checksum', 'status-dot', 'file-note'):
                self.assertIn(family + '-' + suffix, self.parser.ids)
            self.assertIn('name="' + family + '-format"', self.html)

    def test_fallback_for_missing_release_or_rate_limit(self):
        self.assertIn('Availability UNKNOWN', self.script)
        self.assertIn('Browse Releases', self.html)
        self.assertIn('maxPages = 5', self.script)
        self.assertIn('timeoutMs = 10000', self.script)

    def test_json_downloads_are_optional_and_paired(self):
        self.assertIn('id="json-title"', self.html)
        for family in ('json', 'atomic'):
            for option in ('xz', 'zst', 'zip', 'raw'):
                self.assertIn(f'id="{family}-size-{option}"', self.html)
            self.assertIn(f'id="{family}-download" class="download"', self.html)
            self.assertIn(f'id="{family}-checksum" hidden', self.html)
        self.assertIn("pair.sha.browser_download_url", self.script)
        self.assertIn("input.addEventListener('change', refresh)", self.script)
        self.assertIn("'atomic-slim-'", self.script)
        self.assertIn("'json-slim-'", self.script)
        self.assertIn('AtomicCards Release series', self.html)


if __name__ == '__main__':
    unittest.main()
