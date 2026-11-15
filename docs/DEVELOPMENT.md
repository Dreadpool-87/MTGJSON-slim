# Development, validation and release automation

[Back to README](../README.md) · [Usage and CLI examples](USAGE.md) · [Releases](https://github.com/Dreadpool-87/MTGJSON-slim/releases)

This document describes how the repository derives, checks and publishes **three different MTGJSON-slim datasets**. It is a technical reference; the [README](../README.md) is the public project introduction. Public datasets are not generated from each other.

## Architecture and data contracts

| Release family | Authoritative upstream | Builder | Contract / policy |
| --- | --- | --- | --- |
| SQLite (`slim-...`) | Official `AllPrintings.sqlite.xz` | `slim.py` | `profiles/v2_3.json`, `contracts/main-profile-2.3.json` |
| AllPrintings JSON (`json-slim-...`) | Official `AllPrintings.json.xz` | `slim_json.py` | Explicit JSON field-removal policy and independent field auditor |
| AtomicCards JSON (`atomic-slim-...`) | Official `AtomicCards.json.xz` | `atomic_slim.py` | `contracts/atomic-b1.json` |

All sources are individually downloaded and verified using their official SHA-256 sidecars. A successful conversion must match the *selected* official data; it is not sufficient to create parseable JSON or a SQLite file. Schema policies are source-specific: SQLite and AtomicCards reject unexpected structure, while the AllPrintings JSON builder retains newly introduced fields unless explicitly excluded and uses independent source/output field checks. Invalid source data and failed validation block publishing; no format silently asserts unsupported cross-format parity.

### SQLite profile 2.3

The current SQLite projection retains **8 tables, 224 columns and 20 explicit lookup indexes**. It includes card and token printing records, printed/original names, identities, mana, Oracle and printed rule text, faces, format legalities, dated rulings, sets and indexed identifiers. All original physical-printing records remain, including non-English ones; **there is no English-only printing filter**.

From 20 upstream tables, 8 are kept and 12 excluded. Omitted tables include `cardForeignData`, `setTranslations`, purchasing/sealed/booster and source-deck-list tables. Excluded `cards` and `tokens` fields include `boosterTypes`, `skuIds`, `sourceProducts`, `flavorText`, plus `cards.isStorySpotlight`. The absence of the foreign-name translation *table* does **not** mean that non-English physical printing records or printed names were removed. Conversely, searching every translated alternative name is not guaranteed.

The locked [profile inventory](PROFILE_2_3_DATA_INVENTORY.md) is the authority on exact selected columns, constraints, indexes and removals. Profile 2.3 is independent of the archived [2.2 field contract](../contracts/historical-2026-11-07-field-baseline.json). Only the reviewed order-only permutation of the upstream `sets` columns is accepted; unknown field, type and index drift remains blocking. Earlier profile 2.2 can be built for historical comparison, but is not the scheduled default.

### AllPrintings JSON

The JSON source has a nested `meta` + set-keyed `data` shape, each set containing `cards` and `tokens` arrays. It is **not reconstructed from SQLite**. Entire card, token and set records are never filtered by language, legality, format, release year or card type.

The JSON policy omits reviewed packaging/product/deck/translation/narrative fields. In particular, nested `foreignData` is deliberately omitted in AllPrintings JSON; the card-printing records themselves are not discarded. The builder streams the official JSON and validates projected records. [Exact JSON exclusions, source comparison, historical acceptance and measured sizes](JSON_DIRECT_SOURCE_PREVIEW.md) are documented separately. The cross-format audit checks overlapping identities and fields, **not** complete equivalence between SQLite and JSON schemas.

### AtomicCards profile B1

AtomicCards contains card-name groups rather than a full printing/token inventory. Only these card properties are omitted:

- `purchaseUrls`: shopping links, not card identifiers.
- `convertedManaCost`: removed only when exactly equal in type and value to retained `manaValue`.
- `faceConvertedManaCost`: removed only when exactly equal in type and value to retained `faceManaValue`.

Every other reviewed card property and nested value is retained, including translated `foreignData`, identifiers, rules, Commander-related fields, rulings, legalities and card relationships. The builder requires the pinned 114-path source contract, valid mana aliases and exactly one `meta` and `data` root object. The independent auditor separately verifies complete source and output root structure and all retained nested values and name-group/record order. Unknown, duplicate or malformed root fields block publication. Existing consumers of deprecated mana field names must use the modern aliases.

Source: [AtomicCards profile contract](../contracts/atomic-b1.json). A successfully built candidate starts as **unverified**; the independent full-source audit must explicitly mark it verified.

## CI and review gates

The repository's GitHub Actions uses **Python 3.14**. Every applicable job checks that `compression.zstd` can be imported. The full regression gate is:

```bash
python -m pip install -r requirements-json.txt
python scripts/run_regression_tests.py
```

Node.js is also required for executable download-site tests. The Python regression runner fails on failing tests, **skipped tests** or no discovered tests. That gate runs in all three primary release test jobs and catches cross-format, source validation, website and archive regressions. The SQLite converter itself stays standard-library-only; installing JSON and Zstd test dependencies is a **CI test environment** requirement, not a SQLite runtime dependency.

The current six workflow definitions are:

| Workflow | Purpose |
| --- | --- |
| [`verify.yml`](../.github/workflows/verify.yml) | SQLite full-source build, validation and release |
| [`json-weekly.yml`](../.github/workflows/json-weekly.yml) | AllPrintings JSON full-source build and release, including SQLite cross-checks |
| [`atomic-weekly.yml`](../.github/workflows/atomic-weekly.yml) | Atomic full-source build and independent audit |
| [`json-preview.yml`](../.github/workflows/json-preview.yml) | JSON PR regression and site script checks (historical workflow name) |
| [`json-source-acceptance.yml`](../.github/workflows/json-source-acceptance.yml) | Manually triggered independent JSON acceptance |
| [`json-cross-format-audit.yml`](../.github/workflows/json-cross-format-audit.yml) | Manually triggered cross-format acceptance |

The two manual audit workflows are distinct from the weekly jobs. A PR green check does **not** by itself prove that a future scheduled event ran, nor that every manual audit job was dispatched. The normal review/test phase is read-only; public publishing is restricted to the default-branch workflow after a verified change.

## Weekly schedule

| Local time | Dataset |
| --- | --- |
| Tuesday **07:00 Europe/Brussels** | SQLite |
| Tuesday **07:20 Europe/Brussels** | AllPrintings JSON |
| Tuesday **07:40 Europe/Brussels** | AtomicCards |

All three use named local timezones (CET/CEST); GitHub may delay scheduled starts. The first scheduled events after initial publication were set for **17 November 2026**. Verify their *actual* GitHub Actions run events and conclusions rather than assuming a timer fired. GitHub may disable scheduled workflows in an inactive public repository after prolonged inactivity; check Actions settings if updates stop.

## Publication and packaging

A normal source build generates the verified raw database/JSON, a byte-verified XZ copy, individual SHA-256 sidecars and provenance manifests. Validation completes **before** a publication candidate is exposed. Packaging adds:

- `*.zst`: Zstandard level 9, one worker, frame checksum.
- `*.zip`: a single file using standard Deflate.
- One `.sha256` sidecar per format; XZ, Zstd and ZIP all decompress to **the exact original raw bytes**.

`scripts/zstd_support.py` uses Python 3.14's `compression.zstd` in GitHub Actions. On older local Python, it can use the system `zstd` executable as a fallback. Different compressor/runtime versions may produce different **compressed bytes** while decompressing to identical raw data. ZIP remains Deflate, not Zstandard.

Every published Release is separate per family and carries **10 assets**: four data formats, four SHA-256 sidecars, a versioned manifest and `MTGJSON_LICENSE.txt`. The website is deployed from [`docs/index.html`](index.html) through GitHub Pages (`main`, `/docs`) and resolves **published assets** from the GitHub API. The SQLite series retains the `releases/latest` endpoint; the two JSON families have their own release tags. Missing/untrusted assets or checksum sidecars are not enabled in download selectors.

**Fail-closed release sequence:**

1. Fetch official source and SHA-256; reject mismatch.
2. Build and independently validate the selected data against the source, including schema and identity constraints.
3. Build/check XZ and individual checksums; retain a compact evidence manifest.
4. Compare content/profile fingerprints with the previous Release; skip unchanged data when appropriate.
5. Transfer only the verified compressed candidate and necessary sidecars between jobs (temporary artifacts are short-lived).
6. Rehydrate, verify, generate Zstandard/ZIP and roundtrip-check all outputs.
7. Publish a **draft** with all ten assets, verify asset identities, then make it public. Prior published Releases remain unchanged if checks fail.

The SQLite content fingerprint includes retained data, SQL schema and indexes, but excludes incidental source `meta` rows. Metadata-only changes therefore do **not** trigger a new SQLite Release. AllPrintings JSON similarly uses a data-only fingerprint; AtomicCards compares both data and its profile-contract fingerprint. A contract-only Atomic change must have a distinct tag. Rebuilding an unchanged dataset is still useful for validating against a new official daily source snapshot.

A failed draft may require explicit maintenance, not bypassing validation. A publish job with write permissions is separate from read-only build/test jobs. Publication is explicitly controlled by per-family workflow flags: `PUBLICATION_ENABLED` (SQLite), `JSON_PUBLICATION_ENABLED` (AllPrintings JSON) and `ATOMIC_PUBLICATION_ENABLED` (AtomicCards). These are `true` in the current workflows; a maintainer can disable publication for a family without weakening its validation. Never force an overwrite of a prior Release.

## Reproducibility and runtime differences

SQLite output builds tables, rows and indexes in defined order and uses a fixed page size and `VACUUM`. XZ uses Python `lzma` preset 6. Manifests record official source URL/version/digests, profiles, tool commit, Python and SQLite runtime versions, output sizes and SHA-256; build reports additionally track elapsed time and peak memory.

**Logical equality is not the same as byte equality across SQLite versions.** For the pinned source, the Python 3.14 upgrade used SQLite 3.53.1 and produced a different raw SQLite SHA-256 than the earlier runtime; the full selected-data, schema and index fingerprint remained identical. Repeatable bytes are checked **within the same runtime**, not promised across SQLite/liblzma versions. A source-backed logical projection check is required when runtime bytes differ.

Historical acceptance evidence is deliberately maintained outside the README:

- [SQLite 2.3 exact selection and acceptance](PROFILE_2_3_DATA_INVENTORY.md)
- [SQLite 2.2 historical acceptance](acceptance-profile-2.2.md)
- [AllPrintings JSON field audit, full builds and same-date comparison](JSON_DIRECT_SOURCE_PREVIEW.md)
- [GitHub Actions runs and Releases](https://github.com/Dreadpool-87/MTGJSON-slim/actions)

## Errors and troubleshooting

- **Official checksum mismatch:** stop. Fetch a fresh matching archive and official checksum; do not invent or replace the expected hash with the calculated one. Daily files may change while being downloaded.
- **Unexpected source schema, relation, index or identity mismatch:** stop, retain the inventory/report, review a new contract/profile. Never auto-approve unknown fields.
- **Duplicate/orphaned records, SQLite integrity or retained-value errors:** investigate the source and transformation; do not bypass validation.
- **Existing output directory or file:** use a new versioned destination. Only identical verified inputs may be reused when supported.
- **Missing space, timeout or dependency:** provide sufficient temporary disk/runtime time; ensure `ijson`, Node.js and the supported Zstandard backend are available as needed. Do not publish a partial candidate.
- **Failed or incomplete draft Release:** inspect Action evidence and individual assets, repair the cause, and explicitly clean up a failed draft if necessary.
- **Missing website download or checksum:** check the actual published Release's asset names and `.sha256` pairs, GitHub API availability and the Pages deployment. Review **Settings → Pages** for the existing `main` / `/docs` site configuration.

The project intentionally does **not** generate `.sql` or `.psql` exports: neither provides a stronger directly queryable local database than the shipped SQLite format, and both would increase maintenance and validation complexity.

## Attribution

This is an independent unofficial derivative of [MTGJSON](https://mtgjson.com/), not endorsed by MTGJSON or Wizards of the Coast. See [third-party notices](../THIRD_PARTY_NOTICES.md), [code license](../LICENSE) and [upstream notice](../MTGJSON_LICENSE.txt).
