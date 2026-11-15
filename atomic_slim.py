#!/usr/bin/env python3
"""Build and verify a strictly source-backed AtomicCards B1 dataset.

AtomicCards is a name -> list[card] Oracle-level dataset. It is NOT a
printing-level or token database. This builder never fabricates either.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SOURCE_URL = "https://mtgjson.com/api/v5/AtomicCards.json.xz"
PROFILE = "atomic-b1"
CONTRACT = Path(__file__).with_name("contracts") / "atomic-b1.json"
MANIFEST = "atomic-manifest.json"
OMIT = frozenset(("purchaseUrls", "convertedManaCost", "faceConvertedManaCost"))
CHUNK = 1024 * 1024


def hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_stream(stream):
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(CHUNK), b""):
        h.update(chunk)
    return h.hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def load_contract():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if (contract.get("profile") != PROFILE or
            contract.get("source_url") != SOURCE_URL or
            set(contract.get("omitted_card_properties", ())) != OMIT or
            not isinstance(contract.get("expected_paths"), dict)):
        raise ValueError("Atomic B1 contract is missing or inconsistent")
    return contract


def expected_sha(path):
    line = Path(path).read_text(encoding="ascii").splitlines()[0].strip()
    match = re.match(r"^([0-9A-Fa-f]{64})(?:\s+.*)?$", line)
    if not match:
        raise ValueError("Invalid official SHA-256 sidecar")
    return match.group(1).lower()


def check_source(archive, sidecar):
    expected = expected_sha(sidecar)
    actual = hash_file(archive)
    if actual != expected:
        raise ValueError("Official AtomicCards archive SHA-256 mismatch")
    return actual


def download(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / "AtomicCards.json.xz"
    sha = folder / "AtomicCards.json.xz.sha256"
    for destination in (archive, sha):
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("Refusing to overwrite existing source: " + str(destination))
    if shutil.which("curl") is None:
        raise FileNotFoundError("AtomicCards download requires the curl executable")
    with tempfile.TemporaryDirectory(prefix=".atomic-download-", dir=folder) as temporary:
        staged_archive = Path(temporary) / archive.name
        staged_sha = Path(temporary) / sha.name
        for url, destination in ((SOURCE_URL, staged_archive), (SOURCE_URL + ".sha256", staged_sha)):
            subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                            "--retry", "3", "--connect-timeout", "30", "--max-time", "360",
                            "--proto", "=https", "--proto-redir", "=https", "--max-redirs", "5",
                            "--output", str(destination), url], check=True)
        digest = check_source(staged_archive, staged_sha)
        publications = ((staged_sha, sha), (staged_archive, archive))
        try:
            # Each hard link is atomic and refuses existing names. The archive
            # appears last; there is no atomic two-file filesystem transaction.
            for source, destination in publications:
                os.link(source, destination)
        except BaseException:
            for source, destination in reversed(publications):
                try:
                    # Compare entries without following a foreign replacement
                    # symlink; a signal may arrive just after link creation.
                    if os.path.samestat(source.lstat(), destination.lstat()):
                        destination.unlink()
                except FileNotFoundError:
                    pass
            raise
    print(json.dumps({"source_url": SOURCE_URL, "archive_sha256": digest,
                      "archive_size_bytes": archive.stat().st_size, "status": "PASS"}))


def parser_module():
    try:
        import ijson
    except ImportError as exc:
        raise RuntimeError("Install ijson==3.6.0 from requirements-json.txt") from exc
    return ijson


def check_root(path, compressed):
    """Reject unknown/duplicate root fields before projection can hide them."""
    opener = lzma.open if compressed else open
    seen = set()
    waiting = None
    with opener(path, 'rb') as stream:
        events = iter(parser_module().parse(stream, use_float=True))
        if next(events, None) != ('', 'start_map', None):
            raise ValueError('Atomic root must be an object')
        for prefix, event, value in events:
            if prefix == '' and event == 'map_key':
                if value not in {'meta', 'data'} or value in seen:
                    raise ValueError('Unexpected or duplicate Atomic root field: ' + value)
                seen.add(value)
                waiting = value
            elif waiting is not None and prefix == waiting:
                if event != 'start_map':
                    raise ValueError('Atomic root meta/data must be objects')
                waiting = None
    if seen != {'meta', 'data'}:
        raise ValueError('Atomic root must contain exactly meta and data')


def meta_from_archive(archive):
    with lzma.open(archive, "rb") as stream:
        meta = next(parser_module().items(stream, "meta", use_float=True), None)
    if not isinstance(meta, dict) or not all(isinstance(meta.get(k), str) for k in ("date", "version")):
        raise ValueError("Official AtomicCards metadata is missing")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"]):
        raise ValueError("Invalid upstream date")
    if not re.fullmatch(r"[0-9A-Za-z.+-]+", meta["version"]):
        raise ValueError("Invalid upstream version")
    return meta


def groups(archive, compressed=False):
    opener = lzma.open if compressed else open
    with opener(archive, "rb") as stream:
        yield from parser_module().kvitems(stream, "data", use_float=True)


def value_type(value):
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if isinstance(value, (int, float)) and type(value) is not bool:
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise ValueError("Unsupported JSON type: " + str(type(value)))


def walk(path, value, observed):
    kind = value_type(value)
    old = observed.get(path)
    if old is not None and old != kind:
        raise ValueError(f"Conflicting source data types for {path}: {old}, {kind}")
    observed[path] = kind
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or "." in key or "[" in key:
                raise ValueError(f"Unexpected nested field name at {path}")
            walk(path + "." + key, child, observed)
    elif isinstance(value, list):
        for child in value:
            walk(path + "[]", child, observed)


def project(record):
    if not isinstance(record, dict):
        raise ValueError("Atomic name group contains a non-object")
    for old, modern in (("convertedManaCost", "manaValue"),
                        ("faceConvertedManaCost", "faceManaValue")):
        if old in record:
            if modern not in record or type(record[old]) is not type(record[modern]) or record[old] != record[modern]:
                raise ValueError("Unsafe deprecated mana alias removal: " + old)
    return {key: value for key, value in record.items() if key not in OMIT}


def write_sidecar(path):
    path = Path(path)
    value = hash_file(path)
    (path.parent / (path.name + ".sha256")).write_text(f"{value}  {path.name}\n", encoding="ascii")
    return {"name": path.name, "sha256": value, "size_bytes": path.stat().st_size}


def build(archive, sidecar, output_dir):
    source_sha = check_source(archive, sidecar)
    check_root(archive, compressed=True)
    contract = load_contract()
    meta = meta_from_archive(archive)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"AtomicCards-slim-{meta['version']}-{PROFILE}.json"
    raw = output_dir / filename
    xz = output_dir / (filename + ".xz")
    for file in (raw, xz, output_dir / MANIFEST):
        if file.exists():
            raise FileExistsError("Refusing to overwrite " + str(file))
    paths = {}
    walk("$.meta", meta, paths)
    paths["$.data"] = "object"
    data_hash = hashlib.sha256()
    data_hash.update(b"{")
    names = 0
    records = 0
    seen_names = set()
    with raw.open("wb") as stream:
        stream.write(b'{"meta":')
        stream.write(encode(meta))
        stream.write(b',"data":{')
        for name, group in groups(archive, compressed=True):
            if not isinstance(name, str) or not isinstance(group, list) or name in seen_names:
                raise ValueError("Malformed or duplicate AtomicCards name group")
            seen_names.add(name)
            names += 1
            records += len(group)
            walk("$.data.{name}", group, paths)
            for card in group:
                if card.get("name") != name:
                    raise ValueError("Atomic group key does not match card name")
            projected = [project(card) for card in group]
            chunk = encode(name) + b":" + encode(projected)
            if names > 1:
                stream.write(b",")
                data_hash.update(b",")
            stream.write(chunk)
            data_hash.update(chunk)
        stream.write(b"}}")
    data_hash.update(b"}")
    if not names or not records:
        raise ValueError("Empty AtomicCards dataset")
    expected = contract["expected_paths"]
    if paths != expected:
        diff = {"unknown": {k: v for k, v in paths.items() if expected.get(k) != v},
                "missing": {k: v for k, v in expected.items() if paths.get(k) != v}}
        raise ValueError("AtomicCards source schema drift: " + json.dumps(diff, sort_keys=True)[:2000])
    with raw.open("rb") as src, lzma.open(xz, "wb", preset=6) as dest:
        shutil.copyfileobj(src, dest, CHUNK)
    output = {"json": write_sidecar(raw), "xz": write_sidecar(xz)}
    with lzma.open(xz, "rb") as stream:
        if digest_stream(stream) != output["json"]["sha256"]:
            raise ValueError("XZ does not decompress to raw AtomicCards bytes")
    m = {"format": "AtomicCards-slim.json", "profile": PROFILE,
         "verified": False, "independent_audit": "PENDING",
         "upstream": {"url": SOURCE_URL, "date": meta["date"], "version": meta["version"],
                      "sha256_xz": source_sha},
         "contract_sha256": hash_file(CONTRACT),
         "counts": {"names": names, "records": records},
         "data_sha256": data_hash.hexdigest(), "output": output}
    (output_dir / MANIFEST).write_text(json.dumps(m, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8")
    print(json.dumps({"status": "BUILT_PENDING_INDEPENDENT_AUDIT",
                      "counts": m["counts"], "output": output, "data_sha256": m["data_sha256"]},
                     sort_keys=True))


def verify_entry(folder, entry, extension):
    name, sha, size = entry.get("name"), entry.get("sha256"), entry.get("size_bytes")
    if (not isinstance(name, str) or Path(name).name != name or
            not name.startswith("AtomicCards-slim-") or not name.endswith(extension) or
            not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha) or
            type(size) is not int or size <= 0):
        raise ValueError("Invalid Atomic release manifest output")
    path = Path(folder) / name
    if path.stat().st_size != size or hash_file(path) != sha:
        raise ValueError("Atomic artifact differs from manifest: " + name)
    if (path.parent / (name + ".sha256")).read_text(encoding="ascii") != f"{sha}  {name}\n":
        raise ValueError("Atomic checksum sidecar mismatch: " + name)
    return path


def fingerprint(raw):
    digest = hashlib.sha256()
    digest.update(b"{")
    names = records = 0
    meta = None
    with Path(raw).open("rb") as stream:
        meta = next(parser_module().items(stream, "meta", use_float=True), None)
    for name, group in groups(raw):
        if names:
            digest.update(b",")
        digest.update(encode(name) + b":" + encode(group))
        names += 1
        records += len(group)
    digest.update(b"}")
    return meta, {"names": names, "records": records}, digest.hexdigest()


def verify_package(folder):
    folder = Path(folder)
    m = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    if (m.get("format") != "AtomicCards-slim.json" or m.get("profile") != PROFILE or
            m.get("verified") is not True or m.get("independent_audit") != "PASS" or
            m.get("contract_sha256") != hash_file(CONTRACT)):
        raise ValueError("Atomic package has not passed the independent audit")
    if m["upstream"].get("url") != SOURCE_URL or not re.fullmatch(r"[a-f0-9]{64}", m["upstream"].get("sha256_xz", "")):
        raise ValueError("Unverified Atomic source manifest")
    raw = verify_entry(folder, m["output"]["json"], ".json")
    xz = verify_entry(folder, m["output"]["xz"], ".json.xz")
    if xz.name != raw.name + ".xz":
        raise ValueError("Atomic archive name mismatch")
    with lzma.open(xz, "rb") as stream:
        if digest_stream(stream) != m["output"]["json"]["sha256"]:
            raise ValueError("Atomic XZ is not the validated JSON")
    meta, counts, content_digest = fingerprint(raw)
    if (counts != m["counts"] or content_digest != m["data_sha256"] or
            (meta["date"], meta["version"]) != (m["upstream"]["date"], m["upstream"]["version"])):
        raise ValueError("Atomic content/metadata differs from audited manifest")
    return m


def rehydrate(folder):
    folder = Path(folder)
    m = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    if m.get("verified") is not True or m.get("independent_audit") != "PASS":
        raise ValueError("Unverified Atomic candidate")
    xz = verify_entry(folder, m["output"]["xz"], ".json.xz")
    raw = folder / m["output"]["json"]["name"]
    if raw.exists():
        raise FileExistsError("Refusing to overwrite Atomic raw JSON")
    with lzma.open(xz, "rb") as src, raw.open("wb") as dest:
        shutil.copyfileobj(src, dest, CHUNK)
    verify_package(folder)
    print(json.dumps({"status": "PASS", "rehydrated": raw.name}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    dl = commands.add_parser("download")
    dl.add_argument("--directory", required=True)
    b = commands.add_parser("build")
    b.add_argument("--archive", required=True)
    b.add_argument("--checksum-path", required=True)
    b.add_argument("--output-dir", required=True)
    v = commands.add_parser("verify")
    v.add_argument("--package", required=True)
    r = commands.add_parser("rehydrate")
    r.add_argument("--package", required=True)
    args = p.parse_args()
    if args.command == "download":
        download(args.directory)
    elif args.command == "build":
        build(args.archive, args.checksum_path, args.output_dir)
    elif args.command == "verify":
        print(json.dumps({"status": "PASS", "manifest": verify_package(args.package)}, sort_keys=True))
    else:
        rehydrate(args.package)


if __name__ == "__main__":
    main()
