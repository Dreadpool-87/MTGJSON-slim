# Verified SQLite slimming implementation plan

Goal: implement the authoritative 2026-11-13 Drive brief with Python standard library only.
Spec: https://docs.google.com/document/d/1WhdH8hfDKKfBVFL6Y-f0X_g4810QnhlaDrEsr7APHIA/edit

Architecture: verify the official compressed SQLite before decompression. Inventory its complete schema and counts, pin an explicit versioned profile, retain every language and identity/face field, and deterministically rebuild the selected tables. Validate the exact expected schema, integrity and relationships before compression and manifest creation. No release publishing code.

Constraints: English public content; one existing development branch/PR; main unchanged; no databases in Git; no private-repository writes; manual real-data Actions only; fixture tests on pull requests; evidence in the designated Drive Test Results folder.

## Tasks

- [x] Inventory official SQLite schema, indexes, foreign keys, counts, version and multi-face records; check checksum and tampered archive.
- [x] Write failing unittest cases for schema changes, corrupt input, invalid profiles, orphan relations, checksum mismatch, positive conversion and repeatability. Implement verification, inventory, conversion and validation in `slim.py`, with `profiles/v1.json`.
- [x] Add manual workflow with read-only permissions, concurrency and no publishing. Add provenance and version-specific packaging, unchanged detection and positive/negative tests.
- [x] Execute full real-data conversion twice, validate outputs, compare historical reference if accessible, measure resources. Review all changes and run full suite.
- [ ] Update existing PR #1, verify remote commit/main/releases/CI, and save Dutch report plus complete evidence in Drive.

## Review focus

Reject additional schema objects and altered constraints, not just missing columns. Reject null/duplicate identity keys and orphan children. Preserve all languages and face names. Never accept stale manifests as unchanged proof without validating input and existing outputs. Keep partial outputs separate and never overwrite source files.

## Decisions

Use existing PR #1 and its branch, because it remains open and already contains the required foundation. Use table/column reduction only after actual upstream inventory; no speculative schema or English-only filtering. Historical comparison is conditional on legitimate access, never a gate requiring access to private repositories.
