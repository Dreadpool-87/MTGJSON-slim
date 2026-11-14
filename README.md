# MTGJSON-slim

Independent, standard-library Python tooling for creating smaller, verified SQLite datasets from official [MTGJSON](https://mtgjson.com/) downloads.

**Development preview.** Verified slim SQLite and lossless XZ downloads are available through [GitHub Releases](https://github.com/Dreadpool-87/MTGJSON-slim/releases). The converter and database use the versioned [profile 2.3](profiles/v2_3.json).

## Requirements and use

Python 3.11+ on Linux, SQLite (bundled with Python), sufficient local disk space for the source, temporary files and output. No pip dependencies. Run from a clean checkout at the exact tool commit recorded in the manifest:

```bash
python -m unittest discover -s tests -v
python slim.py download --directory downloads --report evidence/download.json
python slim.py inventory --database downloads/AllPrintings.sqlite --report evidence/source.json
```

**Default profile:** running `slim.py build` or `slim.py validate` without `--profile` now selects the main `profiles/v2_3.json`. You may still explicitly supply `--profile profiles/v2_2.json` to reproduce a historical build. GitHub's scheduled workflow explicitly uses 2.3. Neither command depends on the 7 November contract when using the main profile.

`download` retrieves the compressed official SQLite archive and verifies its matching official SHA-256 before accepting it. It does not decompress it. The optional inventory command above requires an already decompressed source; use `xz -dk downloads/AllPrintings.sqlite.xz` after successful verification, or rely on the build's automatic source inventory.

```bash
python slim.py build \
  --archive downloads/AllPrintings.sqlite.xz \
  --sha256 "$(cat downloads/AllPrintings.sqlite.xz.sha256)" \
  --profile profiles/v2_3.json --output-dir output \
  --tool-commit "$(git rev-parse HEAD)" --report evidence/build.json
```

Outputs include a version-specific **uncompressed `.sqlite` and losslessly compressed `.sqlite.xz`**, **a SHA-256 sidecar for each file**, a provenance manifest, a validation report and a full upstream schema/count inventory. The build verifies the archive **before** decompression, prepares in a temporary directory, and exposes the package only after validation and compression succeed. Reports must live outside the package and must not alias inputs.

For a checksum-only upstream check, use `download --previous-sha256 <prior-official-digest>` with the other download arguments; `UNCHANGED` skips the archive download. Repeat the same build command to detect unchanged upstream/profile/tool inputs in an existing package. Existing packages are rechecked against the verified source projection and their compressed/database bytes before returning `UNCHANGED`. A changed input/profile/tool requires a new output directory. Nothing is silently overwritten.

For independent validation, find the version-specific output filename in `output/manifest.json`:

```bash
python slim.py validate --database output/AllPrintings-slim-VERSION-profile-2.3.sqlite \
  --source downloads/AllPrintings.sqlite --profile profiles/v2_3.json \
  --report evidence/validation.json
```

All commands write JSON reports and return nonzero on failure. A protected report-path collision returns a JSON error on stdout without writing that path. Without `--source`, validation checks the expected schema, SQLite integrity, identity keys and relationships; with `--source`, it additionally compares the count and deterministic logical digest of every projected row, including duplicate multiplicity and NULLs.

## Published database formats

When a validated, changed dataset is published, **both** database variants appear on the **same MTGJSON-slim GitHub Release**. No second repository is needed:

| Planned asset | Purpose |
| --- | --- |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite` | Uncompressed, directly usable SQLite database |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite.sha256` | SHA-256 verification for the uncompressed database |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite.xz` | Identical SQLite content compressed with XZ for smaller downloads |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite.xz.sha256` | SHA-256 verification for the compressed database |
| `manifest.json` | Source version/checksum, profile version, output sizes/hashes, tooling and runtime provenance |
| `MTGJSON_LICENSE.txt` | Upstream MTGJSON copyright and MIT license notice |

The converter **already produces both database files locally**. The build now also emits and checks a checksum sidecar for **each** database variant. A compressed file must decompress byte-for-byte to its corresponding `.sqlite`; either file must contain the **same slim projection**: eight retained tables and the explicitly selected fields/indexes. Compression does not determine which data is excluded.

**Release automation:** After validation, the workflow compares retained data and index definitions to the latest published Release. It creates and verifies a draft with the six package assets only when the data meaningfully changed, then makes that Release public. Failed checks prevent publication and the previously published Release remains available. Maintainers can disable future publication by changing `PUBLICATION_ENABLED` to `false` in the workflow.

A `.sql` export is a text script for reconstructing a database, not a directly queryable SQLite file. `psql` is the PostgreSQL client and a `.psql` extension is not a universal database container. The project intentionally **does not** add SQL or PostgreSQL exports; they offer no clear benefit for the primary SQLite consumers and would add build/test complexity.

## Current SQLite data profile

The current [profile](profiles/v2_3.json) selects the fields, tables and lookup indexes preserved from official MTGJSON SQLite data. It pins the complete upstream schema observed for MTGJSON `5.3.0+20261113` and **fails closed** if MTGJSON adds, removes or changes its schema. Changes require an explicit profile review rather than silent data loss.

The output contains **8 tables, 224 columns and 20 explicit indexes**.

**Profile 2.3 consciously drops three non-gameplay columns** relative to 2.2: `cards.flavorText`, `tokens.flavorText` and `cards.isStorySpotlight`. Current rules (`cards.text`, `tokens.text`, `cardRulings.text`), printed/original rule text, alternative card names, identities, relationships and all indexes remain intact. The active 2.3 profile has its own **independent, locked main schema** in [`contracts/main-profile-2.3.json`](contracts/main-profile-2.3.json), covering all 224 selected columns, indexes, source schema and relationships. It **does not depend on** the historical 7 November list or profile 2.2. The historical [`contracts/historical-2026-11-07-field-baseline.json`](contracts/historical-2026-11-07-field-baseline.json) is preserved for archived profile 2.2 and regression checks. Older profile 2.2 remains reproducible.

Every selected record, NULL, face relationship, card printing and language is preserved, including printed/original names and rules text. There is no English-only filter or card-type exclusion.

| Area | Current policy |
| --- | --- |
| Cards and tokens | Keep identities, set/collector numbers, names, Oracle and printed text, mana/type information, multiple faces, relationships, flags, printing and artwork/reference metadata |
| External identifiers, legalities and rulings | Keep all selected external IDs, per-format legality information and card-linked rulings |
| Sets and source metadata | Keep codes, set identities, dates, language metadata, source version/date and token-set links |
| Removed data | Omit localized translation table `cardForeignData`, set-name translations, product/purchase/booster/deck-list tables and six packaging-related fields plus `cards.flavorText`, `tokens.flavorText` and `cards.isStorySpotlight` |
| Source safety | Verify the official source checksum, pin the upstream schema and reject missing required fields, unknown schema changes or broken relationships |
| Lookup policy | Use verified UUID/code identity indexes and non-unique Scryfall printing/Oracle-ID indexes where multi-face records share external IDs |

Every retained value is copied directly from the verified source; no fuzzy matching, translation, Oracle-text reconstruction, rules inference or card-strength claims are added. For exact selections, see the [complete current SQLite data inventory](docs/PROFILE_2_3_DATA_INVENTORY.md).

### Exact data retention and removal

For an **exhaustive, table-by-table and field-by-field list** of what is kept and what is removed, read **[Profile 2.3 — retained and omitted SQLite data](docs/PROFILE_2_3_DATA_INVENTORY.md)**. It is checked against the actual versioned profile, not an approximate description.

From 20 source tables, the output retains 8 and omits 12. The complete `cardForeignData` and `setTranslations` tables and sales, sealed-product, booster, deck-list and token-product tables are excluded. Within `cards` and `tokens`, excluded source fields are `boosterTypes`, `skuIds` and `sourceProducts` (three per table, six total), plus exactly `cards.flavorText`, `tokens.flavorText` and `cards.isStorySpotlight`. These three are non-gameplay narrative fields. Every field of the six other retained tables remains. Original non-English physical printing records and printed names are **not** removed. Schema pinning still checks all omitted upstream tables for drift.

**Profile 2.3 real-data acceptance:** [the full GitHub-hosted comparison run](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43570579132) passed for both profiles built from the same official archive. It confirmed all retained values and 20 indexes were identical; only the three reviewed columns disappeared. Raw SQLite: 282,390,528 → 276,037,632 bytes (**6,352,896 saved**); XZ: 49,264,112 → 47,118,052 bytes (**2,146,060 saved**). See [Profile 2.3 inventory and acceptance measurements](docs/PROFILE_2_3_DATA_INVENTORY.md). The first size figure describes full raw database output, not only the `isStorySpotlight` column.

**Historical profile 2.2 verification:** two full local reproducible builds passed, plus a separate [real-data GitHub-hosted acceptance run](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43516913604) where both the tests and real-data build jobs succeeded. Its official source checksum matched the local source. The raw SQLite/XZ hashes differ between local and GitHub runtimes, so cross-runtime byte reproducibility is **not claimed**; source-selected logical table contents matched in the preserved evidence. See [historical Profile 2.2 acceptance and limitations](docs/acceptance-profile-2.2.md); profile 2.3's independent same-source acceptance is documented above.

The scheduled workflow is configured for **Tuesday at 07:00 Europe/Brussels** and rebuilds a fresh verified SQLite and derives its XZ copy. The [first public Release](https://github.com/Dreadpool-87/MTGJSON-slim/releases/tag/slim-2026-11-13-8fd830df9bd26ec5) was published after a verified full-data build on 14 November 2026. Subsequent scheduled/manual runs publish only when selected data or indexes change.

## Query audit

```bash
python benchmarks/query_audit.py --database path/to/database.sqlite \
  --cases cases.json --create-cases --report benchmark.json --repeats 5
```

Use the same saved case file for every compared database. The audit records exact SQL/parameters, result counts/digests, plans for every sample, five warm-cache timing batches and medians, and per-index dbstat footprints. Missing footprint capability is reported as null plus an error, never as zero bytes. These are sampled lookup workloads with full result retrieval, not whole-database latency promises or cold-cache tests. Oracle cohorts include singleton, moderate and high-fanout IDs; printing samples include singleton and shared multi-face IDs. Unknown-ID cases are explicitly synthetic. No personal collection is required.

These are reproducible **sampled** query measurements, not a guarantee that every lookup is faster. Read the [historical profile 2.2 acceptance report](docs/acceptance-profile-2.2.md) for actual timings and limitations.

## Reproducibility and provenance

Tables, rows and indexes are rebuilt in defined order, with a fixed page size and an SQLite `VACUUM`. XZ uses Python lzma preset 6. The manifest includes upstream URL/version/digests, profile version/digest, tool commit, output sizes/digests and Python/SQLite versions. Byte reproducibility is tested in the same runtime; it is not guaranteed across SQLite/liblzma versions. Logical projection comparison is runtime-independent for the pinned SQLite scalar types. Timing and peak RSS appear in the build report rather than the deterministic database.

## Automation and troubleshooting

**Weekly schedule:** Every **Tuesday at 07:00** in `Europe/Brussels` (CET/CEST). The [GitHub Actions verification workflow](.github/workflows/verify.yml) uses `cron: '0 7 * * 2'` with a named timezone, not a fixed UTC offset. GitHub can delay the exact start time, and scheduled workflows run only from the default branch. A public repository's scheduled workflows may be disabled by GitHub after 60 days without repository activity; review the workflow status if updates stop.

**What runs:** On **every scheduled run** (and every manual run on the default branch), the workflow downloads and checksum-verifies the current official MTGJSON archive, rebuilds a fresh slim SQLite from the version-pinned profile, verifies it against the source, creates the XZ copy, checks that decompression reproduces the exact SQLite bytes and checks both SHA-256 sidecars. Pull requests run only the fixture tests. A source schema change, invalid checksum, broken index or relationship or validation failure stops the build; the previous published Release remains unchanged.

**Change detection:** The newest successful published Release's manifest is compared with the newly built logical fingerprint. It includes all **retained data tables except the upstream `meta` row**, plus resulting SQL schema and indexes. Therefore an MTGJSON date/version-only change **does not** create another Release. A change in card/printing/ruling/legality/set data or schema/indexes **does**. This is a deliberate logical comparison, not a raw SQLite/XZ byte comparison. Each week is rebuilt and revalidated regardless of whether it is eventually published.

**Verified release flow:** The normal build job has read-only repository permissions. A separate publishing job with write permission runs only after successful validation and a meaningful data change. It rechecks the uploaded package, creates a GitHub **draft Release** with exactly six assets (raw SQLite, XZ, their two checksum files, the manifest and the upstream `MTGJSON_LICENSE.txt`), verifies all six assets are present and **only then publishes** the Release. No existing stable Release is overwritten; if any step fails, the old latest Release stays available. A failed draft may require manual cleanup before retrying. The release comparison fails closed on an unreadable or incompatible previous manifest.

**Outputs and retention:** A no-change or failed build does not transfer a public database candidate. Verification JSON and the manifest are kept as GitHub Actions artifacts for **14 days**. A changed, verified database is transferred between jobs with **1-day** artifact retention and published as GitHub Release assets only after checks pass. The content selection remains slim: the same eight retained tables, 224 selected columns and explicit indexes. No SQL or PostgreSQL export is added.

**Security and limitations:** Scheduled Actions executions may be delayed or disabled by GitHub after prolonged inactivity. The profile intentionally rejects unexpected upstream schema changes; an update requiring a new profile must be reviewed rather than silently dropping fields. For upstream provenance, copyright notices and licensing scope, read [third-party notices](THIRD_PARTY_NOTICES.md).

- Checksum mismatch: stop. Do not replace the expected hash with the calculated one; official daily files may change during a download. Fetch a fresh matching official pair and verify again.
- Schema mismatch: inspect the complete upstream inventory and review a new profile. Never auto-accept unknown columns.
- Orphan/duplicate/integrity failure: preserve the report and investigate the source or transformation; do not bypass validation.
- Existing directory: use a new versioned output path, or rerun with identical inputs for a fully verified reuse.
- No space/timeout: provide more temporary disk or time. Failed staging directories are cleaned; source archives remain untouched.

## Source and attribution

**Powered by [MTGJSON](https://mtgjson.com/).** This is an independent, unofficial community project, not affiliated with or endorsed by MTGJSON or Wizards of the Coast.

The converter uses the official MTGJSON `AllPrintings` dataset; its source version and checksums are recorded in each Release manifest. The repository's [MIT license](LICENSE) covers our own converter code. Upstream copyright and other data rights remain with their respective owners. See the [MTGJSON license](https://mtgjson.com/license/), the bundled [MTGJSON MIT notice](MTGJSON_LICENSE.txt) and our [third-party notices](THIRD_PARTY_NOTICES.md).
