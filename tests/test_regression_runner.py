"""Exercise CI exit status with real passing, failing and skipped suites."""
from pathlib import Path
import subprocess
import re
import shlex
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RegressionRunnerTests(unittest.TestCase):
    def run_fixture(self, body, command=None):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'test_fixture.py').write_text(
                'import unittest\nclass Fixture(unittest.TestCase):\n' + body)
            args = command or [sys.executable, str(ROOT / 'scripts/run_regression_tests.py')]
            if '-m' in args:
                args = [directory if item == 'tests' else item for item in args]
            else:
                args = args + ['--start-directory', directory]
            return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)

    def test_passing_suite_is_accepted(self):
        result = self.run_fixture(' def test_pass(self): self.assertEqual(2 + 2, 4)\n')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_failing_suite_is_rejected(self):
        result = self.run_fixture(' def test_fail(self): self.fail("deliberate failure")\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('deliberate failure', result.stderr)

    def test_skipped_suite_is_rejected(self):
        result = self.run_fixture(' @unittest.skip("missing parser")\n def test_skip(self): pass\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('Skipped tests are not allowed', result.stderr)

    def test_empty_suite_is_rejected(self):
        result = self.run_fixture(' pass\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('No tests discovered', result.stderr)

    def test_every_weekly_ci_entrypoint_rejects_skipped_tests(self):
        for filename in ['verify.yml', 'json-weekly.yml', 'atomic-weekly.yml']:
            with self.subTest(workflow=filename):
                source = (ROOT / '.github/workflows' / filename).read_text()
                job = source.split('\n  tests:\n', 1)[1].split('\n  real-data:', 1)[0]
                commands = re.findall(r'^\s+(?:-\s+)?run: (python .*tests.*)$', job, re.M)
                self.assertEqual(len(commands), 1, 'Expected one full regression gate')
                command = shlex.split(commands[0])
                command[0] = sys.executable
                result = self.run_fixture(' @unittest.skip("missing parser")\n def test_skip(self): pass\n', command)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
