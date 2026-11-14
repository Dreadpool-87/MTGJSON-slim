# Third-party notices, branding and distribution gate

## Scope

This repository contains independent Python converter code and documentation under the repository's [MIT LICENSE](LICENSE). The code license **must not be confused** with an unrestricted license to every MTG card name, rules text, illustration, logo, or piece of upstream data. Source provenance, required notices and redistribution permissions must be reviewed separately before a public database Release or automated publishing workflow is authorized.

## MTGJSON — source, attribution and license

- Official project: https://mtgjson.com/
- Official license terms: https://mtgjson.com/license/
- Official brand assets and usage conditions: https://mtgjson.com/brand-assets/
- Upstream project license reference: https://github.com/mtgjson/mtgjson/blob/master/LICENSE.txt

The MTGJSON site publishes MIT license terms, including the copyright notice **Copyright © 2018–Present, Zach Halpern** (upstream repository refers to Zachary Halpern). MIT's copyright and permission notices must be included with copies or substantial portions of the licensed material. Keep attribution and provenance attached to any permitted derivative distribution. An authorized GitHub Release additionally carries the complete upstream MIT notice as `MTGJSON_LICENSE.txt`.

**Powered by [MTGJSON](https://mtgjson.com/).** This is an independent community project and is **not affiliated with or endorsed by MTGJSON**.

### MTGJSON brand assets — explicit policy

The official [Brand Assets](https://mtgjson.com/brand-assets/) page says credit is appreciated, **not mandatory**. It offers PNG/SVG assets and an example using “Powered by MTGJSON”. When using any official MTGJSON brand asset:

1. Use the official asset from the published source; **do not alter its asset content**.
2. Do **not** use it, its placement or accompanying text in any way implying that MTGJSON sponsors, approves or endorses this project.
3. Retain a clear independent-project disclaimer.
4. Recheck the official brand conditions before adding an image, badge, splash screen, GitHub social preview or release graphic.
5. The present repository uses **text credit and links only**. No MTGJSON logo/PNG/SVG is included, modified or bundled. No asset download is required.

A link to the brand page and credit text are not proof of permission to republish every record in a derived card database.

## Wizards of the Coast — separate IP and fan content

- Official [Wizards Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy) (last updated November 15, 2017 according to the page).
- Wizards describes game-card text, artwork and other MTG material as its IP, and requires unofficial, non-endorsed presentation for covered fan content. The policy also restricts the use of Wizards logos/trademarks, commercial licensing of fan content and mere verbatim republication of its materials.
- The policy is **not a blanket approval** to mirror, sell, license or redistribute the complete MTGJSON-derived card database. A dataset may also include third-party material and external identifiers. MTGJSON's MIT notice does not settle rights belonging to Wizards or other rightsholders.
- This repository contains no downloaded Wizards logos or card images. It keeps external identifiers for permitted references to independent services. It does not imply Wizards endorsement.

Suggested project status statement: **“MTGJSON-slim is an independent, unofficial community converter. It is not approved, sponsored or endorsed by MTGJSON or Wizards of the Coast.”**

Do **not** assert that the project is definitively “Fan Content permitted under the Fan Content Policy” without first establishing that the specific proposed distribution qualifies. Preserve applicable original notices and check the current policies before publication.

**2026-11-14 rights review outcome: NOT CLEARED.** Read [the documented source review, approval criteria and unsent permission inquiries](docs/DATA_REDISTRIBUTION_REVIEW_2026-11-14.md). Keep the public-release approval variable disabled until the required written clarifications are received and evaluated.\n\n## Public database distribution is deliberately disabled

At the time of this documentation:

- The repository rebuilds a verified slim SQLite weekly, checks that its lossless XZ copy reproduces the same bytes, and uploads **verification reports only** by default; no database files are committed.
- The publishing workflow is **inactive by default**. The repository variable `MTGJSON_PUBLIC_DISTRIBUTION_APPROVED` must be explicitly set to `true` only after the maintainer has documented redistribution rights for the MTGJSON-derived dataset and its third-party content. The variable alone does not grant permission.
- If authorized, a changed, verified dataset can be published as a draft-first GitHub Release, with the previous stable Release preserved on failure. Without authorization, public release assets are not uploaded.
- A proposed public Release, mirror or automated distribution needs a **separate rights/licensing review and explicit maintainer authorization**. Assess distribution terms for MTGJSON, Wizards and any other contributors to included material; document the decision and required notices.
- A source and database SHA-256 prove byte identity, **not** permission to republish, authenticity of all included card facts, or legal compliance.

When allowed to distribute, include source URL, upstream version/date, upstream SHA-256, converter tool commit, profile SHA-256, build runtime, output SHA-256, generation/validation status, attribution/license notices, independent-project disclaimer and rights-review record in the provenance package.

See [Profile 2.2 retained and omitted data](docs/PROFILE_2_2_DATA_INVENTORY.md) and the [acceptance evidence](docs/acceptance-profile-2.2.md).
