#!/usr/bin/env python3
"""Independent full-source AtomicCards B1 retention audit.

This module never imports the AtomicCards builder/projection logic. Every
retained nested value is compared recursively against the verified source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
from itertools import zip_longest
from pathlib import Path
import re

APPROVED_OMISSIONS = frozenset(("purchaseUrls", "convertedManaCost", "faceConvertedManaCost"))
PROFILE = "atomic-b1"
MANIFEST = "atomic-manifest.json"
SENTINEL = object()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_digest(sidecar):
    line = Path(sidecar).read_text(encoding="ascii").splitlines()[0]
    found = re.match(r"^([a-fA-F0-9]{64})(?:\s+.*)?$", line)
    if not found:
        raise ValueError("Invalid official Atomic checksum")
    return found.group(1).lower()


def source_groups(archive):
    import ijson
    with lzma.open(archive, "rb") as stream:
        yield from ijson.kvitems(stream, "data", use_float=True)


def output_groups(path):
    import ijson
    with open(path, "rb") as stream:
        yield from ijson.kvitems(stream, "data", use_float=True)


def read_meta(path, compressed):
    import ijson
    open_file = lzma.open if compressed else open
    with open_file(path, "rb") as stream:
        return next(ijson.items(stream, "meta", use_float=True), None)


def audit_root(path, compressed):
    """Independently inspect both complete roots; never import builder checks."""
    import ijson
    opener = lzma.open if compressed else open
    names = set()
    pending = None
    with opener(path, 'rb') as stream:
        tokens = iter(ijson.parse(stream, use_float=True))
        if next(tokens, None) != ('', 'start_map', None):
            raise ValueError('Audit root is not an object')
        for prefix, event, value in tokens:
            if prefix == '' and event == 'map_key':
                if value in names or value not in ('meta', 'data'):
                    raise ValueError('Unapproved or repeated audit root key: ' + value)
                names.add(value)
                pending = value
            elif pending is not None and prefix == pending:
                if event != 'start_map':
                    raise ValueError('Audit root meta/data must be objects')
                pending = None
    if names != {'meta', 'data'}:
        raise ValueError('Audit root lacks meta or data')


def exact(expected, actual, loc):
    if type(expected) is not type(actual):
        raise ValueError(f"{loc}: changed value type")
    if isinstance(expected, dict):
        if list(expected) != list(actual):
            raise ValueError(f"{loc}: changed or missing nested keys/order")
        for key in expected:
            exact(expected[key], actual[key], loc + "." + str(key))
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            raise ValueError(f"{loc}: changed array length")
        for i, (a, b) in enumerate(zip(expected, actual)):
            exact(a, b, f"{loc}[{i}]")
    elif expected != actual:
        raise ValueError(f"{loc}: changed retained scalar")


def prove_aliases(record, loc):
    for deprecated, modern in (("convertedManaCost", "manaValue"),
                               ("faceConvertedManaCost", "faceManaValue")):
        if deprecated in record:
            if modern not in record:
                raise ValueError(f"{loc}: alias has no replacement: {deprecated}")
            exact(record[deprecated], record[modern], f"{loc}.{deprecated} equivalence")


def audit(source, sidecar, raw, package, report, mark_verified=False):
    source = Path(source)
    raw = Path(raw)
    package = Path(package)
    output_manifest = package / MANIFEST
    manifest = json.loads(output_manifest.read_text(encoding="utf-8"))
    if manifest.get("profile") != PROFILE or manifest.get("format") != "AtomicCards-slim.json":
        raise ValueError("Unexpected Atomic profile/format")
    original_source = sha(source)
    if original_source != source_digest(sidecar) or original_source != manifest["upstream"]["sha256_xz"]:
        raise ValueError("Source checksum or pinned manifest checksum mismatch")
    if manifest.get("verified") or manifest.get("independent_audit") != "PENDING":
        raise ValueError("Audit input is not a fresh, unverified package")
    audit_root(source, compressed=True)
    audit_root(raw, compressed=False)
    orig_meta = read_meta(source, compressed=True)
    slim_meta = read_meta(raw, compressed=False)
    exact(orig_meta, slim_meta, "$.meta")
    if (orig_meta["date"], orig_meta["version"]) != (
            manifest["upstream"]["date"], manifest["upstream"]["version"]):
        raise ValueError("Source/manifest versions do not match")
    counts = {"names": 0, "records": 0}
    found = set()
    for old, new in zip_longest(source_groups(source), output_groups(raw), fillvalue=SENTINEL):
        if old is SENTINEL or new is SENTINEL:
            raise ValueError("Atomic name group count differs")
        original_name, originals = old
        output_name, results = new
        if original_name != output_name or original_name in found:
            raise ValueError("Atomic name key/order mismatch")
        found.add(original_name)
        if not isinstance(originals, list) or not isinstance(results, list) or len(originals) != len(results):
            raise ValueError(f"{original_name}: changed record array")
        counts["names"] += 1
        counts["records"] += len(originals)
        for pos, (original, result) in enumerate(zip(originals, results)):
            loc = f"$.data[{original_name!r}][{pos}]"
            if not isinstance(original, dict) or not isinstance(result, dict):
                raise ValueError(f"{loc}: record not an object")
            prove_aliases(original, loc)
            # Independently fixed omission policy: NO nested omissions allowed.
            expected = {k: v for k, v in original.items() if k not in APPROVED_OMISSIONS}
            exact(expected, result, loc)
    if not counts["names"] or not counts["records"] or counts != manifest.get("counts"):
        raise ValueError("Atomic record count missing or inconsistent")
    report_data = {
        "status": "PASS", "profile": PROFILE, "counts": counts,
        "source_sha256_xz": original_source, "slim_json_sha256": sha(raw),
        "approved_card_omissions": sorted(APPROVED_OMISSIONS),
        "full_source_nested_value_comparison": True,
        "alias_equivalence_reproved": True, "preserved_name_and_record_order": True
    }
    dest = Path(report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mark_verified:
        # Only a completed independent source audit marks a package publishable.
        verified = dict(manifest)
        verified["verified"] = True
        verified["independent_audit"] = "PASS"
        temporary = output_manifest.with_suffix(".verified-tmp")
        if temporary.exists():
            raise FileExistsError("Refusing to overwrite temporary audit manifest")
        temporary.write_text(json.dumps(verified, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output_manifest)
    print(json.dumps(report_data, sort_keys=True))
    return report_data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True)
    p.add_argument("--checksum-path", required=True)
    p.add_argument("--raw", required=True)
    p.add_argument("--package", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--mark-verified", action="store_true")
    args = p.parse_args()
    audit(args.source, args.checksum_path, args.raw, args.package, args.report, args.mark_verified)


if __name__ == "__main__":
    main()
