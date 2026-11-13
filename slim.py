#!/usr/bin/env python3
"""Verified, fail-closed MTGJSON SQLite projection. Python 3.11+ standard library."""
import argparse
from contextlib import closing
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import resource
import shutil
import sqlite3
import sys
import tempfile
import time
import urllib.request

UPSTREAM = 'https://mtgjson.com/api/v5/AllPrintings.sqlite.xz'
USER_AGENT = 'MTGJSON-slim/1 (+https://github.com/Dreadpool-87/MTGJSON-slim)'


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def connect(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def digest(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def verify(path, expected):
    if not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
        raise ValueError('invalid SHA-256 checksum syntax')
    actual = digest(path)
    if actual != expected.lower():
        raise ValueError(f'checksum mismatch: expected {expected}, actual {actual}')
    return actual


def schema(path):
    with closing(connect(path)) as c:
        return [list(row) for row in c.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema "
            "WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name")]


def inventory(path):
    with closing(connect(path)) as c:
        result = {'size_bytes': Path(path).stat().st_size, 'schema': schema(path), 'tables': {}}
        for kind, name, _, _ in result['schema']:
            if kind != 'table':
                continue
            q = quote(name)
            result['tables'][name] = {
                'columns': [list(x) for x in c.execute(f'PRAGMA table_info({q})')],
                'foreign_keys': [list(x) for x in c.execute(f'PRAGMA foreign_key_list({q})')],
                'indexes': [list(x) for x in c.execute(f'PRAGMA index_list({q})')],
                'count': c.execute(f'SELECT count(*) FROM {q}').fetchone()[0]}
        result['integrity_check'] = [x[0] for x in c.execute('PRAGMA integrity_check')]
        return result


def check_profile(p):
    required = {'version', 'description', 'source_schema', 'tables', 'unique_keys', 'relationships'}
    if not isinstance(p, dict) or set(p) != required:
        raise ValueError('invalid profile keys')
    if not isinstance(p['version'], str) or not re.fullmatch(r'[A-Za-z0-9.-]+', p['version']):
        raise ValueError('invalid profile version')
    if not isinstance(p['tables'], dict) or not p['tables'] or not isinstance(p['unique_keys'], dict):
        raise ValueError('invalid profile tables or keys')
    # Compile the reviewed source DDL in memory to derive column types and indexes.
    with closing(sqlite3.connect(':memory:')) as c:
        try:
            rows = p['source_schema']
            if not isinstance(rows, list) or any(len(x) != 4 or x[0] not in ('table', 'index') for x in rows):
                raise ValueError('invalid profile source schema')
            for kind in ['table', 'index']:
                for typ, _, _, sql in rows:
                    if typ == kind:
                        c.execute(sql)
            actual = [list(x) for x in c.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name")]
            if actual != rows:
                raise ValueError('profile source schema is not canonical')
            ddl = []
            for table, columns in sorted(p['tables'].items()):
                info = {x[1]: x for x in c.execute(f'PRAGMA table_info({quote(table)})')}
                if not isinstance(columns, list) or not columns or len(set(columns)) != len(columns) or not set(columns) <= info.keys():
                    raise ValueError(f'invalid profile columns: {table}')
                for essential in ('uuid', 'printedName', 'facePrintedName'):
                    if essential in info and essential not in columns:
                        raise ValueError(f'profile must retain {table}.{essential}')
                # v1 projects unconstrained upstream tables. Reject constraints instead of losing them.
                source_sql = next(x[3] for x in rows if x[0] == 'table' and x[1] == table)
                if any(x[3] or x[4] is not None or x[5] for x in info.values()) or c.execute(
                        f'PRAGMA foreign_key_list({quote(table)})').fetchall() or re.search(
                            r'\b(CHECK|UNIQUE|REFERENCES|GENERATED)\b', source_sql, re.I):
                    raise ValueError('profile contains unsupported source constraints')
                defs = ', '.join(f'{quote(col)} {info[col][2]}' for col in columns)
                ddl.append(f'CREATE TABLE {quote(table)} ({defs})')
            for typ, name, table, sql in rows:
                if typ == 'index' and table in p['tables']:
                    cols = [x[2] for x in c.execute(f'PRAGMA index_info({quote(name)})')]
                    if all(x in p['tables'][table] for x in cols):
                        ddl.append(sql)
            for table, key in sorted(p['unique_keys'].items()):
                if table not in p['tables'] or key not in p['tables'][table]:
                    raise ValueError('invalid profile unique key')
                ddl.append(f'CREATE UNIQUE INDEX {quote("slim_unique_" + table)} ON {quote(table)} ({quote(key)})')
            if not isinstance(p['relationships'], list):
                raise ValueError('invalid profile relationships')
            for relation in p['relationships']:
                if not isinstance(relation, list) or len(relation) != 4:
                    raise ValueError('invalid profile relationship')
                child, ck, parent, pk = relation
                if child not in p['tables'] or parent not in p['tables'] or ck not in p['tables'][child] or pk not in p['tables'][parent]:
                    raise ValueError('invalid profile relationship columns')
            return ddl
        except (sqlite3.Error, TypeError, KeyError, StopIteration) as e:
            raise ValueError(f'invalid profile: {e}') from e


def output_schema(p):
    with closing(sqlite3.connect(':memory:')) as c:
        for sql in check_profile(p):
            c.execute(sql)
        return [list(x) for x in c.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name")]


def check_data(c, p):
    if [x[0] for x in c.execute('PRAGMA integrity_check')] != ['ok']:
        raise ValueError('SQLite integrity_check failed')
    if c.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('foreign key violations')
    for table, key in p['unique_keys'].items():
        q, k = quote(table), quote(key)
        if c.execute(f'SELECT 1 FROM {q} WHERE {k} IS NULL OR {k}=\'\' LIMIT 1').fetchone():
            raise ValueError(f'null/empty identity: {table}.{key}')
        if c.execute(f'SELECT 1 FROM {q} GROUP BY {k} HAVING count(*)>1 LIMIT 1').fetchone():
            raise ValueError(f'duplicate identity: {table}.{key}')
    for child, ck, parent, pk in p['relationships']:
        if c.execute(f'SELECT 1 FROM {quote(child)} c LEFT JOIN {quote(parent)} p '
                     f'ON c.{quote(ck)}=p.{quote(pk)} WHERE p.{quote(pk)} IS NULL LIMIT 1').fetchone():
            raise ValueError(f'orphan relation: {child}.{ck} -> {parent}.{pk}')
    if 'meta' not in p['tables'] or c.execute('SELECT count(*) FROM meta').fetchone()[0] != 1:
        raise ValueError('expected exactly one meta record')
    date, version = c.execute('SELECT date,version FROM meta').fetchone()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date or '') or not re.fullmatch(r'[A-Za-z0-9.+-]+', version or ''):
        raise ValueError('invalid upstream metadata')


def logical_hash(c, table, columns):
    # Full-column ordering and length-delimited JSON preserve duplicate multiplicity and NULLs.
    cols = ','.join(map(quote, columns))
    h = hashlib.sha256()
    count = 0
    for row in c.execute(f'SELECT {cols} FROM {quote(table)} ORDER BY {cols}'):
        encoded = json.dumps(list(row), ensure_ascii=False, separators=(',', ':')).encode()
        h.update(len(encoded).to_bytes(8, 'big'))
        h.update(encoded)
        count += 1
    return {'count': count, 'logical_sha256': h.hexdigest()}


def validate(path, p, source=None):
    expected = output_schema(p)
    if schema(path) != expected:
        raise ValueError('output schema differs from versioned profile')
    if source is not None and schema(source) != p['source_schema']:
        raise ValueError('source schema differs from versioned profile')
    with closing(connect(path)) as c:
        check_data(c, p)
        tables = {t: logical_hash(c, t, cols) for t, cols in sorted(p['tables'].items())}
    if source is not None:
        with closing(connect(source)) as c:
            check_data(c, p)
            for table, columns in sorted(p['tables'].items()):
                if tables[table] != logical_hash(c, table, columns):
                    raise ValueError(f'projected rows differ from source: {table}')
    return {'status': 'PASS', 'integrity_check': 'ok', 'tables': tables, 'schema': expected}


def convert(source, output, p):
    ddl = check_profile(p)
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or source == output:
        raise FileExistsError('output already exists; refusing overwrite')
    if schema(source) != p['source_schema']:
        raise ValueError('source schema differs from versioned profile')
    with closing(connect(source)) as src:
        check_data(src, p)
        try:
            with closing(sqlite3.connect(output)) as dst:
                dst.execute('PRAGMA page_size=4096')
                dst.execute('PRAGMA journal_mode=DELETE')
                dst.execute('PRAGMA temp_store=FILE')
                dst.execute('PRAGMA cache_size=-16384')
                for sql in ddl:
                    if sql.startswith('CREATE TABLE'):
                        dst.execute(sql)
                for table, columns in sorted(p['tables'].items()):
                    cols = ','.join(map(quote, columns))
                    rows = src.execute(f'SELECT {cols} FROM {quote(table)} ORDER BY {cols}')
                    placeholders = ','.join('?' for _ in columns)
                    dst.executemany(f'INSERT INTO {quote(table)} VALUES ({placeholders})', rows)
                for sql in ddl:
                    if not sql.startswith('CREATE TABLE'):
                        dst.execute(sql)
                dst.commit()
                dst.execute('VACUUM')
            return validate(output, p, source=source)
        except BaseException:
            output.unlink(missing_ok=True)
            Path(str(output) + '-journal').unlink(missing_ok=True)
            raise


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def build(archive, expected, profile_path, output_dir, tool_commit):
    started = time.monotonic()
    verify(archive, expected)  # Must precede all decompression, reuse or SQLite access.
    p = json.loads(Path(profile_path).read_text())
    check_profile(p)
    if not re.fullmatch(r'[0-9a-f]{40}', tool_commit):
        raise ValueError('tool commit must be a full 40-character Git SHA')
    profile_sha = digest(profile_path)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        m = json.loads((output_dir / 'manifest.json').read_text())
        if (m['upstream']['archive_sha256'], m['profile_sha256'], m['tool_commit']) != (expected.lower(), profile_sha, tool_commit):
            raise FileExistsError('output directory exists for different input/profile/tool')
        for field in ['sqlite', 'archive']:
            artifact = m['output'][field]
            name = artifact['name']
            if Path(name).name != name:
                raise ValueError('invalid manifest path')
            verify(output_dir / name, artifact['sha256'])
        db_path = output_dir / m['output']['sqlite']['name']
        with lzma.open(output_dir / m['output']['archive']['name'], 'rb') as f:
            if hashlib.file_digest(f, 'sha256').hexdigest() != m['output']['sqlite']['sha256']:
                raise ValueError('compressed archive differs from SQLite output')
        with tempfile.TemporaryDirectory(prefix='.slim-recheck-', dir=output_dir.parent) as tmp:
            source = Path(tmp) / 'source.sqlite'
            with lzma.open(archive, 'rb') as src, source.open('xb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            validate(db_path, p, source=source)
        return {'status': 'UNCHANGED', 'manifest': m}
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.slim-', dir=output_dir.parent) as tmp:
        work = Path(tmp)
        source = work / 'source.sqlite'
        with lzma.open(archive, 'rb') as src, source.open('xb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        source_inventory = inventory(source)
        if source_inventory['integrity_check'] != ['ok']:
            raise ValueError('source integrity_check failed')
        if source_inventory['schema'] != p['source_schema']:
            raise ValueError('source schema differs from versioned profile')
        with closing(connect(source)) as c:
            date, version = c.execute('SELECT date,version FROM meta').fetchone()
        stage = work / 'package'
        stage.mkdir()
        db = stage / f'AllPrintings-slim-{version}-profile-{p["version"]}.sqlite'
        report = convert(source, db, p)
        compressed = Path(str(db) + '.xz')
        with db.open('rb') as src, lzma.open(compressed, 'wb', preset=6) as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        output = {k: {'name': path.name, 'sha256': digest(path), 'size_bytes': path.stat().st_size}
                  for k, path in [('sqlite', db), ('archive', compressed)]}
        Path(str(compressed) + '.sha256').write_text(f'{output["archive"]["sha256"]}  {compressed.name}\n')
        manifest = {'upstream': {'url': UPSTREAM, 'checksum_url': UPSTREAM + '.sha256',
                    'version': version, 'date': date, 'archive_sha256': expected.lower(),
                    'archive_size_bytes': Path(archive).stat().st_size, 'sqlite_sha256': digest(source),
                    'sqlite_size_bytes': source.stat().st_size},
                    'profile_version': p['version'], 'profile_sha256': profile_sha,
                    'tool_commit': tool_commit, 'output': output,
                    'runtime': {'python': sys.version, 'sqlite': sqlite3.sqlite_version},
                    'distribution': 'local preparation only; redistribution rights require review'}
        write_json(stage / 'manifest.json', manifest)
        write_json(stage / 'validation.json', report)
        write_json(stage / 'source-inventory.json', source_inventory)
        os.rename(stage, output_dir)
    return {'status': 'PASS', 'manifest': manifest, 'elapsed_seconds': time.monotonic() - started,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def download(destination, previous_sha256=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(UPSTREAM + '.sha256', headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        checksum = response.read(1024).decode().strip()
    if not re.fullmatch(r'[0-9a-fA-F]{64}', checksum):
        raise ValueError('invalid official checksum response')
    if previous_sha256:
        if not re.fullmatch(r'[0-9a-fA-F]{64}', previous_sha256):
            raise ValueError('invalid previous upstream SHA-256')
        if checksum.lower() == previous_sha256.lower():
            return {'status': 'UNCHANGED', 'url': UPSTREAM, 'sha256': checksum.lower(),
                    'note': 'Official upstream digest unchanged; no dataset downloaded or validated in this check'}
    archive = destination / 'AllPrintings.sqlite.xz'
    if archive.exists():
        verify(archive, checksum)
    else:
        with tempfile.NamedTemporaryFile(dir=destination, delete=False) as f:
            partial = Path(f.name)
        try:
            with urllib.request.urlopen(urllib.request.Request(UPSTREAM, headers={'User-Agent': USER_AGENT}),
                                        timeout=120) as src, partial.open('wb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            verify(partial, checksum)
            os.rename(partial, archive)
        finally:
            partial.unlink(missing_ok=True)
    Path(str(archive) + '.sha256').write_text(checksum + '\n')
    return {'status': 'PASS', 'url': UPSTREAM, 'archive': str(archive), 'sha256': checksum}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    dl = subs.add_parser('download')
    dl.add_argument('--directory', required=True)
    dl.add_argument('--previous-sha256', help='Optional prior upstream digest: skip download if unchanged')
    inv = subs.add_parser('inventory')
    inv.add_argument('--database', required=True)
    ver = subs.add_parser('validate')
    ver.add_argument('--database', required=True)
    ver.add_argument('--source')
    ver.add_argument('--profile', required=True)
    b = subs.add_parser('build')
    for flag in ['archive', 'sha256', 'profile', 'output-dir', 'tool-commit']:
        b.add_argument('--' + flag, required=True)
    for sub in [dl, inv, ver, b]:
        sub.add_argument('--report', required=True)
    args = parser.parse_args()
    # A report is an output too: reject aliases (including symlinks) before any writes.
    report_path = Path(args.report).resolve()
    protected = [Path(getattr(args, name)).resolve() for name in
                 ['archive', 'profile', 'database', 'source'] if getattr(args, name, None)]
    output_root = Path(args.output_dir).resolve() if args.command == 'build' else None
    download_root = Path(args.directory).resolve() if args.command == 'download' else None
    aliases_input = report_path.exists() and any(
        path.exists() and os.path.samefile(report_path, path) for path in protected)
    if (report_path in protected or aliases_input or
            (output_root and report_path.is_relative_to(output_root)) or
            (download_root and report_path.is_relative_to(download_root))):
        print(json.dumps({'status': 'FAIL', 'error': 'report path overlaps protected input/output'}))
        return 1
    try:
        if args.command == 'download':
            result = download(args.directory, args.previous_sha256)
        elif args.command == 'inventory':
            result = inventory(args.database)
            result['status'] = 'PASS' if result['integrity_check'] == ['ok'] else 'FAIL'
        elif args.command == 'validate':
            result = validate(args.database, json.loads(Path(args.profile).read_text()), args.source)
        else:
            result = build(args.archive, args.sha256, args.profile, args.output_dir, args.tool_commit)
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, EOFError, lzma.LZMAError) as e:
        result = {'status': 'FAIL', 'error': str(e), 'error_type': type(e).__name__}
    write_json(args.report, result)
    print(json.dumps(result, sort_keys=True))
    return 1 if result['status'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
