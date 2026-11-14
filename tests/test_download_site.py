"""Static download-site checks without a browser or external dependencies."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'docs' / 'index.html'


class Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.format_values = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'input' and attrs.get('name') == 'format':
            self.format_values.append(attrs.get('value'))


class DownloadSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = SITE.read_text(encoding='utf-8')
        cls.parser = Inputs()
        cls.parser.feed(cls.html)

    def test_four_clear_database_choices(self):
        self.assertEqual(set(self.parser.format_values), {'sqlite', 'xz', 'zst', 'zip'})
        self.assertEqual(len(self.parser.format_values), 4)

    def test_latest_release_api_and_real_download_links(self):
        self.assertIn('https://api.github.com/repos/', self.html)
        self.assertIn("'/releases/latest'", self.html)
        self.assertIn("'browser_download_url'", self.html.replace('.browser_download_url', "'browser_download_url'"))
        self.assertIn('/releases/download/', self.html)
        self.assertIn("asset.name + '.sha256'", self.html)
        self.assertIn("if (!response.ok)", self.html)

    def test_mobile_accessibility_and_attribution(self):
        self.assertIn('name="viewport"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('name="format"', self.html)
        self.assertIn('https://mtgjson.com/images/assets/logo-mtgjson.svg', self.html)
        self.assertIn('Not affiliated with or endorsed', self.html)
        self.assertIn('id="download"', self.html)
        self.assertIn('id="checksum"', self.html)

    def test_fallback_for_missing_release_or_rate_limit(self):
        self.assertIn("Unable to load GitHub release details", self.html)
        self.assertIn('Open latest Release', self.html)
        self.assertIn("input.disabled = !asset", self.html)


    def test_json_downloads_are_optional_and_verified(self):
        self.assertIn('id="json-title"', self.html)
        self.assertIn('JSON downloads', self.html)
        for suffix in ('.json', '.json.xz', '.json.zst', '.json.zip'):
            self.assertIn('data-json-extension="' + suffix + '"', self.html)
        self.assertIn('aria-disabled="true"', self.html)
        self.assertIn("asset.name + '.sha256'", self.html)
        self.assertIn("item.name.startsWith('AllPrintings-slim-')", self.html)
        self.assertIn("item.browser_download_url.startsWith(prefix)", self.html)
        self.assertIn("link.removeAttribute('aria-disabled')", self.html)
        self.assertIn("JSON is not yet included in the latest public Release.", self.html)


if __name__ == '__main__':
    unittest.main()
