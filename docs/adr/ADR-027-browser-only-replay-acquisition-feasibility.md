# ADR-027: Prove browser-only replay acquisition before product automation

Date: 2026-10-06. Status: accepted product priority; real acquisition and managed operation blocked.
Supersedes ADR-026's primary customer journey and implementation order; retains its implemented
recording-sync module as an optional fallback.

## Context and decision

The owner requires an easy website experience without downloads, pairing, choosing folders,
moving recordings or operating Tekken for each analysis. The primary target is:
sign in -> enter/confirm TEKKEN ID once -> available matches -> Analyze -> private playback/results.
Name lookup remains a separately permitted capability. Metadata import without video remains useful.

Move M22.09 ahead of companion distribution M22.07-08. First prove one permitted real public
replay from identity lookup through acquisition, compatible playback, automatic capture and
private DojoPulse delivery on the same match. Separately test a console player's public online
replay through the PC client; cross-play is not proof of replay retrieval. Private/offline
console replays are outside this promise. Preserve failures and unavailable historical matches.

Evaluate game-assisted playback capture on an operator-owned test PC as a candidate, not a
selected commercial infrastructure. A future documented video export may be preferable. No
supported standalone native renderer was established. No private endpoint, memory hook,
anti-cheat bypass, community recorder installation or unattended game control is implemented.

The current [source investigation](../research/native-tekken-replay-access-2026-10-06.md)
shows the community recorder requires already-downloaded in-game replays. Its recording
loop does not establish automatic ID lookup/download. Separate these stages in acceptance.
The [Steam EULA](https://store.steampowered.com/eula/1778820_eula_0), rechecked 2026-10-06,
provides review inputs for personal use, hardware control and unauthorized tools; no managed
commercial playback/capture grant is established. A local feasibility review cannot authorize
a hosted service. No contact, account creation, purchase or usage approval occurred.
The source investigation's video-policy follow-up provides an additional purpose-specific
review input; recording rights and runtime/automation permission are distinct.

## Evidence-first implementation

Implement a bounded offline qualification plan/report, not a pretend acquisition transport.
The tool checks supplied private evidence hashes, complete stage coverage, exact declared
build compatibility, explicit platform/origin, absence of customer desktop/operator intervention,
same-video delivery evidence, elapsed time, retry/byte limits and review scope/expiry.
Its output is always non-promoting: declarations and matching bytes cannot prove game facts,
current permissions, current backend delivery, scientific validation or release approval.

The installed Computer Use package was initialized, but native enumeration failed with
`failed to connect native pipe ... (os error 2)`. No game input occurred. The dated zero-trial
report therefore remains NOT_RUN. Restore supported native control before the operator trial;
do not substitute synthetic captures or repeated manual setup for the requested customer journey.

After actual evidence and usage review, choose the acquisition adapter/runtime. A Windows
GPU/game runtime cannot be presumed to run in the existing Linux Cloud Run media jobs.
Review permitted runtime placement, entitlements, account/session isolation, queue limits,
patch invalidation, available replay age, quotas, cancellation, privacy and measured cost first.
Then implement actual browser job/progress/error controls using M16/M17 patterns.

## Domain invariants

The service boundary remains PlayerGameIdentity -> MatchSourceRecord/ReplaySource -> validated
ReplayAsset -> reviewed attribution -> versioned observations -> canonical GameplayEvent/player
model. A provider adapter neither creates coaching conclusions nor invents events from metadata.
Public IDs are not account authentication or a grant to another owner's private media. Preserve
access class, upstream lineage, external IDs, source and capture builds, checked-at time, known
expiry and private retention separately. Unknown expiry stays unknown; patches can invalidate
native playback without erasing an independently permitted recording.

M22.11 defines the zero-install journey; M22.12 qualifies preparation tooling; M22.13 requires
the real first-replay proof; M22.14 covers console and managed-service qualification. M13.10
requires the actual browser experience. M22 remains PARTIAL, M04/M05 and X01 retain their
independent usage/technical gates, and G1-G6 remain NOT_RUN.

See [qualification procedure](../architecture/replay-acquisition-feasibility.md).
