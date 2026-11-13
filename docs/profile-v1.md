> Historical **profile v1** reference only; its original profile file is retained in Git history, not the current working tree. The active profile is [v2.2](../profiles/v2_2.json). See [exact retained/omitted v2.2 inventory](PROFILE_2_2_DATA_INVENTORY.md). V1 behavior and removed fields below must not be interpreted as current v2.2 policy.

# Profile v1: complete schema projection

This policy is explicit and versioned. Source DDL is pinned in `profiles/v1.json`; all selected-table rows are preserved, with no language filter. Data model reference: https://mtgjson.com/data-models/. A column keeps its upstream SQLite type and serialized value. No name or face normalization is performed.

## Table and column decisions

| Source table | Source rows | Selected columns | Omitted columns |
| --- | ---: | --- | --- |
| cardForeignData | 442107 | uuid, faceName, identifiers, language, multiverseId, name, text, type | flavorText, sourceProducts, skuIds |
| cardIdentifiers | 115916 | uuid, scryfallId, scryfallOracleId, scryfallIllustrationId, scryfallCardBackId, mcmId, mcmMetaId, mtgArenaId, mtgoId, mtgoFoilId, multiverseId, tcgplayerProductId, tcgplayerEtchedProductId, tcgplayerAlternativeFoilProductId, cardKingdomId, cardKingdomFoilId, cardKingdomEtchedId, cardsphereId, cardsphereAlternativeFoilId, cardsphereEtchedId, cardsphereFoilId, deckboxId, mtgjsonFoilVersionId, mtgjsonNonFoilVersionId, mtgjsonV4Id | (none) |
| cardLegalities | 115916 | uuid, alchemy, brawl, commander, competitivebrawl, duel, future, gladiator, historic, legacy, modern, oathbreaker, oldschool, pauper, paupercommander, penny, pioneer, predh, premodern, standard, standardbrawl, timeless, tlr, vintage | (none) |
| cardPurchaseUrls | 115916 | (table omitted) | uuid, cardKingdom, cardKingdomFoil, cardKingdomEtched, cardmarket, cardmarketFoil, tcgplayer, tcgplayerEtched, tcgplayerAlternativeFoil |
| cardRulings | 284112 | uuid, date, text | (none) |
| cards | 115916 | asciiName, attractionLights, availability, cardParts, colorIdentity, colorIndicator, colors, defense, duelDeck, faceConvertedManaCost, faceFlavorName, faceManaValue, faceName, facePrintedName, flavorName, hand, hasAlternativeDeckLimit, hasContentWarning, isAlternative, isFunny, isGameChanger, isOnlineOnly, isOversized, isRebalanced, keywords, language, layout, leadershipSkills, life, loyalty, manaCost, manaValue, name, number, originalPrintings, originalText, otherFaceIds, power, printedName, printedText, printedType, printings, producedMana, rarity, rebalancedPrintings, relatedCards, setCode, side, subsets, subtypes, supertypes, text, toughness, type, types, uuid, variations | artist, artistIds, boosterTypes, borderColor, edhrecRank, edhrecSaltiness, finishes, flavorText, frameEffects, frameVersion, isFullArt, isPromo, isReprint, isReserved, isStorySpotlight, isTextless, isTimeshifted, originalReleaseDate, promoTypes, securityStamp, signature, skuIds, sourceProducts, watermark |
| meta | 1 | date, version | (none) |
| sealedProducts | 4327 | (table omitted) | setCode, cardCount, category, contents, identifiers, isFoilOnly, name, productSize, purchaseUrls, releaseDate, subtype, uuid |
| setBoosterContentWeights | 3393 | (table omitted) | setCode, boosterName, boosterIndex, boosterWeight |
| setBoosterContents | 14363 | (table omitted) | setCode, boosterName, boosterIndex, sheetName, sheetPicks |
| setBoosterSheetCards | 293356 | (table omitted) | setCode, boosterName, sheetName, cardUuid, cardWeight |
| setBoosterSheets | 4465 | (table omitted) | setCode, boosterName, sheetName, sheetIsFoil, sheetHasBalanceColors, sheetTotalWeight |
| setDecks | 3154 | (table omitted) | setCode, code, name, type, releaseDate, source, sealedProductUuids, sourceSetCodes, mainBoard, sideBoard, commander, displayCommander, tokens, planes, schemes |
| setTranslations | 584 | (table omitted) | code, language, translation |
| sets | 882 | code, mtgoCode, name, block, releaseDate, type, isOnlineOnly, isFoilOnly, tcgplayerGroupId, isNonFoilOnly, parentCode, totalSetSize, baseSetSize, keyruneCode, isPartialPreview, isForeignOnly, isPaperOnly, languages, tokenSetCode, mcmId, mcmName, mcmIdExtras | (none) |
| tokenIdentifiers | 9565 | uuid, scryfallId, scryfallOracleId, scryfallIllustrationId, scryfallCardBackId, mcmId, mcmMetaId, mtgArenaId, mtgoId, mtgoFoilId, multiverseId, tcgplayerProductId, tcgplayerEtchedProductId, tcgplayerAlternativeFoilProductId, cardKingdomId, cardKingdomFoilId, cardKingdomEtchedId, cardsphereId, cardsphereAlternativeFoilId, cardsphereEtchedId, cardsphereFoilId, deckboxId, mtgjsonFoilVersionId, mtgjsonNonFoilVersionId, mtgjsonV4Id | (none) |
| tokenProductIdentifiers | 16337 | (table omitted) | tokenProductUuid, tcgplayerProductId, tcgplayerPurchaseUrl |
| tokenProductParts | 18680 | (table omitted) | tokenProductUuid, uuid |
| tokenProducts | 15051 | (table omitted) | uuid, faceAttribute |
| tokens | 9565 | asciiName, attractionLights, availability, colorIdentity, colorIndicator, colors, faceName, flavorName, isFunny, isOversized, keywords, language, layout, manaCost, name, number, orientation, originalText, otherFaceIds, power, printedType, producedMana, relatedCards, setCode, side, subtypes, supertypes, text, toughness, type, types, uuid | artist, artistIds, boosterTypes, borderColor, edhrecSaltiness, finishes, flavorText, frameEffects, frameVersion, isFullArt, isPromo, isReprint, isTextless, promoTypes, securityStamp, signature, skuIds, sourceProducts, watermark |

## Why these omissions

The profile removes product/packaging and booster-collation structures, purchase URLs, set-level deck lists and translations. They are outside a card/token identity and rules reference. It removes cosmetic presentation, flavor text, finish/promo details, commercial SKU/source-product structures and popularity analytics. Set names/codes and all foreign **card** names/rules remain; set-name translations do not. The removed columns above are the exhaustive policy, even when a retained column is not essential to every consumer.

## Historical reference differences

The verified historical snapshot is `5.3.0+20261107`, whereas the official input is `5.3.0+20261112`. It has 115,906 cards, 9,563 tokens, 284,076 rulings and 881 sets. The current source has 115,916 cards, 9,565 tokens, 284,112 rulings and 882 sets. These are upstream snapshot changes, not filtering. The new profile adds `cardForeignData`, deliberately changes selected columns and their order, deterministically sorts rows, and adds unique identity indexes. No equivalence to the old profile is claimed.

| Table | Historical only columns | New profile only columns |
| --- | --- | --- |
| cardForeignData | (none) | faceName, identifiers, language, multiverseId, name, text, type, uuid |
| cardIdentifiers | (none) | (none) |
| cardLegalities | (none) | (none) |
| cardRulings | (none) | (none) |
| cards | edhrecRank, edhrecSaltiness, finishes, isFullArt, isPromo, isReprint, isReserved, isStorySpotlight, isTextless, isTimeshifted, originalReleaseDate | duelDeck, faceFlavorName, flavorName, hasContentWarning, originalText, printedText, printedType, printings, rebalancedPrintings |
| meta | (none) | (none) |
| sets | (none) | (none) |
| tokenIdentifiers | (none) | (none) |
| tokens | edhrecSaltiness, isPromo, isReprint | flavorName, orientation, originalText, printedType |
