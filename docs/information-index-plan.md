# Field and index audit plan

Spec: new authoritative 2026-11-13 information-preservation and index-audit brief in Drive. Existing branch/PR only; no main or Release changes.

1. Verify actual 07Nov bytes and inspect every historical/current index with PRAGMA index_list/index_info and sqlite_schema.
2. Restore every historical column and retain justified profile-2.1 extras exactly. Fail if a historical source field/type is unavailable. Write the explicit gapmatrix before implementing.
3. Benchmark current 2.1 and same-source index candidates: exact Scryfall/Oracle IDs, CSV name/set/number, legality/ruling joins, face and token routes. Use actual rows and plans, repeated warm-cache measurements and index footprints.
4. Add versioned profile 2.2 with an explicit index policy, eliminating duplicate ordinary+UNIQUE UUID pairs and retaining or replacing historical search routes only with tested equivalents. Add a fixed historical field contract and regression tests.
5. Run the full suite and two complete builds with identical verified source/profile/toolcommit/runtime. Compare bytes, row/field digests, schemas, relationships, complex records, all indexes and benchmark results across historical, 2.1 and same-source variants.
6. Review the change independently, fix verified findings, update the existing PR, and save a Dutch GO/NO-GO report plus compact evidence in the designated Drive folder. Keep previous source/evidence intact.

## Field decisions

| Table | Restore from historical contract | Keep useful additions |
| --- | --- | --- |
| cards | edhrecRank, edhrecSaltiness, finishes, isFullArt, isPromo, isReprint, isReserved, isStorySpotlight, isTextless, isTimeshifted, originalReleaseDate | artist, artistIds, borderColor, duelDeck, faceFlavorName, flavorName, flavorText, frameEffects, frameVersion, hasContentWarning, originalText, printedText, printedType, printings, promoTypes, rebalancedPrintings, securityStamp, signature, watermark |
| tokens | edhrecSaltiness, isPromo, isReprint | artist, artistIds, borderColor, finishes, flavorName, flavorText, frameEffects, frameVersion, isFullArt, isTextless, orientation, originalText, printedType, promoTypes, securityStamp, signature, watermark |
| cardIdentifiers | (none) | (none) |
| tokenIdentifiers | (none) | (none) |
| cardLegalities | (none) | (none) |
| cardRulings | (none) | (none) |
| sets | (none) | (none) |
| meta | (none) | (none) |

## Index decisions pending measurement

Preserve historical unique UUID indexes and ruling UUID lookup; restore the verified non-unique idx_cardIdentifiers_oracleid route. Test non-unique Scryfall indexes because real multi-face rows share printing IDs. Test setCode+number composites against existing setCode indexes, exact printed-name routes, token identifiers and set token-code joins. Keep only measured useful additions. Source schema pin remains unchanged.

## Measured index selection

The initial same-source candidate tests are complete. Oracle/Scryfall and printed-name routes move from scans to explicit indexed searches. Scryfall IDs are non-unique in real card/token data, so UNIQUE is rejected. Keep the historical cards.setCode index alongside a setCode+number composite because the composite-only candidate regressed set-only lookups. The token composite preserves setCode lookups and outperformed a separate single-key token index in its direct test. The selected policy has 20 indexes and no duplicate exact keys. Preserve all ten verified historical index routes and names; add only the measured lookup paths. Evidence: field-gapmatrix.json, index-gapmatrix.json and candidate benchmark reports in the new evidence package.

The successor conservatively retains further card-level artist, printing/frame/promo, watermark, security-stamp and printed flavor/reference metadata. These values are not used as Oracle rules. Only card/token SKU, source-product and booster-packaging fields remain excluded from the source card/token columns. Existing foreign translation/product/booster tables remain excluded. This follows the priority of information retention over MB.

## Completed local verification

33 regression tests passed. Both frozen full builds passed and reproduce SQLite/XZ bytes and manifests. All historical/2.1 field projections and NULL counts match the same verified current source. All ten historical index routes are retained. Twenty-one final query workloads and same-data controls were measured with five repeats. See acceptance-profile-2.2.md for the complete timing table, index footprints and set-only regressions. Full hosted data build remains NOT EXECUTED.
