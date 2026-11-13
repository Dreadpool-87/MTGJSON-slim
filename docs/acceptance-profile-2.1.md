> Historical profile **2.1** acceptance at the time it was tested. Its `NOT EXECUTED` hosted-build statement is preserved as contemporaneous evidence; the later [v2.2 GitHub-hosted build has passed](acceptance-profile-2.2.md). This page does not describe the currently selected profile.

# Profile 2.1 acceptance — 2026-11-13

The two newly completed full builds use official MTGJSON `5.3.0+20261113`, the same profile file, tool commit and runtime. The original unfinished scratch builds were lost; their success is not assumed. Official upstream had changed, so a third v1-selection control was built on the same current source to isolate the profile change. Original v1 results remain a separate, verified Drive evidence baseline.

Tool commit: `34830840b430670092419e89335f0332f0c352e8`. Full local suite: **21 passed**. Hosted PR fixture run: https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43498907584 (21 passed). Full hosted data preparation remains NOT EXECUTED; workflow_dispatch requires the workflow on the default branch, which must remain unchanged in this task.

| Artifact | Previous v1 (12Nov) | V1 control (13Nov) | Profile 2.1 (13Nov) |
| --- | ---: | ---: | ---: |
| SQLite bytes | 457183232 | 457129984 | 261873664 |
| XZ bytes | 73214008 | 73179184 | 39117432 |

Same-source XZ saving: **46.5457%**. Same-source SQLite saving: **42.7135%**. All retained logical row digests and schema objects equal the control. The only output-schema removal is `cardForeignData` and its two indexes. No retained rows or columns are filtered.

- SQLite SHA-256: `cf8845f3e9754486ab1c10a895b653589cfc4156e367d7119e8fb31b341e7120`
- XZ SHA-256: `78d8a40741af1e5fcff9cafe93ee15226abfe7a9ccd75f2389e67e624844f17d`
- Official source archive SHA-256: `628ff982b1a5b764f4b98dfca796fc46c4fd509cf2f4a01077ae01b5092fe42e`
- Profile SHA-256: `25d80a649d0c27e337c1c27ecf93ead43b2684ffee3cc349a5f36b1aaaed05e4`

Both SQLite and XZ pairs passed direct `cmp` and digest comparisons; both manifests are also identical. Independent checks found zero configured orphans, exact language/layout distributions, exact retained fields in twelve complex-layout/token examples, and all 10,938 face links resolved. 2,718 non-English cards and 35 Japanese tokens remain, including eight card records without an English Oracle peer and thirteen names absent in English records. See [language-policy-v2.md](language-policy-v2.md).

The source schema changed only the `sets` column order; names/types/constraints were checked equal before explicitly pinning profile 2.1. The old schema was rejected with a nonzero exit. A full-archive one-byte tamper and five mandatory negative CLI fixtures were also rejected. Unknown future schema changes remain failures.

| Build | Wall seconds | Peak RSS KiB |
| --- | ---: | ---: |
| 2.1 one | 150.199 | 135024 |
| 2.1 two | 148.715 | 134952 |
| V1 control | 238.851 | 136508 |

The three processes overlapped. Wall times are observations under that load, not an isolated benchmark. No cross-runtime byte reproducibility guarantee is made.

Detailed SQL, source/old/current inventories, counts, digests, command exits, logs and manifests are delivered in the requested Test Results folder. Source DDL for omitted tables remains audit-only; no `cardForeignData` rows/table/indexes are in the selected profile output. No database is committed to Git, main is not modified, and no Release is created or published.
