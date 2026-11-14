#!/usr/bin/env python3
"""Add verified Zstandard and ZIP downloads to an independently audited Atomic package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atomic_slim


def stream_digest(stream):
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(chunk)
    return h.hexdigest()


def audit_archive(path, base, raw_sha, kind):
    sidecar = path.parent / (path.name + ".sha256")
    checksum = atomic_slim.hash_file(path)
    if sidecar.read_text(encoding="ascii") != f"{checksum}  {path.name}\n":
        raise ValueError("Invalid atomic archive checksum sidecar")
    if kind == "zstd":
        with subprocess.Popen(["zstd", "-d", "-q", "-c", str(path)],
                              stdout=subprocess.PIPE) as proc:
            digest = stream_digest(proc.stdout)
            if proc.wait():
                raise ValueError("Zstd extraction returned nonzero")
    else:
        with zipfile.ZipFile(path) as z:
            if z.namelist() != [base.name]:
                raise ValueError("Atomic ZIP must contain exactly one named JSON file")
            with z.open(base.name) as src:
                digest = stream_digest(src)
    if digest != raw_sha:
        raise ValueError(f"{kind} decompression does not reproduce original JSON")
    return {"name": path.name, "size_bytes": path.stat().st_size,
            "sha256": checksum, "unpacked_sha256": raw_sha}


def package(folder):
    folder = Path(folder)
    manifest = atomic_slim.verify_package(folder)
    base = folder / manifest["output"]["json"]["name"]
    raw_sha = manifest["output"]["json"]["sha256"]
    paths = {kind: folder / (base.name + suffix)
             for kind, suffix in (("zstd", ".zst"), ("zip", ".zip"))}
    if not shutil.which("zstd"):
        raise RuntimeError("The zstd CLI is required for Atomic publication")
    for path in paths.values():
        if path.exists() or (path.parent / (path.name + ".sha256")).exists():
            raise FileExistsError("Refusing to overwrite existing Atomic archive")
    with tempfile.TemporaryDirectory(prefix=".atomic-formats-", dir=folder) as temp:
        stage = Path(temp)
        for kind, path in paths.items():
            out = stage / path.name
            if kind == "zstd":
                subprocess.run(["zstd", "-9", "-T1", "-q", "-o", str(out), str(base)], check=True)
            else:
                with zipfile.ZipFile(out, "w", allowZip64=True) as z:
                    member = zipfile.ZipInfo(base.name, (1980, 1, 1, 0, 0, 0))
                    member.compress_type = zipfile.ZIP_DEFLATED
                    member._compresslevel = 6
                    member.create_system = 3
                    member.external_attr = 0o644 << 16
                    with z.open(member, "w", force_zip64=True) as dst, base.open("rb") as src:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)
            checksum = atomic_slim.hash_file(out)
            (stage / (out.name + ".sha256")).write_text(f"{checksum}  {out.name}\n", encoding="ascii")
        output = {}
        for kind, path in paths.items():
            output[kind] = audit_archive(stage / path.name, base, raw_sha, kind)
        # Verify the original raw JSON, manifest and XZ after compression, too.
        atomic_slim.verify_package(folder)
        for path in paths.values():
            (stage / path.name).replace(path)
            (stage / (path.name + ".sha256")).replace(folder / (path.name + ".sha256"))
        for kind, path in paths.items():
            audit_archive(path, base, raw_sha, kind)
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()
    output = package(args.package)
    destination = Path(args.report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "archives": output}, sort_keys=True))


if __name__ == "__main__":
    main()
