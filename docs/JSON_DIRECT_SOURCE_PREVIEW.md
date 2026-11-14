# Direct AllPrintings JSON slim — experimental preview

**Status: separate preview only.** This branch adds an independent importer of official MTGJSON
[AllPrintings.json.xz](https://mtgjson.com/api/v5/AllPrintings.json.xz). It deliberately does
**not** alter the existing SQLite converter, profile 2.3, weekly publishing workflow, live site,
or public Releases. A first full official JSON acceptance run succeeded on GitHub Actions; reproducibility and cross-format comparisons remain separate acceptance gates.

## Why independently source JSON?

MTGJSON's official JSON schema is nested: top-level `meta`, `data` keyed by set code, each
set with `cards` and `tokens`. It includes embedded `identifiers`, `legalities`, and
`rulings`. This differs from the separate tables and naming in official SQLite. A JSON
export of the slim SQLite cannot preserve the official JSON shape and type semantics directly.

The preview downloads **official JSON XZ and its official checksum**, verifies the source bytes
and projects each set using a streaming parser. It does **not** create JSON from SQLite.

## Removal policy

All sets and card/token entries remain. Entire objects are **never** filtered by language,
legality, type, release year, or format. Only these selected fields are removed:

| Source context | Removed keys | Why |
| --- | --- | --- |
| Set | `booster`, `decks`, `sealedProduct`, `translations` | Booster/sealed inventory, prebuilt decks, translated set names |
| Card | `boosterTypes`, `flavorText`, `foreignData`, `isStorySpotlight`, `purchaseUrls`, `skuIds`, `sourceProducts` | Packaging, narrative text, separate foreign-language translations and shopping data |
| Token | `boosterTypes`, `flavorText`, `skuIds`, `sourceProducts`, `tokenProducts` | Packaging and non-rules narrative data |

**Important distinctions:** `foreignData` is a *nested JSON field*, not an entire table.
Its removal does not filter out original non-English card-printing records. `flavorName` and
`faceFlavorName` are kept because alternative visible card names can help identify printings.
Identities, Scryfall/Oracle identifiers, original/printed rules text where supplied by JSON,
mana, faces, relationships, rules, format legalities and rulings are preserved as source values.
Properties that are not explicitly excluded are kept, including newly introduced properties,
rather than silently removed. Unknown new schema should receive review before publication.

**No cross-format equivalence claim:** the JSON and SQLite pipelines use different official
input formats with different shapes and sometimes different source fields. They can be checked
for overlapping identities/data once a real pinned-source build is run, but must not be
declared field-identical by default.

## Usage

Python 3.11+, with one JSON-specific streaming dependency. The existing SQLite converter
continues to use only the Python standard library.

```bash
python -m pip install -r requirements-json.txt
python slim_json.py download --directory downloads-json
python slim_json.py build \
  --archive downloads-json/AllPrintings.json.xz \
  --checksum-path downloads-json/AllPrintings.json.xz.sha256 \
  --output-dir output-json
python -m unittest discover -s tests -p 'test_json_slim.py' -v
```

The build writes an uncompressed `.json`, lossless `.json.xz`, SHA-256 sidecars and
`json-manifest.json`. Source and output are read back and compared **set-by-set** against
the independently filtered source, and both the source SHA and compression roundtrip are checked.
Nothing is published automatically. The builder refuses to overwrite an existing output folder.

## First full official-source acceptance (14 November 2026)

[GitHub Actions full-source acceptance run #43609135984](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43609135984) completed successfully from the verified upstream archive for MTGJSON `5.3.0+20261114`.

- Source `AllPrintings.json.xz` SHA-256: `3eacec102b0c7da4dd3fa58e54bfb0b2afe72b3d3a3f64ce0b633dd82babbb2e`
- Source records preserved: **883 sets**, **115,957 card entries**, **9,565 token entries**
- Uncompressed JSON: **290,480,106 bytes**; SHA-256 `eaa382d2f30511a64291848d75880c58b0b3979f757cf5e6881ee3198b04cf8e`
- Compressed JSON XZ: **25,614,036 bytes**; SHA-256 `dd7cd10924a8bc3f1d021616307b45562506cf22619682bf32c8d2cce3a63603`
- Measured build + full independent source/output comparison + XZ compression/roundtrip: **1:46.69** on one GitHub-hosted Linux runner; max RSS **194,768 KiB** (~190 MiB)
- Source and output were compared set-by-set after projection. The published SQLite Release was **not** modified.

This is one full real-data build with source-backed validation; it does **not** by itself prove byte-identical reproduction on a second build, completeness of all cross-format fields, or readiness for public Release integration.

## Acceptance gates before merging or publishing

1. Verify an official full `AllPrintings.json.xz` download and exact upstream checksum.
2. Execute the full JSON build on the GitHub runner, compare source/JSON projections, and
   record set/card/token counts, resulting sizes, hashes and peak runtime resources.
3. Reproduce the build and compare logical content and package hashes in the same runtime.
4. Cross-check selected printing UUIDs, multi-face relationships, Oracle IDs and legalities
   against a same-date validated SQLite output, acknowledging format differences.
5. Review whether the omitted fields are appropriate for deckbuilding users.
6. Only after acceptance, separately approve release asset additions and website downloads,
   avoiding duplicate temporary GitHub Actions storage.

MTGJSON remains the upstream data source. This is an independent unofficial derivative,
not an endorsement or official MTGJSON alternative.
