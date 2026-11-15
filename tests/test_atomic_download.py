"""Downloader filesystem regressions with synthetic transport fault injection."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import atomic_slim


class AtomicDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / 'sp ace-é'
        self.payload = b'synthetic archive bytes\x00\x01'
        self.sha = hashlib.sha256(self.payload).hexdigest()
        self.archive = self.folder / 'AtomicCards.json.xz'
        self.sidecar = self.folder / 'AtomicCards.json.xz.sha256'

    def transport(self, command, check):
        """Simulate only curl's file/network boundary; use the real filesystem."""
        destination = Path(command[command.index('--output') + 1])
        data = (self.sha + '\n').encode() if command[-1].endswith('.sha256') else self.payload
        destination.write_bytes(data)
        return subprocess.CompletedProcess(command, 0)

    def download(self, transport=None):
        with patch('atomic_slim.subprocess.run', side_effect=transport or self.transport):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                atomic_slim.download(self.folder)
        return json.loads(output.getvalue())

    def assert_clean(self):
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_good_pair_matches_original_report_and_preserves_bytes(self):
        report = self.download()
        self.assertEqual(self.archive.read_bytes(), self.payload)
        self.assertEqual(self.sidecar.read_text(), self.sha + '\n')
        self.assertEqual(report, {'source_url': atomic_slim.SOURCE_URL,
                                 'archive_sha256': self.sha,
                                 'archive_size_bytes': len(self.payload), 'status': 'PASS'})
        self.assertEqual({x.name for x in self.folder.iterdir()}, {self.archive.name, self.sidecar.name})

    def test_final_names_remain_absent_until_both_downloads_are_verified(self):
        def fetch(command, check):
            self.assertFalse(self.archive.exists())
            self.assertFalse(self.sidecar.exists())
            return self.transport(command, check)
        self.download(fetch)

    def test_bad_checksum_removes_staged_and_final_files(self):
        def fetch(command, check):
            result = self.transport(command, check)
            if command[-1].endswith('.sha256'):
                Path(command[command.index('--output') + 1]).write_text('0' * 64 + '\n')
            return result
        with self.assertRaises(ValueError):
            self.download(fetch)
        self.assert_clean()

    def test_malformed_checksum_removes_all_files(self):
        def fetch(command, check):
            result = self.transport(command, check)
            if command[-1].endswith('.sha256'):
                Path(command[command.index('--output') + 1]).write_text('not a checksum\n')
            return result
        with self.assertRaises(ValueError):
            self.download(fetch)
        self.assert_clean()

    def test_interrupted_archive_is_cleaned_and_clean_retry_succeeds(self):
        def interrupted(command, check):
            Path(command[command.index('--output') + 1]).write_bytes(b'partial')
            raise subprocess.CalledProcessError(18, command)
        with self.assertRaises(subprocess.CalledProcessError):
            self.download(interrupted)
        self.assert_clean()
        self.download()
        self.assertEqual(self.archive.read_bytes(), self.payload)

    def test_sidecar_timeout_removes_already_staged_archive(self):
        def fetch(command, check):
            if command[-1].endswith('.sha256'):
                Path(command[command.index('--output') + 1]).write_bytes(b'partial')
                raise subprocess.TimeoutExpired(command, 1)
            return self.transport(command, check)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.download(fetch)
        self.assert_clean()

    def test_http_failure_removes_partial_transfer(self):
        def denied(command, check):
            Path(command[command.index('--output') + 1]).write_bytes(b'error page')
            raise subprocess.CalledProcessError(22, command)
        with self.assertRaises(subprocess.CalledProcessError):
            self.download(denied)
        self.assert_clean()

    def test_existing_archive_is_not_changed(self):
        self.folder.mkdir()
        self.archive.write_bytes(b'keep archive')
        with self.assertRaises(FileExistsError):
            self.download()
        self.assertEqual(self.archive.read_bytes(), b'keep archive')
        self.assertEqual(list(self.folder.iterdir()), [self.archive])

    def test_existing_sidecar_refuses_before_creating_archive(self):
        self.folder.mkdir()
        self.sidecar.write_text('keep sidecar')
        with self.assertRaises(FileExistsError):
            self.download()
        self.assertEqual(self.sidecar.read_text(), 'keep sidecar')
        self.assertEqual(list(self.folder.iterdir()), [self.sidecar])

    def test_dangling_final_symlink_is_not_followed_or_replaced(self):
        self.folder.mkdir()
        target = self.folder / 'not-created'
        self.sidecar.symlink_to(target)
        with self.assertRaises(FileExistsError):
            self.download()
        self.assertTrue(self.sidecar.is_symlink())
        self.assertFalse(target.exists())
        self.assertFalse(self.archive.exists())

    def test_repeated_download_refuses_without_changing_pair(self):
        self.download()
        before = (self.archive.read_bytes(), self.sidecar.read_bytes())
        with self.assertRaises(FileExistsError):
            self.download()
        self.assertEqual((self.archive.read_bytes(), self.sidecar.read_bytes()), before)

    def test_missing_curl_reports_dependency_without_partial_files(self):
        with patch.dict(os.environ, {'PATH': ''}):
            with self.assertRaises(FileNotFoundError):
                atomic_slim.download(self.folder)
        self.assert_clean()

    def test_publication_error_rolls_back_owned_link(self):
        original = os.link
        count = 0
        def fail_second(source, destination):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('injected publication error')
            original(source, destination)
        with patch('os.link', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.download()
        self.assert_clean()

    def test_concurrent_archive_collision_is_preserved_and_owned_sidecar_removed(self):
        original = os.link
        def collide(source, destination):
            if Path(destination) == self.archive:
                self.archive.write_bytes(b'concurrent owner')
            original(source, destination)
        with patch('os.link', side_effect=collide):
            with self.assertRaises(FileExistsError):
                self.download()
        self.assertEqual(self.archive.read_bytes(), b'concurrent owner')
        self.assertFalse(self.sidecar.exists())
        self.assertEqual(list(self.folder.iterdir()), [self.archive])

    def test_keyboard_interrupt_rolls_back_owned_link(self):
        original = os.link
        count = 0
        def interrupt_second(source, destination):
            nonlocal count
            count += 1
            if count == 2:
                raise KeyboardInterrupt
            original(source, destination)
        with patch('os.link', side_effect=interrupt_second):
            with self.assertRaises(KeyboardInterrupt):
                self.download()
        self.assert_clean()

    def test_interrupt_after_link_before_return_still_cleans_owned_file(self):
        original = os.link
        def interrupt_after_link(source, destination):
            original(source, destination)
            raise KeyboardInterrupt
        with patch('os.link', side_effect=interrupt_after_link):
            with self.assertRaises(KeyboardInterrupt):
                self.download()
        self.assert_clean()

    def test_rollback_does_not_follow_foreign_replacement_symlink(self):
        original = os.link
        def replace_then_fail(source, destination):
            destination = Path(destination)
            if destination == self.sidecar:
                original(source, destination)
                destination.unlink()
                destination.symlink_to(source)
            else:
                raise OSError('injected second publication failure')
        with patch('os.link', side_effect=replace_then_fail):
            with self.assertRaises(OSError):
                self.download()
        self.assertTrue(self.sidecar.is_symlink())
        self.assertFalse(self.archive.exists())
        self.assertEqual(list(self.folder.iterdir()), [self.sidecar])

    def test_curl_rejects_file_protocol_with_real_executable(self):
        self.assertIsNotNone(shutil.which('curl'), 'Install curl for downloader regression tests')
        source = Path(self.tmp.name) / 'local-source.xz'
        source.write_bytes(self.payload)
        Path(str(source) + '.sha256').write_text(self.sha)
        with patch('atomic_slim.SOURCE_URL', source.as_uri()):
            with self.assertRaises(subprocess.CalledProcessError):
                atomic_slim.download(self.folder)
        self.assert_clean()

    def test_cli_download_failure_is_nonzero_without_leaving_files(self):
        script = str(Path(atomic_slim.__file__).resolve())
        result = subprocess.run([sys.executable, '-B', script, 'download', '--directory', str(self.folder)],
                                env={**os.environ, 'PATH': ''}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('curl', result.stderr)
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
