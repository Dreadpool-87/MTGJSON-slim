"""Independent field-selection audit tests; optional ijson only."""
import importlib.util
import json
import lzma
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@unittest.skipUnless(importlib.util.find_spec("ijson") is not None, "optional ijson parser not installed")
class FieldSelectionTests(unittest.TestCase):
    def setUp(self):
        import audit_json_field_selection
        self.audit = audit_json_field_selection
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.src, self.dst, self.report = root / "src.json.xz", root / "slim.json", root / "report.json"
        self.card = {"uuid": "c-1", "name": "Example", "setCode": "ABC", "number": "1",
                     "text": "Rules matter", "manaCost": "{R}", "identifiers": {"scryfallId": "s-1"},
                     "legalities": {"commander": "Legal"},
                     "foreignData": [{"language": "French", "name": "Exemple"}],
                     "flavorText": "story"}
        self.source = {"meta": {"version": "1", "date": "2026-11-14"}, "data": {
            "ABC": {"code": "ABC", "name": "Sample", "cards": [self.card], "tokens": [],
                    "booster": {"draft": {}}}
        }}
        self.output = json.loads(json.dumps(self.source))
        self.output["data"]["ABC"].pop("booster")
        self.output["data"]["ABC"]["cards"][0].pop("foreignData")
        self.output["data"]["ABC"]["cards"][0].pop("flavorText")
        self.write()

    def write(self):
        self.src.write_bytes(lzma.compress(json.dumps(self.source).encode("utf-8")))
        self.dst.write_text(json.dumps(self.output), encoding="utf-8")

    def test_reviewed_fields_removed_while_rules_and_ids_preserved(self):
        result = self.audit.audit(self.src, self.dst, self.report)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["removed_field_counts"]["cards"]["foreignData"], 1)
        self.assertEqual(result["removed_field_counts"]["cards"]["flavorText"], 1)
        self.assertEqual(result["removed_field_counts"]["sets"]["booster"], 1)
        self.assertEqual(result["counts"], {"sets": 1, "cards": 1, "tokens": 0})

    def test_unapproved_rule_text_loss_is_rejected(self):
        self.output["data"]["ABC"]["cards"][0].pop("text")
        self.write()
        result = self.audit.audit(self.src, self.dst, self.report)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("unapproved_field_loss", [e["type"] for e in result["details"]])

    def test_changed_oracle_identifier_is_rejected(self):
        self.output["data"]["ABC"]["cards"][0]["identifiers"]["scryfallId"] = "wrong"
        self.write()
        result = self.audit.audit(self.src, self.dst, self.report)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("changed_retained_value", [e["type"] for e in result["details"]])


if __name__ == "__main__":
    unittest.main()
