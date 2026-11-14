"""Fail-closed release planning for validated MTGJSON-slim packages (stdlib only)."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slim


def _validated_content(manifest):
    content = manifest.get('content')
    if not isinstance(content, dict) or set(content) != {'fingerprint', 'schema_sha256', 'tables'}:
        raise ValueError('missing or invalid release content fingerprint')
    if not re.fullmatch(r'[0-9a-f]{64}', content['fingerprint']) or not re.fullmatch(
            r'[0-9a-f]{64}', content['schema_sha256']):
        raise ValueError('invalid release fingerprint')
    tables = content['tables']
    if not isinstance(tables, dict) or not tables or 'meta' in tables:
        raise ValueError('invalid release content tables')
    for item in tables.values():
        if not isinstance(item, dict) or not isinstance(item.get('count'), int) or item['count'] < 0 \
                or not re.fullmatch(r'[0-9a-f]{64}', item.get('logical_sha256', '')):
            raise ValueError('invalid release table digest')
    canonical = {'schema_sha256': content['schema_sha256'], 'tables': tables}
    if hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != content['fingerprint']:
        raise ValueError('release fingerprint does not match table digests')
    return content


def verify_package(folder):
    """Verify local manifest, individual files, XZ round-trip and SQLite integrity."""
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    validation = json.loads((folder / 'validation.json').read_text())
    if validation.get('status') != 'PASS' or validation.get('integrity_check') != 'ok':
        raise ValueError('dataset validation did not pass')
    content = _validated_content(manifest)
    if content != slim.release_content(validation):
        raise ValueError('manifest fingerprint differs from validated table contents')
    files = {}
    for key in ('sqlite', 'archive'):
        entry = manifest['output'][key]
        name, sha, size = entry['name'], entry['sha256'], entry['size_bytes']
        if Path(name).name != name or not re.fullmatch(r'[0-9a-f]{64}', sha) or \
                not isinstance(size, int) or size <= 0:
            raise ValueError('invalid release asset entry')
        path = folder / name
        slim.verify(path, sha)
        if path.stat().st_size != size:
            raise ValueError('asset size differs from manifest')
        sidecar = folder / (name + '.sha256')
        if sidecar.read_text() != f'{sha}  {name}\n':
            raise ValueError('invalid release checksum sidecar')
        files[key] = path
    if not files['sqlite'].name.endswith('.sqlite') or files['archive'].name != files['sqlite'].name + '.xz':
        raise ValueError('compressed asset is not derived from the declared SQLite')
    with lzma.open(files['archive'], 'rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != manifest['output']['sqlite']['sha256']:
            raise ValueError('XZ does not decompress to the exact released SQLite')
    with sqlite3.connect(files['sqlite'].resolve().as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('released SQLite integrity check failed')
    version = manifest['upstream']['version']
    date = manifest['upstream']['date']
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) or \
            not re.fullmatch(r'[A-Za-z0-9.+-]+', version):
        raise ValueError('invalid upstream version or date')
    return manifest


def decide(current, previous=None, enabled=False):
    new = _validated_content(current)
    tag = 'slim-' + current['upstream']['date'] + '-' + new['fingerprint'][:16]
    if not enabled:
        action, reason = 'BLOCKED', 'Public release publishing is disabled in this workflow'
        changes = []
    elif previous is None:
        action, reason, changes = 'PUBLISH', 'First validated public release', ['initial']
    else:
        old = _validated_content(previous)
        changes = sorted(set(new['tables']) ^ set(old['tables']))
        changes += [name for name in sorted(set(new['tables']) & set(old['tables']))
                    if new['tables'][name] != old['tables'][name]]
        if new['schema_sha256'] != old['schema_sha256']:
            changes.append('schema_and_indexes')
        if new['fingerprint'] == old['fingerprint']:
            action, reason = 'SKIP_UNCHANGED', 'Only upstream metadata or packaging changed'
        else:
            action, reason = 'PUBLISH', 'Validated data or SQL schema/indexes changed'
    return {'status': 'PASS', 'action': action, 'reason': reason, 'tag': tag,
            'content_fingerprint': new['fingerprint'], 'changed_areas': changes,
            'upstream_version': current['upstream']['version'],
            'sqlite_sha256': current['output']['sqlite']['sha256'],
            'xz_sha256': current['output']['archive']['sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True)
    parser.add_argument('--previous')
    parser.add_argument('--disabled', action='store_true')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    try:
        current = verify_package(args.package)
        previous = json.loads(Path(args.previous).read_text()) if args.previous else None
        result = decide(current, previous, enabled=not args.disabled)
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, lzma.LZMAError) as error:
        result = {'status': 'FAIL', 'error': str(error), 'error_type': type(error).__name__}
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
