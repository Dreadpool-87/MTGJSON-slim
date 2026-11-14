"""Synthetic, version-pinned positive and negative JSON/SQLite comparison tests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_json_sqlite


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(importlib.util.find_spec("ijson") is not None, "optional ijson dependency not installed")
class CrossFormatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cross-format-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jp, self.sp = self.root / "json", self.root / "sqlite"
        self.jp.mkdir()
        self.sp.mkdir()
        self.version = "5.3.0+20261114"
        self.date = "2026-11-14"
        self.card = {
            "uuid": "card-1", "name": "Example", "setCode": "ABC", "number": "1",
            "layout": "normal", "side": None,
            "manaCost": "{1}{G}", "manaValue": 2, "text": "Example rules",
            "identifiers": {"scryfallId": "scryfall-1", "scryfallOracleId": "oracle-1"},
            "legalities": {"commander": "Legal"},
            "rulings": [{"date": "2026-01-01", "text": "Example ruling."}]
        }
        self.json_data = {
            "meta": {"version": self.version, "date": self.date},
            "data": {"ABC": {"code": "ABC", "name": "Set", "cards": [self.card], "tokens": []}}
        }
        self.json_file = self.jp / "AllPrintings-slim-example.json"
        self.sql_file = self.sp / "AllPrintings-slim-example.sqlite"
        self._write_json()
        with sqlite3.connect(self.sql_file) as db:
            db.executescript("""
                CREATE TABLE meta(version TEXT, date TEXT);
                CREATE TABLE cards(uuid TEXT, name TEXT, setCode TEXT, number TEXT,
                                   layout TEXT, side TEXT, manaCost TEXT, manaValue REAL, text TEXT);
                CREATE TABLE tokens(uuid TEXT, name TEXT, setCode TEXT, number TEXT, text TEXT);
                CREATE TABLE cardIdentifiers(uuid TEXT, scryfallId TEXT, scryfallOracleId TEXT);
                CREATE TABLE tokenIdentifiers(uuid TEXT, scryfallId TEXT, scryfallOracleId TEXT);
                CREATE TABLE cardLegalities(uuid TEXT, commander TEXT);
                CREATE TABLE cardRulings(uuid TEXT, date TEXT, text TEXT);
            """)
            db.execute("INSERT INTO meta VALUES (?,?)", (self.version, self.date))
            db.execute("INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?)", (
                "card-1", "Example", "ABC", "1", "normal", None, "{1}{G}", 2, "Example rules"))
            db.execute("INSERT INTO cardIdentifiers VALUES (?,?,?)", ("card-1", "scryfall-1", "oracle-1"))
            db.execute("INSERT INTO cardLegalities VALUES (?,?)", ("card-1", "Legal"))
            db.execute("INSERT INTO cardRulings VALUES (?,?,?)", ("card-1", "2026-01-01", "Example ruling."))
        self._write_manifest()

    def _write_json(self):
        self.json_file.write_text(json.dumps(self.json_data, ensure_ascii=False) + "\n", encoding="utf-8")

    def _write_manifest(self, json_date=None, sqlite_date=None):
        jd = json_date or self.date
        sd = sqlite_date or self.date
        self._write_json()
        (self.jp / "json-manifest.json").write_text(json.dumps({
            "format": "AllPrintings-slim.json", "verified": True,
            "upstream": {"version": self.version, "date": jd},
            "output": {"json": {"name": self.json_file.name,
                                "size_bytes": self.json_file.stat().st_size,
                                "sha256": sha(self.json_file)}}
        }))
        (self.sp / "manifest.json").write_text(json.dumps({
            "upstream": {"version": self.version, "date": sd},
            "output": {"sqlite": {"name": self.sql_file.name,
                                  "size_bytes": self.sql_file.stat().st_size,
                                  "sha256": sha(self.sql_file)}}
        }))

    def run_audit(self):
        return audit_json_sqlite.audit(self.jp, self.sp, self.root / "report.json")

    def test_same_date_overlapping_identity_and_fields(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["counts"]["cards"], 1)
        self.assertEqual(result["counts"]["cards_sqlite"], 1)
        self.assertEqual(result["mismatches"], {})

    def test_mismatched_date_refuses_comparison(self):
        self._write_manifest(sqlite_date="2026-11-13")
        with self.assertRaisesRegex(ValueError, "Different upstream versions/dates"):
            self.run_audit()

    def test_modified_json_card_refused(self):
        self.card["manaCost"] = "{2}{G}"
        self._write_manifest()
        result = self.run_audit()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["mismatches"]["field_mismatch"], 1)

    def test_unmatched_printing_uuid_refused(self):
        self.card["uuid"] = "no-match"
        self._write_manifest()
        result = self.run_audit()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["mismatches"]["uuid_not_in_sqlite"], 1)

    def test_corrupted_json_rejected_before_query(self):
        self.json_file.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Manifest asset checksum/size mismatch"):
            self.run_audit()

    def test_wrong_source_metadata_rejected(self):
        self.json_data["meta"]["date"] = "2026-11-13"
        self._write_manifest()
        with self.assertRaisesRegex(ValueError, "JSON payload metadata differs"):
            self.run_audit()


if __name__ == "__main__":
    unittest.main()
