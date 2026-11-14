"""Fail-closed JSON release planning, independent of existing SQLite release flow."""
from __future__ import annotations
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slim_json


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_manifest(manifest):
    if manifest.get("format") != "AllPrintings-slim.json" or manifest.get("verified") is not True:
        raise ValueError("JSON manifest is not a verified deckbuilding slim package")
    if manifest.get("profile") != slim_json.PROFILE:
        raise ValueError("unexpected JSON profile")
    if not valid_hash(manifest.get("data_sha256")):
        raise ValueError("missing or invalid data-only JSON fingerprint")
    src = manifest.get("upstream", {})
    if src.get("url") != slim_json.SOURCE_URL or not valid_hash(src.get("sha256_xz")):
        raise ValueError("unverified official upstream source")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", src.get("date", "")):
        raise ValueError("invalid upstream date")
    if not re.fullmatch(r"[A-Za-z0-9.+-]+", src.get("version", "")):
        raise ValueError("invalid upstream version")
    counts = manifest.get("counts", {})
    if any(type(counts.get(k)) is not int or counts[k] <= 0 for k in ("sets", "cards", "tokens")):
        raise ValueError("invalid set/card/token counts")
    output = manifest.get("output", {})
    for key, ext in (("json", ".json"), ("xz", ".json.xz")):
        file = output.get(key, {})
        name = file.get("name")
        if (not isinstance(name, str) or Path(name).name != name or
                not name.startswith("AllPrintings-slim-") or not name.endswith(ext)
                or not valid_hash(file.get("sha256")) or
                type(file.get("size_bytes")) is not int or file["size_bytes"] <= 0):
            raise ValueError("malformed JSON asset entry")
    if output["xz"]["name"] != output["json"]["name"] + ".xz":
        raise ValueError("mismatched raw/XZ JSON asset names")
    return manifest


def _assert_asset(package, info):
    name = info["name"]
    path = package / name
    if not path.is_file() or path.stat().st_size != info["size_bytes"]:
        raise ValueError("missing or mismatched asset size " + name)
    if slim_json.file_sha256(path) != info["sha256"]:
        raise ValueError("asset hash mismatch " + name)
    if (package / (name + ".sha256")).read_text(encoding="ascii") != f'{info["sha256"]}  {name}\n':
        raise ValueError("bad asset checksum sidecar " + name)
    return path


def fingerprint_and_counts(path):
    import ijson
    digest_map = {}
    counts = {"sets": 0, "cards": 0, "tokens": 0}
    with Path(path).open("rb") as stream:
        meta = next(ijson.items(stream, "meta", use_float=True), None)
    for code, group in slim_json.output_sets(path):
        if not isinstance(group, dict) or not isinstance(group.get("cards"), list) or not isinstance(group.get("tokens"), list):
            raise ValueError("invalid card or token set in candidate JSON")
        if code in digest_map:
            raise ValueError("duplicate JSON set")
        digest_map[code] = hashlib.sha256(slim_json.canonical(group).encode("utf-8")).hexdigest()
        counts["sets"] += 1
        counts["cards"] += len(group["cards"])
        counts["tokens"] += len(group["tokens"])
    fingerprint = hashlib.sha256(slim_json.canonical(digest_map).encode("utf-8")).hexdigest()
    return meta, counts, fingerprint


def verify_package(folder):
    folder = Path(folder)
    manifest = validate_manifest(json.loads((folder / "json-manifest.json").read_text(encoding="utf-8")))
    raw = _assert_asset(folder, manifest["output"]["json"])
    archived = _assert_asset(folder, manifest["output"]["xz"])
    with lzma.open(archived, "rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != manifest["output"]["json"]["sha256"]:
        raise ValueError("XZ does not unpack to verified JSON")
    meta, counts, fingerprint = fingerprint_and_counts(raw)
    if (meta.get("version"), meta.get("date")) != (
        manifest["upstream"]["version"], manifest["upstream"]["date"]):
        raise ValueError("JSON content metadata differs from upstream")
    if counts != manifest["counts"] or fingerprint != manifest["data_sha256"]:
        raise ValueError("data-only fingerprint or counts differ from manifest")
    return manifest


def decide(current, previous=None, enabled=False):
    validate_manifest(current)
    if previous is not None:
        validate_manifest(previous)
    tag = "json-slim-" + current["upstream"]["date"] + "-" + current["data_sha256"][:16]
    if not enabled:
        action, reason = "BLOCKED", "JSON public publishing remains disabled"
    elif previous is None:
        action, reason = "PUBLISH", "First validated JSON release"
    elif current["data_sha256"] == previous["data_sha256"]:
        action, reason = "SKIP_UNCHANGED", "Only upstream metadata/packaging changed"
    else:
        action, reason = "PUBLISH", "Deckbuilding JSON content changed"
    return {"status": "PASS", "action": action, "reason": reason, "tag": tag,
            "data_sha256": current["data_sha256"], "upstream": current["upstream"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--previous")
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        manifest = verify_package(args.package)
        previous = json.loads(Path(args.previous).read_text()) if args.previous else None
        result = decide(manifest, previous, enabled=args.enabled)
    except (OSError, ValueError, KeyError, TypeError, EOFError, lzma.LZMAError) as exc:
        result = {"status": "FAIL", "error": str(exc), "error_type": type(exc).__name__}
    dest = Path(args.report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
