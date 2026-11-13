# Profile 2.2 — exact retained and omitted SQLite data

This is the **machine-checked field inventory** for the existing profile [`profiles/v2_2.json`](../profiles/v2_2.json), derived from the committed profile, not an attempt to reconstruct the database from memory.

- Pinned upstream source schema: MTGJSON `5.3.0+20261113` (source snapshot). A later upstream change **must** be reviewed and versioned; this inventory must then be regenerated and checked.
- Output: **8 tables, 227 retained columns, 20 explicit indexes**. The pinned upstream source has **20 tables**. All output rows, values and `NULL`s in the selected tables/columns are preserved from that same verified source; no filtering by language, printing, or card layout.
- Historical baseline: all **191 fields** in the verified 07 November slim database remain, including the 14 fields missing in profile 2.1. This does **not** mean 07 November and 13 November contain identical card data.
- Converter scope: authoritative source projection and integrity checks, **not** an AI model, MTG gameplay/rules engine, ownership tracker, deck strength evaluator, price service or dataset distribution service.
- The upstream `source_schema` pin still lists omitted objects for fail-closed source-drift checks. Listed in that pin **does not mean copied into the slim SQLite output**.

## Tables kept (all original rows, selected columns)

| Table | Fields | Purpose |
| --- | ---: | --- |
| `cards` | 78 | Physical printing/face identities, names, Oracle and printed metadata, types, mana, rules-related fields, relations and useful printing/art metadata |
| `tokens` | 48 | Token identity, faces, types, color, printed/reference and relevant printing metadata |
| `cardIdentifiers` | 25 | UUID and external IDs such as `scryfallId` (printing) and `scryfallOracleId` (Oracle identity) |
| `tokenIdentifiers` | 25 | External token/printing IDs, distinct from token-product packages |
| `cardLegalities` | 24 | Format legalities at the source snapshot |
| `cardRulings` | 3 | Card-linked source rulings and dates |
| `sets` | 22 | Set identities, codes, dates, languages and token-set links |
| `meta` | 2 | MTGJSON source date and version |

**Full exact column inventory** (each list below corresponds directly to `profiles/v2_2.json`):

### `cards` (78 columns)

`uuid`, `setCode`, `number`, `name`, `printedName`, `asciiName`, `layout`, `side`, `faceName`, `facePrintedName`, `faceManaValue`, `faceConvertedManaCost`, `cardParts`, `relatedCards`, `otherFaceIds`, `variations`, `manaCost`, `manaValue`, `colors`, `colorIdentity`, `colorIndicator`, `producedMana`, `text`, `types`, `type`, `subtypes`, `supertypes`, `keywords`, `power`, `toughness`, `loyalty`, `defense`, `hand`, `life`, `hasAlternativeDeckLimit`, `leadershipSkills`, `isGameChanger`, `isFunny`, `isOnlineOnly`, `isOversized`, `isAlternative`, `isRebalanced`, `isPromo`, `isTextless`, `isReserved`, `isReprint`, `rarity`, `finishes`, `availability`, `language`, `originalReleaseDate`, `isStorySpotlight`, `edhrecRank`, `edhrecSaltiness`, `attractionLights`, `subsets`, `isFullArt`, `isTimeshifted`, `originalPrintings`, `duelDeck`, `faceFlavorName`, `flavorName`, `hasContentWarning`, `originalText`, `printedText`, `printedType`, `printings`, `rebalancedPrintings`, `artist`, `artistIds`, `borderColor`, `flavorText`, `frameEffects`, `frameVersion`, `promoTypes`, `securityStamp`, `signature`, `watermark`

### `tokens` (48 columns)

`uuid`, `setCode`, `number`, `name`, `asciiName`, `layout`, `side`, `faceName`, `manaCost`, `colors`, `colorIdentity`, `colorIndicator`, `producedMana`, `text`, `types`, `type`, `subtypes`, `supertypes`, `keywords`, `power`, `toughness`, `otherFaceIds`, `relatedCards`, `isFunny`, `isOversized`, `isPromo`, `isReprint`, `availability`, `language`, `attractionLights`, `edhrecSaltiness`, `flavorName`, `orientation`, `originalText`, `printedType`, `artist`, `artistIds`, `borderColor`, `finishes`, `flavorText`, `frameEffects`, `frameVersion`, `isFullArt`, `isTextless`, `promoTypes`, `securityStamp`, `signature`, `watermark`

### `cardIdentifiers` (25 columns)

`uuid`, `scryfallId`, `scryfallOracleId`, `scryfallIllustrationId`, `scryfallCardBackId`, `mcmId`, `mcmMetaId`, `mtgArenaId`, `mtgoId`, `mtgoFoilId`, `multiverseId`, `tcgplayerProductId`, `tcgplayerEtchedProductId`, `tcgplayerAlternativeFoilProductId`, `cardKingdomId`, `cardKingdomFoilId`, `cardKingdomEtchedId`, `cardsphereId`, `cardsphereAlternativeFoilId`, `cardsphereEtchedId`, `cardsphereFoilId`, `deckboxId`, `mtgjsonFoilVersionId`, `mtgjsonNonFoilVersionId`, `mtgjsonV4Id`

### `tokenIdentifiers` (25 columns)

`uuid`, `scryfallId`, `scryfallOracleId`, `scryfallIllustrationId`, `scryfallCardBackId`, `mcmId`, `mcmMetaId`, `mtgArenaId`, `mtgoId`, `mtgoFoilId`, `multiverseId`, `tcgplayerProductId`, `tcgplayerEtchedProductId`, `tcgplayerAlternativeFoilProductId`, `cardKingdomId`, `cardKingdomFoilId`, `cardKingdomEtchedId`, `cardsphereId`, `cardsphereAlternativeFoilId`, `cardsphereEtchedId`, `cardsphereFoilId`, `deckboxId`, `mtgjsonFoilVersionId`, `mtgjsonNonFoilVersionId`, `mtgjsonV4Id`

### `cardLegalities` (24 columns)

`uuid`, `alchemy`, `brawl`, `commander`, `competitivebrawl`, `duel`, `future`, `gladiator`, `historic`, `legacy`, `modern`, `oathbreaker`, `oldschool`, `pauper`, `paupercommander`, `penny`, `pioneer`, `predh`, `premodern`, `standard`, `standardbrawl`, `timeless`, `tlr`, `vintage`

### `cardRulings` (3 columns)

`uuid`, `date`, `text`

### `sets` (22 columns)

`code`, `mtgoCode`, `name`, `block`, `releaseDate`, `type`, `isOnlineOnly`, `isFoilOnly`, `tcgplayerGroupId`, `isNonFoilOnly`, `parentCode`, `totalSetSize`, `baseSetSize`, `keyruneCode`, `isPartialPreview`, `isForeignOnly`, `isPaperOnly`, `languages`, `tokenSetCode`, `mcmId`, `mcmName`, `mcmIdExtras`

### `meta` (2 columns)

`date`, `version`

## Exact source-row counts for the verified 13 November 2026 snapshot

The counts below come from the **actual GitHub-hosted source inventory** in [Actions run 43516913604](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43516913604), archived in [Drive acceptance evidence](https://drive.google.com/file/d/1TsaBRve9Kt0YgVIZBVtB5NJfqmSVMtvq/view). Official source archive SHA-256: `628ff982b1a5b764f4b98dfca796fc46c4fd509cf2f4a01077ae01b5092fe42e`.

| Source table | Source rows | Output status |
| --- | ---: | --- |
| `cardForeignData` | 441,563 | Omitted entirely |
| `cardIdentifiers` | 116,005 | Kept: all rows |
| `cardLegalities` | 116,005 | Kept: all rows |
| `cardPurchaseUrls` | 116,005 | Omitted entirely |
| `cardRulings` | 284,339 | Kept: all rows |
| `cards` | 116,005 | Kept: all rows |
| `meta` | 1 | Kept: all rows |
| `sealedProducts` | 4,327 | Omitted entirely |
| `setBoosterContents` | 14,414 | Omitted entirely |
| `setBoosterContentWeights` | 3,400 | Omitted entirely |
| `setBoosterSheetCards` | 295,590 | Omitted entirely |
| `setBoosterSheets` | 4,482 | Omitted entirely |
| `setDecks` | 3,154 | Omitted entirely |
| `sets` | 882 | Kept: all rows |
| `setTranslations` | 584 | Omitted entirely |
| `tokenIdentifiers` | 9,565 | Kept: all rows |
| `tokenProductIdentifiers` | 16,337 | Omitted entirely |
| `tokenProductParts` | 18,680 | Omitted entirely |
| `tokenProducts` | 15,051 | Omitted entirely |
| `tokens` | 9,565 | Kept: all rows |
| **TOTAL** | **1,585,954** | **652,367 retained / 933,587 omitted** |

**Warning:** these are **table rows**, not unique cards, printings or lost MTG game data. An excluded purchase-URL or foreign-name row is not an excluded `cards` row. Counts legitimately change when upstream MTGJSON updates, even without a profile change. Do not extrapolate these snapshot counts to future builds.

## Tables omitted entirely (12 of 20 source tables)

These tables, their source rows and their indexes are **not present** in the slim output:

| Omitted upstream table | Reason |
| --- | --- |
| `cardForeignData` | Bulk localized/foreign card-face names and text, redundant for this curated identity/rules profile; deleting this output table does NOT authorize dropping non-English printing rows or printed names from cards/tokens. |
| `cardPurchaseUrls` | Storefront/purchase links; not authoritative card identity or Oracle rules. |
| `sealedProducts` | Sealed-product catalog and packaging relationships, not individual playable card facts. |
| `setBoosterContentWeights` | Booster collation weights; packaging-only. |
| `setBoosterContents` | Booster contents/pick instructions; packaging-only. |
| `setBoosterSheetCards` | Booster sheet composition/weights; packaging-only. |
| `setBoosterSheets` | Booster sheet definitions; packaging-only. |
| `setDecks` | Published/preconstructed deck lists; this database is NOT a deck catalog or deck-strength reference. |
| `setTranslations` | Set-name translations; not physical-printing identifiers or Oracle rules. |
| `tokenProductIdentifiers` | Commercial token-product identifiers, distinct from the preserved actual tokenIdentifiers table. |
| `tokenProductParts` | Token-product packaging relationships, distinct from token-face identity. |
| `tokenProducts` | Token-product packages, distinct from the preserved actual tokens table. |

## Columns omitted from otherwise retained tables (6)

| Table | Omitted source columns | Reason |
| --- | --- | --- |
| `cards` | `boosterTypes`, `skuIds`, `sourceProducts` | Booster packaging / commercial SKU or source-product information; not a physical printing identifier or Oracle rule |
| `tokens` | `boosterTypes`, `skuIds`, `sourceProducts` | Same exclusions for token product and packaging metadata |

No other source column is omitted from `cards` or `tokens`. **No source column is omitted** from the six other selected tables.

## Important details about information that remains

- **Foreign printings remain.** `cards.language`, `tokens.language`, `printedName`, `facePrintedName`, their original UUIDs, printing IDs and other selected fields are retained. The dropped `cardForeignData` translation table is not equivalent to dropping non-English physical printings. Do not describe this output as an English-only database.
- **Oracle vs printed text.** `cards.text` remains the source Oracle-like rules text; `printedText`, `originalText`, `printedType` and flavor/reference fields are separate. Never replace authoritative Oracle text with flavor or historic printing text.
- **Complex cards and relationships.** Preserve `layout`, `side`, face names/IDs, `otherFaceIds`, `cardParts`, `relatedCards`, `variations`, and all selected printing records. Do not merge cards just because they share an Oracle ID or Scryfall printing ID.
- **Collection import.** This database describes cards and printings, not what any user owns. Physical ownership must come from a separately and explicitly supplied collection.
- **Rules limitations.** A stored legality value or ruling is snapshot data, not a complete live game-rules validator or guarantee of deck legality/quality.
- **Index semantics.** The 20 indexes use `UNIQUE` for verified UUID/set-code identity invariants and **non-unique** indexes for Scryfall printing/Oracle IDs because actual multiple faces/rows can share those IDs. See the exact index inventory below; more indexes do not necessarily improve every query.

## Explicit output indexes (20)

| Index name | Table | Columns | Unique |
| --- | --- | --- | --- |
| `idx_cardIdentifiers_oracleid` | `cardIdentifiers` | `scryfallOracleId` | No |
| `idx_cardIdentifiers_scryfallid` | `cardIdentifiers` | `scryfallId` | No |
| `idx_cardIdentifiers_uuid` | `cardIdentifiers` | `uuid` | Yes |
| `idx_cardLegalities_uuid` | `cardLegalities` | `uuid` | Yes |
| `idx_cardRulings_uuid` | `cardRulings` | `uuid` | No |
| `idx_cards_facePrintedName` | `cards` | `facePrintedName` | No |
| `idx_cards_name` | `cards` | `name` | No |
| `idx_cards_printedName` | `cards` | `printedName` | No |
| `idx_cards_setCode` | `cards` | `setCode` | No |
| `idx_cards_set_number` | `cards` | `setCode`, `number` | No |
| `idx_cards_uuid` | `cards` | `uuid` | Yes |
| `idx_sets_code` | `sets` | `code` | Yes |
| `idx_sets_name` | `sets` | `name` | No |
| `idx_sets_tokenSetCode` | `sets` | `tokenSetCode` | No |
| `idx_tokenIdentifiers_oracleid` | `tokenIdentifiers` | `scryfallOracleId` | No |
| `idx_tokenIdentifiers_scryfallid` | `tokenIdentifiers` | `scryfallId` | No |
| `idx_tokenIdentifiers_uuid` | `tokenIdentifiers` | `uuid` | Yes |
| `idx_tokens_name` | `tokens` | `name` | No |
| `idx_tokens_set_number` | `tokens` | `setCode`, `number` | No |
| `idx_tokens_uuid` | `tokens` | `uuid` | Yes |

## Validation, changes and distribution boundaries

- The converter verifies the official downloaded archive against the official SHA-256; profiles reject unreviewed source schema drift; output checks include schema, integrity, identities, configured links and full selected-row logical digests against the source.
- **Profile 2.2 is pinned to a source schema**, not a promise that every future MTGJSON release will build unchanged. Changes in *omitted* source tables also trigger review.
- The exact historical November 7 archive is an information-contract baseline, **not** a target for byte-identical hashes or static card counts.
- Two full local profile-2.2 builds reproduced identical bytes in the same runtime. A GitHub-hosted full-data job also passed on [Actions run 43516913604](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43516913604), but its SQLite/XZ hashes differ from the local build because of different Python/SQLite/runtime details; compare logical selected-table hashes, not cross-runtime raw bytes.
- Some `setCode`-only lookups were slower in measured samples than profile 2.1; identity and printing lookups improved substantially. See [acceptance report](acceptance-profile-2.2.md) for test scope and limitations.
- **Consumer compatibility is not implied by historical field preservation.** The profile-2.2 SQLite is **282,390,528 bytes** (approximately 269.3 MiB), which exceeds some consumers' independently configured 256 MiB file-size limits. Consumers may also pin earlier database SHA-256 values. Do not weaken an existing consumer's provenance checks or change another project as part of this converter PR; migrate each consumer separately after this repo is accepted.
- **Data availability is not a release.** GitHub Actions uploads JSON validation evidence only; the SQLite/XZ database is not published as a downloadable GitHub Release in this repo. A separate release/distribution design is required before external applications can reliably auto-fetch new versions.
- A validated local output is **not automatically cleared for public redistribution**; see [third-party notices](../THIRD_PARTY_NOTICES.md) and [MTGJSON brand assets policy](https://mtgjson.com/brand-assets/). No unattended publication or schedule is enabled.
