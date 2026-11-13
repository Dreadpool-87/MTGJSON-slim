# Profile 2.2 information and index acceptance — 2026-11-13

**Local acceptance: GO.** All 191 verified 07Nov fields are retained, including 14 restored fields; all 2.1 data remains intact. The output has eight tables, 227 fields and 20 explicit indexes. cardForeignData remains absent. No consumer repository, main branch or Release is changed.

Tool commit: `a0bf438f790f88471554928f5ba96f9a98c787d2`. The full local fixture suite passes 33 tests. Actual initial CI run: https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43510051664 (33 tests, success). Full hosted data build is NOT EXECUTED; manual dispatch requires a workflow on the default branch, which remains untouched.

## Evidence of information preservation

- Verified actual 07Nov archive bytes and schema/indexes, including the non-unique `idx_cardIdentifiers_oracleid`. All historical UUIDs/set codes still exist in the new output.
- Source and output historical-field projections, all prior-2.1 field projections, NULL counts, exact language/layout distributions and twelve complex-layout/token examples match. All 10,938 face edges resolve.
- Two full builds use the same verified 13Nov archive, profile, tool commit and runtime. SQLite, XZ and manifests are identical; direct cmp and SHA-256 checks passed.
- Historical INT/NUM declarations and current INTEGER/BOOLEAN/DATE declarations have equivalent SQLite affinities. Source values are copied exactly; no rule/text/boolean/date reconstruction is performed. Cross-snapshot updates and list ordering differences are explicitly separated from conversion loss.

## Measured sizes

| Artifact | Historical 07Nov | Profile 2.1 | Profile 2.2 |
| --- | ---: | ---: | ---: |
| SQLite bytes | 227905536 | 261873664 | 282390528 |
| XZ bytes | 45020048 | 39117432 | 49212160 |

- SQLite SHA-256: `9c9f6adfda843d095e0e3c79deb637feb22d8611921df018922571ec8bf8cc18`
- XZ SHA-256: `5e9cc09d7ece7e30e5e52549bf78559b27eee7800551d7bef9d9cd8a95edf4d2`
- Source XZ SHA-256: `628ff982b1a5b764f4b98dfca796fc46c4fd509cf2f4a01077ae01b5092fe42e`

## Query measurements

Twenty-one deterministic sampled workloads were run with five repeated warm-cache batches and complete result retrieval. The same parameters were used on actual 07Nov, 2.1, 2.2 and a same-data 2.2 copy carrying the 2.1 index set. Every current-source result digest is identical. Different historical snapshots are context, not isolated causal performance comparisons.

| Workload | 2.1 us | 2.2 us | Same-data old-index us |
| --- | ---: | ---: | ---: |
| csv_name_set_number | 600.93 | 5.15 | 970.56 |
| scryfall_printing | 8957.93 | 7.58 | 10397.86 |
| oracle_printings | 9481.10 | 45.02 | 10203.39 |
| legality_ruling_join | 9.39 | 9.25 | 10.64 |
| name | 6.39 | 6.13 | 6.27 |
| printed_name | 134419.97 | 5.27 | 24184.90 |
| face_printed_name | 133189.54 | 5.23 | 23979.00 |
| set_number | 325.14 | 5.05 | 559.33 |
| set_only | 97.23 | 119.40 | 101.47 |
| token_printing | 3043.29 | 7.17 | 3068.24 |
| token_oracle | 591.82 | 7.02 | 627.58 |
| token_name | 5.22 | 5.17 | 5.42 |
| token_set_number | 23.66 | 5.12 | 69.96 |
| set_token_code | 60.70 | 4.60 | 65.43 |
| set_name | 4.48 | 4.57 | 4.57 |
| face_lookup | 5.37 | 5.54 | 8.13 |
| any_exact_name | 140344.25 | 6.19 | 28780.50 |
| token_set_only | 16.40 | 20.59 | 14.50 |
| missing_scryfall | 9065.06 | 3.88 | 9196.19 |
| missing_oracle | 9133.94 | 3.91 | 9000.98 |
| missing_csv | 4.16 | 4.16 | 3.92 |

Large gains in exact Scryfall/Oracle/printed-name/collector routes are supported by plans moving from scans to searches. This is not a promise that every query gets faster. Card set-only and token set-only were slower in the main run; alternating sensitivity runs retained a smaller card difference and a measurable token difference. Correctness/result digests remain identical. The policy favors the measured identity/collector routes, retains every historical index route, and documents the tradeoffs.

| Dataset | Indexes | Index bytes | Duplicate exact-key groups |
| --- | ---: | ---: | ---: |
| historical_07Nov | 10 | 38981632 | 0 |
| profile_2_1 | 18 | 51007488 | 6 |
| profile_2_2 | 20 | 49741824 | 0 |
| same_data_old_indexes | 18 | 51064832 | 6 |

All ten historical index routes/names are retained. Six ordinary+UNIQUE duplicate key groups from 2.1 are removed. Scryfall IDs are non-unique in actual multi-face data, so their indexes are non-unique; UUID/code invariants are explicitly UNIQUE. Card setCode and setCode+number overlap intentionally for different measured queries; there are no duplicate exact keys. Missing dbstat capability reports null/error, never zero bytes.

The field/index gapmatrix, plans for every sample, timing arrays, counts, footprints, negative tests, source/value comparisons and exact commands are delivered in the new compact Drive evidence package. Previous evidence/source snapshots remain unchanged; no duplicate full source archive is created.
