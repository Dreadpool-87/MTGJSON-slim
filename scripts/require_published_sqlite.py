"""Fail-closed prerequisite: verified public SQLite release before publishing JSON.

The JSON pipeline already rebuilds and cross-audits both official MTGJSON
datasets. This gate additionally proves the corresponding *public* slim SQLite
release exists and agrees with that freshly validated SQLite build. The same
check runs before JSON release planning and again immediately before publish.

No network access inside this module: workflow passes GitHub's official release
API response and the downloaded public manifest as independently fetched files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


HASH = re.compile(r"[0-9a-f]{64}\Z")
PROFILE = "2.3"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require_hash(value, context):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError("invalid SHA-256: " + context)
    return value


def expected_tag(local):
    """The same immutable SQLite content-derived tag as scripts/release_plan.py."""
    if local.get("profile_version") != PROFILE:
        raise ValueError("unexpected SQLite profile")
    upstream = local.get("upstream", {})
    date = upstream.get("date")
    version = upstream.get("version")
    if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("invalid SQLite source date")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9.+-]+", version):
        raise ValueError("invalid SQLite source version")
    fingerprint = require_hash(local.get("content", {}).get("fingerprint"), "SQLite fingerprint")
    return "slim-" + date + "-" + fingerprint[:16]


def validate(local_sqlite, local_json, public_release, public_manifest, public_bytes):
    tag = expected_tag(local_sqlite)
    if not isinstance(local_json, dict) or local_json.get("verified") is not True:
        raise ValueError("JSON validation evidence absent")
    src = local_json.get("upstream", {})
    sqlite_src = local_sqlite["upstream"]
    if (src.get("date"), src.get("version")) != (sqlite_src["date"], sqlite_src["version"]):
        raise ValueError("official JSON and SQLite snapshots differ")
    require_hash(src.get("sha256_xz"), "JSON official source")
    require_hash(sqlite_src.get("archive_sha256"), "SQLite official archive")
    if local_sqlite.get("profile_sha256") != public_manifest.get("profile_sha256"):
        raise ValueError("published SQLite profile checksum differs")
    # A public release can have a different tool_commit/runtime from the local
    # JSON job. Never require byte-identical manifests, only identical source
    # provenance, projected contents, database bytes and profile selection.
    for field in ("profile_version", "content", "output"):
        if local_sqlite.get(field) != public_manifest.get(field):
            raise ValueError("published SQLite differs in " + field)
    for field in ("url", "version", "date", "archive_sha256", "sqlite_sha256",
                  "archive_size_bytes", "sqlite_size_bytes"):
        if sqlite_src.get(field) != public_manifest.get("upstream", {}).get(field):
            raise ValueError("published SQLite source differs: " + field)
    if expected_tag(public_manifest) != tag:
        raise ValueError("published manifest tag differs")
    if not isinstance(public_release, dict) or public_release.get("tag_name") != tag:
        raise ValueError("matching SQLite release not found")
    if public_release.get("draft") is not False or public_release.get("prerelease") is not False:
        raise ValueError("SQLite release is draft or prerelease")
    if not isinstance(public_release.get("published_at"), str) or not public_release["published_at"]:
        raise ValueError("SQLite release is not publicly published")
    assets = public_release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("missing public SQLite assets")
    by_name = {}
    for entry in assets:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or entry["name"] in by_name:
            raise ValueError("invalid or duplicate public SQLite asset")
        by_name[entry["name"]] = entry
    out = local_sqlite["output"]
    sqlite = out["sqlite"]
    archive = out["archive"]
    if archive.get("name") != sqlite.get("name", "") + ".xz":
        raise ValueError("SQLite/XZ names inconsistent")
    base = sqlite["name"]
    if Path(base).name != base or not base.endswith(".sqlite"):
        raise ValueError("unsafe SQLite filename")
    required = [base + suffix for suffix in ("", ".xz", ".zst", ".zip")]
    required += [name + ".sha256" for name in required]
    required += ["manifest.json", "MTGJSON_LICENSE.txt"]
    for name in required:
        asset = by_name.get(name)
        if asset is None or type(asset.get("size")) is not int or asset["size"] <= 0:
            raise ValueError("SQLite public release asset missing/empty: " + name)
        digest = asset.get("digest")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ValueError("SQLite asset has no SHA-256 digest: " + name)
        require_hash(digest[7:], "GitHub asset " + name)
    for record in (sqlite, archive):
        name = record["name"]
        require_hash(record.get("sha256"), "SQLite manifest asset " + name)
        if by_name[name]["size"] != record["size_bytes"] or by_name[name]["digest"] != "sha256:" + record["sha256"]:
            raise ValueError("published SQLite asset differs from validated build: " + name)
    if by_name["manifest.json"]["size"] != len(public_bytes) or \
            by_name["manifest.json"]["digest"] != "sha256:" + sha256(public_bytes):
        raise ValueError("published manifest asset digest mismatch")
    # Card identity/card count parity is independently proven by the full
    # JSON/SQLite comparison step earlier in the pipeline.
    for table, key in (("cards", "cards"), ("tokens", "tokens"), ("sets", "sets")):
        if local_sqlite["content"]["tables"][table]["count"] != local_json["counts"][key]:
            raise ValueError("JSON and SQLite record counts differ: " + table)
    return {
        "status": "PASS", "dependency": "published_verified_slim_sqlite",
        "sqlite_tag": tag, "published_at": public_release["published_at"],
        "upstream_version": sqlite_src["version"], "upstream_date": sqlite_src["date"],
        "sqlite_sha256": sqlite["sha256"], "sqlite_xz_sha256": archive["sha256"],
        "sqlite_content_fingerprint": local_sqlite["content"]["fingerprint"],
        "sqlite_source_sha256": sqlite_src["archive_sha256"],
        "json_source_sha256": src["sha256_xz"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-manifest", required=True)
    parser.add_argument("--json-manifest")
    parser.add_argument("--release-json")
    parser.add_argument("--published-manifest")
    parser.add_argument("--report")
    parser.add_argument("--print-tag", action="store_true")
    args = parser.parse_args()
    try:
        sqlite_manifest = json.loads(Path(args.sqlite_manifest).read_text(encoding="utf-8"))
        if args.print_tag:
            print(expected_tag(sqlite_manifest))
            return 0
        if not all((args.json_manifest, args.release_json, args.published_manifest, args.report)):
            parser.error("verification needs JSON manifest, public API response, public manifest and report")
        blob = Path(args.published_manifest).read_bytes()
        result = validate(sqlite_manifest,
                          json.loads(Path(args.json_manifest).read_text(encoding="utf-8")),
                          json.loads(Path(args.release_json).read_text(encoding="utf-8")),
                          json.loads(blob))
        status = 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        result = {"status": "BLOCKED_SQLITE_RELEASE", "error": str(exc), "type": type(exc).__name__}
        status = 1
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
