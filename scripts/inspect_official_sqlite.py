"""Read-only inspection of an official MTGJSON SQLite archive and schema drift.

Research tool: produces a checksum-verified official SQLite copy for same-date
JSON/SQLite comparison when the pinned slim profile rejects a changed upstream
schema. This file MUST NEVER be passed off as an approved slim SQLite Release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import sqlite3
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slim


def inspect(archive, sidecar, profile, output_dir, report):
    archive = Path(archive)
    output_dir = Path(output_dir)
    report = Path(report)
    if output_dir.exists():
        raise FileExistsError("refusing to overwrite source inspection directory")
    expected = Path(sidecar).read_text(encoding="ascii").strip().split()[0].lower()
    slim.verify(archive, expected)
    approved = json.loads(Path(profile).read_text(encoding="utf-8"))
    slim.check_profile(approved)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".upstream-sqlite-", dir=output_dir.parent) as tmp:
        dest = Path(tmp)
        path = dest / "official-AllPrintings.sqlite"
        with lzma.open(archive, "rb") as source, path.open("xb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        with sqlite3.connect(path) as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(f"official SQLite integrity check failed: {integrity}")
            current_schema = [list(x) for x in db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name")]
            date, version = db.execute("SELECT date,version FROM meta").fetchone()
            record_counts = {name: db.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                             for name in ("cards", "tokens", "sets")}
        current = {(row[0], row[1]): row[3] for row in current_schema}
        original = {(row[0], row[1]): row[3] for row in approved["source_schema"]}
        added = sorted(set(current) - set(original))
        removed = sorted(set(original) - set(current))
        altered = sorted(key for key in set(current) & set(original) if current[key] != original[key])
        changes = []
        for name in altered:
            changes.append({"kind": name[0], "name": name[1], "expected_ddl": original[name],
                            "actual_ddl": current[name]})
        result = {"status": "PASS", "mode": "official-source-inspection-only",
                  "upstream": {"date": date, "version": version, "sha256_xz": expected},
                  "source_schema_equal_to_pinned_2_3": current_schema == approved["source_schema"],
                  "added_schema_objects": [list(x) for x in added],
                  "removed_schema_objects": [list(x) for x in removed],
                  "altered_schema_objects": changes,
                  "record_counts": record_counts,
                  "integrity_check": integrity,
                  "database_size_bytes": path.stat().st_size}
        digest = slim.digest(path)
        manifest = {"comparison_target": "official-verified-upstream-sqlite-NOT-slim",
                    "upstream": {"version": version, "date": date},
                    "output": {"sqlite": {"name": path.name, "size_bytes": path.stat().st_size,
                                          "sha256": digest}}}
        (dest / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        Path(report).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        shutil.move(str(dest), str(output_dir))
    print(json.dumps(result, sort_keys=True))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True)
    p.add_argument("--checksum", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()
    inspect(args.archive, args.checksum, args.profile, args.output_dir, args.report)


if __name__ == "__main__":
    main()
