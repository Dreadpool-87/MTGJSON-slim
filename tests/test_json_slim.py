"""Regression tests for independently sourced, deckbuilding-focused MTGJSON JSON."""
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import tempfile
import unittest

import slim_json


def sample_source():
    return {
        "meta": {"date": "2026-11-13", "version": "5.3.0+20261113"},
        "data": {
            "M19": {
                "code": "M19", "name": "Core Set 2019", "type": "core",
                "cards": [
                    {
                        "uuid": "card-front", "name": "Sample // Back", "setCode": "M19",
                        "number": "100", "layout": "transform", "side": "a",
                        "faceName": "Sample", "otherFaceIds": ["card-back"],
                        "identifiers": {"scryfallId": "scryfall-print", "scryfallOracleId": "scryfall-oracle"},
                        "legalities": {"commander": "Legal", "modern": "Legal"},
                        "rulings": [{"date": "2026-01-01", "text": "Rules matter."}],
                        "manaValue": 2, "manaCost": "{1}{R}", "text": "Deal damage.",
                        "printedText": "Original printed wording.",
                        "foreignData": [{"language": "French", "name": "Exemple"}],
                        "purchaseUrls": {"tcgplayer": "https://example.invalid"},
                        "skuIds": {"normal": ["product-id"]},
                        "boosterTypes": ["draft"], "flavorText": "Pure story.",
                        "isStorySpotlight": True, "sourceProducts": {"sealed": ["id"]},
                        "customFutureField": {"preserve": [None, False, 3.25]},
                        "flavorName": "Alternative printed name"
                    },
                    {
                        "uuid": "card-back", "name": "Sample // Back", "setCode": "M19",
                        "number": "100", "layout": "transform", "side": "b",
                        "otherFaceIds": ["card-front"], "identifiers": {"scryfallId": "side-b"},
                        "legalities": {}, "text": "Other face."
                    }
                ],
                "tokens": [
                    {
                        "uuid": "token-uuid", "name": "Sample Token", "setCode": "TM19",
                        "number": "1", "identifiers": {"scryfallId": "token-scryfall"},
                        "text": "Token ability.", "tokenProducts": [{"id": "store-product"}],
                        "skuIds": [], "sourceProducts": {}, "flavorText": "Lore",
                        "otherFaceIds": ["token-other-face"]
                    }
                ],
                "booster": {"draft": {"sheets": []}}, "decks": [{"name": "Example deck"}],
                "sealedProduct": [{"name": "Example booster box"}],
                "translations": {"French": "Set traduit"},
                "tokenSetCode": "TM19", "releaseDate": "2018-07-13"
            },
            "LEA": {
                "code": "LEA", "name": "Limited Edition Alpha", "type": "core",
                "cards": [{
                    "uuid": "non-english-original", "name": "Black Lotus", "setCode": "LEA",
                    "number": "1", "language": "German",
                    "identifiers": {"scryfallId": "original"},
                    "legalities": {"commander": "Banned"}, "text": "{T}: Add mana."
                }],
                "tokens": [],
                "translations": {}
            }
        }
    }


class JsonSelectionTests(unittest.TestCase):
    def test_card_faces_id_rulings_printings_and_token_survive(self):
        result = slim_json.project_set("M19", sample_source()["data"]["M19"])
        self.assertEqual(len(result["cards"]), 2)
        self.assertEqual(len(result["tokens"]), 1)
        self.assertEqual(result["cards"][0]["otherFaceIds"], ["card-back"])
        self.assertEqual(result["cards"][0]["identifiers"]["scryfallOracleId"], "scryfall-oracle")
        self.assertEqual(result["cards"][0]["rulings"][0]["text"], "Rules matter.")
        self.assertEqual(result["cards"][0]["legalities"]["modern"], "Legal")
        self.assertEqual(result["cards"][0]["flavorName"], "Alternative printed name")
        self.assertEqual(result["cards"][0]["customFutureField"]["preserve"], [None, False, 3.25])
        self.assertEqual(result["tokens"][0]["otherFaceIds"], ["token-other-face"])
        for field in slim_json.SET_OMIT:
            self.assertNotIn(field, result)
        for field in slim_json.CARD_OMIT:
            self.assertNotIn(field, result["cards"][0])
        for field in slim_json.TOKEN_OMIT:
            self.assertNotIn(field, result["tokens"][0])

    def test_no_language_filter(self):
        result = slim_json.project_set("LEA", sample_source()["data"]["LEA"])
        self.assertEqual(len(result["cards"]), 1)
        self.assertEqual(result["cards"][0]["language"], "German")

    def test_missing_identity_and_malformed_sets_fail(self):
        card = sample_source()["data"]["M19"]["cards"][0]
        card.pop("uuid")
        with self.assertRaises(ValueError):
            slim_json.project_set("M19", sample_source()["data"]["M19"])
        with self.assertRaises(ValueError):
            slim_json.project_set("BAD", sample_source()["data"]["LEA"])

    def test_preserve_all_other_card_fields(self):
        source = sample_source()["data"]["M19"]["cards"][0]
        projected = slim_json.project_card(source, "card")
        self.assertEqual(set(source) - set(projected), slim_json.CARD_OMIT & set(source))


@unittest.skipUnless(importlib.util.find_spec('ijson') is not None, 'install optional ijson for streaming integration tests')
class JsonPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / "AllPrintings.json.xz"
        self.sidecar = self.folder / "AllPrintings.json.xz.sha256"
        payload = json.dumps(sample_source(), ensure_ascii=False).encode("utf-8")
        self.source.write_bytes(lzma.compress(payload))
        self.sidecar.write_text(hashlib.sha256(self.source.read_bytes()).hexdigest() + "\n")

    def test_verified_independent_build_and_identical_xz(self):
        dest = self.folder / "output"
        manifest = slim_json.build(self.source, self.sidecar, dest)
        self.assertEqual(manifest["counts"], {"sets": 2, "cards": 3, "tokens": 1})
        self.assertEqual(manifest["profile"], slim_json.PROFILE)
        self.assertEqual(manifest["upstream"]["url"], slim_json.SOURCE_URL)
        raw = dest / manifest["output"]["json"]["name"]
        compressed = dest / manifest["output"]["xz"]["name"]
        self.assertEqual(lzma.decompress(compressed.read_bytes()), raw.read_bytes())
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), manifest["output"]["json"]["sha256"])
        self.assertEqual(json.loads(raw.read_text())["data"]["LEA"]["cards"][0]["language"], "German")
        self.assertEqual((dest / "json-manifest.json").exists(), True)
        with self.assertRaises(FileExistsError):
            slim_json.build(self.source, self.sidecar, dest)

    def test_corrupt_archive_rejected_without_published_output(self):
        self.source.write_bytes(self.source.read_bytes() + b"corruption")
        with self.assertRaises(ValueError):
            slim_json.build(self.source, self.sidecar, self.folder / "output")
        self.assertFalse((self.folder / "output").exists())

    def test_bad_source_rows_rejected(self):
        fixture = sample_source()
        fixture["data"]["M19"]["cards"][0].pop("identifiers")
        self.source.write_bytes(lzma.compress(json.dumps(fixture).encode()))
        self.sidecar.write_text(hashlib.sha256(self.source.read_bytes()).hexdigest() + "\n")
        with self.assertRaises(ValueError):
            slim_json.build(self.source, self.sidecar, self.folder / "output")
        self.assertFalse((self.folder / "output").exists())

    def test_read_back_detects_modified_output(self):
        raw = self.folder / "tampered.json"
        raw.write_text(json.dumps({"meta": sample_source()["meta"], "data": {
            "M19": slim_json.project_set("M19", sample_source()["data"]["M19"])
        }}))
        with self.assertRaises(ValueError):
            slim_json.compare_to_source(self.source, raw, sample_source()["meta"],
                                        {"sets": 2, "cards": 3, "tokens": 1})


if __name__ == "__main__":
    unittest.main()
