# Profile v2 language policy

Profile v2 removes the entire selected `cardForeignData` table and its two indexes. It does not generate its rows or its relationship to cards. The original source DDL remains pinned, including omitted tables, so upstream schema changes still fail closed. The immutable v1 policy is available through Git history rather than as an active profile file.

## Evidence-based decisions

The same verified official `5.3.0+20261112` source used for v1 was examined with read-only SQL. Using the same source isolates the policy change from upstream data changes.

| Data | Observed source | Decision |
| --- | --- | --- |
| cardForeignData | 442,107 localized reference rows | Remove the entire table as explicitly requested |
| cards.language | 113,278 English and 2,638 non-English records across 20 languages | Keep every record and language tag |
| tokens.language | 9,530 English and 35 Japanese records | Keep every record and language tag |
| Printing identifiers | Every non-English card/token record has its own MTGJSON UUID and a Scryfall printing ID; face records can share a Scryfall ID | Preserve UUIDs and all identifier rows; do not deduplicate by Oracle ID |
| English Oracle peers | Eight non-English card records lack an English record with the same Oracle ID; thirteen distinct non-English record names do not occur among English records | An English-only filter would lose supported identities |
| printedName / facePrintedName | Non-null localized and alternate printed names differ from canonical names in actual records | Keep exact values, including NULLs; necessary for printing/name recognition |
| text | Canonical rules field, separate from printed/original wording | Keep exact source values; do not replace with translated text |
| printedText / originalText / printedType | Printed/original wording and printed type, including non-English values; not equivalent to canonical Oracle fields | Keep exact values; no field is removed based merely on language or non-ASCII characters |
| sets.languages | Available printing languages as set metadata | Keep; this is not a duplicate translated-card table |
| sets.name / mcmName | Set/edition names, sometimes containing non-ASCII characters | Keep; names are not proven redundant translations |
| cardRulings / cardLegalities / meta | Rules rulings, format statuses, source date/version | Keep all columns and records; these tables have no language selector to filter safely |
| setTranslations | Already excluded in v1 | Remain excluded |

`otherFaceIds`, `layout`, side, name/face names, identity fields and all complex card types are untouched. Serialized fields remain as stored; the pipeline does not infer a language from accents, punctuation or Unicode symbols. An English Oracle peer is not a replacement for a collection CSV's printing UUID.

## Validation

Regression tests check that no cardForeignData table/index is generated, while changes to the omitted upstream table still fail closed. Non-English names, reciprocal complex faces, canonical rules text and external identifiers remain exact in fixtures. Real acceptance additionally compares every retained row with both the official source and v1, checks all language/layout distributions, all face edges and explicit relation/identity invariants. Both complete v2 builds must use the same source, profile, tool commit and runtime.

The complete queries, example records and field statistics are included in the separately delivered `language-investigation.json`. No other language data was demonstrated safe to remove without losing reference information; no additional language deletion is performed.
