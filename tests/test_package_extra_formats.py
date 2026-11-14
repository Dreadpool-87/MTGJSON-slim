"""Verify two extra archives contain the same SQLite bytes as the original."""
import json
import shutil
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import package_extra_formats


class ExtraFormatsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='slim-extra-test-')
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.name = 'sample.sqlite'
        self.db = self.folder / self.name
        with sqlite3.connect(self.db) as connection:
            connection.execute('CREATE TABLE cards (id INTEGER PRIMARY KEY, text TEXT)')
            connection.executemany('INSERT INTO cards(text) VALUES (?)', [(f'value-{i}',) for i in range(350)])
        self.digest = package_extra_formats.sha256(self.db)
        (self.folder / 'manifest.json').write_text(json.dumps({'output': {'sqlite': {
            'name': self.name, 'size_bytes': self.db.stat().st_size,
            'sha256': self.digest}}}))
        (self.folder / (self.name + '.sha256')).write_text(f'{self.digest}  {self.name}\n')

    @unittest.skipUnless(shutil.which('zstd'), 'zstd CLI is not installed')
    def test_roundtrip_and_checksums(self):
        items = package_extra_formats.prepare(self.folder)
        self.assertEqual(set(items), {'zstd', 'zip'})
        for kind, item in items.items():
            self.assertEqual(item['unpacked_sha256'], self.digest)
            blob = self.folder / item['name']
            self.assertEqual(item['sha256'], package_extra_formats.sha256(blob))
            self.assertEqual((self.folder / (item['name'] + '.sha256')).read_text(),
                             f"{item['sha256']}  {item['name']}\n")
        with zipfile.ZipFile(self.folder / (self.name + '.zip')) as z:
            self.assertEqual(z.namelist(), [self.name])
        with self.assertRaises(FileExistsError):
            package_extra_formats.prepare(self.folder)

    def test_tampered_sqlite_is_rejected(self):
        self.db.write_bytes(self.db.read_bytes() + b'corruption')
        with self.assertRaisesRegex(ValueError, 'differs from manifest'):
            package_extra_formats.prepare(self.folder)

    def test_wrong_checksum_sidecar_is_rejected(self):
        (self.folder / (self.name + '.sha256')).write_text('invalid\n')
        with self.assertRaisesRegex(ValueError, 'checksum sidecar'):
            package_extra_formats.prepare(self.folder)

    def test_filename_traversal_is_rejected(self):
        m = json.loads((self.folder / 'manifest.json').read_text())
        m['output']['sqlite']['name'] = '../sample.sqlite'
        (self.folder / 'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, 'safe .sqlite'):
            package_extra_formats.prepare(self.folder)


if __name__ == '__main__':
    unittest.main()
