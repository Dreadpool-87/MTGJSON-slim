#!/usr/bin/env python3
"""Fail-closed release decision for the independent AtomicCards B1 series."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atomic_slim


def valid_sha(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def check_manifest(m):
    if (m.get("format") != "AtomicCards-slim.json" or
            m.get("profile") != atomic_slim.PROFILE or
            m.get("verified") is not True or m.get("independent_audit") != "PASS"):
        raise ValueError("Atomic manifest not independently verified for profile B1")
    if not valid_sha(m.get("contract_sha256")) or not valid_sha(m.get("data_sha256")):
        raise ValueError("Missing Atomic schema or content fingerprint")
    src = m.get("upstream", {})
    if (src.get("url") != atomic_slim.SOURCE_URL or not valid_sha(src.get("sha256_xz")) or
            not isinstance(src.get("date"), str) or
            not re.fullmatch(r"\d{4}-\d{2}-\d{2}", src["date"]) or
            not isinstance(src.get("version"), str)):
        raise ValueError("Atomic source provenance invalid")
    counts = m.get("counts", {})
    if any(type(counts.get(k)) is not int or counts[k] <= 0 for k in ("names", "records")):
        raise ValueError("Atomic manifest counts invalid")
    return m


def decide(current, previous, enabled):
    check_manifest(current)
    if previous is not None:
        check_manifest(previous)
    tag = f"atomic-slim-{current['upstream']['date']}-{current['data_sha256'][:16]}"
    if not enabled:
        action, reason = "BLOCKED", "Publishing disabled"
    elif previous is None:
        action, reason = "PUBLISH", "First independently verified Atomic release"
    elif (previous["data_sha256"] == current["data_sha256"] and
          previous["contract_sha256"] == current["contract_sha256"]):
        action, reason = "SKIP_UNCHANGED", "Atomic content and profile unchanged"
    else:
        action, reason = "PUBLISH", "New audited Atomic content or profile"
    return {"status": "PASS", "action": action, "reason": reason, "tag": tag,
            "data_sha256": current["data_sha256"], "profile": atomic_slim.PROFILE}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", required=True)
    p.add_argument("--previous")
    p.add_argument("--enabled", action="store_true")
    p.add_argument("--report", required=True)
    a = p.parse_args()
    try:
        current = atomic_slim.verify_package(a.package)
        previous = json.loads(Path(a.previous).read_text(encoding="utf-8")) if a.previous else None
        result = decide(current, previous, a.enabled)
    except (OSError, KeyError, ValueError, TypeError, EOFError) as exc:
        result = {"status": "FAIL", "error": str(exc), "error_type": type(exc).__name__}
    out = Path(a.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
