# MTGJSON-slim

**Smaller, source-verified Magic: The Gathering datasets for deckbuilding tools, collection apps and AI-assisted workflows.** Built independently from official [MTGJSON](https://mtgjson.com/) data; not affiliated with MTGJSON or Wizards of the Coast.

**[Download datasets](https://dreadpool-87.github.io/MTGJSON-slim/)** · [GitHub Releases](https://github.com/Dreadpool-87/MTGJSON-slim/releases) · [Usage guide](docs/USAGE.md) · [Development guide](docs/DEVELOPMENT.md)

## Choose a dataset

| Dataset | Best for | What it contains |
| --- | --- | --- |
| **AllPrintings SQLite** | Indexed searches, local tools and collection/printing matching | Selected printing and token records, names, identifiers, rules, legalities, rulings and indexes |
| **AllPrintings JSON** | Applications that prefer JSON and need individual card printings or tokens | Independent, source-derived printing and token data grouped by set |
| **AtomicCards JSON** | Card-name and Oracle-oriented lookups | Cards grouped by name, with rules, identities, translated data and relationships |

**Important:** AtomicCards is **not** a replacement for AllPrintings when you need individual printing or standalone token records. The formats have different source schemas; matching selected fields does **not** establish complete JSON/SQLite equivalence.

## Download formats

Every dataset has four lossless download options, plus a separate **SHA-256 checksum** for each file.

| Format | Choose it when… |
| --- | --- |
| **XZ** (`.xz`) | You want a smaller download |
| **Zstandard** (`.zst`) | Your application supports fast decompression |
| **ZIP** (`.zip`) | You want straightforward extraction on common devices |
| **Raw** (`.sqlite` or `.json`) | Your application needs an immediately usable file |

Use the [download page](https://dreadpool-87.github.io/MTGJSON-slim/) to select a dataset and format; **you do not need Python or a GitHub account just to download it**. The website enables download options only when the matching published file and checksum are available. Verify the SHA-256 before trusting a download; see [Usage](docs/USAGE.md).

## What is preserved?

All datasets are generated from separately checksum-verified official sources. Their reviewed selections retain **card names, mana costs and values, rules text, card faces, identifiers, format legalities and rulings**. Validation failures block publishing. SQLite and AtomicCards reject unexpected schema changes; the AllPrintings JSON policy keeps unexcluded source fields rather than silently dropping them.

The datasets are **intentionally not identical**: SQLite profile 2.3 and AllPrintings JSON omit reviewed nonessential fields (including some translation or product data). **Omitting translation tables or nested translations does not remove non-English card-printing records or their printed names.** AtomicCards B1 retains nested translations but removes seller links and two verified redundant mana aliases. For the **exact** kept/removed fields, consult the linked inventories and [data policy](docs/DEVELOPMENT.md). These files are data sources, **not** a complete MTG rules engine, deckbuilder, ownership database or AI model.

## Use or build locally

Downloads are ready to use after extraction. To build from official sources, use the individual instructions for [SQLite, AllPrintings JSON and AtomicCards](docs/USAGE.md); you do not need to run all three pipelines.

Our GitHub Actions builds use **Python 3.14**, including its native Zstandard module. Older local Python versions can use the `zstd` command-line fallback for Zstandard packaging. The SQLite converter itself remains standard-library-only; the JSON converters additionally require the pinned streaming parser.

## Documentation

| Guide | Contents |
| --- | --- |
| [Usage](docs/USAGE.md) | Downloads, SHA-256 checks, extraction and CLI examples |
| [Development & automation](docs/DEVELOPMENT.md) | CI, schedules, release safety, reproducibility and troubleshooting |
| [SQLite profile 2.3 inventory](docs/PROFILE_2_3_DATA_INVENTORY.md) | Exact retained/omitted tables, columns and indexes |
| [AllPrintings JSON source audit](docs/JSON_DIRECT_SOURCE_PREVIEW.md) | JSON selection, same-date comparisons and historical acceptance evidence |
| [AtomicCards B1 profile](contracts/atomic-b1.json) | Exact AtomicCards source schema, retained fields and three approved omissions |
| [Historical SQLite profile 2.2 acceptance](docs/acceptance-profile-2.2.md) | Prior profile and test evidence |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | Source attribution, licenses and branding |

All three families have **separate, weekly verified release pipelines**, scheduled on Tuesdays (07:00 SQLite, 07:20 AllPrintings JSON, 07:40 AtomicCards; `Europe/Brussels`). GitHub may delay scheduled starts. Unchanged validated data are not republished.

## License and attribution

**Powered by [MTGJSON](https://mtgjson.com/).** This independent project's code is [MIT-licensed](LICENSE); upstream data and card-related rights are governed separately. Every Release includes the upstream [MTGJSON license notice](MTGJSON_LICENSE.txt). See [third-party notices](THIRD_PARTY_NOTICES.md) for attribution, usage limitations and official branding terms.

<a href="https://mtgjson.com/">
  <img src="https://mtgjson.com/images/assets/logo-mtgjson.svg" width="60" alt="MTGJSON logo" />
</a>
