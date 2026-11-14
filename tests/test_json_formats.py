"""Regression checks for JSON -> XZ/ZIP/Zstandard lossless packaging."""
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_json_formats


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class JsonFormatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="json-format-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.filename = "AllPrintings-slim-example-json-deckbuilding-1.0.json"
        self.path = self.root / self.filename
        data = {"meta": {"version": "test"}, "data": {"M19": {"cards": [
            {"name": "Sample", "identifiers": {"scryfallOracleId": "abc"},
             "otherFaceIds": ["other"], "rulings": [], "legalities": {"commander": "Legal"}}
        ], "tokens": []}}}
        self.path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
        xz = self.root / (self.filename + ".xz")
        xz.write_bytes(lzma.compress(self.path.read_bytes(), preset=6))
        entries = {}
        for key, file in (("json", self.path), ("xz", xz)):
            sha = digest(file)
            entries[key] = {"name": file.name, "size_bytes": file.stat().st_size,
                            "sha256": sha}
            (self.root / (file.name + ".sha256")).write_text(f"{sha}  {file.name}\n")
        (self.root / "json-manifest.json").write_text(json.dumps({
            "format": "AllPrintings-slim.json", "verified": True, "output": entries
        }))

    @unittest.skipUnless(shutil.which("zstd"), "zstd CLI is required")
    def test_archive_generation_roundtrip_and_sidecars(self):
        data = package_json_formats.prepare(self.root)
        self.assertEqual(set(data), {"zip", "zstd"})
        for record in data.values():
            self.assertEqual(record["unpacked_sha256"], digest(self.path))
            self.assertEqual(digest(self.root / record["name"]), record["sha256"])
        with zipfile.ZipFile(self.root / (self.filename + ".zip")) as archive:
            self.assertEqual(archive.namelist(), [self.filename])
        self.assertEqual(package_json_formats.verify_extra(self.root, self.path,
                                                           digest(self.path)), data)
        with self.assertRaises(FileExistsError):
            package_json_formats.prepare(self.root)

    def test_corrupted_json_and_xz_fail_closed(self):
        self.path.write_text("tamper")
        with self.assertRaisesRegex(ValueError, "differs from manifest"):
            package_json_formats.verify_base(self.root)
        self.assertFalse((self.root / (self.filename + ".zip")).exists())

    def test_wrong_xz_content_is_not_trusted(self):
        xz = self.root / (self.filename + ".xz")
        xz.write_bytes(lzma.compress(b'{"data":{}}'))
        manifest_path = self.root / "json-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["output"]["xz"].update(size_bytes=xz.stat().st_size, sha256=digest(xz))
        manifest_path.write_text(json.dumps(manifest))
        (self.root / (xz.name + ".sha256")).write_text(f"{digest(xz)}  {xz.name}\n")
        with self.assertRaisesRegex(ValueError, "unpack to JSON"):
            package_json_formats.verify_base(self.root)

    def test_filename_traversal_rejected(self):
        manifest_path = self.root / "json-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["output"]["json"]["name"] = "../bad.json"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "unsafe output"):
            package_json_formats.verify_base(self.root)


if __name__ == "__main__":
    unittest.main()
