#!/usr/bin/env python3
"""Read-only, deterministic warm-cache consumer query audit; standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import statistics
import time


def connect(path):
    return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)


def workloads(path, samples=12):
    c=connect(path);rng=random.Random(20261113)
    def choose(sql,n=samples):
        rows=c.execute(sql).fetchall()
        return rng.sample(rows,min(n,len(rows)))
    cases={
      'csv_name_set_number':('SELECT uuid FROM cards WHERE name=? AND setCode=? AND number=? ORDER BY uuid',choose('SELECT name,setCode,number FROM cards ORDER BY uuid')),
      'scryfall_printing':('SELECT c.uuid,c.name,c.layout,c.side FROM cardIdentifiers i JOIN cards c ON c.uuid=i.uuid WHERE i.scryfallId=? ORDER BY c.uuid',choose('SELECT scryfallId FROM cardIdentifiers GROUP BY scryfallId HAVING count(*)=1 ORDER BY scryfallId',6)+choose('SELECT scryfallId FROM cardIdentifiers GROUP BY scryfallId HAVING count(*)>1 ORDER BY scryfallId',6)),
      'oracle_printings':('SELECT c.uuid,c.name,c.setCode,c.number FROM cardIdentifiers i JOIN cards c ON c.uuid=i.uuid WHERE i.scryfallOracleId=? ORDER BY c.uuid',choose('SELECT scryfallOracleId FROM cardIdentifiers GROUP BY scryfallOracleId HAVING count(*)=1 ORDER BY scryfallOracleId',4)+choose('SELECT scryfallOracleId FROM cardIdentifiers GROUP BY scryfallOracleId HAVING count(*) BETWEEN 2 AND 10 ORDER BY scryfallOracleId',4)+choose('SELECT scryfallOracleId FROM cardIdentifiers GROUP BY scryfallOracleId HAVING count(*)>10 ORDER BY count(*) DESC,scryfallOracleId LIMIT 200',4)),
      'legality_ruling_join':('SELECT c.uuid,l.commander,r.date,r.text FROM cards c JOIN cardLegalities l ON l.uuid=c.uuid LEFT JOIN cardRulings r ON r.uuid=c.uuid WHERE c.uuid=? ORDER BY r.date,r.text',choose('SELECT uuid FROM cardRulings GROUP BY uuid ORDER BY uuid')),
      'name':('SELECT uuid,name,setCode,number FROM cards WHERE name=? ORDER BY uuid',choose('SELECT name FROM cards GROUP BY name ORDER BY name')),
      'printed_name':('SELECT uuid,name,printedName FROM cards WHERE printedName=? ORDER BY uuid',choose('SELECT printedName FROM cards WHERE printedName IS NOT NULL GROUP BY printedName ORDER BY printedName')),
      'face_printed_name':('SELECT uuid,name,facePrintedName FROM cards WHERE facePrintedName=? ORDER BY uuid',choose('SELECT facePrintedName FROM cards WHERE facePrintedName IS NOT NULL GROUP BY facePrintedName ORDER BY facePrintedName')),
      'set_number':('SELECT uuid,name FROM cards WHERE setCode=? AND number=? ORDER BY uuid',choose('SELECT setCode,number FROM cards ORDER BY uuid')),
      'set_only':('SELECT uuid FROM cards WHERE setCode=? ORDER BY uuid',choose('SELECT setCode FROM cards GROUP BY setCode ORDER BY setCode')),
      'token_printing':('SELECT t.uuid,t.name,s.code FROM tokenIdentifiers i JOIN tokens t ON t.uuid=i.uuid LEFT JOIN sets s ON s.tokenSetCode=t.setCode WHERE i.scryfallId=? ORDER BY t.uuid,s.code',choose('SELECT scryfallId FROM tokenIdentifiers GROUP BY scryfallId ORDER BY scryfallId')),
      'token_oracle':('SELECT t.uuid,t.name FROM tokenIdentifiers i JOIN tokens t ON t.uuid=i.uuid WHERE i.scryfallOracleId=? ORDER BY t.uuid',choose('SELECT scryfallOracleId FROM tokenIdentifiers GROUP BY scryfallOracleId ORDER BY scryfallOracleId')),
      'token_name':('SELECT uuid,name FROM tokens WHERE name=? ORDER BY uuid',choose('SELECT name FROM tokens GROUP BY name ORDER BY name')),
      'token_set_number':('SELECT uuid,name FROM tokens WHERE setCode=? AND number=? ORDER BY uuid',choose('SELECT setCode,number FROM tokens ORDER BY uuid')),
      'set_token_code':('SELECT code,name FROM sets WHERE tokenSetCode=? ORDER BY code',choose('SELECT tokenSetCode FROM sets WHERE tokenSetCode IS NOT NULL ORDER BY tokenSetCode')),
      'set_name':('SELECT code,name FROM sets WHERE name=? ORDER BY code',choose('SELECT name FROM sets ORDER BY name')),
    }
    pairs=[]
    for uuid,links in choose('SELECT uuid,otherFaceIds FROM cards WHERE otherFaceIds IS NOT NULL ORDER BY uuid'):
        pairs.append((links.split(',')[0].strip(),uuid))
    cases['face_lookup']=('SELECT a.uuid,a.layout,a.otherFaceIds,b.uuid,b.name FROM cards a JOIN cards b ON b.uuid=? WHERE a.uuid=?',pairs)
    names=choose('SELECT printedName FROM cards WHERE printedName IS NOT NULL GROUP BY printedName ORDER BY printedName')
    cases['any_exact_name']=('SELECT uuid,name FROM cards WHERE name=? OR printedName=? OR facePrintedName=? ORDER BY uuid',[(x[0],)*3 for x in names])
    cases['token_set_only']=('SELECT uuid FROM tokens WHERE setCode=? ORDER BY uuid',choose('SELECT setCode FROM tokens GROUP BY setCode ORDER BY setCode'))
    missing='00000000-0000-0000-0000-000000000000'
    assert not c.execute('SELECT 1 FROM cardIdentifiers WHERE scryfallId=? OR scryfallOracleId=?',(missing,missing)).fetchone()
    cases['missing_scryfall']=('SELECT uuid FROM cardIdentifiers WHERE scryfallId=?',[(missing,)])
    cases['missing_oracle']=('SELECT uuid FROM cardIdentifiers WHERE scryfallOracleId=?',[(missing,)])
    cases['missing_csv']=('SELECT uuid FROM cards WHERE name=? AND setCode=? AND number=?',[('__synthetic_missing__','__none__','__none__')])
    c.close()
    result={k:{'sql':sql,'parameters':params} for k,(sql,params) in cases.items()}
    for name,case in result.items():
        case['sampling']='Deterministic seed 20261113; sample from complete candidate population.'
        if name=='oracle_printings':case['sampling']='4 singleton Oracle IDs, 4 with 2-10 rows, 4 sampled from top 200 high-fanout IDs.'
        if name=='scryfall_printing':case['sampling']='6 singleton printing IDs and 6 shared multi-face printing IDs.'
        if name.startswith('missing_'):case['sampling']='Explicit synthetic miss; not a personal collection.'
    return result


def index_inventory(c):
    result=[]
    footprint={}
    footprint_error=None
    try:footprint=dict(c.execute("SELECT name,sum(pgsize) FROM dbstat GROUP BY name"))
    except sqlite3.Error as error:footprint_error=str(error)
    for table, in c.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT GLOB 'sqlite_*' ORDER BY name").fetchall():
        for row in c.execute('PRAGMA index_list("'+table+'")').fetchall():
            name=row[1]
            result.append({'table':table,'name':name,'unique':bool(row[2]),'columns':[x[2] for x in c.execute('PRAGMA index_info("'+name+'")')],
                'origin':row[3],'partial':bool(row[4]),'bytes':footprint.get(name),'sql':c.execute('SELECT sql FROM sqlite_schema WHERE name=?',(name,)).fetchone()[0]})
    measured=all(x['bytes'] is not None for x in result) and footprint_error is None
    return {'indexes':result,'index_bytes':sum(x['bytes'] for x in result) if measured else None,
            'index_footprint_error':footprint_error, 'index_footprint_source':'dbstat' if measured else None}


def run(path,cases,repeats=5):
    c=connect(path);c.execute('PRAGMA automatic_index=ON')
    result={'database':str(path),'size_bytes':Path(path).stat().st_size,'meta':c.execute('SELECT * FROM meta').fetchall(),
      'sqlite_version':sqlite3.sqlite_version,'mode':'warm cache, one unmeasured warmup; full fetchall; deterministic parameters; five repeated batches by default',
      'automatic_index':c.execute('PRAGMA automatic_index').fetchone()[0],'repeats':repeats,'queries':{}}
    result.update(index_inventory(c))
    for name,case in cases.items():
        sql=case['sql'];params=case['parameters'];assert params,name
        expected=[c.execute(sql,p).fetchall() for p in params]
        times=[]
        for _ in range(repeats):
            start=time.perf_counter_ns();values=[c.execute(sql,p).fetchall() for p in params];elapsed=time.perf_counter_ns()-start
            assert values==expected
            times.append(elapsed/1000/len(params))
        result['queries'][name]={'sql':sql,'parameters':params,'sampling':case.get('sampling','See pinned case file.'),'sample_count':len(params),'rows_per_sample':[len(x) for x in expected],
          'result_sha256':hashlib.sha256(json.dumps(expected,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
          'microseconds_per_lookup_runs':times,'median_microseconds_per_lookup':statistics.median(times),
          'explain_query_plan':[{'parameters':p,'plan':c.execute('EXPLAIN QUERY PLAN '+sql,p).fetchall()} for p in params]}
    c.close();return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True);p.add_argument('--cases',required=True);p.add_argument('--report',required=True);p.add_argument('--repeats',type=int,default=5);p.add_argument('--create-cases',action='store_true');a=p.parse_args()
    if a.create_cases:Path(a.cases).write_text(json.dumps(workloads(a.database),indent=2))
    result=run(a.database,json.loads(Path(a.cases).read_text()),a.repeats);Path(a.report).write_text(json.dumps(result,indent=2));print(json.dumps({k:round(x['median_microseconds_per_lookup'],2) for k,x in result['queries'].items()}))

if __name__=='__main__':main()
