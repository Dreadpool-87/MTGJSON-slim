"""Create verified ZIP and Zstandard downloads from a validated SQLite package.

Only run after the main SQLite/XZ package has passed its own checks. This script
uses Python 3.14's native Zstandard support, or the CLI on older runtimes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import zstd_support


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def contents_sha256(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def zstd_content_sha256(path):
    return zstd_support.decompressed_sha256(path)


def prepare(package):
    package = Path(package)
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    item = manifest['output']['sqlite']
    name, expected_sha, expected_size = item['name'], item['sha256'], item['size_bytes']
    if Path(name).name != name or not name.endswith('.sqlite'):
        raise ValueError('manifest does not name a safe .sqlite file')
    if not re.fullmatch(r'[a-f0-9]{64}', expected_sha):
        raise ValueError('invalid manifest SHA-256')
    db_path = package / name
    if db_path.stat().st_size != expected_size or sha256(db_path) != expected_sha:
        raise ValueError('SQLite differs from manifest checksum or size')
    if (package / (name + '.sha256')).read_text(encoding='utf-8') != f'{expected_sha}  {name}\n':
        raise ValueError('SQLite checksum sidecar differs from manifest')
    with sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity_check failed')

    zst = package / (name + '.zst')
    zip_path = package / (name + '.zip')
    targets = [zst, zip_path]
    if any(p.exists() or Path(str(p) + '.sha256').exists() for p in targets):
        raise FileExistsError('refusing to overwrite an existing compressed asset')
    if not zstd_support.available():
        raise RuntimeError('Python native Zstandard support or the system zstd CLI is required')

    try:
        # Single-thread, fixed level for repeatable output in a given runtime.
        zstd_support.compress_file(db_path, zst)
        if zstd_content_sha256(zst) != expected_sha:
            raise ValueError('Zstandard output differs from SQLite')

        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry._compresslevel = 6
            entry.create_system = 3
            entry.external_attr = 0o644 << 16
            with archive.open(entry, 'w', force_zip64=True) as target, db_path.open('rb') as source:
                shutil.copyfileobj(source, target, 1024 * 1024)
        with zipfile.ZipFile(zip_path) as archive:
            if archive.namelist() != [name]:
                raise ValueError('ZIP must contain only the expected SQLite file')
            with archive.open(name) as stream:
                if contents_sha256(stream) != expected_sha:
                    raise ValueError('ZIP output differs from SQLite')

        artifacts = {}
        for kind, path in [('zstd', zst), ('zip', zip_path)]:
            digest = sha256(path)
            Path(str(path) + '.sha256').write_text(f'{digest}  {path.name}\n', encoding='utf-8')
            artifacts[kind] = {'name': path.name, 'sha256': digest,
                               'size_bytes': path.stat().st_size,
                               'unpacked_sha256': expected_sha}
        # Recheck the source, in case it changed during compression.
        if sha256(db_path) != expected_sha:
            raise ValueError('SQLite source changed during packaging')
        return artifacts
    except BaseException:
        for path in targets:
            path.unlink(missing_ok=True)
            Path(str(path) + '.sha256').unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, help='directory with manifest and SQLite')
    parser.add_argument('--report', help='optional JSON output path outside release assets')
    args = parser.parse_args()
    result = prepare(args.package)
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
