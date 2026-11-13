# Profile v2 language reduction plan

Authoritative change request: remove cardForeignData entirely from the selected output, investigate other non-English data, and delete only demonstrably redundant language information. Continue existing PR #1 and branch; main and Releases remain untouched. Existing Drive brief remains applicable except where this newer request changes the output policy.

1. Reuse and reverify the exact official 5.3.0+20261112 archive used for v1 so size/hash/count comparisons isolate the profile change. Read-only SQL inventory identifies language-bearing fields, printing UUIDs, external IDs, English peers and unique names.
2. Add regression tests first: active profile excludes cardForeignData and its indexes/relations, omitted-source schema drift still fails, and language-specific printing identities/names/faces remain exact.
3. Replace the active v1 profile with version 2; keep the original source DDL for fail-closed auditing, but omit cardForeignData from output selection and relationships. Git history preserves v1; the active workflow and README use v2. Remove further language data only if query evidence proves it redundant without dropping printing identities or Oracle/face semantics.
4. Run the complete fixture suite. Publish a single implementation commit on the same branch before running two builds with the same source, profile, tool commit and runtime. Independently compare both outputs to source and v1, including schema, row counts, hashes, face links and language distributions.
5. Update current English documentation and the existing PR; save a separate Dutch v2 report and full evidence package in the designated Drive Test Results folder without replacing the v1 evidence. Mark hosted full-data Actions NOT EXECUTED if the default-branch dispatch constraint remains.

Implementation choice: no blind English-only row filter, UUID deduplication or language-column deletion. A matching Oracle ID is not proof that a separate printing UUID is expendable.

## Resumption adjustment

The original temporary data and incomplete builds were lost. Official upstream changed from 2026-11-12 to 2026-11-13. Only the source sets column order changed; an explicit name/type/constraint comparison reviewed this change for profile 2.1. Two 2.1 builds and a v1-selection control now use the same current source, while the verified prior Drive evidence remains the historical baseline. The active file is profiles/v2_1.json; old profile files are removed from the branch but preserved in Git history.

## Completed verification

Two profile 2.1 builds and the current-source v1-selection control completed successfully. Direct byte comparisons, full retained-row digests, schema/count comparisons, language/layout distributions and all face edges passed. See acceptance-profile-2.1.md. Delivery target for the new Dutch report and evidence package is the user-designated Drive folder, separately from the v1 results.
