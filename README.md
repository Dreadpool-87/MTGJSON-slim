# MTGJSON-slim

Independent, standard-library Python tooling for creating smaller, verified SQLite datasets from official [MTGJSON](https://mtgjson.com/) downloads.

**Development preview.** Local preparation is implemented. Public dataset distribution is disabled. No automatic or draft Release is created.

## Requirements and use

Python 3.11+ on Linux, SQLite (bundled with Python), sufficient local disk space for the source, temporary files and output. No pip dependencies. Run from a clean checkout at the exact tool commit recorded in the manifest:

```bash
python -m unittest discover -s tests -v
python slim.py download --directory downloads --report evidence/download.json
python slim.py inventory --database downloads/AllPrintings.sqlite --report evidence/source.json
```

`download` retrieves the compressed official SQLite archive and verifies its matching official SHA-256 before accepting it. It does not decompress it. The optional inventory command above requires an already decompressed source; use `xz -dk downloads/AllPrintings.sqlite.xz` after successful verification, or rely on the build's automatic source inventory.

```bash
python slim.py build \
  --archive downloads/AllPrintings.sqlite.xz \
  --sha256 "$(cat downloads/AllPrintings.sqlite.xz.sha256)" \
  --profile profiles/v2_2.json --output-dir output \
  --tool-commit "$(git rev-parse HEAD)" --report evidence/build.json
```

Outputs include a version-specific `.sqlite`, `.sqlite.xz`, archive SHA-256 sidecar, provenance manifest, validation report and full upstream schema/count inventory. The build verifies the archive **before** decompression, prepares in a temporary directory, and exposes the package only after validation and compression succeed. Reports must live outside the package and must not alias inputs.

For a checksum-only upstream check, use `download --previous-sha256 <prior-official-digest>` with the other download arguments; `UNCHANGED` skips the archive download. Repeat the same build command to detect unchanged upstream/profile/tool inputs in an existing package. Existing packages are rechecked against the verified source projection and their compressed/database bytes before returning `UNCHANGED`. A changed input/profile/tool requires a new output directory. Nothing is silently overwritten.

For independent validation, find the version-specific output filename in `output/manifest.json`:

```bash
python slim.py validate --database output/AllPrintings-slim-VERSION-profile-2.2.sqlite \
  --source downloads/AllPrintings.sqlite --profile profiles/v2_2.json \
  --report evidence/validation.json
```

All commands write JSON reports and return nonzero on failure. A protected report-path collision returns a JSON error on stdout without writing that path. Without `--source`, validation checks the expected schema, SQLite integrity, identity keys and relationships; with `--source`, it additionally compares the count and deterministic logical digest of every projected row, including duplicate multiplicity and NULLs.

## Current SQLite data profile

The current [profile](profiles/v2_2.json) selects the fields, tables and lookup indexes preserved from official MTGJSON SQLite data. It pins the complete upstream schema observed for MTGJSON `5.3.0+20261113` and **fails closed** if MTGJSON adds, removes or changes its schema. Changes require an explicit profile review rather than silent data loss.

The output contains **8 tables, 227 columns and 20 explicit indexes**. It preserves every selected record, NULL, face relationship, card printing and language, including printed/original names and text. There is no English-only filter or card-type exclusion.

| Area | Current policy |
| --- | --- |
| Cards and tokens | Keep identities, set/collector numbers, names, Oracle and printed text, mana/type information, multiple faces, relationships, flags, printing and artwork/reference metadata |
| External identifiers, legalities and rulings | Keep all selected external IDs, per-format legality information and card-linked rulings |
| Sets and source metadata | Keep codes, set identities, dates, language metadata, source version/date and token-set links |
| Removed data | Omit localized translation table `cardForeignData`, set-name translations, product/purchase/booster/deck-list tables and six packaging-related card/token fields |
| Source safety | Verify the official source checksum, pin the upstream schema and reject missing required fields, unknown schema changes or broken relationships |
| Lookup policy | Use verified UUID/code identity indexes and non-unique Scryfall printing/Oracle-ID indexes where multi-face records share external IDs |

Every retained value is copied directly from the verified source; no fuzzy matching, translation, Oracle-text reconstruction, rules inference or card-strength claims are added. For exact selections, see the [complete current SQLite data inventory](docs/PROFILE_2_2_DATA_INVENTORY.md).

### Exact data retention and removal

For an **exhaustive, table-by-table and field-by-field list** of what is kept and what is removed, read **[Profile 2.2 — retained and omitted SQLite data](docs/PROFILE_2_2_DATA_INVENTORY.md)**. It is checked against the actual versioned profile, not an approximate description.

From 20 source tables, the output retains 8 and omits 12. The complete `cardForeignData` and `setTranslations` tables and sales, sealed-product, booster, deck-list and token-product tables are excluded. Within `cards` and `tokens`, the only source fields dropped are `boosterTypes`, `skuIds` and `sourceProducts` (three fields per table, six total). Every field of the six other retained tables remains. Original non-English physical printing records and printed names are **not** removed. Schema pinning still checks all omitted upstream tables for drift.

**Verification status:** two full local reproducible builds passed, plus a separate [real-data GitHub-hosted acceptance run](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43516913604) where both the tests and real-data build jobs succeeded. Its official source checksum matched the local source. The raw SQLite/XZ hashes differ between local and GitHub runtimes, so cross-runtime byte reproducibility is **not claimed**; source-selected logical table contents matched in the preserved evidence. See [Profile 2.2 acceptance and limitations](docs/acceptance-profile-2.2.md).

A weekly GitHub Actions verification is configured for **Tuesday at 07:00 Europe/Brussels**; it becomes active when the workflow change is merged to the default branch. **No public database Release or publication is enabled.**

## Query audit

```bash
python benchmarks/query_audit.py --database path/to/database.sqlite \
  --cases cases.json --create-cases --report benchmark.json --repeats 5
```

Use the same saved case file for every compared database. The audit records exact SQL/parameters, result counts/digests, plans for every sample, five warm-cache timing batches and medians, and per-index dbstat footprints. Missing footprint capability is reported as null plus an error, never as zero bytes. These are sampled lookup workloads with full result retrieval, not whole-database latency promises or cold-cache tests. Oracle cohorts include singleton, moderate and high-fanout IDs; printing samples include singleton and shared multi-face IDs. Unknown-ID cases are explicitly synthetic. No personal collection is required.

These are reproducible **sampled** query measurements, not a guarantee that every lookup is faster. Read the [current acceptance report](docs/acceptance-profile-2.2.md) for actual timings and limitations.

## Reproducibility and provenance

Tables, rows and indexes are rebuilt in defined order, with a fixed page size and an SQLite `VACUUM`. XZ uses Python lzma preset 6. The manifest includes upstream URL/version/digests, profile version/digest, tool commit, output sizes/digests and Python/SQLite versions. Byte reproducibility is tested in the same runtime; it is not guaranteed across SQLite/liblzma versions. Logical projection comparison is runtime-independent for the pinned SQLite scalar types. Timing and peak RSS appear in the build report rather than the deterministic database.

## Automation and troubleshooting

**Weekly schedule:** Every **Tuesday at 07:00** in `Europe/Brussels` (CET/CEST). The [GitHub Actions verification workflow](.github/workflows/verify.yml) uses `cron: '0 7 * * 2'` with a named timezone, not a fixed UTC offset. GitHub can delay the exact start time, and scheduled workflows run only from the default branch. A public repository's scheduled workflows may be disabled by GitHub after 60 days without repository activity; review the workflow status if updates stop.

**What runs:** Pull requests run the fixture tests only. On Tuesday, or when manually dispatched from Actions, the existing workflow runs the fixture tests, then verifies the official MTGJSON archive download and checksum, builds using the pinned profile, and validates the output. An upstream schema change, download/checksum error or failed validation **fails the job**. There is no automatic acceptance of a changed schema.

**Workload:** A scheduled run has no previous-build input or persistent checked-in baseline. It therefore normally performs **one official download and one complete build per week**, not a daily build. Because MTGJSON's official source SHA-256 can change when build metadata changes, a different checksum does **not** by itself prove important card content changed. An optional **manual** input, `previous_upstream_sha256`, can skip the download/build if the current official SHA-256 matches that supplied digest. Do not claim the scheduled workflow detects semantic card differences or avoids unnecessary builds; those features are not implemented.

**Outputs and retention:** Only JSON reports, source inventory, validation results and a provenance manifest are retained as a GitHub Actions artifact for **14 days**. The database and compressed database are **not** uploaded, released, committed or published. There is no persistent "latest database" in GitHub created by this workflow; a failed run cannot overwrite one. If long-term version history, semantic change reports, notifications, an automatic retry or distribution are needed, those require separate design and rights review.

**Security:** The workflow has read-only repository permissions, does not push to `main`, and has no public Release action or dataset artifact. The entire build uses temporary runner storage, with per-ref concurrency and bounded timeouts.

- Checksum mismatch: stop. Do not replace the expected hash with the calculated one; official daily files may change during a download. Fetch a fresh matching official pair and verify again.
- Schema mismatch: inspect the complete upstream inventory and review a new profile. Never auto-accept unknown columns.
- Orphan/duplicate/integrity failure: preserve the report and investigate the source or transformation; do not bypass validation.
- Existing directory: use a new versioned output path, or rerun with identical inputs for a fully verified reuse.
- No space/timeout: provide more temporary disk or time. Failed staging directories are cleaned; source archives remain untouched.

## Attribution and licensing

**Powered by [MTGJSON](https://mtgjson.com/).** Independent community project; not affiliated with or endorsed by MTGJSON or Wizards of the Coast.

The official [MTGJSON brand-assets policy](https://mtgjson.com/brand-assets/) says credit is appreciated but not mandatory. If future maintainers choose its official PNG/SVG logo, it **must not be altered or used to imply endorsement**. The repository currently uses text credit only, no downloaded logos. Read the [MTGJSON license](https://mtgjson.com/license/) and our detailed [third-party, brand, and distribution notices](THIRD_PARTY_NOTICES.md).

The MIT [LICENSE](LICENSE) covers our original project code and documentation; it is not blanket permission to republish Wizards of the Coast card text, artwork or all other third-party data. See the official [Wizards Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). Public database release automation needs a separate, recorded rights review and explicit authorization.

