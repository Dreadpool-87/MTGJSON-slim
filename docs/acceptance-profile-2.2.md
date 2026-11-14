# MTGJSON-slim — current profile 2.2 acceptance

**Historical status: technical acceptance PASS on the verified MTGJSON `5.3.0+20261113` source.** This report documents profile 2.2 as tested at the time; the [current README](../README.md) describes the active profile, scheduler and public Releases.

## Verified output

- Profile: [`profiles/v2_2.json`](../profiles/v2_2.json), SHA-256 `2f3755454c6626a9e35b6ee0289ed394b86b2cc22b208ac171d11b0a59cb11fc`.
- Input: official MTGJSON `AllPrintings.sqlite.xz`, SHA-256 `628ff982b1a5b764f4b98dfca796fc46c4fd509cf2f4a01077ae01b5092fe42e`.
- Output: **8 tables, 227 retained columns, 20 explicit indexes**, with no `cardForeignData` or `setTranslations` table.
- All rows and NULLs in the selected tables/columns match the verified official source. No language or card-layout filtering, card-face merging or invented translation.
- Verified SQLite integrity, unique UUID/set-code identity constraints, configured source relationships and **10,938 card-face links**. Named, printed and original text remain distinct; all sampled complex layouts, printing identities and token facts were checked.
- Exact table/field/index selection and 20-table source row-count inventory: [current data inventory](PROFILE_2_2_DATA_INVENTORY.md).

## Executed tests and complete builds

- **33 regression/fixture tests passed** locally and on GitHub.
- Two full **local builds** with identical source, profile, tool commit and runtime reproduced byte-for-byte matching output SQLite, XZ and deterministic manifests.
- Independent full-data [GitHub Actions run 43516913604](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43516913604) completed with `tests=success`, `real-data=success`: official archive download/checksum, full SQLite conversion and validation succeeded.
- The temporary PR-only hosted-build trigger was restored to **manual-only** after this acceptance run. [Subsequent CI 43517444042](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43517444042) passed following that restoration.
- Validation evidence is preserved in the [designated Drive folder](https://drive.google.com/file/d/1TsaBRve9Kt0YgVIZBVtB5NJfqmSVMtvq/view). This is necessary because GitHub Actions artifacts have limited retention.

| Output artifact | Local bytes | Local SHA-256 | GitHub-hosted bytes | GitHub-hosted SHA-256 |
| --- | ---: | --- | ---: | --- |
| SQLite | 282,390,528 | `9c9f6adfda843d095e0e3c79deb637feb22d8611921df018922571ec8bf8cc18` | 282,390,528 | `c0bd615eeb6dad88b884ce2d52667503fe099d535ac3d62b794b9016bade4dfc` |
| XZ | 49,212,160 | `5e9cc09d7ece7e30e5e52549bf78559b27eee7800551d7bef9d9cd8a95edf4d2` | 49,264,112 | `3891bdc3f441c069911e9c0876cd4b5f0b75906f83ffcee39c6e5b3a5ba52435` |

The local and GitHub **raw hashes are not identical** because their runtimes differ (local Python 3.12.14/SQLite 3.53.1, hosted Python 3.12.16/SQLite 3.45.1). The full projected-table **logical hashes and row counts matched**. Byte-for-byte reproducibility is established only within the same pinned runtime, not across different runtimes.

Hosted converter elapsed time: approximately **169 seconds**; peak RSS: **143,232 KiB**.

## Query and index verification

The 20 verified indexes include **UNIQUE** UUID/code identity indexes and **non-unique** Scryfall and Oracle ID indexes for printing/face records that can share an external ID. The exact names, columns, uniqueness and intended use are enumerated in [the data inventory](PROFILE_2_2_DATA_INVENTORY.md).

A set of **21 deterministic SQL workloads** was measured using five warm-cache batches each, complete result retrieval, saved parameters, query plans and result digests. Selected current-profile median batch means (microseconds per lookup):

| Query | Profile 2.2 (µs) |
| --- | ---: |
| CSV name/set/collector number | 5.15 |
| Scryfall printing ID | 7.58 |
| Scryfall Oracle ID printings | 45.02 |
| Printed card name | 5.27 |
| Token printing ID | 7.17 |
| Card set code only | 119.40 |
| Token set code only | 20.59 |

These are **sampled warmed-cache results**, not universal performance guarantees, cold-cache tests or complete game-rules validation. Some set-only lookup patterns remain relatively slow. An index does not automatically optimize every query.

## Independent review and maintenance boundaries

- A first documentation pass enumerated all source/output tables, selected columns, omitted tables/columns and index definitions directly from the committed profile.
- A second pass checked the published inventory against every profile entry, and compared actual SQLite structure/integrity and source/selected-table counts against the preserved hosted evidence. **Both checks passed**.
- Source credits, upstream licenses and independent-project status are recorded in [third-party notices](../THIRD_PARTY_NOTICES.md). The project uses text attribution only; it does not bundle third-party branding logos.
- This version pins a specific upstream schema; schema drift **stops the build for review**. Subsequent scheduler and Release work is documented in the [current README](../README.md).
- Successful source conversion is **not** proof that every downstream application's size limits, checksum pins or runtime constraints accept this database.

**Historical acceptance decision:** GO for the independently verified profile 2.2 converter output. This decision is limited to the original testing scope; current operations are documented separately.
