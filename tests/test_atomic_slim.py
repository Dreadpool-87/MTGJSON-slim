"""Isolated synthetic regressions for AtomicCards B1 and its independent auditor."""
import copy
import json
import lzma
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import atomic_slim
from scripts import audit_atomic_source as independent
from scripts import atomic_release_plan as planning
from scripts import package_atomic_formats as packaging

ROOT = Path(__file__).resolve().parents[1]


class AtomicSlimTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.output = self.root / "out"
        self.archive = self.root / "AtomicCards.json.xz"
        self.sidecar = self.root / "AtomicCards.json.xz.sha256"
        self.contract_file = self.root / "atomic-b1.json"
        self.cards = [
            {"name": "Example", "layout": "transform", "side": "a",
             "manaValue": 3, "convertedManaCost": 3,
             "faceManaValue": 2, "faceConvertedManaCost": 2,
             "colorIdentity": ["B", "W"], "text": "Oracle rules text",
             "foreignData": [{"language": "French", "name": "Exemple",
                              "skuIds": {"nonfoil": "original-id"}}],
             "relatedCards": {"tokens": ["token-id"], "spellbook": ["Other"]},
             "legalities": {"commander": "Legal"},
             "leadershipSkills": {"commander": False},
             "purchaseUrls": {"cardmarket": "https://example.com/buy"}},
            {"name": "Example", "layout": "transform", "side": "b",
             "manaValue": 3, "convertedManaCost": 3,
             "text": "Different face", "identifiers": {"scryfallOracleId": "oracle"}},
        ]
        self.original = {"meta": {"date": "2026-11-14", "version": "5.3.0+20261114"},
                         "data": {"Example": copy.deepcopy(self.cards)}}

    def prepare(self):
        raw = json.dumps(self.original, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with lzma.open(self.archive, "wb") as f:
            f.write(raw)
        self.sidecar.write_text(f"{atomic_slim.hash_file(self.archive)}  {self.archive.name}\n",
                                encoding="ascii")
        observed = {"$.data": "object"}
        atomic_slim.walk("$.meta", self.original["meta"], observed)
        atomic_slim.walk("$.data.{name}", self.original["data"]["Example"], observed)
        contract = {"profile": atomic_slim.PROFILE, "source_url": atomic_slim.SOURCE_URL,
                    "omitted_card_properties": sorted(atomic_slim.OMIT),
                    "expected_paths": observed}
        self.contract_file.write_text(json.dumps(contract), encoding="utf-8")

    def test_remove_exactly_three_properties_and_keep_nested_values(self):
        self.prepare()
        with patch.object(atomic_slim, "CONTRACT", self.contract_file):
            atomic_slim.build(self.archive, self.sidecar, self.output)
            m = json.loads((self.output / atomic_slim.MANIFEST).read_text())
            self.assertFalse(m["verified"])
            self.assertEqual(m["counts"], {"names": 1, "records": 2})
            with self.assertRaises(ValueError):
                atomic_slim.verify_package(self.output)
            raw = self.output / m["output"]["json"]["name"]
            actual = json.loads(raw.read_text(encoding="utf-8"))
            self.assertEqual(len(actual["data"]["Example"]), 2)
            self.assertEqual(actual["data"]["Example"][0]["foreignData"],
                             self.cards[0]["foreignData"])
            self.assertEqual(actual["data"]["Example"][0]["relatedCards"],
                             self.cards[0]["relatedCards"])
            self.assertEqual(actual["data"]["Example"][0]["leadershipSkills"]["commander"], False)
            for item in actual["data"]["Example"]:
                for key in atomic_slim.OMIT:
                    self.assertNotIn(key, item)
            independent.audit(self.archive, self.sidecar, raw, self.output,
                              self.root / "audit.json", mark_verified=True)
            atomic_slim.verify_package(self.output)
            raw.unlink()
            atomic_slim.rehydrate(self.output)
            self.assertEqual(json.loads(raw.read_text())["data"], actual["data"])

    def test_unsafe_alias_rejected(self):
        self.original["data"]["Example"][0]["convertedManaCost"] = 9
        self.prepare()
        with patch.object(atomic_slim, "CONTRACT", self.contract_file):
            with self.assertRaisesRegex(ValueError, "Unsafe deprecated mana alias"):
                atomic_slim.build(self.archive, self.sidecar, self.output)

    def test_source_schema_drift_rejected(self):
        self.prepare()
        self.original["data"]["Example"][0]["unknownGameplayField"] = True
        with lzma.open(self.archive, "wb") as f:
            f.write(json.dumps(self.original).encode())
        self.sidecar.write_text(f"{atomic_slim.hash_file(self.archive)}  {self.archive.name}\n")
        with patch.object(atomic_slim, "CONTRACT", self.contract_file):
            with self.assertRaisesRegex(ValueError, "source schema drift"):
                atomic_slim.build(self.archive, self.sidecar, self.output)

    def test_source_checksum_mismatch_rejected(self):
        self.prepare()
        self.sidecar.write_text("0" * 64 + "  AtomicCards.json.xz\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            atomic_slim.check_source(self.archive, self.sidecar)

    def test_independent_audit_catches_removed_rules(self):
        self.prepare()
        with patch.object(atomic_slim, "CONTRACT", self.contract_file):
            atomic_slim.build(self.archive, self.sidecar, self.output)
            m = json.loads((self.output / atomic_slim.MANIFEST).read_text())
            path = self.output / m["output"]["json"]["name"]
            output = json.loads(path.read_text())
            del output["data"]["Example"][0]["text"]
            path.write_text(json.dumps(output))
            with self.assertRaisesRegex(ValueError, "nested keys"):
                independent.audit(self.archive, self.sidecar, path, self.output,
                                  self.root / "audit.json")

    def test_independent_audit_catches_fabricated_values(self):
        with self.assertRaises(ValueError):
            independent.exact({"a": False}, {"a": 0}, "record")
        with self.assertRaises(ValueError):
            independent.exact({"a": []}, {"a": None}, "record")
        with self.assertRaises(ValueError):
            independent.exact([1, 2], [2, 1], "record")
        with self.assertRaises(ValueError):
            independent.exact({"a": 1}, {"b": 1}, "record")

    def test_missing_modern_mana_value_fails_closed(self):
        card = {"name": "X", "convertedManaCost": 3}
        with self.assertRaisesRegex(ValueError, "Unsafe deprecated"):
            atomic_slim.project(card)

    def test_release_planner_requires_independent_audit(self):
        m = {"format": "AtomicCards-slim.json", "profile": atomic_slim.PROFILE,
             "verified": False, "independent_audit": "PENDING",
             "data_sha256": "a" * 64, "contract_sha256": "b" * 64,
             "counts": {"names": 1, "records": 2},
             "upstream": {"url": atomic_slim.SOURCE_URL,
                          "date": "2026-11-14", "version": "5.3.0+20261114",
                          "sha256_xz": "c" * 64}}
        with self.assertRaises(ValueError):
            planning.decide(m, None, True)
        m["verified"] = True
        m["independent_audit"] = "PASS"
        self.assertEqual(planning.decide(m, None, True)["action"], "PUBLISH")
        self.assertEqual(planning.decide(m, m, True)["action"], "SKIP_UNCHANGED")
        self.assertEqual(planning.decide(m, None, False)["action"], "BLOCKED")

    def test_atomic_download_page_requires_checksums(self):
        site = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn('id="atomic-title"', site)
        self.assertIn("item.tag_name.startsWith('atomic-slim-')", site)
        self.assertIn("item.name.startsWith('AtomicCards-slim-')", site)
        for ext in (".json", ".json.xz", ".json.zst", ".json.zip"):
            self.assertIn('data-atomic-extension="' + ext + '"', site)
            self.assertIn('data-atomic-sha="' + ext + '"', site)
        self.assertIn("checksumLink.href = sidecar.browser_download_url", site)
        self.assertIn("link.removeAttribute('aria-disabled')", site)

    def test_atomic_workflow_is_isolated(self):
        workflow = (ROOT / ".github/workflows/atomic-weekly.yml").read_text()
        self.assertIn("atomic-slim-", workflow)
        self.assertIn("--mark-verified", workflow)
        self.assertIn("--latest=false", workflow)
        self.assertIn("scripts/audit_atomic_source.py", workflow)
        self.assertIn("atomic-manifest.json", workflow)
        self.assertIn("name: verified-atomic-release-candidate", workflow)

    @unittest.skipUnless(shutil.which("zstd"), "zstd CLI not available")
    def test_zip_zstd_roundtrips(self):
        self.prepare()
        with patch.object(atomic_slim, "CONTRACT", self.contract_file):
            atomic_slim.build(self.archive, self.sidecar, self.output)
            m = json.loads((self.output / atomic_slim.MANIFEST).read_text())
            path = self.output / m["output"]["json"]["name"]
            independent.audit(self.archive, self.sidecar, path, self.output,
                              self.root / "audit.json", mark_verified=True)
            formats = packaging.package(self.output)
            self.assertEqual(set(formats), {"zip", "zstd"})
            self.assertEqual(formats["zip"]["unpacked_sha256"], m["output"]["json"]["sha256"])


if __name__ == "__main__":
    unittest.main()
