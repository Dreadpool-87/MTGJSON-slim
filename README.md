# MTGJSON-slim

Independent, standard-library Python tooling for creating smaller, verified SQLite datasets from official [MTGJSON](https://mtgjson.com/) downloads.

**Development preview.** Local conversion and weekly rebuild are implemented. A validated public Release pipeline exists but is **disabled until redistribution rights are reviewed and the maintainer explicitly enables it**. No dataset is public by default.

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

## Prepared distribution formats (public Release requires explicit authorization)

When distribution has been separately cleared and approved, **both** database variants must be available from the **same MTGJSON-slim repository Release**. No second repository is needed:

| Planned asset | Purpose |
| --- | --- |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite` | Uncompressed, directly usable SQLite database |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite.sha256` | SHA-256 verification for the uncompressed database |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite.xz` | Identical SQLite content compressed with XZ for smaller downloads |
| `AllPrintings-slim-<source-version>-profile-2.3.sqlite.xz.sha256` | SHA-256 verification for the compressed database |
| `manifest.json` | Source version/checksum, profile version, output sizes/hashes, tooling and runtime provenance |
| `MTGJSON_LICENSE.txt` | Required upstream MIT copyright and license notice when release redistribution is authorized |

The converter **already produces both database files locally**. The build now also emits and checks a checksum sidecar for **each** database variant. A compressed file must decompress byte-for-byte to its corresponding `.sqlite`; either file must contain the **same slim projection**: eight retained tables and the explicitly selected fields/indexes. Compression does not determine which data is excluded.

**Rights review (2026-11-14): NO-GO for public dataset redistribution.** See [the source-based distribution assessment and permission-request drafts](docs/DATA_REDISTRIBUTION_REVIEW_2026-11-14.md). MTGJSON's MIT notice does not by itself resolve Wizards' bulk card-text republication restrictions or third-party provenance. No permission requests have been sent and the release gate must remain disabled until written scope clarification and maintainer authorization.

**Distribution remains disabled by default.** GitHub Actions retains JSON evidence only unless the repository-level variable `MTGJSON_PUBLIC_DISTRIBUTION_APPROVED` is explicitly set to `true` **after** a documented redistribution-rights review (MTGJSON, Wizards and any other contributors). The variable is a publication gate, not itself proof of legal permission. No second repository is required. With authorization, the workflow transfers the verified SQLite and its lossless XZ copy and publishes both from the same Release; if authorization is absent, neither is uploaded as a public release candidate.

A `.sql` export is a text script for reconstructing a database, not a directly queryable SQLite file. `psql` is the PostgreSQL client and a `.psql` extension is not a universal database container. The project intentionally **does not** add SQL or PostgreSQL exports; they offer no clear benefit for the primary SQLite consumers and would add build/test complexity.

## Current SQLite data profile

The current [profile](profiles/v2_3.json) selects the fields, tables and lookup indexes preserved from official MTGJSON SQLite data. It pins the complete upstream schema observed for MTGJSON `5.3.0+20261113` and **fails closed** if MTGJSON adds, removes or changes its schema. Changes require an explicit profile review rather than silent data loss.

The output contains **8 tables, 224 columns and 20 explicit indexes**.

**Profile 2.3 consciously drops three non-gameplay columns** relative to 2.2: `cards.flavorText`, `tokens.flavorText` and `cards.isStorySpotlight`. Current rules (`cards.text`, `tokens.text`, `cardRulings.text`), printed/original rule text, alternative card names, identities, relationships and all indexes remain intact. The active 2.3 profile has its own **independent, locked main schema** in [`contracts/main-profile-2.3.json`](contracts/main-profile-2.3.json), covering all 224 selected columns, indexes, source schema and relationships. It **does not depend on** the historical 7 November list or profile 2.2. The historical `contracts/07nov-fields.json` is kept unmodified for archived profile 2.2 and regression checks; it is not a user agreement. Older profile 2.2 remains reproducible. Excluding narrative text does **not** automatically authorize redistribution of the remaining MTG card texts.

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

The scheduled workflow is configured for **Tuesday at 07:00 Europe/Brussels**. It always builds a fresh verified SQLite and derives the XZ archive from that SQLite. Public release publishing remains disabled until rights approval.

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

**Change detection:** If public distribution is authorized, the newest successful published Release's manifest is compared with the newly built logical fingerprint. It includes all **retained data tables except the upstream `meta` row**, plus resulting SQL schema and indexes. Therefore an MTGJSON date/version-only change **does not** create another Release. A change in card/printing/ruling/legality/set data or schema/indexes **does**. This is a deliberate logical comparison, not a raw SQLite/XZ byte comparison. Each week is rebuilt and revalidated regardless of whether it is eventually published.

**Safe distribution:** The normal build job has read-only repository permissions. A separate publishing job with write permission runs only after successful validation, meaningful changes and an explicit maintainer rights approval via repository variable `MTGJSON_PUBLIC_DISTRIBUTION_APPROVED=true`. It rechecks the uploaded package, creates a GitHub **draft Release** with exactly the raw SQLite, XZ, their two checksum files and a manifest, verifies that all five assets are present and **only then publishes** the Release. No existing stable Release is overwritten; if any step fails, the old latest Release stays available. A failed draft may require manual cleanup before retrying. The release comparison fails closed on an unreadable or incompatible previous manifest.

**Outputs and retention:** Without authorization, only verification JSON and the manifest are kept as GitHub Actions artifacts for **14 days**; no database is exposed by the workflow. After approval, a changed verified database is transferred temporarily between jobs with a **1-day** retention and published as GitHub Release assets. The content selection remains slim: the same eight retained tables, 224 selected columns and explicit indexes. No SQL or PostgreSQL export is added.

**Security and limitations:** Scheduled Actions executions may be delayed or disabled by GitHub after prolonged inactivity. The profile intentionally rejects unexpected upstream schema changes; an update requiring a new profile must be reviewed rather than silently dropping fields. This workflow does not independently decide whether redistribution is lawful. No public Release can occur until the maintainer records that decision and enables the variable.

- Checksum mismatch: stop. Do not replace the expected hash with the calculated one; official daily files may change during a download. Fetch a fresh matching official pair and verify again.
- Schema mismatch: inspect the complete upstream inventory and review a new profile. Never auto-accept unknown columns.
- Orphan/duplicate/integrity failure: preserve the report and investigate the source or transformation; do not bypass validation.
- Existing directory: use a new versioned output path, or rerun with identical inputs for a fully verified reuse.
- No space/timeout: provide more temporary disk or time. Failed staging directories are cleaned; source archives remain untouched.

## Attribution and licensing

**Powered by [MTGJSON](https://mtgjson.com/).** Independent community project; not affiliated with or endorsed by MTGJSON or Wizards of the Coast.

The official [MTGJSON brand-assets policy](https://mtgjson.com/brand-assets/) says credit is appreciated but not mandatory. If future maintainers choose its official PNG/SVG logo, it **must not be altered or used to imply endorsement**. The repository currently uses text credit only, no downloaded logos. Read the [MTGJSON license](https://mtgjson.com/license/) and our detailed [third-party, brand, and distribution notices](THIRD_PARTY_NOTICES.md).

The MIT [LICENSE](LICENSE) covers our original project code and documentation; it is not blanket permission to republish Wizards of the Coast card text, artwork or all other third-party data. See the official [Wizards Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). Public database release automation needs a separate, recorded rights review and explicit authorization.

