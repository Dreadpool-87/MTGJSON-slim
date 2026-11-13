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

## Profile v2.2 information and index policy

The explicit [profile](profiles/v2_2.json) pins the complete official SQLite DDL observed for MTGJSON `5.3.0+20261113`. It rejects added, removed or changed tables, columns, indexes, views and triggers, including new fields in tables that would otherwise be omitted. A future schema change requires inventory, human review, a new versioned profile and tests. The converter supports the unconstrained source tables pinned here; it rejects new source constraints rather than silently losing them.

Profile 2.2 preserves all **191 historical fields across eight tables**, restores the 14 fields missing from 2.1, retains its useful additions, and conservatively keeps further source card-level printing/artwork/reference metadata. See the [field and index decisions](docs/information-index-plan.md), [fixed historical contract](contracts/07nov-fields.json), and the separately delivered complete gapmatrix.

| Area | Policy |
| --- | --- |
| Cards/tokens | Keep every printing, face, language and NULL. Preserve canonical/printed/original text, identity/layout characteristics, historical flags, finishes, dates and rankings; useful printing/artwork/frame/promo/watermark metadata remain available |
| Identifiers/legalities/rulings/sets/meta | Preserve all historical fields and all existing 2.1 fields/rows |
| Excluded data | cardForeignData and setTranslations; sales/product/booster tables; card/token SKU, source-product and booster-packaging fields |
| Historical contract | Numeric profiles 2.2 and later must match the independent 07Nov contract file; removing/rewriting the embedded contract cannot disable it. Missing source fields or changed affinities fail before conversion |
| SQLite type names | Historical CTAS aliases INT/NUM and source INTEGER/BOOLEAN/DATE have equivalent SQLite affinities; exact source values and NULLs are copied, not translated or cast |
| Identity indexes | One actual UNIQUE index per UUID/code invariant; no duplicate ordinary+UNIQUE exact keys |
| Printing/Oracle indexes | Explicit non-unique Scryfall and Oracle ID indexes, for cards and tokens; multi-face records share IDs and are never merged |
| Name/CSV routes | Exact name, printedName, facePrintedName and setCode/collector-number lookups. Keep the historical cards.setCode index after measuring the composite-only regression |
| Source audit | Pin all original source DDL, including omitted tables; upstream schema drift remains an error |

No English-only filter, fuzzy matching, invented translation or rules inference is performed. Printed/reference/flavor metadata stays separate from Oracle rules. Popularity metrics remain snapshot metadata, not a strength guarantee. The historical 07Nov bytes are a verified minimum field/index reference, not an output-byte target. Profile 2.1 remains unchanged and usable for historical reproduction.

### Exact data retention and removal

For an **exhaustive, table-by-table and field-by-field list** of what is kept and what is removed, read **[Profile 2.2 — retained and omitted SQLite data](docs/PROFILE_2_2_DATA_INVENTORY.md)**. It is checked against the actual versioned profile, not an approximate description.

From 20 source tables, the output retains 8 and omits 12. The complete `cardForeignData` and `setTranslations` tables and sales, sealed-product, booster, deck-list and token-product tables are excluded. Within `cards` and `tokens`, the only source fields dropped are `boosterTypes`, `skuIds` and `sourceProducts` (three fields per table, six total). Every field of the six other retained tables remains. Original non-English physical printing records and printed names are **not** removed. Schema pinning still checks all omitted upstream tables for drift.

**Verification status:** two full local reproducible builds passed, plus a separate [real-data GitHub-hosted acceptance run](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43516913604) where both the tests and real-data build jobs succeeded. Its official source checksum matched the local source. The raw SQLite/XZ hashes differ between local and GitHub runtimes, so cross-runtime byte reproducibility is **not claimed**; source-selected logical table contents matched in the preserved evidence. See [Profile 2.2 acceptance and limitations](docs/acceptance-profile-2.2.md).

No automatic weekly schedule, public release, publication or approval to merge is implied by this result.

## Query audit

```bash
python benchmarks/query_audit.py --database path/to/database.sqlite \
  --cases cases.json --create-cases --report benchmark.json --repeats 5
```

Use the same saved case file for every compared database. The audit records exact SQL/parameters, result counts/digests, plans for every sample, five warm-cache timing batches and medians, and per-index dbstat footprints. Missing footprint capability is reported as null plus an error, never as zero bytes. These are sampled lookup workloads with full result retrieval, not whole-database latency promises or cold-cache tests. Oracle cohorts include singleton, moderate and high-fanout IDs; printing samples include singleton and shared multi-face IDs. Unknown-ID cases are explicitly synthetic. No personal collection is required.

Compare different snapshots only as context. The final audit also compares 2.2 with a same-data variant carrying 2.1 indexes, so index effects can be separated from restored/wider data. More indexes do not imply every query gets faster; detailed regressions and tradeoffs belong in the report.

## Reproducibility and provenance

Tables, rows and indexes are rebuilt in defined order, with a fixed page size and an SQLite `VACUUM`. XZ uses Python lzma preset 6. The manifest includes upstream URL/version/digests, profile version/digest, tool commit, output sizes/digests and Python/SQLite versions. Byte reproducibility is tested in the same runtime; it is not guaranteed across SQLite/liblzma versions. Logical projection comparison is runtime-independent for the pinned SQLite scalar types. Timing and peak RSS appear in the build report rather than the deterministic database.

## Automation and troubleshooting

The workflow runs fixture tests on PR updates. Real-data preparation is **manual only** (`workflow_dispatch`), with read-only repository permissions, per-ref concurrency and a timeout. Only JSON evidence is uploaded as an Actions artifact. There is no schedule, Release action, dataset upload or repository write permission. **Important:** GitHub requires a `workflow_dispatch` workflow to exist on the repository's default branch for normal manual execution; while this PR remains unmerged, the manual full-data button is not available from `main`. The successful hosted run above used a temporary PR-only trigger that was removed immediately after acceptance. A future weekly `schedule` also runs on the default branch and must be reviewed in a **separate PR**; it is not part of profile-2.2 acceptance. An optional manual input `previous_upstream_sha256` (from a previously successful manifest) compares the current official checksum and skips the download/build when unchanged. This is an upstream-change check, not revalidation of a prior dataset. Omit it when testing a new profile or tool version. Without that input, hosted runs rebuild on their fresh disks; local package reuse performs full revalidation.

- Checksum mismatch: stop. Do not replace the expected hash with the calculated one; official daily files may change during a download. Fetch a fresh matching official pair and verify again.
- Schema mismatch: inspect the complete upstream inventory and review a new profile. Never auto-accept unknown columns.
- Orphan/duplicate/integrity failure: preserve the report and investigate the source or transformation; do not bypass validation.
- Existing directory: use a new versioned output path, or rerun with identical inputs for a fully verified reuse.
- No space/timeout: provide more temporary disk or time. Failed staging directories are cleaned; source archives remain untouched.

## Attribution and licensing

**Powered by [MTGJSON](https://mtgjson.com/).** Independent community project; not affiliated with or endorsed by MTGJSON or Wizards of the Coast.

The official [MTGJSON brand-assets policy](https://mtgjson.com/brand-assets/) says credit is appreciated but not mandatory. If future maintainers choose its official PNG/SVG logo, it **must not be altered or used to imply endorsement**. The repository currently uses text credit only, no downloaded logos. Read the [MTGJSON license](https://mtgjson.com/license/) and our detailed [third-party, brand, and distribution notices](THIRD_PARTY_NOTICES.md).

The MIT [LICENSE](LICENSE) covers our original project code and documentation; it is not blanket permission to republish Wizards of the Coast card text, artwork or all other third-party data. See the official [Wizards Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). Public database release automation needs a separate, recorded rights review and explicit authorization.

The retained profile 2.1 explicitly reviews the 2026-11-13 upstream change: only the source `sets` column order changed; names/types/constraints remain equal. Retained output columns and order are unchanged. Earlier strict profiles reject this source as designed.
