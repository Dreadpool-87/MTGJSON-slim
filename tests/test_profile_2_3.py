"""Profile 2.3 preserves every v2.2 field except three explicit narrative fields."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slim

ROOT = Path(__file__).resolve().parents[1]
P22 = json.loads((ROOT / 'profiles/v2_2.json').read_text())
P23 = json.loads((ROOT / 'profiles/v2_3.json').read_text())
LOCK = json.loads((ROOT / 'contracts/main-profile-2.3.json').read_text())
REMOVED = {'cards': {'flavorText', 'isStorySpotlight'}, 'tokens': {'flavorText'}}


class ReviewedOmissionTests(unittest.TestCase):

    def test_main_profile_standalone_and_exact_historical_difference(self):
        self.assertEqual(P23['version'], '2.3')
        self.assertNotIn('historical_contract', P23)
        self.assertNotIn('intentional_omissions', P23)
        self.assertEqual(LOCK['profile_version'], '2.3')
        for key in ('tables', 'indexes', 'relationships', 'unique_keys', 'source_schema'):
            self.assertEqual(P23[key], LOCK[key])
        self.assertEqual(set(P23['tables']), set(P22['tables']))
        self.assertEqual(sum(map(len, P22['tables'].values())), 227)
        self.assertEqual(sum(map(len, P23['tables'].values())), 224)
        for table, columns in P22['tables'].items():
            self.assertEqual(P23['tables'][table],
                             [field for field in columns if field not in REMOVED.get(table, set())])
        for key in ('source_schema', 'indexes', 'relationships', 'unique_keys'):
            self.assertEqual(P23[key], P22[key])
        self.assertEqual(len(P23['indexes']), 20)
        self.assertEqual(slim.DEFAULT_PROFILE_PATH, ROOT / 'profiles/v2_3.json')
        self.assertTrue(slim.output_schema(P22))
        self.assertTrue(slim.output_schema(P23))

    def test_main_does_not_read_archived_profile_or_07nov_fields(self):
        original_read_text = Path.read_text

        def refuse_historical(path, *args, **kwargs):
            if path.name in ('v2_1.json', 'v2_2.json', '07nov-fields.json'):
                raise AssertionError('active 2.3 accessed historical baseline')
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, 'read_text', refuse_historical):
            self.assertTrue(slim.check_profile(P23))

    def test_missing_main_lock_fails_closed(self):
        original_read_text = Path.read_text

        def refuse_main_lock(path, *args, **kwargs):
            if path.name == 'main-profile-2.3.json':
                raise FileNotFoundError('simulation: main lock unavailable')
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, 'read_text', refuse_main_lock), self.assertRaisesRegex(
                ValueError, 'main profile 2.3 lock unavailable'):
            slim.check_profile(P23)

    def test_disallowed_extra_drops_fail_closed(self):
        for table, col in [('cards', 'text'), ('cards', 'originalText'),
                           ('cards', 'printedText'), ('cards', 'flavorName'),
                           ('cards', 'faceFlavorName'), ('cards', 'isReserved'),
                           ('tokens', 'text'), ('sets', 'code')]:
            bad = copy.deepcopy(P23)
            bad['tables'][table].remove(col)
            with self.subTest(col=f'{table}.{col}'), self.assertRaisesRegex(
                    ValueError, 'main profile 2.3 differs from locked approved selection'):
                slim.check_profile(bad)

    def test_main_cannot_bypass_lock(self):
        for mode in ['add-removed-column', 'extra-removal', 'old-contract', 'legacy-exception',
                     'other-version', 'source-pin', 'index', 'identity', 'relationship']:
            bad = copy.deepcopy(P23)
            if mode == 'add-removed-column':
                bad['tables']['cards'].append('flavorText')
            elif mode == 'extra-removal':
                bad['tables']['cards'].remove('printedText')
            elif mode == 'old-contract':
                bad['historical_contract'] = P22['historical_contract']
            elif mode == 'legacy-exception':
                bad['intentional_omissions'] = {'cards': ['flavorText']}
            elif mode == 'other-version':
                bad['version'] = '2.4'
            elif mode == 'source-pin':
                bad['source_schema'] = bad['source_schema'][:-1]
            elif mode == 'index':
                bad['indexes'] = bad['indexes'][:-1]
            elif mode == 'identity':
                bad['unique_keys']['cards'] = 'name'
            elif mode == 'relationship':
                bad['relationships'] = bad['relationships'][:-1]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                slim.check_profile(bad)

    def test_main_build_cli_default_does_not_require_profile_argument(self):
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / 'build-report.json'
            captured = {}

            def fake_build(archive, expected, profile_path, output_dir, tool_commit):
                captured['profile_path'] = profile_path
                return {'status': 'PASS'}

            argv = ['slim.py', 'build', '--archive', 'unused.xz', '--sha256', '0'*64,
                    '--output-dir', str(Path(td)/'output'), '--tool-commit', 'a'*40,
                    '--report', str(report)]
            with patch.object(sys, 'argv', argv), patch.object(slim, 'build', fake_build):
                self.assertEqual(slim.main(), 0)
            self.assertEqual(captured['profile_path'], str(slim.DEFAULT_PROFILE_PATH))
            self.assertEqual(json.loads(report.read_text())['status'], 'PASS')

    def test_previous_baseline_profile_cannot_remove_story_spotlight(self):
        old = copy.deepcopy(P22)
        old['tables']['cards'].remove('isStorySpotlight')
        with self.assertRaisesRegex(ValueError, 'historical'):
            slim.check_profile(old)

    def test_real_sqlite_projection_preserves_rules_and_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, old, slim23 = (root / f for f in ('source.sqlite', 'old.sqlite', 'new.sqlite'))
            with sqlite3.connect(source) as db:
                for kind in ('table', 'index'):
                    for typ, _, _, sql in P23['source_schema']:
                        if typ == kind:
                            db.execute(sql)
                db.execute("INSERT INTO sets(code,name,tokenSetCode) VALUES ('SYN','Synthetic Set','TSYN')")
                db.execute("INSERT INTO meta VALUES ('2026-11-14','5.3.0+20261113')")
                db.execute("""INSERT INTO cards(uuid,setCode,number,name,printedName,
                           facePrintedName,language,text,originalText,printedText,
                           flavorText,isStorySpotlight,flavorName,faceFlavorName)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           ('a','SYN','1','Synthetic A','Printed A','Face A','English',
                            'Draw a card.','Original rules.','Printed rules.',
                            'Narrative flavor text.',1,'Alternative name','Alternate face'))
                db.execute("""INSERT INTO tokens(uuid,setCode,number,name,language,text,flavorText)
                           VALUES (?,?,?,?,?,?,?)""",
                           ('t','TSYN','1','Synthetic Token','English','Flying','Narrative token text.'))
                db.execute("INSERT INTO cardIdentifiers(uuid,scryfallId,scryfallOracleId) VALUES ('a','id-a','oracle-a')")
                db.execute("INSERT INTO cardLegalities(uuid,commander) VALUES ('a','Legal')")
                db.execute("INSERT INTO cardRulings(uuid,date,text) VALUES ('a','2026-11-14','Ruling survives.')")
                db.execute("INSERT INTO tokenIdentifiers(uuid,scryfallId) VALUES ('t','token-id')")
            report22 = slim.convert(source, old, P22)
            report23 = slim.convert(source, slim23, P23)
            self.assertEqual(report22['status'], 'PASS')
            self.assertEqual(report23['status'], 'PASS')
            with sqlite3.connect(old) as a, sqlite3.connect(slim23) as b:
                for table, removed in REMOVED.items():
                    old_columns = {row[1] for row in a.execute(f'PRAGMA table_info({table})')}
                    new_columns = {row[1] for row in b.execute(f'PRAGMA table_info({table})')}
                    self.assertEqual(old_columns - new_columns, removed)
                for table, fields in P23['tables'].items():
                    projection = ','.join('"' + x + '"' for x in fields)
                    self.assertEqual(
                        a.execute(f'SELECT {projection} FROM "{table}" ORDER BY {projection}').fetchall(),
                        b.execute(f'SELECT {projection} FROM "{table}" ORDER BY {projection}').fetchall())
                self.assertEqual(b.execute(
                    "SELECT text,originalText,printedText,flavorName,faceFlavorName FROM cards WHERE uuid='a'"
                ).fetchone(),('Draw a card.','Original rules.','Printed rules.',
                              'Alternative name','Alternate face'))
                self.assertEqual(b.execute('SELECT text FROM cardRulings').fetchone()[0],
                                 'Ruling survives.')
                self.assertEqual(b.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(
                    sorted((x[0],x[1],x[2]) for x in a.execute(
                        "SELECT name,tbl_name,sql FROM sqlite_schema WHERE type='index'")),
                    sorted((x[0],x[1],x[2]) for x in b.execute(
                        "SELECT name,tbl_name,sql FROM sqlite_schema WHERE type='index'")))
            self.assertEqual(slim.validate(slim23, P23, source=source)['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
