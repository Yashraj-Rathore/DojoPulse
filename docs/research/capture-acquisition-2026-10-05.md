# Footage acquisition investigation - 2026-10-05

User requested searching YouTube or obtaining recordings through the game after confirming
no existing capture paths/reviewers were available. Scope: public documentation and read-only
local installation inventory. No video was downloaded, personal player rows collected, game
started, account contacted, reverse-engineered endpoint accessed or recorder code executed.

## Candidate routes and actual findings

| Route | Evidence | Decision / unresolved constraint |
|---|---|---|
| Installed Tekken 8 replay viewer | Steam library inventory lists app 1778820 installed; no running Tekken process or Tekken/Polaris video was found in the usual local video directory | Practical candidate for player-created original recordings. Installation is not verified in-game build evidence, usable replays, processing rights or 20 captures. Native game control is unavailable in this session |
| Community Wavu API | [Maintainer API](https://wank.wavu.wiki/api) and [about](https://wank.wavu.wiki/about), rechecked | COMMUNITY_PUBLIC_API match metadata. No video/input/event payload is documented; existing live usage gates remain. It cannot supply the target observation dataset |
| Open-source local recorder | [Cathesilta/tekken8_oneshot_replays](https://github.com/Cathesilta/tekken8_oneshot_replays), README reviewed | Describes downloading replays **inside the game**, then recording local playback using ShadowPlay. GPL-3.0 code license does not grant game-data/recording rights. No code copied, installed or run |
| Public YouTube replay channels | Public search found the Tekken 8 Replays channel reference; direct channel enumeration was unavailable | No exact-build, required-overlay, licensed/consented full-match set verified. Titles/search visibility are discovery evidence only. Do not scrape/download a channel or enroll its players |
| Public trailer on Commons | [Tekken 8 reveal trailer](https://commons.wikimedia.org/wiki/File:TEKKEN_8_%E2%80%93_Reveal_Trailer.webm), metadata/license page reviewed | 2022 promotional video, 4K WebM, edited and outside the match profile. The page claims CC BY 3.0 but also flags the external licence as not yet independently reviewed. Rejected as G1/game-fact/held-out evidence; not downloaded |

The directory/process inventory is bounded, not proof no recordings exist anywhere on the
computer. Private Steam account identifiers and unrelated installed titles are not retained.
No universal current game version, replay TTL or rights conclusion is inferred from installation.

[YouTube licence help](https://support.google.com/youtube/answer/2797468?hl=en) distinguishes
standard and Creative Commons licences and requires attribution when reusing CC material.
[YouTube terms](https://www.youtube.com/t/terms), Permissions and Restrictions, constrain
downloads and automated access. A licence/discovery result does not by itself prove consent,
unseen evaluation independence, exact build, overlay coverage or a permitted acquisition method.
Creator-supplied originals with appropriate permissions are another candidate route, not activated.

[Official v3.00.00 update impact](https://www.tekken-official.jp/tekken_news/?p=2427), dated
2026-03-17, says older downloaded/local replays become unplayable and older Online Replay
data is deleted by that update. This is version-specific evidence of expiry risk, not a claim
that 3.00.00 is current, a universal time-based TTL or a public external download API.

## Result

Zero qualifying captures acquired; exact installed in-game build unverified; qualified expert,
two reviewers and adjudicator still pending. G1/G2 remain NOT_RUN. Prepare the official-client
capture procedure and local [observability assessment](../architecture/observability-assessment.md),
then acquire purpose-consented exact-build originals and perform independent review. Direct
undocumented Tekken transports remain disabled under the original provider-access requirement.
