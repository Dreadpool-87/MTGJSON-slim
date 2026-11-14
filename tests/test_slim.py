"""Behavioral pipeline tests; miniature relational SQLite, never live downloads."""
import copy
import hashlib
import json
import lzma
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import slim
except ImportError:
    slim = None


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(slim, 'slim pipeline is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'source.sqlite'
        with sqlite3.connect(self.db) as c:
            c.executescript('''CREATE TABLE cards (uuid TEXT, name TEXT, printedName TEXT,
                facePrintedName TEXT, language TEXT, cosmetic TEXT);
                CREATE INDEX idx_cards_name ON cards(name);
                CREATE TABLE cardIdentifiers (uuid TEXT, externalId TEXT);
                CREATE TABLE meta (date TEXT, version TEXT);''')
            c.executemany('INSERT INTO cards VALUES (?,?,?,?,?,?)', [
                ('a','Fire // Ice','Feu // Glace','Feu','French','art'),
                ('b','Fire // Ice','Feu // Glace','Glace','French','art')])
            c.executemany('INSERT INTO cardIdentifiers VALUES (?,?)',[('a','1'),('b','2')])
            c.execute("INSERT INTO meta VALUES ('2026-11-12','5.3.0+20261112')")
        self.profile = {'version':'test-1','description':'fixture',
            'source_schema':slim.schema(self.db),
            'tables':{'cards':['uuid','name','printedName','facePrintedName','language'],
                      'cardIdentifiers':['uuid','externalId'],'meta':['date','version']},
            'unique_keys':{'cards':'uuid','cardIdentifiers':'uuid'},
            'relationships':[['cardIdentifiers','uuid','cards','uuid']]}
        self.archive = self.root/'source.sqlite.xz'
        self.archive.write_bytes(lzma.compress(self.db.read_bytes()))
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.profile_path=self.root/'profile.json'
        self.profile_path.write_text(json.dumps(self.profile))

    def test_retains_multilingual_names_and_repeats_bytes(self):
        outputs=[]
        for n in ['one','two']:
            out=self.root/(n+'.sqlite')
            slim.convert(self.db,out,self.profile)
            report=slim.validate(out,self.profile,source=self.db)
            self.assertEqual(report['status'],'PASS')
            with sqlite3.connect(out) as c:
                self.assertEqual(c.execute('SELECT printedName,facePrintedName,language FROM cards ORDER BY uuid').fetchall(),
                    [('Feu // Glace','Feu','French'),('Feu // Glace','Glace','French')])
            outputs.append(out.read_bytes())
        self.assertEqual(*outputs)

    def test_checksum_rejects_tamper(self):
        slim.verify(self.archive,self.digest)
        self.archive.write_bytes(self.archive.read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'checksum'):
            slim.verify(self.archive,self.digest)

    def test_schema_changes_fail_before_output(self):
        for sql in ['DROP TABLE cardIdentifiers','ALTER TABLE cards ADD COLUMN newField TEXT',
                    'CREATE TABLE surprise (x TEXT)','CREATE INDEX surprise ON cards(language)',
                    'CREATE TRIGGER surprise AFTER INSERT ON cards BEGIN SELECT 1; END']:
            changed=self.root/'changed.sqlite'
            changed.write_bytes(self.db.read_bytes())
            with sqlite3.connect(changed) as c:c.execute(sql)
            out=self.root/'must-not-exist.sqlite'
            with self.subTest(sql=sql), self.assertRaisesRegex(ValueError,'schema'):
                slim.convert(changed,out,self.profile)
            self.assertFalse(out.exists())

    def test_invalid_profile_fails_closed(self):
        for change in [{'version':''},{'unexpected':True},{'tables':{'cards':['uuid','missing']}},
                       {'relationships':[['missing','uuid','cards','uuid']]},
                       {'unique_keys':{'cards':'missing'}}]:
            profile=copy.deepcopy(self.profile);profile.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                slim.convert(self.db,self.root/'bad.sqlite',profile)

    def test_orphan_and_duplicate_rejected(self):
        for sql in ["UPDATE cardIdentifiers SET uuid='orphan' WHERE uuid='a'",
                    "UPDATE cards SET uuid='b' WHERE uuid='a'", "UPDATE cards SET uuid=NULL WHERE uuid='a'"]:
            bad=self.root/'bad.sqlite';bad.write_bytes(self.db.read_bytes())
            with sqlite3.connect(bad) as c:c.execute(sql)
            with self.subTest(sql=sql),self.assertRaises(ValueError):
                slim.convert(bad,self.root/'out.sqlite',self.profile)
            self.assertFalse((self.root/'out.sqlite').exists())

    def test_validator_rejects_changed_output_and_rows(self):
        out=self.root/'out.sqlite';slim.convert(self.db,out,self.profile)
        with sqlite3.connect(out) as c:c.execute("UPDATE cards SET printedName='wrong' WHERE uuid='a'")
        with self.assertRaisesRegex(ValueError,'rows'):
            slim.validate(out,self.profile,source=self.db)
        with sqlite3.connect(out) as c:c.execute('DROP INDEX idx_cards_name')
        with self.assertRaisesRegex(ValueError,'schema'):
            slim.validate(out,self.profile)

    def test_corrupt_sqlite_rejected(self):
        self.db.write_bytes(b'not sqlite')
        with self.assertRaises((ValueError,sqlite3.DatabaseError)):
            slim.convert(self.db,self.root/'out.sqlite',self.profile)

    def test_existing_output_and_source_overwrite_rejected(self):
        before=self.db.read_bytes()
        with self.assertRaises((ValueError,FileExistsError)):
            slim.convert(self.db,self.db,self.profile)
        self.assertEqual(before,self.db.read_bytes())

    def test_cli_failures_nonzero_and_machine_readable(self):
        for case in ['missing-table','changed-column','bad-checksum','corrupt-sqlite','invalid-profile']:
            root=self.root/case;root.mkdir()
            db=root/'input.sqlite';db.write_bytes(self.db.read_bytes())
            profile=copy.deepcopy(self.profile)
            if case=='missing-table':
                with sqlite3.connect(db) as c:c.execute('DROP TABLE cards')
            if case=='changed-column':
                with sqlite3.connect(db) as c:c.execute('ALTER TABLE cards ADD COLUMN unknown TEXT')
            if case=='corrupt-sqlite':db.write_bytes(b'corrupted')
            if case=='invalid-profile':profile['version']=''
            profile_path=root/'profile.json';profile_path.write_text(json.dumps(profile))
            archive=root/'source.xz';archive.write_bytes(lzma.compress(db.read_bytes()))
            digest=hashlib.sha256(archive.read_bytes()).hexdigest()
            if case=='bad-checksum':digest='0'*64
            report=root/'report.json'
            result=subprocess.run([sys.executable,str(Path(slim.__file__)),'build','--archive',str(archive),
                '--sha256',digest,'--profile',str(profile_path),'--output-dir',str(root/'output'),
                '--report',str(report),'--tool-commit','a'*40],capture_output=True,text=True)
            with self.subTest(case=case):
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(json.loads(report.read_text())['status'],'FAIL')
                self.assertFalse(list((root/'output').glob('*.xz')))


if __name__ == '__main__':unittest.main()

class PackagingTests(unittest.TestCase):
    setUp = PipelineTests.setUp
    def test_package_manifest_and_unchanged_detection(self):
        out=self.root/'package'
        first=slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)
        self.assertEqual(first['status'],'PASS')
        m=first['manifest']
        self.assertEqual(m['upstream']['version'],'5.3.0+20261112')
        self.assertEqual(m['profile_version'],'test-1')
        self.assertEqual(m['tool_commit'],'a'*40)
        archive=out/m['output']['archive']['name']
        db=out/m['output']['sqlite']['name']
        self.assertEqual(lzma.decompress(archive.read_bytes()), db.read_bytes())
        for artifact in m['output'].values():
            filename=artifact['name']
            sidecar=out/(filename+'.sha256')
            self.assertEqual(sidecar.read_text(), f"{artifact['sha256']}  {filename}\n")
            self.assertEqual(hashlib.sha256((out/filename).read_bytes()).hexdigest(), artifact['sha256'])
        with sqlite3.connect(db) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)['status'],'UNCHANGED')
        archive.write_bytes(archive.read_bytes()+b'tampered')
        with self.assertRaisesRegex(ValueError,'checksum'):
            slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)

    def test_reject_missing_or_tampered_distribution_sidecars(self):
        for field in ['sqlite', 'archive']:
            for tamper in ['missing', 'changed']:
                out=self.root/f'package-{field}-{tamper}'
                m=slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)['manifest']
                name=m['output'][field]['name']
                sidecar=out/(name+'.sha256')
                if tamper=='missing':
                    sidecar.unlink()
                else:
                    sidecar.write_text('0'*64+'  '+name+'\\n')
                with self.subTest(field=field,tamper=tamper), self.assertRaisesRegex(ValueError,'invalid checksum sidecar'):
                    slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)

    def test_reject_changed_tool_and_missing_printed_name(self):
        out=self.root/'package';slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)
        with self.assertRaises(FileExistsError):
            slim.build(self.archive,self.digest,self.profile_path,out,'b'*40)
        p=copy.deepcopy(self.profile);p['tables']['cards'].remove('printedName')
        with self.assertRaisesRegex(ValueError,'printedName'):
            slim.convert(self.db,self.root/'bad.sqlite',p)

class OfficialProfileTests(unittest.TestCase):
    def test_tokens_use_documented_token_set_code(self):
        p=json.loads((Path(slim.__file__).parent/'profiles/v2_1.json').read_text())
        self.assertIn(['tokens','setCode','sets','tokenSetCode'],p['relationships'])
        self.assertNotIn(['tokens','setCode','sets','code'],p['relationships'])

class ReviewRegressionTests(unittest.TestCase):
    setUp = PipelineTests.setUp

    def test_sqlite_prefix_lookalike_is_unknown_schema(self):
        with sqlite3.connect(self.db) as c:c.execute('CREATE TABLE sqliteXunexpected (x TEXT)')
        with self.assertRaisesRegex(ValueError,'schema'):
            slim.convert(self.db,self.root/'bad.sqlite',self.profile)

    def test_reuse_rejects_forged_manifest_for_changed_database(self):
        out=self.root/'package';m=slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)['manifest']
        db=out/m['output']['sqlite']['name']
        with sqlite3.connect(db) as c:c.execute("UPDATE cards SET printedName='wrong' WHERE uuid='a'")
        m['output']['sqlite']['sha256']=slim.digest(db)
        (out/'manifest.json').write_text(json.dumps(m))
        with self.assertRaises(ValueError):
            slim.build(self.archive,self.digest,self.profile_path,out,'a'*40)

    def test_report_cannot_overwrite_input_or_package(self):
        for report in [self.archive,self.profile_path,self.root/'package'/'manifest.json']:
            before=self.archive.read_bytes();profile_before=self.profile_path.read_bytes()
            result=subprocess.run([sys.executable,str(Path(slim.__file__)),'build',
                '--archive',str(self.archive),'--sha256',self.digest,'--profile',str(self.profile_path),
                '--output-dir',str(self.root/'package'),'--tool-commit','a'*40,'--report',str(report)],
                capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(self.archive.read_bytes(),before)
            self.assertEqual(self.profile_path.read_bytes(),profile_before)

class DownloadTests(unittest.TestCase):
    setUp = PipelineTests.setUp

    def test_real_http_download_named_agent_tamper_and_unchanged(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        archive_bytes=self.archive.read_bytes()
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                requests.append((self.path,self.headers.get('User-Agent')))
                if not self.headers.get('User-Agent','').startswith('MTGJSON-slim/'):
                    self.send_response(403);self.end_headers();return
                self.send_response(200);self.end_headers()
                self.wfile.write(hashlib.sha256(archive_bytes).hexdigest().encode()
                    if self.path.endswith('.sha256') else archive_bytes)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        original=slim.UPSTREAM
        slim.UPSTREAM=f'http://127.0.0.1:{server.server_port}/source.xz'
        self.addCleanup(setattr,slim,'UPSTREAM',original)
        result=slim.download(self.root/'download')
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(Path(result['archive']).read_bytes(),archive_bytes)
        requests.clear()
        result=slim.download(self.root/'unchanged',previous_sha256=self.digest)
        self.assertEqual(result['status'],'UNCHANGED')
        self.assertEqual(len(requests),1)
        self.assertTrue(requests[0][0].endswith('.sha256'))
        self.assertFalse((self.root/'unchanged'/'AllPrintings.sqlite.xz').exists())
        Path(self.root/'download'/'AllPrintings.sqlite.xz').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'checksum'):
            slim.download(self.root/'download')

class ReportAliasTests(unittest.TestCase):
    setUp = PipelineTests.setUp

    def test_report_hardlink_cannot_overwrite_verified_archive(self):
        report=self.root/'aliased-report.json';report.hardlink_to(self.archive)
        before=self.archive.read_bytes()
        result=subprocess.run([sys.executable,str(Path(slim.__file__)),'build',
            '--archive',str(self.archive),'--sha256',self.digest,'--profile',str(self.profile_path),
            '--output-dir',str(self.root/'package'),'--tool-commit','a'*40,'--report',str(report)],
            capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.archive.read_bytes(),before)

class ProfileV2Tests(unittest.TestCase):
    setUp = PipelineTests.setUp

    def test_active_profile_omits_foreign_data_but_audits_upstream_schema(self):
        p=json.loads((Path(slim.__file__).parent/'profiles/v2_1.json').read_text())
        self.assertEqual(p['version'],'2.1')
        self.assertNotIn('cardForeignData',p['tables'])
        self.assertFalse(any('cardForeignData' in r for r in p['relationships']))
        self.assertTrue(any(row[0]=='table' and row[1]=='cardForeignData' for row in p['source_schema']))
        schema=slim.output_schema(p)
        self.assertFalse(any(row[2]=='cardForeignData' for row in schema))
        self.assertEqual(len([r for r in schema if r[0]=='table']),8)
        for essential in ['uuid','name','text','printedName','facePrintedName','otherFaceIds','language']:
            self.assertIn(essential,p['tables']['cards'])

    def add_foreign_source_table(self):
        with sqlite3.connect(self.db) as c:
            c.executescript('CREATE TABLE cardForeignData (uuid TEXT, language TEXT, name TEXT);'
                'CREATE INDEX idx_foreign_uuid ON cardForeignData(uuid);')
            c.execute("INSERT INTO cardForeignData VALUES ('a','French','Feu')")
        self.profile['source_schema']=slim.schema(self.db)

    def test_foreign_table_and_index_absent_from_generated_sqlite(self):
        self.add_foreign_source_table()
        out=self.root/'v2.sqlite';slim.convert(self.db,out,self.profile)
        slim.validate(out,self.profile,source=self.db)
        with sqlite3.connect(out) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM sqlite_schema WHERE tbl_name='cardForeignData'").fetchone()[0],0)
            self.assertEqual(c.execute('SELECT uuid,printedName,facePrintedName,language FROM cards ORDER BY uuid').fetchall(),
                [('a','Feu // Glace','Feu','French'),('b','Feu // Glace','Glace','French')])

    def test_drift_in_omitted_foreign_source_table_still_fails(self):
        self.add_foreign_source_table()
        with sqlite3.connect(self.db) as c:c.execute('ALTER TABLE cardForeignData ADD COLUMN newField TEXT')
        with self.assertRaisesRegex(ValueError,'schema'):
            slim.convert(self.db,self.root/'v2.sqlite',self.profile)
        self.assertFalse((self.root/'v2.sqlite').exists())

    def test_nonenglish_complex_faces_keep_oracle_text_and_printing_ids(self):
        with sqlite3.connect(self.db) as c:
            for name in ['layout','otherFaceIds','side','text']:
                c.execute(f'ALTER TABLE cards ADD COLUMN {name} TEXT')
            c.execute("UPDATE cards SET layout='transform',otherFaceIds='b',side='a',text='Draw a card.' WHERE uuid='a'")
            c.execute("UPDATE cards SET layout='transform',otherFaceIds='a',side='b',text='Flying' WHERE uuid='b'")
        self.profile['tables']['cards']+=['layout','otherFaceIds','side','text']
        self.profile['source_schema']=slim.schema(self.db)
        out=self.root/'v2.sqlite';slim.convert(self.db,out,self.profile)
        with sqlite3.connect(out) as c:
            self.assertEqual(c.execute('SELECT uuid,language,layout,otherFaceIds,side,text FROM cards ORDER BY uuid').fetchall(),
                [('a','French','transform','b','a','Draw a card.'),('b','French','transform','a','b','Flying')])
            self.assertEqual(c.execute('SELECT * FROM cardIdentifiers ORDER BY uuid').fetchall(),[('a','1'),('b','2')])
