# Profile 2.3 — precise retained and omitted SQLite fields

This document is generated from the actual committed profile [`profiles/v2_3.json`](../profiles/v2_3.json). It describes the intended selection and existing source schema pin; it is not a claim of an independently measured new full-size build until that build passes.

- Source schema is pinned to official MTGJSON `5.3.0+20261113`, unchanged from profile 2.2. An upstream change fails closed until explicitly reviewed.
- Output: **8 tables, 224 columns, 20 explicit indexes**; all rows in retained tables, card faces, UUIDs, languages and selected field values are preserved.
- Exactly **three new omissions** compared with version 2.2: `cards.flavorText`, `tokens.flavorText`, and `cards.isStorySpotlight`. This removes non-gameplay narrative information, not any card-rules, ruling or identity text.
- Prior `profiles/v2_2.json` and `contracts/07nov-fields.json` are unchanged. The latter is a programming safeguard against accidental field removal, **not** a legal agreement or user permission contract. The converter permits only the three reviewed exceptions in profile 2.3 and checks every other field against v2.2.

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
- This removes 3 output columns; it does not imply that a public dataset Release is legally authorized. The rights gate remains disabled until distribution is cleared.
- Storage savings in raw SQLite and XZ depend on actual non-null value frequencies and SQLite page layout. **No size claim is made before two measured builds.**

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

## Testing and distribution

Run `python -m unittest discover -s tests -v`. The new tests verify the complete v2.2→v2.3 field difference, exact approved omissions, retained rules/rulings/alternative names, preserved indexes, fail-closed behavior and live SQLite projection on a synthetic source. The weekly GitHub workflow uses `profiles/v2_3.json` and rebuilds a fresh SQLite before generating the lossless XZ copy. Public Releases remain guarded by explicit rights approval. Exact live source-backed acceptance and size measurements must be recorded separately; do not infer them from old v2.2 results.
