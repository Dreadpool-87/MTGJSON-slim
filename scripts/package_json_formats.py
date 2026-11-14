"""Add verified ZIP and Zstandard downloads to a validated direct-source slim JSON package.

The authoritative JSON and XZ are built/validated by slim_json.py.  This module
only adds lossless archives from those exact JSON bytes, without changing the
source, JSON schema, or existing manifest.  Requires the system zstd executable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def stream_hash(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(chunk)
    return result.hexdigest()


def check_entry(folder, item, extension):
    if not isinstance(item, dict):
        raise ValueError("missing manifest output")
    name, digest, length = item.get("name"), item.get("sha256"), item.get("size_bytes")
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(extension):
        raise ValueError("unsafe output filename")
    if not name.startswith("AllPrintings-slim-") or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid manifest output")
    if type(length) is not int or length <= 0:
        raise ValueError("invalid manifest output size")
    path = folder / name
    if path.stat().st_size != length or file_hash(path) != digest:
        raise ValueError("output differs from manifest")
    if (folder / (name + ".sha256")).read_text(encoding="ascii") != f"{digest}  {name}\n":
        raise ValueError("checksum sidecar differs from manifest")
    return path, digest


def verify_base(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "json-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "AllPrintings-slim.json" or manifest.get("verified") is not True:
        raise ValueError("JSON build has not been verified")
    base, digest = check_entry(folder, manifest["output"]["json"], ".json")
    xz, _ = check_entry(folder, manifest["output"]["xz"], ".json.xz")
    if xz.name != base.name + ".xz":
        raise ValueError("XZ file does not match declared JSON")
    with lzma.open(xz, "rb") as stream:
        if stream_hash(stream) != digest:
            raise ValueError("XZ does not unpack to JSON bytes")
    return base, digest


def verify_extra(folder, base, digest):
    result = {}
    for kind, suffix in (("zstd", ".zst"), ("zip", ".zip")):
        path = folder / (base.name + suffix)
        if not path.is_file():
            raise FileNotFoundError(f"missing {kind} archive")
        checksum = file_hash(path)
        if (folder / (path.name + ".sha256")).read_text(encoding="ascii") != f"{checksum}  {path.name}\n":
            raise ValueError(f"{kind} checksum sidecar differs")
        if kind == "zstd":
            if not shutil.which("zstd"):
                raise RuntimeError("system zstd CLI is required")
            with subprocess.Popen(["zstd", "-d", "-q", "-c", str(path)],
                                  stdout=subprocess.PIPE) as process:
                unpacked_hash = stream_hash(process.stdout)
                if process.wait() != 0:
                    raise ValueError("Zstandard decompression failed")
        else:
            with zipfile.ZipFile(path, "r") as archive:
                if archive.namelist() != [base.name]:
                    raise ValueError("ZIP must contain exactly one JSON file")
                with archive.open(base.name) as stream:
                    unpacked_hash = stream_hash(stream)
        if unpacked_hash != digest:
            raise ValueError(f"{kind} does not unpack to JSON bytes")
        result[kind] = {"name": path.name, "sha256": checksum,
                        "size_bytes": path.stat().st_size, "unpacked_sha256": digest}
    return result


def prepare(folder):
    folder = Path(folder)
    base, digest = verify_base(folder)
    targets = [folder / (base.name + suffix) for suffix in (".zst", ".zip")]
    if any(p.exists() or Path(str(p) + ".sha256").exists() for p in targets):
        raise FileExistsError("refusing to overwrite existing JSON archives")
    if not shutil.which("zstd"):
        raise RuntimeError("system zstd CLI is required")
    with tempfile.TemporaryDirectory(prefix=".json-extra-", dir=folder) as temp:
        stage = Path(temp)
        zst, zipped = (stage / p.name for p in targets)
        subprocess.run(["zstd", "-9", "-T1", "-q", "-o", str(zst), str(base)], check=True)
        with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            entry = zipfile.ZipInfo(base.name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry._compresslevel = 6
            entry.create_system = 3
            entry.external_attr = 0o644 << 16
            with archive.open(entry, "w", force_zip64=True) as dest, base.open("rb") as source:
                shutil.copyfileobj(source, dest, length=1024 * 1024)
        for path in (zst, zipped):
            checksum = file_hash(path)
            (stage / (path.name + ".sha256")).write_text(f"{checksum}  {path.name}\n", encoding="ascii")
        result = verify_extra(stage, base, digest)
        # Recheck original input before publishing any generated assets.
        verify_base(folder)
        for path in (zst, zipped):
            path.replace(folder / path.name)
            (stage / (path.name + ".sha256")).replace(folder / (path.name + ".sha256"))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--report", help="optional evidence JSON outside the package")
    args = parser.parse_args()
    result = prepare(args.package)
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
