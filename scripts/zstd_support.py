"""Streaming Zstandard: Python 3.14 stdlib preferred, CLI for older runtimes."""
import hashlib
from pathlib import Path
import shutil
import subprocess

try:
    from compression import zstd as NATIVE
except ImportError:
    NATIVE = None


def available():
    return NATIVE is not None or shutil.which('zstd') is not None


def _cli():
    executable = shutil.which('zstd')
    if executable is None:
        raise RuntimeError('Python 3.14 compression.zstd or the system zstd CLI is required')
    return executable


def compress_file(source, target):
    """Create a new level-9 archive, never replacing an existing file."""
    source, target = Path(source), Path(target)
    if target.exists():
        raise FileExistsError('Refusing to overwrite Zstandard output: ' + str(target))
    if NATIVE is not None:
        options = {NATIVE.CompressionParameter.compression_level: 9,
                   NATIVE.CompressionParameter.checksum_flag: 1,
                   NATIVE.CompressionParameter.nb_workers: 0}
        with source.open('rb') as src, NATIVE.open(target, 'xb', options=options) as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
    else:
        subprocess.run([_cli(), '-9', '-T1', '-q', '-o', str(target), str(source)], check=True)


def decompressed_sha256(path):
    """Read all frames and reject corrupt/truncated streams before trusting a digest."""
    digest = hashlib.sha256()
    if NATIVE is not None:
        try:
            with NATIVE.open(path, 'rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
        except (NATIVE.ZstdError, EOFError) as exc:
            raise ValueError('Zstandard decompression failed') from exc
    else:
        with subprocess.Popen([_cli(), '-d', '-q', '-c', str(path)],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
            for block in iter(lambda: process.stdout.read(1024 * 1024), b''):
                digest.update(block)
            if process.wait() != 0:
                raise ValueError('Zstandard decompression failed')
    return digest.hexdigest()
