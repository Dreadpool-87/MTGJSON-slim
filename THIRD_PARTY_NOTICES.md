# Third-party notices

## MTGJSON data source

MTGJSON-slim is an independent, unofficial converter built from the official [MTGJSON](https://mtgjson.com/) `AllPrintings` SQLite dataset. It is not affiliated with, sponsored by or endorsed by MTGJSON or Wizards of the Coast. Card data are downloaded from MTGJSON, not scraped directly from separate card-data providers by this converter.

- MTGJSON project: https://mtgjson.com/
- MTGJSON license: https://mtgjson.com/license/
- MTGJSON source license: https://github.com/mtgjson/mtgjson/blob/master/LICENSE.txt
- MTGJSON brand-assets terms: https://mtgjson.com/brand-assets/

**Powered by MTGJSON.** The upstream MIT copyright and license notice is included in [`MTGJSON_LICENSE.txt`](MTGJSON_LICENSE.txt) and with each published database Release. Build manifests preserve the source version, archive checksum and converter/profile identifiers.

## Copyright and license scope

The repository's [MIT license](LICENSE) applies to its original converter code and documentation. It does not transfer ownership of the underlying MTG card information. Names, rules text, printed/original card text, rulings and other source data may be subject to rights held by Wizards of the Coast or other contributors; upstream content is not automatically relicensed by this project's code license.

Profile 2.3 does **not** bundle card image files, `flavorText` or `isStorySpotlight`. It **does** preserve card rules text, printed/original rules text, official rulings and identifiers for functionality. Consult the [exact field inventory](docs/PROFILE_2_3_DATA_INVENTORY.md).

## Branding and distribution

The README displays MTGJSON's official SVG logo from its published URL without changing or repackaging it, alongside a clear independent-project disclaimer. No Wizards logos or card artwork are packaged as project branding. Follow the linked official brand-assets terms.

Public [GitHub Releases](https://github.com/Dreadpool-87/MTGJSON-slim/releases) include the raw SQLite file, lossless XZ copy, their SHA-256 sidecars, the provenance manifest and `MTGJSON_LICENSE.txt`. These checksums establish file integrity; they are not a determination of third-party intellectual-property rights.
