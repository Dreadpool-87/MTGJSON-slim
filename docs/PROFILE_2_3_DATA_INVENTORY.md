# Profile 2.3 — precise retained and omitted SQLite fields

This document is generated from the actual committed profile [`profiles/v2_3.json`](../profiles/v2_3.json). It describes the intended selection and existing source schema pin; its exact selected fields and source-backed output were verified in an independent GitHub-hosted full-data comparison (see results below).

- Source schema is pinned to official MTGJSON `5.3.0+20261113`, unchanged from profile 2.2. An upstream change fails closed until explicitly reviewed.
- Output: **8 tables, 224 columns, 20 explicit indexes**; all rows in retained tables, card faces, UUIDs, languages and selected field values are preserved.
- Exactly **three new omissions** compared with version 2.2: `cards.flavorText`, `tokens.flavorText`, and `cards.isStorySpotlight`. This removes non-gameplay narrative information, not any card-rules, ruling or identity text.
- Profile 2.3 is the **standalone main profile** and CLI default. Its own [`contracts/main-profile-2.3.json`](../contracts/main-profile-2.3.json) locks all 224 selected fields, 20 indexes, the pinned source schema, relationships and identity keys. The active converter **does not load** older profile 2.2 or `contracts/historical-2026-11-07-field-baseline.json` for a 2.3 build.
- Older `profiles/v2_2.json` and `contracts/historical-2026-11-07-field-baseline.json` remain unchanged solely as historical reference and archived-profile regression safeguards. The historical baseline is **not** a legal contract, permission statement or requirement to restore `isStorySpotlight`.

## Tables and exact fields retained

| Table | Columns | Function |
| --- | ---: | --- |
| `cards` | 76 | Card printing/face identities, rules, printed text, mana, relations and printing metadata |
| `tokens` | 47 | Token identity, faces, rules and printing metadata |
| `cardIdentifiers` | 25 | Printing, Scryfall and other external reference IDs |
| `tokenIdentifiers` | 25 | Token IDs and external references |
| `cardLegalities` | 24 | Format legality snapshot |
| `cardRulings` | 3 | Dated card-linked rulings and text |
| `sets` | 22 | Set identity, codes, dates and linked token sets |
| `meta` | 2 | MTGJSON source date/version |

### `cards` (76 columns)

`uuid`, `setCode`, `number`, `name`, `printedName`, `asciiName`, `layout`, `side`, `faceName`, `facePrintedName`, `faceManaValue`, `faceConvertedManaCost`, `cardParts`, `relatedCards`, `otherFaceIds`, `variations`, `manaCost`, `manaValue`, `colors`, `colorIdentity`, `colorIndicator`, `producedMana`, `text`, `types`, `type`, `subtypes`, `supertypes`, `keywords`, `power`, `toughness`, `loyalty`, `defense`, `hand`, `life`, `hasAlternativeDeckLimit`, `leadershipSkills`, `isGameChanger`, `isFunny`, `isOnlineOnly`, `isOversized`, `isAlternative`, `isRebalanced`, `isPromo`, `isTextless`, `isReserved`, `isReprint`, `rarity`, `finishes`, `availability`, `language`, `originalReleaseDate`, `edhrecRank`, `edhrecSaltiness`, `attractionLights`, `subsets`, `isFullArt`, `isTimeshifted`, `originalPrintings`, `duelDeck`, `faceFlavorName`, `flavorName`, `hasContentWarning`, `originalText`, `printedText`, `printedType`, `printings`, `rebalancedPrintings`, `artist`, `artistIds`, `borderColor`, `frameEffects`, `frameVersion`, `promoTypes`, `securityStamp`, `signature`, `watermark`

### `tokens` (47 columns)

`uuid`, `setCode`, `number`, `name`, `asciiName`, `layout`, `side`, `faceName`, `manaCost`, `colors`, `colorIdentity`, `colorIndicator`, `producedMana`, `text`, `types`, `type`, `subtypes`, `supertypes`, `keywords`, `power`, `toughness`, `otherFaceIds`, `relatedCards`, `isFunny`, `isOversized`, `isPromo`, `isReprint`, `availability`, `language`, `attractionLights`, `edhrecSaltiness`, `flavorName`, `orientation`, `originalText`, `printedType`, `artist`, `artistIds`, `borderColor`, `finishes`, `frameEffects`, `frameVersion`, `isFullArt`, `isTextless`, `promoTypes`, `securityStamp`, `signature`, `watermark`

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

## Exact profile-2.3 exclusions compared with profile 2.2

| Table | Removed column | Impact |
| --- | --- | --- |
| `cards` | `flavorText` | Removes the narrative flavor text printed on cards; no game-rule effect |
| `tokens` | `flavorText` | Removes token narrative flavor text; no game-rule effect |
| `cards` | `isStorySpotlight` | Removes one `NUM` column indicating story-related cards. This is **one column per card row**, not a single cell; its byte footprint has not yet been measured |

Exact difference checked against v2.2:

```json
{
  "cards": [
    "isStorySpotlight",
    "flavorText"
  ],
  "tokens": [
    "flavorText"
  ]
}
```

The earlier profile already omits **12 entire source tables**: `cardForeignData`, `cardPurchaseUrls`, `sealedProducts`, `setBoosterContentWeights`, `setBoosterContents`, `setBoosterSheetCards`, `setBoosterSheets`, `setDecks`, `setTranslations`, `tokenProductIdentifiers`, `tokenProductParts`, and `tokenProducts`. The three earlier packaging columns `boosterTypes`, `skuIds`, `sourceProducts` remain excluded from both `cards` and `tokens`. Source schema audits still include these omitted objects to detect upstream changes.

## Invariants and implications

- **Kept:** `cards.text`, `tokens.text`, `cardRulings.text`, `originalText`, `printedText`, `flavorName`, `faceFlavorName`, `printedName`, `facePrintedName` and exact IDs/relations.
- The absence of `flavorText` does **not** permit removing the alternative physical card name `flavorName` or `faceFlavorName`. These are printing-identification data.
- `isStorySpotlight` affects narrative metadata only. No gameplay, Oracle, legality, printed-name or index column is dropped.
- **All 20 indexes unchanged** and checked against profile 2.2. See below.
- Original non-English physical printings and their retained printed names are still preserved. Dropping `cardForeignData` does not imply English-only printings.
- These three omissions leave rules text, original/printed text and card rulings intact; consult [source and third-party notices](../THIRD_PARTY_NOTICES.md) for data provenance and attribution.
- Storage savings in raw SQLite and XZ depend on actual non-null value frequencies and SQLite page layout. The exact combined savings have now been measured, with a single official source archive for both profiles (see below). The contribution of each removed column individually was not measured.

## Explicit indexes (unchanged: 20)

| Index | Table | Columns | Unique |
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

## Verified full-data comparison (14 November 2026)

Both profiles were built and source-validated **independently from the exact same official archive** MTGJSON `5.3.0+20261113`, verified SHA-256 `628ff982b1a5b764f4b98dfca796fc46c4fd509cf2f4a01077ae01b5092fe42e`.

| Output | Profile 2.2 | Profile 2.3 | Saved |
| --- | ---: | ---: | ---: |
| Raw `.sqlite` | 282,390,528 bytes | 276,037,632 bytes | **6,352,896 bytes** |
| `.sqlite.xz` | 49,264,112 bytes | 47,118,052 bytes | **2,146,060 bytes** |

The source-backed comparison verified that all 8 tables kept the same row counts (652,367 total retained rows), every retained column's logical values matched exactly across both full databases, all 20 index definitions were identical and only `cards.isStorySpotlight`, `cards.flavorText` and `tokens.flavorText` were absent. The `meta` source record remained unchanged. Both complete builds and every comparison test passed.

**Evidence:** [GitHub Actions acceptance run #43570579132](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43570579132), artifact `validation-evidence` with `profile_comparison.json`, `build.json`, `build22.json`, validation reports and manifests. Build-byte results are specific to this source and GitHub runner; future versions can have different sizes.

## Testing and distribution

Run `python -m unittest discover -s tests -v`. The new tests verify the complete v2.2→v2.3 field difference, exact approved omissions, retained rules/rulings/alternative names, preserved indexes, fail-closed behavior and live SQLite projection on a synthetic source. The weekly GitHub workflow uses `profiles/v2_3.json` and rebuilds a fresh SQLite before generating the lossless XZ copy. Public Releases use the verified draft-first publish workflow; see [GitHub Releases](https://github.com/Dreadpool-87/MTGJSON-slim/releases). Full source-backed acceptance and exact measured sizes are recorded above.
