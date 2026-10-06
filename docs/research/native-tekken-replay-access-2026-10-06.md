# Direct Tekken replay acquisition investigation

Research date: 2026-10-06. Scope: public documentation, bounded GitHub repository searches,
public file inventories and pinned source inspection. No undocumented/private Tekken request,
game login, credential acquisition, native replay download, game control or third-party code
execution occurred. No videos/native payloads acquired. Personal profile IDs and player rows
are not retained in this report.

## Answer and confidence

Tekken has a replay backend used by its official client. Public evidence also establishes
third-party access to match-list metadata. Saying no Tekken replay API exists, or that direct
native acquisition is technically impossible, would overstate the evidence.

This review did **not verify** a permitted external operation that accepts a TEKKEN ID and
supplies playable native bytes or ready video. Metadata retrieval, native acquisition, decoding
and video rendering are separate capabilities. No supported external native decoder/renderer
was established by the inspected implementations. External native access remains UNVERIFIED,
with X01 BLOCKED on technical/usage review; this does not rule out a private implementation
or future publisher integration.

## Primary evidence

| Source / revision | Observed behavior | Limit |
|---|---|---|
| [Wavu data description](https://wank.wavu.wiki/about), rechecked 2026-10-06 | Maintainer says its collector queries the same replay-list endpoint as Online Replays approximately every 60 seconds for the latest 999 ranked records | No native-download operation, video or publisher authorization for our access established |
| [Wavu API](https://wank.wavu.wiki/api), rechecked 2026-10-06 | JSON metadata windows and ratings; current names can differ from match-time names | No documented video/native-payload download. Inspected response field inventory remains separately dated 2026-09-18 |
| [EWGF API](https://ewgf.gg/api-docs), rechecked 2026-10-06 | Bearer-authenticated per-ID battle and profile operations | No documented video/native-download endpoint; current authenticated schema not tested |
| EWGF backend, `ebadab559f09bd9d93cb82fe035b28ba21a64101` | WavuService fetches Battle lists. Battle contains participant/result/version/rank metadata. Inspected PolarisProxyService methods fetch profile statistics and leaderboards | These paths do not demonstrate playable downloads or decoding. Archived code does not characterize the closed-source continuation or the complete delegated upstream proxy |
| Cathesilta recorder, `ed6f393a9ea8f9b610cab41e19846dccb06934d9` | README requires downloading replays inside Tekken. Recording code uses screenshots, fixed screen regions, keyboard actions and a recorder hotkey to create MP4s | This is playback capture, not a native-download API or standalone renderer; current game/UI/hardware compatibility and permitted automation untested |
| GamesDat, `d1cb422b6dc000e377574ea0774a30d6770d722d` | README marks Tekken support untested. Source watches SaveGames with `*.*`, says the extension needs actual-game testing, and is excluded by the inspected test-data helper | No Tekken payload parser, frame/input decoder, API acquisition or renderer demonstrated by these files; their game/storage assumptions are not accepted as verified facts |
| [Tekken Replay Database](https://github.com/joeycf/tekken-replay-database), observed tree `d1548911983e49809375e4fba3a210aadba8da80` | README describes YouTube Data API discovery and title/description parsing into a video index | Recorded-video discovery, not footage fetched from Tekken or verified TEKKEN-ID attribution |

Pinned source references:

- [EWGF WavuService](https://github.com/ewgf-gg/ewgfgg-backend/blob/ebadab559f09bd9d93cb82fe035b28ba21a64101/src/main/java/org/ewgf/services/WavuService.java),
  [Battle](https://github.com/ewgf-gg/ewgfgg-backend/blob/ebadab559f09bd9d93cb82fe035b28ba21a64101/src/main/java/org/ewgf/models/Battle.java),
  [PolarisProxyService](https://github.com/ewgf-gg/ewgfgg-backend/blob/ebadab559f09bd9d93cb82fe035b28ba21a64101/src/main/java/org/ewgf/services/PolarisProxyService.java).
- [Cathesilta README](https://github.com/Cathesilta/tekken8_oneshot_replays/blob/ed6f393a9ea8f9b610cab41e19846dccb06934d9/README.md)
  and [recorder](https://github.com/Cathesilta/tekken8_oneshot_replays/blob/ed6f393a9ea8f9b610cab41e19846dccb06934d9/script/Tekken8/recorder_t8.py).
- [GamesDat source](https://github.com/codegefluester/GamesDat/blob/d1cb422b6dc000e377574ea0774a30d6770d722d/GamesDat/Telemetry/Sources/Tekken8/Tekken8ReplayFileSource.cs)
  and [test exclusions](https://github.com/codegefluester/GamesDat/blob/d1cb422b6dc000e377574ea0774a30d6770d722d/GamesDat.Tests/Helpers/FileWatcherTestData.cs).

The absence of video fields in a Battle DTO cannot prove the game has no separate native
download operation. No game request was reproduced. These are bounded findings, not an
exhaustive description of Tekken internals or proof of every searched repository's behavior.

## Playback, conversion and expiry

The [official replay feature](https://tk8.tekken-official.jp/mode/replay.php) provides in-game
playback/takeover. The version-specific [v3.00.02 notes](https://www.bandainamcoent.com/news/tekken-8-patch-notes-v3-00-02)
say prior replay data becomes unplayable and prior online data is deleted. This demonstrates
runtime/version dependence and expiry risk, not an input-byte schema, universal TTL, current
installed version or permission for a standalone emulator.

If a permitted source supplies native bytes, the proposed video route is: discover the match,
acquire the payload, reproduce compatible playback, encode/validate video and attach it to the
canonical match. Acquisition alone does not solve rendering. A compatible official runtime is
one candidate; no supported standalone renderer was found. Exact payload format, clocks,
inputs, seeds/state, required content/entitlements and exportable events remain unverified.
Reconstruction or takeover cannot substitute for original match evidence without a validated
representation contract and the existing gameplay quality gates.

## Usage and provider classes

The [EULA linked for Steam app 1778820](https://store.steampowered.com/eula/1778820_eula_0)
is dated 2022-04-01 on the retrieved page. Sections 3/4 describe game-use conditions, a
personal/noncommercial license, reverse-engineering/modification restrictions and security
measures; section 12 addresses unauthorized tools. These are review inputs, not a legal
opinion on enforceability, regional/additional terms or every permitted video use. No external
replay-acquisition or commercial server-rendering grant was established. Game ownership and
an open-source code license do not independently settle those rights.

| Our access | Class / disposition |
|---|---|
| In-client replay viewing | OFFICIAL feature; player-created recording enters USER_UPLOAD with verified lineage |
| Documented Wavu/EWGF metadata API | COMMUNITY_PUBLIC_API; M04/M05 gates remain |
| Undocumented game requests or unreviewed native integration | REVERSE_ENGINEERED; disabled pending explicit technical and usage review, regardless of publisher-owned origin |
| Consented original recording/export | USER_UPLOAD; existing media, attribution and scientific gates |
| Future publisher-authorized external payload/video operation | OFFICIAL only with evidence of that authorization and contract |

## Engineering consequence and next evidence

Retain [ADR-026](../adr/ADR-026-id-search-and-private-recording-companion.md) as a staged fallback,
not proof that a companion is the only possible solution. Do not build a native client from
metadata names, archived DTOs or a file-watcher support badge.

Before direct acquisition implementation, obtain a permitted operation contract or explicit
technical/usage review covering authentication/entitlement, ID-to-match-to-payload mapping,
schema, version/content compatibility, availability/expiry, quotas, retention/redistribution
and allowed playback/rendering. Then qualify permitted redacted fixtures and supported-build
playback against the same canonical event rules. Provider/publisher contact requires an
owner-authorized contact task; no messages or account creation occurred here.

Public-source research is complete for this scope; native endpoint execution and payload
validation are not. M04/M05, M22.09, X01 and G1-G6 remain gated. The practical architecture
can support direct acquisition later if those prerequisites are established.

## Browser-only managed-capture usage follow-up, 2026-10-06

The [official video policy](https://www.bandainamcoent.co.jp/english/videopolicy/), enacted
2022-01-26 and retrieved 2026-10-06, covers individual noncommercial fan videos subject to
game terms and third-party rights. It permits certain platform monetization functions,
excludes legal-entity production/direction and allows game-specific policies to take priority.
Our inference: those conditions do not establish permission for DojoPulse's automated
managed playback/capture/analysis service. Personal fan recording and commercial runtime
operation require separate scope review; this is not a legal opinion or a claim that all
recording is prohibited. No publisher approval or contact occurred.

[ADR-027](../adr/ADR-027-browser-only-replay-acquisition-feasibility.md) now prioritizes actual
browser-only acquisition proof. Native app enumeration failed with an absent control pipe;
zero game trials were run. The [offline qualification tool](../architecture/replay-acquisition-feasibility.md)
cannot resolve these permissions or substitute synthetic evidence for actual replay access.
