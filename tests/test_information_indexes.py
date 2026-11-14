"""Historical data contract and measured index policy regressions."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import slim
import test_slim as fixtures
ROOT=Path(slim.__file__).parent

class InformationContractTests(unittest.TestCase):
    def test_profile_is_full_historical_superset_with_exact_contract(self):
        p=json.loads((ROOT/'profiles/v2_2.json').read_text())
        contract=json.loads((ROOT/'contracts/historical-2026-11-07-field-baseline.json').read_text())['tables']
        self.assertEqual(p['historical_contract'],contract)
        old=json.loads((ROOT/'profiles/v2_1.json').read_text())
        self.assertEqual(set(p['tables']),set(contract))
        for table,columns in contract.items():
            self.assertTrue(set(columns)<=set(p['tables'][table]))
            self.assertTrue(set(old['tables'][table])<=set(p['tables'][table]))
        self.assertNotIn('cardForeignData',p['tables'])
        self.assertTrue(slim.output_schema(p))

    def test_historical_field_or_affinity_loss_rejected(self):
        p=json.loads((ROOT/'profiles/v2_2.json').read_text())
        for change in ['missing','wrong_affinity']:
            bad=copy.deepcopy(p)
            if change=='missing':bad['tables']['cards'].remove('isReserved')
            else:bad['historical_contract']['cards']['isReserved']='TEXT'
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'historical'):slim.check_profile(bad)

    def test_prior_profile_schema_remains_supported(self):
        old=json.loads((ROOT/'profiles/v2_1.json').read_text())
        expected={('table',t) for t in old['tables']}
        self.assertTrue(expected<={(r[0],r[1]) for r in slim.output_schema(old)})
        self.assertNotIn('indexes',old)

class ExplicitIndexTests(unittest.TestCase):
    setUp=fixtures.PipelineTests.setUp
    def fixture_profile(self):
        p=copy.deepcopy(self.profile)
        p['historical_contract']={'cards':{'uuid':'TEXT','printedName':'TEXT','facePrintedName':'TEXT','language':'TEXT'}}
        p['indexes']=[{'name':'idx_cards_uuid','table':'cards','columns':['uuid'],'unique':True},
            {'name':'idx_identifiers_uuid','table':'cardIdentifiers','columns':['uuid'],'unique':True},
            {'name':'idx_external','table':'cardIdentifiers','columns':['externalId'],'unique':False},
            {'name':'idx_cards_name_language','table':'cards','columns':['name','language'],'unique':False}]
        return p
    def test_lookup_join_multiface_null_and_no_duplicate_indexes(self):
        p=self.fixture_profile()
        with sqlite3.connect(self.db) as c:c.execute("UPDATE cardIdentifiers SET externalId='shared'")
        out=self.root/'indexed.sqlite';slim.convert(self.db,out,p)
        with sqlite3.connect(out) as c:
            rows=c.execute("SELECT c.uuid,c.printedName,c.facePrintedName FROM cardIdentifiers i JOIN cards c ON c.uuid=i.uuid WHERE i.externalId=? ORDER BY c.uuid",('shared',)).fetchall()
            self.assertEqual(rows,[('a','Feu // Glace','Feu'),('b','Feu // Glace','Glace')])
            plan=c.execute('EXPLAIN QUERY PLAN SELECT uuid FROM cardIdentifiers WHERE externalId=?',('shared',)).fetchall()
            self.assertTrue(any('idx_external' in str(x) for x in plan))
            self.assertEqual(len(c.execute('PRAGMA index_list(cards)').fetchall()),2)
        slim.validate(out,p,source=self.db)
    def test_bad_duplicate_or_missing_unique_index_rejected(self):
        for change in ['duplicate','missing_unique','missing_column','bad_unique_flag']:
            p=self.fixture_profile()
            if change=='duplicate':p['indexes'].append({'name':'duplicate','table':'cards','columns':['uuid'],'unique':False})
            if change=='missing_unique':p['indexes']=p['indexes'][1:]
            if change=='missing_column':p['indexes'][0]['columns']=['doesNotExist']
            if change=='bad_unique_flag':p['indexes'][0]['unique']='false'
            with self.subTest(change=change),self.assertRaises(ValueError):slim.check_profile(p)
    def test_missing_source_field_contract_is_rejected(self):
        p=self.fixture_profile();p['historical_contract']['cards']['unknown']='TEXT'
        with self.assertRaisesRegex(ValueError,'historical'):slim.check_profile(p)
    def test_null_identifiers_preserved_with_nonunique_lookup(self):
        p=self.fixture_profile()
        with sqlite3.connect(self.db) as c:c.execute("UPDATE cardIdentifiers SET externalId=NULL WHERE uuid='a'")
        out=self.root/'null.sqlite';slim.convert(self.db,out,p)
        with sqlite3.connect(out) as c:self.assertIsNone(c.execute("SELECT externalId FROM cardIdentifiers WHERE uuid='a'").fetchone()[0])
    def test_source_schema_drift_and_orphans_still_fail(self):
        p=self.fixture_profile()
        with sqlite3.connect(self.db) as c:c.execute("UPDATE cardIdentifiers SET uuid='orphan' WHERE uuid='a'")
        with self.assertRaisesRegex(ValueError,'orphan'):slim.convert(self.db,self.root/'bad.sqlite',p)
        with sqlite3.connect(self.db) as c:c.execute('ALTER TABLE cards ADD COLUMN newField TEXT')
        with self.assertRaisesRegex(ValueError,'schema'):slim.convert(self.db,self.root/'bad.sqlite',p)

class InventoryPolicyTests(unittest.TestCase):
    setUp=fixtures.PipelineTests.setUp
    def test_inventory_reports_actual_index_columns(self):
        result=slim.inventory(self.db)
        indexes=result['tables']['cards']['index_details']
        self.assertEqual(indexes[0]['name'],'idx_cards_name')
        self.assertEqual(indexes[0]['columns'],['name'])
        self.assertFalse(indexes[0]['unique'])


class NamedConsumerQueries(unittest.TestCase):
    def test_actual_identifier_names_csv_nulls_and_multiface_printings(self):
        import csv
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.sqlite';out=root/'out.sqlite'
            p=json.loads((ROOT/'profiles/v2_3.json').read_text())
            with sqlite3.connect(source) as c:
                for kind in ['table','index']:
                    for typ,_,_,sql in p['source_schema']:
                        if typ==kind:c.execute(sql)
                c.execute("INSERT INTO sets(code,name,tokenSetCode) VALUES ('SYN','Synthetic Set','TSYN')")
                c.execute("INSERT INTO meta VALUES ('2026-11-13','5.3.0+20261113')")
                c.executemany('INSERT INTO cards(uuid,setCode,number,name,printedName,facePrintedName,otherFaceIds,layout,side,text,language,isReserved,isPromo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',[
                    ('a','SYN','1','Synthetic Front // Back','印刷名','顔Ａ','b','transform','a','Draw a card.','Japanese',1,0),
                    ('b','SYN','1','Synthetic Front // Back','印刷名','顔Ｂ','a','transform','b','Flying','Japanese',None,1)])
                c.execute("UPDATE cards SET artist='Synthetic Artist',watermark='synthetic-mark' WHERE uuid='a'")
                c.executemany('INSERT INTO cardIdentifiers(uuid,scryfallId,scryfallOracleId) VALUES (?,?,?)',[('a','same-printing','same-oracle'),('b','same-printing','same-oracle')])
                c.executemany('INSERT INTO cardLegalities(uuid,commander) VALUES (?,?)',[('a','Legal'),('b','Legal')])
                c.execute("INSERT INTO cardRulings VALUES ('a','2026-11-13','Synthetic ruling.')")
                c.execute("INSERT INTO tokens(uuid,setCode,number,name,language) VALUES ('t','TSYN','1','Synthetic Token','Japanese')")
                c.execute("INSERT INTO tokenIdentifiers(uuid,scryfallId,scryfallOracleId) VALUES ('t','token-printing','token-oracle')")
            slim.convert(source,out,p)
            with slim.connect(out) as c:
                for field,index in [('scryfallId','idx_cardIdentifiers_scryfallid'),('scryfallOracleId','idx_cardIdentifiers_oracleid')]:
                    value='same-printing' if field=='scryfallId' else 'same-oracle'
                    sql=f'SELECT c.uuid,c.isReserved,c.facePrintedName FROM cardIdentifiers i JOIN cards c ON c.uuid=i.uuid WHERE i.{field}=? ORDER BY c.uuid'
                    self.assertEqual(c.execute(sql,(value,)).fetchall(),[('a',1,'顔Ａ'),('b',None,'顔Ｂ')])
                    self.assertIn(index,str(c.execute('EXPLAIN QUERY PLAN '+sql,(value,)).fetchall()))
                self.assertEqual(c.execute("SELECT artist,watermark FROM cards WHERE uuid='a'").fetchone(),('Synthetic Artist','synthetic-mark'))
                row=next(csv.DictReader(io.StringIO('Name,Set,Number\nSynthetic Front // Back,SYN,1\n')))
                self.assertEqual(c.execute('SELECT uuid FROM cards WHERE name=? AND setCode=? AND number=? ORDER BY uuid',(row['Name'],row['Set'],row['Number'])).fetchall(),[('a',),('b',)])
                self.assertEqual(c.execute('SELECT t.uuid FROM tokenIdentifiers i JOIN tokens t ON t.uuid=i.uuid WHERE i.scryfallId=?',('token-printing',)).fetchall(),[('t',)])
                self.assertIsNone(c.execute("SELECT multiverseId FROM cardIdentifiers WHERE uuid='a'").fetchone()[0])
                self.assertEqual(c.execute("SELECT c.uuid,l.commander,r.text FROM cards c JOIN cardLegalities l ON l.uuid=c.uuid LEFT JOIN cardRulings r ON r.uuid=c.uuid WHERE c.uuid='a'").fetchone(),('a','Legal','Synthetic ruling.'))
                with self.assertRaises(sqlite3.OperationalError):c.execute("DELETE FROM cards")


class ReviewRegressions(unittest.TestCase):
    def test_preservation_profile_cannot_remove_or_rewrite_fixed_contract(self):
        p=json.loads((ROOT/'profiles/v2_2.json').read_text())
        for mode in ['remove_contract','rewrite_contract']:
            bad=copy.deepcopy(p)
            bad['tables']['cards'].remove('isReserved')
            if mode=='remove_contract':bad.pop('historical_contract')
            else:bad['historical_contract']['cards'].pop('isReserved')
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'historical'):
                slim.output_schema(bad)

    def test_unavailable_dbstat_is_not_reported_as_zero_bytes(self):
        import tempfile
        from unittest.mock import patch
        from benchmarks import query_audit as qa
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sample.sqlite'
            c=sqlite3.connect(path)
            c.executescript('CREATE TABLE cards(uuid TEXT); CREATE INDEX idx_cards_uuid ON cards(uuid); INSERT INTO cards VALUES ("a"); CREATE TABLE meta(date TEXT,version TEXT); INSERT INTO meta VALUES ("2026-11-13","5.3.0+20261113");')
            c.set_authorizer(lambda action,arg1,arg2,db,trigger: sqlite3.SQLITE_DENY if arg1=='dbstat' else sqlite3.SQLITE_OK)
            with patch.object(qa,'connect',return_value=c):
                report=qa.run(path,{'uuid':{'sql':'SELECT uuid FROM cards WHERE uuid=?','parameters':[['a']]}},repeats=1)
            self.assertIsNone(report['index_bytes'])
            self.assertTrue(report['index_footprint_error'])
            self.assertEqual(len(report['indexes']),1)

if __name__=='__main__':unittest.main()
