#!/usr/bin/env python3
"""Experimental direct MTGJSON AllPrintings.json -> AllPrintings-slim.json builder.

This is deliberately independent of slim.py and its SQLite source. Only the
optional JSON route requires ijson (pip install -r requirements-json.txt).
No GitHub Release or scheduled build is changed by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request

SOURCE_URL = "https://mtgjson.com/api/v5/AllPrintings.json.xz"
PROFILE = "json-deckbuilding-1.0"
USER_AGENT = "MTGJSON-slim/1 (+https://github.com/Dreadpool-87/MTGJSON-slim)"

# Blacklist deliberately limited to reviewed non-gameplay/product data.
# All other source properties and all printing/token records are retained,
# including unrecognized properties. This prevents silent data-field loss.
SET_OMIT = frozenset(("booster", "decks", "sealedProduct", "translations"))
CARD_OMIT = frozenset((
    "boosterTypes", "flavorText", "foreignData", "isStorySpotlight",
    "purchaseUrls", "skuIds", "sourceProducts",
))
TOKEN_OMIT = frozenset((
    "boosterTypes", "flavorText", "skuIds", "sourceProducts", "tokenProducts",
))
REQUIRED_CARD = frozenset(("uuid", "name", "setCode", "number", "identifiers", "legalities"))
REQUIRED_TOKEN = frozenset(("uuid", "name", "setCode", "number", "identifiers"))
REQUIRED_SET = frozenset(("code", "name", "cards", "tokens"))


def streaming_parser():
    try:
        import ijson
    except ImportError as exc:
        raise RuntimeError(
            "JSON streaming requires ijson==3.6.0: pip install -r requirements-json.txt"
        ) from exc
    return ijson


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_digest(sidecar):
    value = Path(sidecar).read_text(encoding="ascii").strip().split()[0].lower()
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("Invalid official SHA-256 sidecar")
    return value


def verify_source(archive, sha256):
    actual = file_sha256(archive)
    if actual != sha256:
        raise ValueError("Official AllPrintings.json.xz checksum mismatch")
    return actual


def project_card(card, kind):
    if not isinstance(card, dict):
        raise ValueError(f"{kind} must be a JSON object")
    required = REQUIRED_CARD if kind == "card" else REQUIRED_TOKEN
    if not required <= set(card):
        raise ValueError(f"{kind} missing required identity/data fields: {sorted(required - set(card))}")
    for name in ("uuid", "name", "setCode", "number"):
        if not isinstance(card[name], str) or not card[name]:
            raise ValueError(f"{kind} invalid {name}")
    if not isinstance(card["identifiers"], dict):
        raise ValueError(f"{kind} identifiers must be an object")
    if kind == "card" and not isinstance(card["legalities"], dict):
        raise ValueError("card legalities must be an object")
    omitted = CARD_OMIT if kind == "card" else TOKEN_OMIT
    return {k: v for k, v in card.items() if k not in omitted}


def project_set(code, source):
    if not isinstance(code, str) or not code or not isinstance(source, dict):
        raise ValueError("Invalid set object or code")
    if not REQUIRED_SET <= set(source):
        raise ValueError(f"Set {code} missing required fields")
    if source["code"] != code or not isinstance(source["cards"], list) or not isinstance(source["tokens"], list):
        raise ValueError(f"Set {code} code/card/token structure mismatch")
    result = {k: v for k, v in source.items() if k not in SET_OMIT | {"cards", "tokens"}}
    result["cards"] = [project_card(card, "card") for card in source["cards"]]
    result["tokens"] = [project_card(token, "token") for token in source["tokens"]]
    return result


def check_root(archive):
    """Fail closed on unfamiliar or duplicate top-level source fields (streaming)."""
    seen = set()
    pending = None
    with lzma.open(archive, "rb") as stream:
        events = iter(streaming_parser().parse(stream, use_float=True))
        if next(events, None) != ("", "start_map", None):
            raise ValueError("JSON root must be an object")
        for prefix, event, value in events:
            if prefix == "" and event == "map_key":
                if value not in {"meta", "data"} or value in seen:
                    raise ValueError("Unknown or duplicate JSON root field: " + value)
                seen.add(value)
                pending = value
            elif pending is not None and prefix == pending:
                if event != "start_map":
                    raise ValueError("JSON root meta/data must be objects")
                pending = None
    if seen != {"meta", "data"}:
        raise ValueError("JSON root must contain exactly meta and data")


def read_meta(archive):
    ijson = streaming_parser()
    with lzma.open(archive, "rb") as stream:
        meta = next(ijson.items(stream, "meta", use_float=True), None)
    if not isinstance(meta, dict) or not isinstance(meta.get("date"), str) or not isinstance(meta.get("version"), str):
        raise ValueError("Missing or malformed official JSON meta")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"]):
        raise ValueError("Invalid official source date")
    if not re.fullmatch(r"[A-Za-z0-9.+-]+", meta["version"]):
        raise ValueError("Invalid official source version")
    return meta


def source_sets(archive):
    ijson = streaming_parser()
    with lzma.open(archive, "rb") as stream:
        yield from ijson.kvitems(stream, "data", use_float=True)


def output_sets(path):
    ijson = streaming_parser()
    with Path(path).open("rb") as stream:
        yield from ijson.kvitems(stream, "data", use_float=True)


def make_json(archive, output):
    meta = read_meta(archive)
    counts = {"sets": 0, "cards": 0, "tokens": 0}
    set_digests = {}
    # Streaming by whole set: no full 650+ MiB source JSON is loaded into RAM.
    with Path(output).open("w", encoding="utf-8", newline="\n") as dest:
        dest.write('{"meta":')
        dest.write(canonical(meta))
        dest.write(',"data":{')
        first = True
        for code, source in source_sets(archive):
            slim = project_set(code, source)
            if not first:
                dest.write(",")
            dest.write(canonical(code))
            dest.write(":")
            normalized_set = canonical(slim)
            dest.write(normalized_set)
            set_digests[code] = hashlib.sha256(normalized_set.encode("utf-8")).hexdigest()
            first = False
            counts["sets"] += 1
            counts["cards"] += len(slim["cards"])
            counts["tokens"] += len(slim["tokens"])
        dest.write("}}\n")
    if not counts["sets"] or not counts["cards"]:
        raise ValueError("No card sets found in official JSON source")
    # Content identity excludes the upstream meta/date/version so a metadata-only
    # daily MTGJSON rebuild cannot create duplicate public releases.
    content_digest = hashlib.sha256(canonical(set_digests).encode("utf-8")).hexdigest()
    return meta, counts, content_digest


def compare_to_source(archive, output, meta, counts):
    """Independent read-back: every retained source value and row must match."""
    parsed = streaming_parser()
    with Path(output).open("rb") as stream:
        observed_meta = next(parsed.items(stream, "meta", use_float=True), None)
    if observed_meta != meta:
        raise ValueError("Output meta differs from verified source")
    actual = {"sets": 0, "cards": 0, "tokens": 0}
    source_iter = iter(source_sets(archive))
    output_iter = iter(output_sets(output))
    sentinel = object()
    while True:
        a = next(source_iter, sentinel)
        b = next(output_iter, sentinel)
        if a is sentinel and b is sentinel:
            break
        if a is sentinel or b is sentinel:
            raise ValueError("Missing or extra output set")
        code, source = a
        out_code, actual_set = b
        if code != out_code or project_set(code, source) != actual_set:
            raise ValueError(f"Lossy or altered JSON content in set {code}")
        actual["sets"] += 1
        actual["cards"] += len(actual_set["cards"])
        actual["tokens"] += len(actual_set["tokens"])
    if actual != counts:
        raise ValueError("JSON card/token/set record counts differ")
    return actual


def build(archive, checksum_path, output_dir):
    archive = Path(archive)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite output directory")
    official_hash = expected_digest(checksum_path)
    verify_source(archive, official_hash)
    check_root(archive)
    meta = read_meta(archive)
    filename = f'AllPrintings-slim-{meta["version"]}-{PROFILE}.json'
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".json-slim-", dir=output_dir.parent) as tmp:
        temp = Path(tmp)
        result = temp / filename
        meta_again, counts, content_digest = make_json(archive, result)
        if meta_again != meta:
            raise ValueError("Official source metadata changed during build")
        compare_to_source(archive, result, meta, counts)
        compressed = temp / (filename + ".xz")
        with result.open("rb") as reader, lzma.open(compressed, "wb", preset=6) as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
        raw_hash = file_sha256(result)
        with lzma.open(compressed, "rb") as unpacked:
            digest = hashlib.sha256()
            for block in iter(lambda: unpacked.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != raw_hash:
            raise ValueError("JSON XZ roundtrip mismatch")
        assets = {}
        for key, path in (("json", result), ("xz", compressed)):
            digest = file_sha256(path)
            (temp / (path.name + ".sha256")).write_text(f"{digest}  {path.name}\n", encoding="ascii")
            assets[key] = {"name": path.name, "sha256": digest, "size_bytes": path.stat().st_size}
        manifest = {
            "format": "AllPrintings-slim.json",
            "profile": PROFILE,
            "upstream": {"url": SOURCE_URL, "sha256_xz": official_hash, **meta},
            "counts": counts,
            "data_sha256": content_digest,
            "output": assets,
            "verified": True,
            "note": "Independent JSON source; SQLite/JSON need not have identical schemas.",
        }
        (temp / "json-manifest.json").write_text(canonical(manifest) + "\n", encoding="utf-8")
        # Atomic on the same filesystem; never expose unverified artifacts.
        shutil.move(str(temp), str(output_dir))
        return manifest


def download(target):
    """Fetch official JSON XZ + upstream SHA256, preserving an existing download."""
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    archive = target / "AllPrintings.json.xz"
    sidecar = target / "AllPrintings.json.xz.sha256"
    if archive.exists() or sidecar.exists():
        raise FileExistsError("Official JSON source exists; use a clean download directory")
    request = lambda url: urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request(SOURCE_URL + ".sha256"), timeout=60) as response:
        sha = response.read(256).decode("ascii").strip().split()[0]
    if not re.fullmatch(r"[a-fA-F0-9]{64}", sha):
        raise ValueError("Invalid official source checksum")
    with tempfile.TemporaryDirectory(dir=target, prefix=".download-") as tmp:
        candidate = Path(tmp) / archive.name
        with urllib.request.urlopen(request(SOURCE_URL), timeout=120) as response, candidate.open("wb") as dst:
            shutil.copyfileobj(response, dst, length=1024 * 1024)
        verify_source(candidate, sha.lower())
        candidate.replace(archive)
        sidecar.write_text(sha.lower() + "\n", encoding="ascii")
    return {"archive": str(archive), "sha256": sha.lower()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("download")
    p.add_argument("--directory", required=True)
    b = sub.add_parser("build")
    b.add_argument("--archive", required=True)
    b.add_argument("--checksum-path", required=True)
    b.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        result = download(args.directory) if args.command == "download" else build(
            args.archive, args.checksum_path, args.output_dir
        )
        print(canonical({"status": "PASS", **result}))
        return 0
    except (OSError, ValueError, RuntimeError, lzma.LZMAError, EOFError) as exc:
        print(canonical({"status": "FAIL", "error": str(exc), "type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
