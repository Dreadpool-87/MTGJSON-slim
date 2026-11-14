"""Real codec I/O, corruption controls, and old-runtime interoperability."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts import zstd_support
except ImportError:
    zstd_support = None


class ZstdSupportTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(zstd_support, 'Shared Zstandard implementation is missing')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / 'cards.json'
        self.source.write_bytes(('Oracle text — face // other face\n' * 80000).encode())
        self.target = self.folder / 'cards.json.zst'
        self.expected = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def test_streaming_roundtrip(self):
        zstd_support.compress_file(self.source, self.target)
        self.assertEqual(zstd_support.decompressed_sha256(self.target), self.expected)

    def test_corrupt_or_truncated_archive_is_rejected(self):
        zstd_support.compress_file(self.source, self.target)
        content = self.target.read_bytes()
        for bad in [b'not a zstd file', content[:-3]]:
            with self.subTest(length=len(bad)):
                self.target.write_bytes(bad)
                with self.assertRaises(ValueError):
                    zstd_support.decompressed_sha256(self.target)

    def test_existing_output_is_not_overwritten(self):
        self.target.write_bytes(b'existing artifact')
        with self.assertRaises(FileExistsError):
            zstd_support.compress_file(self.source, self.target)
        self.assertEqual(self.target.read_bytes(), b'existing artifact')

    def test_native_backend_works_without_any_external_command(self):
        with patch('shutil.which', return_value=None):
            if zstd_support.NATIVE is None:
                with self.assertRaises(RuntimeError):
                    zstd_support.compress_file(self.source, self.target)
            else:
                with (patch('subprocess.run', side_effect=AssertionError('external compression')),
                      patch('subprocess.Popen', side_effect=AssertionError('external decompression'))):
                    zstd_support.compress_file(self.source, self.target)
                    self.assertEqual(zstd_support.decompressed_sha256(self.target), self.expected)

    def test_cli_fallback_and_native_files_are_interoperable(self):
        cli = shutil.which('zstd')
        with patch.object(zstd_support, 'NATIVE', None):
            if cli is None:
                with self.assertRaises(RuntimeError):
                    zstd_support.compress_file(self.source, self.target)
                return
            zstd_support.compress_file(self.source, self.target)
            self.assertEqual(zstd_support.decompressed_sha256(self.target), self.expected)
        self.assertEqual(zstd_support.decompressed_sha256(self.target), self.expected)
        if zstd_support.NATIVE is not None:
            self.target.unlink()
            zstd_support.compress_file(self.source, self.target)
            decoded = subprocess.run([cli, '-d', '-q', '-c', str(self.target)],
                                     check=True, capture_output=True).stdout
            self.assertEqual(hashlib.sha256(decoded).hexdigest(), self.expected)
