"""Behavioral checks for weekly semantic change detection and release package integrity."""
import hashlib
import json
import lzma
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import slim
import release_plan
from test_slim import PipelineTests


class ReleasePlanTests(unittest.TestCase):
    setUp = PipelineTests.setUp

    def built(self, directory='package'):
        out = self.root / directory
        result = slim.build(self.archive, self.digest, self.profile_path, out, 'a' * 40)
        self.assertEqual(result['status'], 'PASS')
        return out, release_plan.verify_package(out)

    def revised_source(self, sql, new_directory):
        with sqlite3.connect(self.db) as db:
            db.execute(sql)
        self.archive.write_bytes(lzma.compress(self.db.read_bytes()))
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        return self.built(new_directory)

    def test_exact_raw_and_xz_and_sidecar_checks_pass(self):
        out, manifest = self.built()
        result = release_plan.decide(manifest, enabled=True)
        self.assertEqual(result['action'], 'PUBLISH')
        self.assertTrue(result['tag'].startswith('slim-2026-11-12-'))
        self.assertEqual(release_plan.decide(manifest, enabled=False)['action'], 'BLOCKED')
        self.assertEqual(release_plan.decide(manifest, manifest, enabled=True)['action'], 'SKIP_UNCHANGED')
        self.assertNotIn('meta', manifest['content']['tables'])

    def test_weekly_rebuild_metadata_only_does_not_release(self):
        _, old = self.built('old')
        _, fresh = self.revised_source(
            "UPDATE meta SET date='2026-11-13', version='5.3.0+20261113'", 'new')
        self.assertNotEqual(old['upstream']['archive_sha256'], fresh['upstream']['archive_sha256'])
        self.assertEqual(old['content']['fingerprint'], fresh['content']['fingerprint'])
        self.assertEqual(release_plan.decide(fresh, old, enabled=True)['action'], 'SKIP_UNCHANGED')

    def test_actual_card_change_requires_new_release(self):
        _, old = self.built('old')
        _, fresh = self.revised_source(
            "UPDATE cards SET printedName='Changed' WHERE uuid='a'", 'new')
        result = release_plan.decide(fresh, old, enabled=True)
        self.assertEqual(result['action'], 'PUBLISH')
        self.assertIn('cards', result['changed_areas'])

    def test_schema_or_index_changes_trigger_release(self):
        _, old = self.built('old')
        changed = json.loads(json.dumps(old))
        changed['content']['schema_sha256'] = '1' * 64
        canonical = {'schema_sha256': changed['content']['schema_sha256'],
                     'tables': changed['content']['tables']}
        changed['content']['fingerprint'] = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        result = release_plan.decide(changed, old, enabled=True)
        self.assertEqual(result['action'], 'PUBLISH')
        self.assertIn('schema_and_indexes', result['changed_areas'])

    def test_any_asset_or_manifest_tampering_is_rejected(self):
        out, m = self.built()
        for field in ('sqlite', 'archive'):
            name = m['output'][field]['name']
            target = out / name
            original = target.read_bytes()
            target.write_bytes(original + b'tamper')
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'checksum'):
                release_plan.verify_package(out)
            target.write_bytes(original)
        checksum = out / (m['output']['sqlite']['name'] + '.sha256')
        checksum.write_text('incorrect\n')
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            release_plan.verify_package(out)

    def test_previous_release_fingerprint_is_fail_closed(self):
        _, m = self.built()
        previous = json.loads(json.dumps(m))
        previous['content']['fingerprint'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            release_plan.decide(m, previous, enabled=True)

    def test_previous_release_fingerprint_absent_is_rejected(self):
        _, m = self.built()
        previous = json.loads(json.dumps(m))
        previous.pop('content')
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            release_plan.decide(m, previous, enabled=True)


if __name__ == '__main__':
    unittest.main()
