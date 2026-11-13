> Previous profile v1 results, retained as the comparison baseline. Current v2 results will be recorded separately.

# Local acceptance evidence — 2026-11-13

The official MTGJSON source was verified and two complete local builds succeeded. The final local suite passes 17 tests, including deliberately corrupted inputs, unknown schema, invalid profiles, orphans, duplicate identities, forged reused output and report aliases (including hardlinks). See PR #1 checks for hosted fixture-test results. The full hosted data-preparation job has **not** been executed; it remains manual.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Official XZ | 125147780 | `d42f434dc63dbbb698070a9c38464971fa3fa074113fe951677d23d4e9746f65` |
| Slim SQLite | 457183232 | `2c57b5acbe7bd7e13e2a7b1f65001d4b6aef515d717093cb4d347016fc7ba5e7` |
| Slim XZ | 73214008 | `0464efa0a02254731159fd7585ceadde2fdfc53a3c09e18c799045b8f1972d23` |

Both builds preserve all 115,916 cards, 9,565 tokens, 115,916 card identifiers, 9,565 token identifiers, 115,916 legalities, 284,112 rulings, 442,107 foreign-data rows, 882 sets and one meta row. All projected row hashes match the verified source. Independent SQL checks found zero configured relation orphans, matched language distributions, and resolved all 10,938 face links. Eleven concrete source-record examples preserve all selected fields and face identity.

| Build | Wall seconds | Peak RSS KiB | Tool commit |
| --- | ---: | ---: | --- |
| One | 392.127 | 136288 | `aab8c25b1ed965a20a179210697abb3d97efdf54` |
| Two | 433.023 | 135996 | `83571e57bdd75b81f6399e2328a3631b630dfba4` |

The runs overlap partially; timings are observed wall times under that load. The conversion, inventory, validation and packaging function ASTs are identical between these commits. A downloader correction occurred between them; the manifests truthfully record different tool commits. SQLite and XZ bytes reproduce; manifest byte equality is not claimed. Cross-runtime byte reproducibility is not guaranteed.

The legitimately obtained historical archive matches its prescribed 45,020,048 bytes and SHA-256. Its raw SQLite integrity is ok and its digest is `be74e3bea927e29a50f27499e51fdd3dc1ccd1820f5d256eec6705bc29e248ac`. It is not an input or equivalent output. The new output is larger because of the different documented profile, particularly retained foreign card data. Full column differences are in [profile-v1.md](profile-v1.md).

No dataset is committed or published, no Release is created, and main is unchanged. Detailed commands, JSON reports, complete schema/count inventories, source-record comparisons, negative-case exits and logs are delivered separately in the requested evidence folder. Public distribution still requires an explicit rights review and authorization.
