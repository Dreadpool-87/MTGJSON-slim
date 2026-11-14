"""Independent same-source-version JSON/SQLite identity and gameplay-field audit.

Requires ijson (JSON streaming dependency).  Compares direct-from-MTGJSON slim
JSON against a separately built and validated slim SQLite. It does NOT
reconstruct either format from the other. Never claims structural equality
between the two official source formats.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import ijson


CARD_FIELDS = ("name", "setCode", "number", "layout", "side", "faceName",
               "printedName", "facePrintedName", "manaCost", "manaValue",
               "type", "text", "power", "toughness", "loyalty", "defense")
TOKEN_FIELDS = ("name", "setCode", "number", "layout", "side", "faceName",
                "manaCost", "type", "text", "power", "toughness")
ID_FIELDS = ("scryfallId", "scryfallOracleId", "scryfallIllustrationId")
MAX_DETAILS = 25


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _file_from_manifest(folder, item, suffix):
    name = item.get("name")
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(suffix):
        raise ValueError("Unsafe manifest asset name")
    path = Path(folder) / name
    if path.stat().st_size != item.get("size_bytes") or checksum(path) != item.get("sha256"):
        raise ValueError("Manifest asset checksum/size mismatch: " + name)
    return path


def _scalar(value):
    # Preserve missing-vs-NULL separately. Numeric SQLite affinities and booleans
    # in MTGJSON JSON may differ without being different card properties.
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def audit(json_package, sqlite_package, report):
    json_package = Path(json_package)
    sqlite_package = Path(sqlite_package)
    jm = json.loads((json_package / "json-manifest.json").read_text())
    sm = json.loads((sqlite_package / "manifest.json").read_text())
    if jm.get("verified") is not True or jm.get("format") != "AllPrintings-slim.json":
        raise ValueError("JSON source build is not marked verified")
    version_date = (jm["upstream"]["version"], jm["upstream"]["date"])
    sqlite_date = (sm["upstream"]["version"], sm["upstream"]["date"])
    if version_date != sqlite_date:
        raise ValueError(f"Different upstream versions/dates: JSON {version_date} versus SQLite {sqlite_date}")
    raw = _file_from_manifest(json_package, jm["output"]["json"], ".json")
    sqlpath = _file_from_manifest(sqlite_package, sm["output"]["sqlite"], ".sqlite")
    result = {"status": "PASS", "upstream": {"version": version_date[0], "date": version_date[1]},
              "json_sha256": jm["output"]["json"]["sha256"],
              "sqlite_sha256": sm["output"]["sqlite"]["sha256"],
              "counts": {"cards": 0, "tokens": 0},
              "mismatches": {}, "sample_details": []}
    with sqlite3.connect(sqlpath.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("SQLite quick_check failed")
        for table in ("cards", "tokens", "cardIdentifiers", "tokenIdentifiers", "cardLegalities", "cardRulings"):
            if db.execute("SELECT COUNT(*) FROM sqlite_schema WHERE type='table' AND name=?", (table,)).fetchone()[0] != 1:
                raise ValueError("Missing slim SQLite table " + table)
        with raw.open("rb") as inp:
            meta = next(ijson.items(inp, "meta", use_float=True), None)
        if not isinstance(meta, dict) or (meta.get("version"), meta.get("date")) != version_date:
            raise ValueError("JSON payload metadata differs from manifest")
        actual = db.execute("SELECT version,date FROM meta").fetchone()
        if (actual["version"], actual["date"]) != version_date:
            raise ValueError("SQLite payload metadata differs from manifest")
        # TEMP tables ensure every printing UUID is covered without storing whole
        # collections in Python memory.
        db.execute("CREATE TEMP TABLE seen_cards (uuid TEXT PRIMARY KEY)")
        db.execute("CREATE TEMP TABLE seen_tokens (uuid TEXT PRIMARY KEY)")
        counts = Counter()

        def fail(code, identifier, field=None, json_value=None, sql_value=None):
            counts[code] += 1
            if len(result["sample_details"]) < MAX_DETAILS:
                result["sample_details"].append({
                    "code": code, "uuid": identifier, "field": field,
                    "json": str(json_value)[:140], "sqlite": str(sql_value)[:140]})

        def one(table, card):
            identifier = card.get("uuid")
            if not isinstance(identifier, str) or not identifier:
                fail("invalid_json_uuid", str(identifier))
                return
            result["counts"][table] += 1
            try:
                db.execute("INSERT INTO seen_" + table + "(uuid) VALUES (?)", (identifier,))
            except sqlite3.IntegrityError:
                fail("duplicate_json_uuid", identifier)
                return
            row = db.execute('SELECT * FROM "' + table + '" WHERE uuid=?', (identifier,)).fetchone()
            if row is None:
                fail("uuid_not_in_sqlite", identifier)
                return
            for field in CARD_FIELDS if table == "cards" else TOKEN_FIELDS:
                if field not in card or field not in row.keys():
                    continue
                a, b = _scalar(card[field]), _scalar(row[field])
                if a != b:
                    fail("field_mismatch", identifier, field, a, b)
            idtable = "cardIdentifiers" if table == "cards" else "tokenIdentifiers"
            ids = db.execute('SELECT * FROM "' + idtable + '" WHERE uuid=?', (identifier,)).fetchone()
            data_ids = card.get("identifiers", {})
            if not isinstance(data_ids, dict):
                fail("malformed_identifiers", identifier)
            elif ids is None:
                fail("missing_sqlite_identifiers", identifier)
            else:
                for field in ID_FIELDS:
                    if field in data_ids and data_ids[field] is not None and field in ids.keys():
                        if str(data_ids[field]) != str(ids[field]):
                            fail("identifier_mismatch", identifier, field, data_ids[field], ids[field])
            if table == "cards":
                legality = card.get("legalities")
                if isinstance(legality, dict):
                    record = db.execute("SELECT * FROM cardLegalities WHERE uuid=?", (identifier,)).fetchone()
                    if record is None:
                        fail("missing_sqlite_legalities", identifier)
                    else:
                        for key, value in legality.items():
                            if key in record.keys() and value is not None and str(value) != str(record[key]):
                                fail("legality_mismatch", identifier, key, value, record[key])
                rulings = card.get("rulings")
                if isinstance(rulings, list):
                    source_rulings = Counter((r.get("date"), r.get("text")) for r in rulings if isinstance(r, dict))
                    sqlite_rulings = Counter((r[0], r[1]) for r in db.execute(
                        "SELECT date,text FROM cardRulings WHERE uuid=?", (identifier,)))
                    if source_rulings != sqlite_rulings:
                        fail("rulings_mismatch", identifier, "rulings",
                             sum(source_rulings.values()), sum(sqlite_rulings.values()))

        with raw.open("rb") as stream:
            for code, set_data in ijson.kvitems(stream, "data", use_float=True):
                if not isinstance(set_data, dict):
                    fail("invalid_set", str(code))
                    continue
                for table in ("cards", "tokens"):
                    records = set_data.get(table, [])
                    if not isinstance(records, list):
                        fail("invalid_set_cards_or_tokens", str(code), table)
                        continue
                    for card in records:
                        if isinstance(card, dict):
                            one(table, card)
                        else:
                            fail("invalid_json_card", str(code), table)
        for table in ("cards", "tokens"):
            count_sql = db.execute('SELECT count(*) FROM "' + table + '"').fetchone()[0]
            count_seen = db.execute("SELECT count(*) FROM seen_" + table).fetchone()[0]
            result["counts"][table + "_sqlite"] = count_sql
            result["counts"][table + "_unique_json"] = count_seen
            if count_sql != count_seen:
                fail("sqlite_unmatched_uuid_count", table, "count", count_seen, count_sql)
    result["mismatches"] = dict(sorted(counts.items()))
    result["status"] = "PASS" if not counts else "FAIL"
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-package", required=True)
    parser.add_argument("--sqlite-package", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        result = audit(args.json_package, args.sqlite_package, args.report)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        result = {"status": "FAIL", "error": str(exc), "error_type": type(exc).__name__}
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
