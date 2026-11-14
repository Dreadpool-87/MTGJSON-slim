"""Run the complete CI suite; skipped or undiscovered tests are failures."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-directory', default=str(ROOT / 'tests'))
    args = parser.parse_args(argv)
    suite = unittest.defaultTestLoader.discover(args.start_directory)
    if not suite.countTestCases():
        print('No tests discovered; refusing a green CI result', file=sys.stderr)
        return 1
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print('Skipped tests are not allowed in the full regression gate', file=sys.stderr)
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
