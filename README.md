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
  --profile profiles/v2.json --output-dir output \
  --tool-commit "$(git rev-parse HEAD)" --report evidence/build.json
```

Outputs include a version-specific `.sqlite`, `.sqlite.xz`, archive SHA-256 sidecar, provenance manifest, validation report and full upstream schema/count inventory. The build verifies the archive **before** decompression, prepares in a temporary directory, and exposes the package only after validation and compression succeed. Reports must live outside the package and must not alias inputs.

For a checksum-only upstream check, use `download --previous-sha256 <prior-official-digest>` with the other download arguments; `UNCHANGED` skips the archive download. Repeat the same build command to detect unchanged upstream/profile/tool inputs in an existing package. Existing packages are rechecked against the verified source projection and their compressed/database bytes before returning `UNCHANGED`. A changed input/profile/tool requires a new output directory. Nothing is silently overwritten.

For independent validation, find the version-specific output filename in `output/manifest.json`:

```bash
python slim.py validate --database output/AllPrintings-slim-VERSION-profile-2.sqlite \
  --source downloads/AllPrintings.sqlite --profile profiles/v2.json \
  --report evidence/validation.json
```

All commands write JSON reports and return nonzero on failure. A protected report-path collision returns a JSON error on stdout without writing that path. Without `--source`, validation checks the expected schema, SQLite integrity, identity keys and relationships; with `--source`, it additionally compares the count and deterministic logical digest of every projected row, including duplicate multiplicity and NULLs.

## Profile v2 policy

The explicit [profile](profiles/v2.json) pins the complete official SQLite DDL observed for MTGJSON `5.3.0+20261112`. It rejects added, removed or changed tables, columns, indexes, views and triggers, including new fields in tables that would otherwise be omitted. A future schema change requires inventory, human review, a new versioned profile and tests. The converter supports the unconstrained source tables pinned here; it rejects new source constraints rather than silently losing them.

| Area | Policy |
| --- | --- |
| Cards/tokens | Keep every row and language; retain UUIDs, layouts, face IDs, names, rules, printed text/types where present, game characteristics and flags listed explicitly in the profile |
| Printed names | Preserve `printedName` and `facePrintedName` exactly, including NULLs; token source has neither column |
| Identifiers/legalities/rulings | Retain every column and row |
| Foreign card data | Exclude the entire `cardForeignData` table, its indexes and its output relationship |
| Sets/meta | Retain every column and row |
| Removed tables | cardForeignData, purchase URLs, sealed products, booster collation, set decks/translations and token product packaging |
| Removed columns | Explicit cosmetic/commercial/analytics fields, such as artist, flavor text, finish, frame, promotional details, SKU/source products and rankings; see profile and schema comparison |
| Indexes | Retain source indexes whose table and columns remain; add unique indexes for identity keys; reject null/empty keys |
| Relationships | Check card identifiers/legalities/rulings against cards, token identifiers against tokens, cards against set codes, tokens against **tokenSetCode** |

English-only filtering is **not** performed. Read-only source analysis found 2,638 non-English card printings and 35 Japanese tokens, all with distinct printing IDs. Eight non-English cards lack an English Oracle-ID peer, and thirteen names do not occur among English card records. These are not expendable translation-table rows. Printed names and localized printed text remain intact; the separate `cardForeignData` table is removed. See [language policy and evidence](docs/language-policy-v2.md). Serialized upstream fields are preserved as stored; this tool does not reinterpret JSON/boolean strings, normalize names, merge faces or infer missing rules. Slimming is a projection, not a data correction.

The historical `AllPrintings_slim_07Nov.sqlite.xz` is a separate reference (version `5.3.0+20261107`, recorded SHA-256 `9bc865c411a142801812e3df0d0ad1aed5cc792c055205592851b4b66c968af1`). It is not an upstream input or an equivalent output. Profile v2 omits foreign card data, as does that reference, but uses different selected columns, ordering and indexes. The previous profile v1 (available in Git history) included foreign card data and produced a 73,214,008-byte XZ archive from this source. No 45 MB size target or historical byte equality is promised.

The complete upstream source DDL still contains `cardForeignData` for schema auditing. Its presence in `source_schema` is not an output selection: no rows, table, indexes or validation relationship for it are generated. The source table must still match the reviewed schema.

## Reproducibility and provenance

Tables, rows and indexes are rebuilt in defined order, with a fixed page size and an SQLite `VACUUM`. XZ uses Python lzma preset 6. The manifest includes upstream URL/version/digests, profile version/digest, tool commit, output sizes/digests and Python/SQLite versions. Byte reproducibility is tested in the same runtime; it is not guaranteed across SQLite/liblzma versions. Logical projection comparison is runtime-independent for the pinned SQLite scalar types. Timing and peak RSS appear in the build report rather than the deterministic database.

## Automation and troubleshooting

The workflow runs fixture tests on PR updates. Real-data preparation is **manual only** (`workflow_dispatch`), with read-only repository permissions, per-ref concurrency and a timeout. Only JSON evidence is uploaded as an Actions artifact. There is no schedule, Release action, dataset upload or repository write permission. An optional manual input `previous_upstream_sha256` (from a previously successful manifest) compares the current official checksum and skips the download/build when unchanged. This is an upstream-change check, not revalidation of a prior dataset. Omit it when testing a new profile or tool version. Without that input, hosted runs rebuild on their fresh disks; local package reuse performs full revalidation.

- Checksum mismatch: stop. Do not replace the expected hash with the calculated one; official daily files may change during a download. Fetch a fresh matching official pair and verify again.
- Schema mismatch: inspect the complete upstream inventory and review a new profile. Never auto-accept unknown columns.
- Orphan/duplicate/integrity failure: preserve the report and investigate the source or transformation; do not bypass validation.
- Existing directory: use a new versioned output path, or rerun with identical inputs for a fully verified reuse.
- No space/timeout: provide more temporary disk or time. Failed staging directories are cleaned; source archives remain untouched.

## Attribution and licensing

**Powered by [MTGJSON](https://mtgjson.com/).** Independent community project; not affiliated with or endorsed by MTGJSON or Wizards of the Coast.

MTGJSON's [license](https://mtgjson.com/license/) and [brand conditions](https://mtgjson.com/brand-assets/) apply to its materials. This project uses text credit, without copying a logo. Official brand assets must remain unmodified and must not imply endorsement.

The MIT [LICENSE](LICENSE) covers original project code and documentation, not independent rights to all third-party card content. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Public dataset publication requires a separate redistribution-rights review and explicit authorization; this task does not establish legal clearance.
