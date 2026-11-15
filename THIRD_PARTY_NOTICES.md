# Third-party notices

## Official MTGJSON sources

**MTGJSON-slim is independent and unofficial.** It downloads and transforms the following official [MTGJSON](https://mtgjson.com/) datasets, not data scraped directly from separate card-data providers:

| Published family | Official source |
| --- | --- |
| AllPrintings SQLite | `AllPrintings.sqlite.xz` |
| AllPrintings JSON | `AllPrintings.json.xz` |
| AtomicCards JSON | `AtomicCards.json.xz` |

Every source archive is validated against its official SHA-256 checksum. The GitHub Releases contain a provenance manifest identifying its source, version, checksum and the selected converter profile. These datasets have different field selections and source structures: AtomicCards is name/Oracle-oriented, while AllPrintings is printing-oriented.

- MTGJSON project: https://mtgjson.com/
- MTGJSON license: https://mtgjson.com/license/
- MTGJSON source license: https://github.com/mtgjson/mtgjson/blob/master/LICENSE.txt
- MTGJSON brand-assets terms: https://mtgjson.com/brand-assets/

**Powered by MTGJSON.** The upstream copyright/MIT license notice is preserved in [`MTGJSON_LICENSE.txt`](MTGJSON_LICENSE.txt) and accompanies every published dataset Release.

## Copyright and license scope

The repository's own [MIT license](LICENSE) covers original converter code and project documentation. It does **not** transfer ownership of the underlying Magic: The Gathering card information. Names, rules, printed/original card text, rulings and related records may be subject to rights held by Wizards of the Coast or other contributors. Third-party content is not automatically relicensed by this project's code license.

Data selections differ by family. SQLite profile 2.3 removes `flavorText` and `isStorySpotlight` from specified tables but retains selected gameplay text, rulings and identifiers. AllPrintings JSON also removes its reviewed narrative, translation, packaging and seller fields; AtomicCards B1 retains translated nested data but omits seller links and two redundant mana aliases. For exact claims about the data present, consult the [SQLite inventory](docs/PROFILE_2_3_DATA_INVENTORY.md), [AllPrintings JSON policy](docs/JSON_DIRECT_SOURCE_PREVIEW.md) and [AtomicCards contract](contracts/atomic-b1.json).

No card image files are bundled as dataset downloads. Refer to upstream terms for questions about downstream reuse, distribution or branding.

## Branding and distribution

The [README](README.md) displays the official MTGJSON SVG logo from its published URL, with an independent-project disclaimer. It is not modified or repackaged in the repository's dataset assets. No Wizards logos or card artwork are used as project branding. Follow the official brand-assets terms linked above.

The three separate [GitHub Release families](https://github.com/Dreadpool-87/MTGJSON-slim/releases) each provide raw data, lossless XZ, Zstandard and ZIP archives, SHA-256 sidecars, a provenance manifest and the upstream license notice. Checksums establish **file integrity**, not ownership or permission to use third-party intellectual property.
