# MTGJSON-slim

Independent community tooling for creating smaller, validated datasets from official [MTGJSON](https://mtgjson.com/) downloads.

> **Project status: planning / not yet implemented.** There is no working converter, automated release pipeline, or downloadable slim dataset in this repository yet.

## Scope

- Download official MTGJSON archives and verify their published checksums before processing.
- Initially support `AllPrintings.sqlite.xz`; consider JSON support only after SQLite conversion is verified.
- Apply an explicit, versioned slimming profile while preserving essential card identities and relationships.
- Validate SQLite integrity, expected schema, and card/identifier relationships; fail closed on unknown schema changes.
- Publish versioned compressed outputs and SHA-256 checksums as GitHub Release assets **only after** end-to-end tests and a separate redistribution-rights review.

This project does **not** build decks, run AI models, implement an MCP server, or rebuild the full MTGJSON upstream dataset.

## Planned release safeguards

A future workflow should check the upstream checksum for changes, download and verify the upstream archive, run a reproducible slim conversion, validate its output, and publish only on success. Releases should be immutable and should never silently replace a prior snapshot. Large generated databases belong in Release assets, **not** Git history.

The historical `AllPrintings_slim_07Nov.sqlite.xz` file is a reference artifact, **not** a published asset of this repository. Its recorded SHA-256 is `9bc865c411a142801812e3df0d0ad1aed5cc792c055205592851b4b66c968af1`. Matching this checksum is not expected for future upstream versions.

## MTGJSON attribution and brand assets

**Powered by [MTGJSON](https://mtgjson.com/)**

MTGJSON offers [official brand assets](https://mtgjson.com/brand-assets/) for attribution. Their conditions require that assets are **not modified** and **not used to imply MTGJSON endorsement**. This repository currently uses a text credit rather than redistributing a logo. If a logo is added later, use the official unaltered asset and retain this disclaimer.

**Independent community project. Not affiliated with or endorsed by MTGJSON or Wizards of the Coast.**

## Licensing and third-party content

The repository's MIT `LICENSE` covers original project code and documentation. It does not independently grant rights to Wizards of the Coast card text, trademarks, or other third-party content. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Publication of transformed datasets remains subject to a separate rights review.

## Development

No converter or GitHub Actions release workflow is implemented yet. The first implementation milestone is a reproducible SQLite-only conversion and a verified comparison against the historical slim snapshot, submitted through a pull request.
