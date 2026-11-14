# Direct AllPrintings JSON slim — experimental preview

**Status: separate preview only.** This branch adds an independent importer of official MTGJSON
[AllPrintings.json.xz](https://mtgjson.com/api/v5/AllPrintings.json.xz). It deliberately does
**not** alter the existing SQLite converter, profile 2.3, weekly publishing workflow, live site,
or public Releases. Two full official-source JSON builds in one GitHub Actions run produced byte-identical output. Cross-format checks and public-release integration remain separate acceptance gates.

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

### Additional download packages (after validating the raw JSON)

The official source may be downloaded as `AllPrintings.json.xz` to save bandwidth. It is
stream-decompressed during projection into `AllPrintings-slim.json`. The verified JSON
is then independently packaged in XZ, ZIP and Zstandard formats, just as SQLite is
available in multiple lossless packages. JSON is **never** reconstructed from SQLite.

```bash
# After the JSON build, with the system zstd executable installed:
python scripts/package_json_formats.py --package output-json --report json-packaging-proof.json
```

This creates `.json.zst` (single-thread Zstandard level 9) and `.json.zip`
(Deflate level 6, exactly one JSON entry), each with its own `.sha256`. The
script re-verifies the original JSON and XZ against `json-manifest.json`, then
decompresses both new archives and checks byte-identical JSON SHA-256 hashes.
It refuses to overwrite existing archives. The original JSON and JSON manifest
are unchanged; the report records the two additional archive hashes.

A preview of the planned additional download choices is in `docs/index.html`
on this branch. The live GitHub Pages website remains unchanged until a reviewed
merge. The JSON links are deliberately **disabled** if no actual verified JSON
assets appear in the latest public GitHub Release. No release publishing is
enabled by this draft PR.

**Still required before publication:** a same-source-date JSON/SQLite identity
audit, an independent review of the retained/omitted deckbuilding fields, and
a release integration plan that retains source provenance, validates all assets
before making a Release public, and avoids excessive temporary Actions storage.

## First full official-source acceptance (14 November 2026)

[GitHub Actions full-source acceptance run #43609135984](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43609135984) completed successfully from the verified upstream archive for MTGJSON `5.3.0+20261114`.

- Source `AllPrintings.json.xz` SHA-256: `3eacec102b0c7da4dd3fa58e54bfb0b2afe72b3d3a3f64ce0b633dd82babbb2e`
- Source records preserved: **883 sets**, **115,957 card entries**, **9,565 token entries**
- Uncompressed JSON: **290,480,106 bytes**; SHA-256 `eaa382d2f30511a64291848d75880c58b0b3979f757cf5e6881ee3198b04cf8e`
- Compressed JSON XZ: **25,614,036 bytes**; SHA-256 `dd7cd10924a8bc3f1d021616307b45562506cf22619682bf32c8d2cce3a63603`
- Measured build + full independent source/output comparison + XZ compression/roundtrip: **1:46.69** on one GitHub-hosted Linux runner; max RSS **194,768 KiB** (~190 MiB)
- Source and output were compared set-by-set after projection. The published SQLite Release was **not** modified.

**Independent reproducibility check:** [GitHub Actions run #43609523767](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43609523767) downloaded and verified official `AllPrintings.json.xz` once, then performed **two full direct-source builds**. Both sets of raw JSON and XZ hashes and the complete manifests were identical (`SECOND_BUILD_BYTE_IDENTICAL_PASS`). Each build independently validated all retained values against the source and the XZ roundtrip. The full run succeeded.

This verifies deterministic same-runtime outputs for the pinned official source. A JSON-versus-SQLite cross-format identity audit and safe publishing integration are still outstanding; no public JSON files are released.

## Verified full-data packaging — 14 November 2026

[GitHub Actions #43616001606](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43616001606) built both independent source-derived JSON outputs from official MTGJSON `5.3.0+20261114`, confirmed byte-identical JSON/XZ and matching manifests, then produced ZIP and Zstandard from the verified first JSON.

| Format | Bytes | SHA-256 |
| --- | ---: | --- |
| Raw `.json` | 290,480,106 | `eaa382d2f30511a64291848d75880c58b0b3979f757cf5e6881ee3198b04cf8e` |
| XZ `.json.xz` | 25,614,036 | `dd7cd10924a8bc3f1d021616307b45562506cf22619682bf32c8d2cce3a63603` |
| Zstandard `.json.zst` | 32,897,371 | `8e2c0b789d2b29dd84994d7893152a4cb539e9bea1c6cbc90c8a256ce8b9c8bd` |
| ZIP `.json.zip` | 54,195,094 | `e2cdfd5838bbfcdb7de716ed32b1e40a2c934ee063e9899e019f2c79bcf6a60f` |

The ZIP contains exactly one JSON file; ZIP and Zstandard both unpacked to raw JSON SHA-256 `eaa382d2f30511a64291848d75880c58b0b3979f757cf5e6881ee3198b04cf8e`. The full packaging step returned `FULL_JSON_ZIP_ZSTD_ROUNDTRIP_PASS`; it ran in 11.42 seconds on the GitHub runner. These are pinned-source measurements and not promises for future data.

**No public JSON Release was created.** Cross-format semantic acceptance and approval of the public publishing integration are still pending.

## Same-date JSON / SQLite acceptance and field policy (14 November 2026)

The first comparison was correctly blocked when the existing SQLite Release was dated
13 November and the JSON source was dated 14 November. The subsequent
[full same-date audit #43618066105](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43618066105)
downloaded **both** official sources with their own upstream checksums and built both
slim outputs from MTGJSON `5.3.0+20261114`.

- **PASS:** all 115,957 card-printing UUIDs and 9,565 token UUIDs matched.
- **PASS:** checked overlapping fields, identifiers (including Scryfall/Oracle), mana,
  names, rules text, dated rulings and legalities; zero unexplained mismatches.
- **PASS:** 883 sets preserved and independent source-vs-slim-JSON field audit found
  zero altered retained fields and zero unapproved removals.
- **Source-shape nuance:** JSON embeds tokens under parent sets (e.g. `10E`), while
  SQLite uses the token set code (e.g. `T10E`). Previously there were 2,997 such
  differences. They are now accepted **only** if the official
  `sets.tokenSetCode` value proves the relationship. The corrected full audit
  reported zero mismatches.
- **SQLite source schema drift:** the 14 November official SQLite reordered
  existing `sets` columns without adding/removing/changing their names or types.
  The code on this branch allows **only** that proven `sets`-column permutation;
  unknown field/type/index changes still fail closed. The full validated SQLite
  build succeeded using this compatibility rule; locked selected profile 2.3
  fields and output schema remained unchanged.

**Field-selection decision:** the approved removals concern purchasing, sealed
products, booster packaging, source deck lists, foreign-language translation
side tables, narrative flavor text and story metadata. For deck construction,
the actual card-printing records, printed/alternative names, identities,
mana, rules, rulings, legalities and multi-face relationships remain. The
`foreignData`/set-translation omission does reduce support for searching
cards by translated alternative names, and booster/deck-list omissions limit
draft/stock-deck analysis. Those omissions are deliberate, but applications
which need those functions should use official MTGJSON.

This comparison checks the documented intersecting fields, not strict equality
of the two format-specific schemas, and cannot substitute for a complete
Magic: The Gathering rules engine.

## Release and site architecture

JSON uses **separate versioned Releases** named `json-slim-<date>-<data-fingerprint>`
rather than modifying existing, immutable SQLite releases. This allows JSON-only
changes to publish without duplicating SQLite assets, and leaves GitHub's
`/releases/latest` for SQLite. The download website detects published JSON
Releases separately and displays the four JSON formats and checksum links only
when the assets really exist. The site source is staged in the draft PR; the
public site does not change until merge.

The new JSON release planner uses a data-only fingerprint, excluding upstream
`meta.date` and `meta.version`: daily metadata-only rebuilds must not create
new downloads. The weekly JSON pipeline is timed for Tuesday 07:20
Europe/Brussels, after the SQLite job's scheduled start. Only verified XZ plus
small metadata is passed between Actions jobs (~26 MB in the pinned test);
the publication job reconstructs and rechecks raw JSON before generating ZIP
and Zstandard. Public upload is draft-first and enabled **only** after all
checks pass. No independent JSON public Release is created by fixture tests.

**Publication acceptance:** [the full end-to-end read-only run #43618756802](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43618756802)
passed both full source-backed builders, independent JSON-field and SQLite
identity checks, validation of the JSON-only data fingerprint, and a guarded
release plan (blocked intentionally during the dry-run). The workflow now has
`JSON_PUBLICATION_ENABLED: 'true'`, but **only main** is allowed to publish.
The new Releases and live website remain unchanged until the PR is merged and
the first main-branch publishing job actually succeeds.

## Acceptance gates before merging or publishing

1. **PASS** — Official full `AllPrintings.json.xz` download and checksum verification.
2. **PASS** — Full builder, independent source/output per-set comparison, counts, hashes, sizes, and memory/time measurements.
3. **PASS** — Two byte-identical complete builds in one runner from the same verified archive.
4. **PASS** — Full-data Zstandard/ZIP packaging, exact roundtrip hashes and per-file checksums.
5. **PASS** — Same-date printing UUIDs, source-backed token-set relationships, Oracle IDs, rules, rulings and legalities compared against validated SQLite: 0 unexplained differences.
6. **PASS WITH LIMITATIONS** — Source-vs-output field-loss audit and explicit deckbuilding omission policy; alternate-language search and draft/stock-deck analysis are deliberately out of scope.
7. **PASS FOR INTEGRATION** — The separate JSON Release pipeline and website code passed full read-only end-to-end testing. Actual first public Release, uploaded assets and live Pages deployment still require post-merge verification.

MTGJSON remains the upstream data source. This is an independent unofficial derivative,
not an endorsement or official MTGJSON alternative.
