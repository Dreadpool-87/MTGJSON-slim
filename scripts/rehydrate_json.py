"""Rehydrate and verify the small XZ-only JSON release handoff.

Avoid transferring a ~290 MB raw JSON file via GitHub Actions artifacts.
Never publish a rehydrated file that differs from source-backed manifest hashes.
"""
import argparse
import json
import lzma
from pathlib import Path
import shutil

import json_release_plan


def prepare(folder):
    folder = Path(folder)
    manifest = json_release_plan.validate_manifest(json.loads(
        (folder / "json-manifest.json").read_text(encoding="utf-8")))
    raw = folder / manifest["output"]["json"]["name"]
    archived = folder / manifest["output"]["xz"]["name"]
    item = manifest["output"]["xz"]
    if raw.exists() or (folder / (raw.name + ".sha256")).exists():
        raise FileExistsError("refusing to overwrite existing raw JSON")
    json_release_plan._assert_asset(folder, item)
    try:
        with lzma.open(archived, "rb") as source, raw.open("xb") as dest:
            shutil.copyfileobj(source, dest, length=1024 * 1024)
        expected = manifest["output"]["json"]
        (folder / (raw.name + ".sha256")).write_text(
            f'{expected["sha256"]}  {raw.name}\n', encoding="ascii")
        json_release_plan.verify_package(folder)
        return {"status": "PASS", "raw_json": raw.name, "sha256": expected["sha256"]}
    except BaseException:
        raw.unlink(missing_ok=True)
        (folder / (raw.name + ".sha256")).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.package), sort_keys=True))


if __name__ == "__main__":
    main()
