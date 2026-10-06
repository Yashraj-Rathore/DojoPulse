# ADR-026: ID search with a private Windows recording companion

Date: 2026-10-06. Status: accepted product direction; local source companion implemented under D041, real integrations not activated.

## Context

The owner wants TEKKEN-ID search to show matches with recordings playable in DojoPulse,
without repeated manual video uploads, and delegated the choice of approach. Rechecked
[EWGF documentation](https://ewgf.gg/api-docs) offers per-ID recent battles and profile
metadata, but no documented video or native-payload download. [Wavu's API](https://wank.wavu.wiki/api)
offers a global metadata feed. Neither establishes the desired video capability.

The [community recorder](https://github.com/Cathesilta/tekken8_oneshot_replays) describes
downloading replays inside Tekken and recording playback with ShadowPlay. That is a feasibility
lead, not verified current compatibility or permission for a commercial integration. Actual
payload internals remain unverified. No publisher-supported external video API was located.

## Decision

Choose a hybrid: provider-neutral ID-based metadata discovery plus owner-authorized recording
sync from a Windows companion. Evaluate EWGF first for metadata because its documented
per-player operation avoids scanning a global archive. It remains COMMUNITY_PUBLIC_API and
disabled until M04/M05 usage, credential, identity and schema requirements are met. Wavu is
an alternative metadata source, not an automatic failover or a video service.

Build the companion in stages. First pair it to a DojoPulse owner, let that owner select a
recording folder, and sync completed supported MP4s through M06's resumable evidence path.
The player still creates or exports recordings in this stage; it removes the repeated manual
upload, not replay creation. Exact attribution remains a separate reviewed operation.

Next investigate recording available in-client replays with the installed game. This stage
requires a separate technical and usage review, version/expiry tests and real capture evidence.
Do not implement game control, memory access, private endpoints, replay decoding or recorder
code installation as part of the folder-sync stage. A licensed external video source, if later
available, can replace capture without changing canonical events or player models.

ID search never grants access to another owner's recordings. Play appears only for media the
requesting owner may access. Missing media is an explicit state, never a promised queued video
unless an actual capture/upload job exists. Video playback, media validation, match attribution
and coaching approval are distinct states.

## Alternatives and consequences

- ID-only website video retrieval: no supported source verified; keep as a future capability.
- Wavu archive scanning per search: unsuitable for bounded interactive discovery; no video.
- Cloud Tekken rendering: defer; no approved acquisition/licensing/runtime path or cost evidence.
- YouTube discovery: supplementary permitted footage only; names do not establish identity,
  ownership, download permission, complete history or exact match attribution.
- Manual upload: retained for other platforms, unsupported capture tools and companion recovery.

Add M22 for companion requirements. Its first implementation is independent of live metadata
activation: recordings may create upload-only matches using existing review gates. It does not
change the first scientific scope or grant G1-G6, native replay or hosted release approval.

See the [companion contract](../architecture/recording-companion.md) and
[provider-neutral ingestion](../architecture/match-ingestion.md).

Follow-up public [native-access research](../research/native-tekken-replay-access-2026-10-06.md)
confirms replay-list access exists but does not verify external playable-payload retrieval or
a supported renderer. This hybrid is a staged fallback, not proof that direct acquisition is
impossible. X01 remains available if technical and usage evidence establishes a permitted path.
