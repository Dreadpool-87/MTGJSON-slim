"""Profile 2.3 preserves every v2.2 field except three explicit narrative fields."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slim

ROOT = Path(__file__).resolve().parents[1]
P22 = json.loads((ROOT / 'profiles/v2_2.json').read_text())
P23 = json.loads((ROOT / 'profiles/v2_3.json').read_text())
REMOVED = {'cards': {'flavorText', 'isStorySpotlight'}, 'tokens': {'flavorText'}}


class ReviewedOmissionTests(unittest.TestCase):
    def test_exact_differences_and_old_profiles_remain_unchanged(self):
        self.assertEqual(P23['version'], '2.3')
        self.assertEqual(P23['intentional_omissions'],
                         {k: sorted(v) for k, v in REMOVED.items()})
        self.assertEqual(P23['historical_contract'], P22['historical_contract'])
        self.assertEqual(set(P23['tables']), set(P22['tables']))
        self.assertEqual(sum(map(len, P22['tables'].values())), 227)
        self.assertEqual(sum(map(len, P23['tables'].values())), 224)
        for table, columns in P22['tables'].items():
            self.assertEqual(P23['tables'][table],
                             [field for field in columns if field not in REMOVED.get(table, set())])
        for key in ('source_schema', 'indexes', 'relationships', 'unique_keys'):
            self.assertEqual(P23[key], P22[key])
        self.assertEqual(len(P23['indexes']), 20)
        self.assertTrue(slim.output_schema(P22))
        self.assertTrue(slim.output_schema(P23))

    def test_disallowed_extra_drops_fail_closed(self):
        for table, col in [('cards', 'text'), ('cards', 'originalText'),
                           ('cards', 'printedText'), ('cards', 'flavorName'),
                           ('cards', 'faceFlavorName'), ('cards', 'isReserved'),
                           ('tokens', 'text'), ('sets', 'code')]:
            bad = copy.deepcopy(P23)
            bad['tables'][table].remove(col)
            with self.subTest(col=f'{table}.{col}'), self.assertRaisesRegex(
                    ValueError, 'only the three explicitly approved columns'):
                slim.check_profile(bad)

    def test_omissions_cannot_be_expanded_or_bypassed(self):
        for mode in ['none', 'wrong', 'baseline', 'old-contract', 'other-version',
                     'source-pin', 'index']:
            p = copy.deepcopy(P23)
            if mode == 'none':
                p.pop('intentional_omissions')
            elif mode == 'wrong':
                p['intentional_omissions']['cards'].append('text')
            elif mode == 'baseline':
                p['tables']['cards'].append('flavorText')
            elif mode == 'old-contract':
                p['historical_contract']['cards'].pop('isStorySpotlight')
            elif mode == 'other-version':
                p['version'] = '2.4'
            elif mode == 'source-pin':
                p['source_schema'] = p['source_schema'][:-1]
            elif mode == 'index':
                p['indexes'] = p['indexes'][:-1]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                slim.check_profile(p)

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
