"""Safe JSON release decisions: reject bad evidence, do not publish metadata-only updates."""
import copy
import importlib.util
import json
import shutil
import lzma
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import json_release_plan
import rehydrate_json
import slim_json


@unittest.skipUnless(importlib.util.find_spec("ijson") is not None, "optional ijson parser not installed")
class JsonReleasePlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        source = folder / "source.json.xz"
        check = folder / "source.json.xz.sha256"
        original = {"meta": {"date": "2026-11-14", "version": "5.3.0+20261114"},
                    "data": {"ABC": {"code": "ABC", "name": "Set", "cards": [{
                        "uuid": "card-1", "name": "Test", "setCode": "ABC", "number": "1",
                        "identifiers": {}, "legalities": {"commander": "Legal"},
                        "text": "Rules text"
                    }], "tokens": [{"uuid": "token-1", "name": "Token",
                                    "setCode": "TABC", "number": "1", "identifiers": {}}]}}}
        source.write_bytes(lzma.compress(json.dumps(original).encode("utf-8")))
        check.write_text(hashlib.sha256(source.read_bytes()).hexdigest() + "\n")
        self.output = folder / "package"
        self.manifest = slim_json.build(source, check, self.output)

    def test_manifest_fingerprint_matches_full_dataset(self):
        self.assertEqual(json_release_plan.verify_package(self.output), self.manifest)
        self.assertEqual(json_release_plan.decide(self.manifest, enabled=True)["action"], "PUBLISH")
        self.assertEqual(json_release_plan.decide(self.manifest, enabled=False)["action"], "BLOCKED")

    def test_same_cards_different_meta_skips(self):
        old = copy.deepcopy(self.manifest)
        old["upstream"]["date"] = "2026-11-13"
        old["upstream"]["version"] = "5.3.0+20261113"
        self.assertEqual(json_release_plan.decide(self.manifest, old, True)["action"], "SKIP_UNCHANGED")

    def test_updated_cards_publish(self):
        old = copy.deepcopy(self.manifest)
        old["data_sha256"] = "0" * 64
        self.assertEqual(json_release_plan.decide(self.manifest, old, True)["action"], "PUBLISH")

    def test_tampered_xz_rejected(self):
        archived = self.output / self.manifest["output"]["xz"]["name"]
        archived.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            json_release_plan.verify_package(self.output)

    def test_compressed_handoff_rehydrates_and_revalidates_exact_json(self):
        candidate = self.output.parent / "release-candidate"
        candidate.mkdir()
        names = [self.manifest["output"]["xz"]["name"],
                 self.manifest["output"]["xz"]["name"] + ".sha256",
                 "json-manifest.json"]
        for name in names:
            shutil.copyfile(self.output / name, candidate / name)
        result = rehydrate_json.prepare(candidate)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["sha256"], self.manifest["output"]["json"]["sha256"])
        self.assertEqual(json_release_plan.verify_package(candidate), self.manifest)
        with self.assertRaises(FileExistsError):
            rehydrate_json.prepare(candidate)

    def test_missing_fingerprint_fails_closed(self):
        stale = copy.deepcopy(self.manifest)
        del stale["data_sha256"]
        with self.assertRaises(ValueError):
            json_release_plan.decide(self.manifest, stale, True)


if __name__ == "__main__":
    unittest.main()
