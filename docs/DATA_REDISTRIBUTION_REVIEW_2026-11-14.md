# MTGJSON-slim dataset redistribution review — 2026-11-14

**Operational decision update, 2026-11-14:** The repository maintainer explicitly directed enabling **free public GitHub Releases** of the existing validated slim SQLite/XZ even **without** written rights confirmations. The publication workflow was changed to attempt Releases after validated builds; this is an *owner's technical distribution decision*, **not** a grant or verification of third-party rights. The original review below remains historically accurate as the review's earlier recommendation; no MTGJSON/Wizards/partner permission request was answered and no legal clearance is asserted. Possible takedown, GitHub copyright complaints, suspension of access or legal claims remain risks. The maintainer can disable future releases by setting `PUBLICATION_ENABLED: 'false'` in `.github/workflows/verify.yml` and may need to remove already published assets separately.

**Decision: NOT CLEARED — public dataset Releases remain DISABLED.**

This is a project risk-and-permissions review of the proposed freely downloadable SQLite datasets, not a legal opinion or confirmation of rights. The public converter code remains available. The Tuesday 07:00 Europe/Brussels full rebuild, integrity verification, XZ round-trip verification and JSON-only evidence workflow continue as before. No GitHub Release should be published or rights-approval repository variable enabled on the basis of this document alone.

## Exactly what would be redistributed

- Source: MTGJSON official `AllPrintings.sqlite.xz`, with its matching official SHA-256.
- Product: a newly generated, verified **slim SQLite**, and **one losslessly compressed XZ copy of that exact same SQLite**. Not the complete unfiltered upstream database.
- Current proposed profile: `profiles/v2_3.json`; **8 tables, 224 selected columns and 20 explicit indexes**. Profile and source schema are pinned and fail closed on unexpected changes.
- Includes essentially the complete selected per-printing gameplay and descriptive data, including card and token names, rules/Oracle/printed/original text, rulings, printed/original card text and legalities, set metadata, relationships, artist/printing metadata, EDHREC rank/saltiness and identifiers for Scryfall and commercial partners.
- Does not contain embedded card artwork or purchased card images. Commercial pricing, foreign translation table `cardForeignData`, booster, sealed-product and deck-list tables are omitted. Non-English physical-printing records are **not** filtered out.
- Proposed distribution: unrestricted, free, automatic **public GitHub Releases**, containing raw `.sqlite`, identical `.sqlite.xz`, their checksums, manifest and original applicable notices, potentially every week when retained data or indexes actually change. The database may be consumed by third-party applications and AI agents.
- The repository code's MIT license and the upstream MTGJSON MIT notice **do not independently prove rights to every piece of included third-party data**.

## Primary sources reviewed

1. MTGJSON website license: https://mtgjson.com/license/ — states that its website and content are covered by MIT terms; the license notice must be retained with copies or substantial portions. The upstream source license is also at https://github.com/mtgjson/mtgjson/blob/master/LICENSE.txt.
2. MTGJSON FAQ: https://mtgjson.com/faq/ — MTGJSON collects from multiple providers, specifically including Wizards' Gatherer, Scryfall and TCGplayer. It recommends local processing of downloaded compressed files; this is **not itself an explicit authorization of all possible third-party redistribution**.
3. Wizards Fan Content Policy: https://company.wizards.com/en/legal/fancontentpolicy (page last updated 2017-11-15) — supports many freely available, unofficial fan creations, but explicitly distinguishes original fan creations from verbatim copying/reposting of Wizards' IP, and enumerates card text among Wizards' IP. It states that cases outside the policy require prior written approval, available via https://support.wizards.com, and lack of a response does not constitute approval.
4. Wizards General Terms: https://company.wizards.com/en/legal/terms (page last updated 2025-12-10) — reserves ownership of game data/content and limits copying or redistribution without applicable permission. Any exception or overriding authorization must be substantiated, not assumed.
5. Scryfall API: https://scryfall.com/docs/api — official text could **not** be directly inspected during this review (HTTP 403). Secondary copies describe restrictions on merely repackaging Scryfall data, but are **not treated as verified official terms** here. Ask MTGJSON about the provenance of the retained fields and partner-specific redistribution requirements; review the original Scryfall terms through an accessible official channel before resolving this item.

## Findings, distinctions and open questions

| Topic | What is known | Disposition |
| --- | --- | --- |
| Our own conversion source code | Independently authored software under this repository's MIT license | **Can remain public** |
| MTGJSON aggregation and metadata | MTGJSON publishes a MIT license for website/content, with an attribution/notice requirement | **Positive, but insufficient alone** |
| Wizards card texts, rulings and other original expression | The proposed dataset retains extensive original text. Wizards' Fan Content Policy does not unambiguously authorize bulk verbatim republication simply because the files are free | **Unresolved; seek explicit written clarification/authorization** |
| Third-party partner data | External identifiers, ranks/metrics, artist/printing fields and selected metadata can have mixed provenance; source-per-field rights are not documented for this release | **Unresolved; require MTGJSON provenance/permission clarification, then provider review where necessary** |
| Card art/images | No image binaries are redistributed | **Lower risk than image mirroring; not a substitute for the other permissions** |
| Weekly rebuild and ZIP/XZ packaging | Technical method and validation do not grant legal authorization | **Keep running, with publication disabled** |
| Public Release workflow | Created and gated, but the actual public upload/publish path has not been live-executed | **No live publishing claim** |

**Not an affirmative clearance:** The facts that MTGJSON itself provides an official public SQLite download, that the project adds indexes/removes fields, or that the GitHub release would be free do **not** on their own establish that a third party may mirror a near-complete selection of card texts and related data.

## Profile 2.3 clarification (14 November 2026)

The maintainer explicitly decided to omit `cards.flavorText`, `tokens.flavorText` and `cards.isStorySpotlight` in profile 2.3. The original 2.2 profile and 07nov historical reference are retained, but the standalone main 2.3 profile is now validated against [`contracts/main-profile-2.3.json`](../contracts/main-profile-2.3.json) without reading those older files. Both profiles were built from the same checksum-verified source and compared field by field: [GitHub Actions acceptance run #43570579132](https://github.com/Dreadpool-87/MTGJSON-slim/actions/runs/43570579132). All retained rows and values were identical.

The proposed public dataset **no longer contains these two narrative flavor-text columns or the story spotlight flag**, but still includes Oracle/gameplay card text, original and printed rule text, rulings, and other third-party data. **The public distribution decision remains NOT CLEARED.** This selective removal does not resolve the bulk republication question.

## Decision and release gate

**NO-GO for the public SQLite and XZ database assets as of 2026-11-14.**

Leave `MTGJSON_PUBLIC_DISTRIBUTION_APPROVED` **absent or disabled**. Do not set it to `true` until:

1. The project maintainer has obtained and retained an explicit, attributable written response from MTGJSON about redistribution of a freely published derived `AllPrintings.sqlite` subset, including applicable downstream/partner licensing obligations and required notices.
2. Wizards has confirmed that the described bulk distribution of complete selected card/rules/printed text falls within a permission applicable to this exact use, or provides written authorization; **no reply is not consent**.
3. Any additional providers whose licensed materials remain in the selected fields are identified and their redistribution requirements resolved, with permission or a reviewed exclusion. Don't silently remove gameplay-critical information just to bypass this gate.
4. The response/authorization scope, applicable terms, conditions, permitted contents and any revocation requirements are recorded in this repository and independently checked against the actual profile fields.
5. Maintainer explicitly decides to enable `MTGJSON_PUBLIC_DISTRIBUTION_APPROVED=true` only after those conditions. Perform a separately observed first publish/asset-download acceptance test; do not claim that publication was already proven.

If the answers are negative or unclear, keep the code and tools public and let users **download official MTGJSON from MTGJSON themselves and build the slim database locally**. This preserves the project's utility without adding an unapproved secondary public data mirror.

## Outreach request — MTGJSON (draft; NOT SENT)

**Subject:** Permission and downstream-license clarification for public MTGJSON-slim SQLite Releases

Hello MTGJSON maintainers,

I'm developing an independent, free, open-source converter at https://github.com/Dreadpool-87/MTGJSON-slim . It downloads the official, checksum-verified `AllPrintings.sqlite.xz`, builds a smaller offline SQLite (currently eight tables and 224 selected columns with additional indexes), and provides an identical lossless XZ copy. The project targets Magic deckbuilders, validators and AI tooling. It contains card names and Oracle/printed text, rulings, legalities, alternative card names and printing metadata, artist references, EDHREC metrics and external IDs. It does not distribute card images or pricing tables.

The converter itself is open source, and builds are verified weekly. Before offering the derived SQLite and XZ files as **free public GitHub Release downloads**, could you please confirm in writing:

1. Is public redistribution of such a transformed/filtered MTGJSON dataset covered by your project's MIT terms, subject to carrying your copyright and license notice?
2. Are any included fields supplied under partner terms that prohibit onward public bulk redistribution, especially card/rules/printed text, Scryfall-derived records, EDHREC metrics, IDs or printing/artist metadata?
3. What credits, licenses, disclaimers or source links must accompany the released files, and do you recommend excluding any specific fields?
4. Do you know of a further permission process required by Wizards of the Coast or other upstream rightsholders?

We will leave public dataset distribution disabled until the scope of permitted release is clear. Thanks for your guidance.

**Contact route:** MTGJSON's official website/FAQ links to its Discord and to its GitHub project: https://mtgjson.com/faq/ and https://github.com/mtgjson/mtgjson . Do not present this template as a message already sent.

## Outreach request — Wizards of the Coast (draft; NOT SENT)

**Subject:** Written clarification requested: free, derived MTG card-information SQLite database

Hello Wizards of the Coast team,

I'm maintaining an independent, unofficial, noncommercial Magic: The Gathering community tool: https://github.com/Dreadpool-87/MTGJSON-slim . The project converts the publicly downloadable MTGJSON AllPrintings database into a smaller offline SQLite file for deckbuilders and card validators. It would offer both an uncompressed SQLite and a lossless XZ copy through free public GitHub Releases, without registration or paywalls. There are no card-image binaries and no sale of the dataset.

The database would still contain selected full card/Oracle/printed rules text, card names, rulings, original and printed rule text, printing/set information, format legalities and identifiers, across many cards and printings. We understand that your Fan Content Policy supports many noncommercial fan creations but does not automatically cover verbatim republication of Wizards IP. We are not treating that policy as prior authorization.

Could you confirm in writing whether **bulk public redistribution of this described derived card-data database** is permitted under an existing Wizards policy, or whether specific written permission is necessary? If it is permitted, please specify the scope and required credit/disclaimer; if not, please identify any acceptable alternative (for example, distributing only the converter so users fetch source data themselves).

We will not enable public dataset releases without clarity. Thank you.

**Contact route:** https://support.wizards.com, expressly identified by the Fan Content Policy for content outside its ordinary scope. Do not present this template as a message already sent.

## Follow-up / provenance

- Research date: 2026-11-14 (public policies viewed on this date).
- Reviewer: ChatGPT (AI-assisted technical and permissions review; not legal counsel).
- Project profile: `profiles/v2_3.json` (formerly `profiles/v2_2.json`; only three narrative columns removed).
- No permission responses have been received, no outbound inquiries have been sent, and no public dataset Release has been created by this review.
- Reassess after receiving attributable written answers or if source fields, sources, policies, or desired distribution scope change.
