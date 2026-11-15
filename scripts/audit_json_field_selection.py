"""Independently audit every field removed from the official slim JSON source.

Unlike slim_json.compare_to_source this check does not call its projection
functions: it computes actual source-to-result key/value differences directly.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import lzma
from pathlib import Path

import ijson

APPROVED_REMOVALS = {
    "sets": {"booster", "decks", "sealedProduct", "translations"},
    "cards": {"boosterTypes", "flavorText", "foreignData", "isStorySpotlight",
              "purchaseUrls", "skuIds", "sourceProducts"},
    "tokens": {"boosterTypes", "flavorText", "skuIds", "sourceProducts", "tokenProducts"},
}
CORE_CARD = {"uuid", "name", "number", "setCode", "identifiers", "legalities"}
CORE_TOKEN = {"uuid", "name", "number", "setCode", "identifiers"}
MAX_DETAIL = 20


def audit_root(path, compressed):
    """Independently reject unknown, repeated or malformed top-level JSON keys."""
    opener = lzma.open if compressed else open
    seen = set()
    pending = None
    with opener(path, "rb") as stream:
        events = iter(ijson.parse(stream, use_float=True))
        if next(events, None) != ("", "start_map", None):
            raise ValueError("Audit JSON root must be an object")
        for prefix, event, value in events:
            if prefix == "" and event == "map_key":
                if value in seen or value not in {"meta", "data"}:
                    raise ValueError("Unknown or duplicate audit JSON root field: " + value)
                seen.add(value)
                pending = value
            elif pending is not None and prefix == pending:
                if event != "start_map":
                    raise ValueError("Audit JSON root meta/data must be objects")
                pending = None
    if seen != {"meta", "data"}:
        raise ValueError("Audit JSON root must contain exactly meta and data")


def items_json_xz(archive):
    with lzma.open(archive, "rb") as stream:
        yield from ijson.kvitems(stream, "data", use_float=True)


def items_json(path):
    with Path(path).open("rb") as stream:
        yield from ijson.kvitems(stream, "data", use_float=True)


def audit(archive, slim_json, report):
    audit_root(archive, compressed=True)
    audit_root(slim_json, compressed=False)
    found = {kind: Counter() for kind in APPROVED_REMOVALS}
    retained = {kind: Counter() for kind in APPROVED_REMOVALS}
    removed = {kind: Counter() for kind in APPROVED_REMOVALS}
    failures = []
    counts = {"sets": 0, "cards": 0, "tokens": 0}

    def err(type_, key, field):
        if len(failures) < MAX_DETAIL:
            failures.append({"type": type_, "location": key, "field": field})

    def compare(before, after, category, key, mandatory=()):
        if not isinstance(before, dict) or not isinstance(after, dict):
            err("unexpected_object_type", key, category)
            return
        found[category].update(before.keys())
        retained[category].update(after.keys())
        removed_keys = set(before) - set(after)
        added_keys = set(after) - set(before)
        for field in removed_keys:
            removed[category][field] += 1
            if field not in APPROVED_REMOVALS[category]:
                err("unapproved_field_loss", key, field)
        for field in added_keys:
            err("fabricated_output_field", key, field)
        for field in set(before) & set(after):
            if before[field] != after[field]:
                err("changed_retained_value", key, field)
        for field in mandatory:
            if field not in after:
                err("lost_required_field", key, field)

    source_iterator = iter(items_json_xz(archive))
    output_iterator = iter(items_json(slim_json))
    sentinel = object()
    while True:
        orig = next(source_iterator, sentinel)
        out = next(output_iterator, sentinel)
        if orig is sentinel or out is sentinel:
            if orig is not sentinel or out is not sentinel:
                err("set_count_mismatch", "source", "data")
            break
        code, orig_set = orig
        out_code, out_set = out
        if code != out_code:
            err("set_key_order_mismatch", str(code), str(out_code))
            continue
        counts["sets"] += 1
        if not isinstance(orig_set, dict) or not isinstance(out_set, dict):
            err("bad_set", code, "set")
            continue
        core_orig = {k:v for k,v in orig_set.items() if k not in ("cards", "tokens")}
        core_out = {k:v for k,v in out_set.items() if k not in ("cards", "tokens")}
        compare(core_orig, core_out, "sets", code, {"code", "name"})
        for category in ("cards", "tokens"):
            originals = orig_set.get(category)
            outputs = out_set.get(category)
            if not isinstance(originals, list) or not isinstance(outputs, list) or len(originals) != len(outputs):
                err("changed_card_or_token_count", code, category)
                continue
            counts[category] += len(originals)
            for pos, (one, two) in enumerate(zip(originals, outputs)):
                compare(one, two, category, f"{code}/{category}/{pos}",
                        CORE_CARD if category == "cards" else CORE_TOKEN)
    report_data = {
        "status": "FAIL" if failures else "PASS",
        "counts": counts,
        "removed_field_counts": {k: dict(sorted(v.items())) for k,v in removed.items()},
        "source_field_counts": {k: dict(sorted(v.items())) for k,v in found.items()},
        "retained_field_counts": {k: dict(sorted(v.items())) for k,v in retained.items()},
        "reviewed_allowed_omissions": {k: sorted(v) for k,v in APPROVED_REMOVALS.items()},
        "details": failures
    }
    path = Path(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report_data.items() if k != "source_field_counts" and k != "retained_field_counts"}, sort_keys=True))
    return report_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--slim-json", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    result = audit(args.source, args.slim_json, args.report)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
