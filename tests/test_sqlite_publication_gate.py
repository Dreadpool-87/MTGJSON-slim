"""Negative and positive tests for public SQLite release gate; no network needed."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import require_published_sqlite as gate


H = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def fixture():
    name = "AllPrintings-slim-5.3.0+20261114-profile-2.3.sqlite"
    sq = {
        "profile_version": "2.3", "profile_sha256": D,
        "upstream": {
            "url": "https://mtgjson.com/api/v5/AllPrintings.sqlite.xz",
            "version": "5.3.0+20261114", "date": "2026-11-14",
            "archive_sha256": B, "sqlite_sha256": C,
            "archive_size_bytes": 125284124, "sqlite_size_bytes": 722452480
        },
        "content": {"fingerprint": H, "schema_sha256": D,
                    "tables": {"cards": {"count": 115957},
                               "tokens": {"count": 9565}, "sets": {"count": 883}}},
        "output": {
            "sqlite": {"name": name, "sha256": C, "size_bytes": 275902464},
            "archive": {"name": name + ".xz", "sha256": B, "size_bytes": 47093924}
        },
        "tool_commit": "build-a", "runtime": {"python": "3.12"}
    }
    js = {
        "verified": True, "format": "AllPrintings-slim.json",
        "upstream": {"version": "5.3.0+20261114", "date": "2026-11-14",
                     "sha256_xz": D},
        "counts": {"cards": 115957, "tokens": 9565, "sets": 883}
    }
    published = deepcopy(sq)
    published["tool_commit"] = "other-verified-build"
    published["runtime"]["python"] = "3.13"
    published_bytes = (json.dumps(published, sort_keys=True) + "\n").encode()
    base = name
    names = [base + ext for ext in ("", ".xz", ".zst", ".zip")]
    names += [n + ".sha256" for n in names]
    names += ["manifest.json", "MTGJSON_LICENSE.txt"]
    assets = [
        {"name": n, "size": 128, "digest": "sha256:" + D} for n in names
    ]
    by_name = {a["name"]: a for a in assets}
    by_name[base]["size"] = sq["output"]["sqlite"]["size_bytes"]
    by_name[base]["digest"] = "sha256:" + C
    by_name[base + ".xz"]["size"] = sq["output"]["archive"]["size_bytes"]
    by_name[base + ".xz"]["digest"] = "sha256:" + B
    by_name["manifest.json"]["size"] = len(published_bytes)
    by_name["manifest.json"]["digest"] = "sha256:" + hashlib.sha256(published_bytes).hexdigest()
    release = {
        "tag_name": gate.expected_tag(sq),
        "draft": False, "prerelease": False, "published_at": "2026-11-14T17:33:37Z",
        "assets": assets
    }
    return sq, js, release, published, published_bytes


class SqlitePublicationGateTests(unittest.TestCase):
    def test_verified_public_release_passes_with_different_tool_commit(self):
        sq, js, release, published, raw = fixture()
        result = gate.validate(sq, js, release, published, raw)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["sqlite_tag"], "slim-2026-11-14-" + H[:16])
        self.assertEqual(result["sqlite_sha256"], C)

    def test_json_newer_than_sqlite_is_blocked(self):
        sq, js, release, published, raw = fixture()
        js["upstream"]["date"] = "2026-11-15"
        with self.assertRaisesRegex(ValueError, "snapshots differ"):
            gate.validate(sq, js, release, published, raw)

    def test_unpublished_or_wrong_release_is_blocked(self):
        for field, value in (("draft", True), ("prerelease", True),
                             ("tag_name", "slim-2026-11-13-0000000000000000"),
                             ("published_at", None)):
            with self.subTest(field=field):
                sq, js, release, published, raw = fixture()
                release[field] = value
                with self.assertRaises(ValueError):
                    gate.validate(sq, js, release, published, raw)

    def test_stale_sqlite_content_is_blocked(self):
        sq, js, release, published, raw = fixture()
        published["content"]["fingerprint"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "published SQLite differs"):
            gate.validate(sq, js, release, published, raw)

    def test_source_checksum_and_profile_mismatches_are_blocked(self):
        sq, js, release, published, raw = fixture()
        published["upstream"]["archive_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "published SQLite source differs"):
            gate.validate(sq, js, release, published, raw)
        sq, js, release, published, raw = fixture()
        published["profile_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "profile checksum differs"):
            gate.validate(sq, js, release, published, raw)

    def test_missing_asset_and_bad_hash_block_release(self):
        sq, js, release, published, raw = fixture()
        release["assets"] = [a for a in release["assets"] if not a["name"].endswith(".zip.sha256")]
        with self.assertRaisesRegex(ValueError, "missing/empty"):
            gate.validate(sq, js, release, published, raw)
        sq, js, release, published, raw = fixture()
        release["assets"][0]["digest"] = "sha256:" + D
        with self.assertRaisesRegex(ValueError, "asset differs"):
            gate.validate(sq, js, release, published, raw)

    def test_modified_published_manifest_bytes_are_blocked(self):
        sq, js, release, published, raw = fixture()
        with self.assertRaisesRegex(ValueError, "manifest asset digest mismatch"):
            gate.validate(sq, js, release, published, raw + b"tampered")

    def test_card_count_mismatch_is_blocked(self):
        sq, js, release, published, raw = fixture()
        js["counts"]["cards"] += 1
        with self.assertRaisesRegex(ValueError, "record counts differ"):
            gate.validate(sq, js, release, published, raw)

    def test_reject_unknown_profile_and_invalid_digest(self):
        sq, js, release, published, raw = fixture()
        sq["profile_version"] = "2.4"
        with self.assertRaisesRegex(ValueError, "unexpected SQLite profile"):
            gate.validate(sq, js, release, published, raw)
        sq, js, release, published, raw = fixture()
        sq["content"]["fingerprint"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "invalid SHA"):
            gate.validate(sq, js, release, published, raw)

    def test_cli_reports_blocked_and_exits_nonzero(self):
        sq, js, release, published, raw = fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for filename, obj in (("sqlite.json", sq), ("json.json", js),
                                  ("release.json", release)):
                (root / filename).write_text(json.dumps(obj))
            (root / "published.json").write_bytes(raw)
            # Test with a modified public API release so the CLI cannot pass.
            release["draft"] = True
            (root / "release.json").write_text(json.dumps(release))
            import subprocess
            result = subprocess.run([
                sys.executable, str(Path(gate.__file__)),
                "--sqlite-manifest", str(root / "sqlite.json"),
                "--json-manifest", str(root / "json.json"),
                "--release-json", str(root / "release.json"),
                "--published-manifest", str(root / "published.json"),
                "--report", str(root / "report.json"),
            ], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads((root / "report.json").read_text())["status"],
                             "BLOCKED_SQLITE_RELEASE")


if __name__ == "__main__":
    unittest.main()
