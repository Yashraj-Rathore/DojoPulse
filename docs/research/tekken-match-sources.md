# Tekken match ingestion: source investigation

Research date: 2026-09-18. Scope: public documentation, archived implementation inspection,
and one documented Wavu API response. No private Tekken endpoint was called, authenticated,
reproduced or implemented. No playable replay payload was acquired. Findings are bounded to
the evidence below, not a declaration of commercial permission or full coverage.

## Findings that determine the design

1. Match metadata can remove the upload requirement for history/results and aggregate matchup
   reporting. The reviewed community interfaces do not supply the temporal evidence required
   by DojoPulse's block-punish metric.
2. A record named a replay is not necessarily a playable replay payload, video, input stream
   or event log. Metadata import must succeed independently of gameplay analysis.
3. Persistent identity resolution is distinct from authentication. A name search can suggest
   a profile; selecting a public TEKKEN ID does not prove account ownership.
4. Source access class and upstream lineage are separate. A community's documented API stays
   COMMUNITY_PUBLIC_API even if that community obtains upstream data using an undocumented
   game-client interface. That ancestry still matters to permission, reliability and coverage.

## Current flow: online replay to community metadata

Wavu describes polling the game client's Online Replays interface approximately once per
minute for the latest 999 ranked records, then persisting its own history. Its author reports
collection gaps and says older upstream records cannot be recovered through that collector;
patches commonly remove them. This is the maintainer's description, not a guarantee that
every native query or future game build has identical behavior. Wavu's own historical database
can therefore retain metadata after the native replay has disappeared.
[Maintainer's data description](https://wank.wavu.wiki/about)

The game's in-client replay feature is OFFICIAL. An independently reproduced, undocumented
connection to its server is REVERSE_ENGINEERED, even if the server belongs to Bandai Namco.
No publisher-supported external developer replay API, public payload schema or commercial
access contract was located in this review. Absence from this search is not proof none exists.

Current official 3.02.01 notes explicitly invalidate playback of older downloaded/local
replays and delete older Online Replay data. Version change and upstream availability must
be tracked independently from DojoPulse retention. There is no basis here for inventing a
universal seven-day or thirty-day upstream TTL.
[Official update impact](https://www.bandainamcoent.com/news/tekken-8-patch-notes-v3-02-01)

## Wavu Wank: documented community API

GET /api/replays?before=T returns a global time slice satisfying
T - 700 < battle_at <= T, newest first. It is not documented as a per-player history endpoint.
Accept compressed responses and keep one request in flight; the documentation describes
one request per second for archival traversal, not a purchased SLA or unlimited entitlement.
Names are current names at retrieval, not necessarily names used during the match.
Some site pages support ?_format=json, but that is not a stable documented search contract.
[API documentation](https://wank.wavu.wiki/api)

A single public historical slice was read for schema verification. It returned 12,440 records;
only field names/types were retained, not those players' rows. This confirms that the site's
approximate page size is not a fixed limit. The observation is not evidence of present-day
coverage or correctness. A new schema can add/remove optional fields.

Observed exact fields:

| Scope | Fields | Interpretation / limits |
|---|---|---|
| Match | battle_id, battle_at, battle_type, game_version, stage_id, winner | external battle key, Unix timestamp, raw enum/version codes, stage code, winner slot |
| Both player slots (prefix p1_ / p2_) | polaris_id, user_id, name, chara_id, power, rank, rounds | public identity, distinct numeric upstream ID, current display name, character code, prowess, rank code, rounds won |
| Both slots | area_id, region_id, lang | provider/game classifications; not reliable physical-location assertions |
| Both slots | rating_before, rating_change | Wavu-enriched rating context, not native frame-level performance |

The observed user_id values are integers large enough to exceed JavaScript's exact integer
range; parse losslessly at the adapter and expose identifiers as strings. Match fields and
the separately enriched rating fields also appear in the pinned legacy
[Battle model](https://github.com/ewgf-gg/ewgfgg-backend/blob/ebadab559f09bd9d93cb82fe035b28ba21a64101/src/main/java/org/ewgf/models/Battle.java).

No input samples, individual round timings, move IDs, health timeline, positions, block/hit
events, resource timeline, punish judgments, replay bytes or video URL appeared in that
response. Unknown fields in a future response require schema review; they are not silently
promoted into gameplay evidence.

Retained research artifact: [observed field/type inventory](wavu-schema-observed-2026-09-18.json).
It contains no player rows. The committed adapter fixture is explicitly synthetic.

## EWGF.GG: live API versus legacy source

The live public interface documents token-authenticated battle lookup by TEKKEN ID and profile
lookup, including a bulk profile request of up to 50 IDs. Free access is described as 100
requests/hour with the last 50 battles delayed 24 hours; Pro is described as 1,000/hour and
the last 100 battles without that delay. Profiles require Pro. Budget from response metadata
and Retry-After/X-RateLimit headers; these dated limits must be rechecked before activation.
The public endpoint list does not include name search or replay-payload download. A website
search box is not a documented developer endpoint.
[Current API documentation](https://ewgf.gg/api-docs)

No API key was supplied or created, so authenticated response fields, effective coverage,
retention, current numeric code mappings and playable payload availability were not tested.
The documentation's expandable field references were not accessible in the text extraction.
Its terms page yielded no usable terms text; reading its public documentation bundle returned
403, and was not bypassed. Commercial use, caching, attribution, redistribution, derivative
analytics and deletion obligations therefore remain unresolved.
[Published terms location](https://ewgf.gg/terms)

The public backend is archived. Its README announces a closed-source continuation; GitHub
shows archival on 2025-11-13, while the README names 2025-10-16. Inspected revision:
ebadab559f09bd9d93cb82fe035b28ba21a64101. Its AGPL-3.0 source license is distinct from permission
to collect or commercially reuse service/game data. No implementation was copied into DojoPulse.
The legacy data flow is acquisition, message queue, batched persistence and aggregate updates.
It provides useful lessons on idempotency, overlapping time windows and version-aware statistics,
but no justification to add RabbitMQ to our small Django prototype.
[Archived project](https://github.com/ewgf-gg/ewgfgg-backend)

The legacy PlayerService assigns polarisId to the DTO field tekkenId, retains a separate
numeric playerId, and searches its own database by name/Polaris ID. Its old
/player-stats/search route is not a live public API contract and must not be called on that
assumption. Preserve ID case and source assertions; never derive a platform account or merge
cross-platform identities from a display name.
[Pinned identity handling](https://github.com/ewgf-gg/ewgfgg-backend/blob/ebadab559f09bd9d93cb82fe035b28ba21a64101/src/main/java/org/ewgf/services/PlayerService.java)

A second implementation, TK8-thing, consumes Wavu metadata to calculate rank distributions,
character usage and wins. This corroborates the metadata-analysis use case, not a playable
replay decoder. Its older extraction approach is not needed or executed here.
[Project and methodology](https://github.com/elgonio/TK8-thing)

## Exact capability boundary

| Information | Reviewed community metadata | Actual native replay payload | Uploaded recording |
|---|---|---|---|
| Participants, characters, result, rank context | Yes where fields exist; schema/mapping pinned | May be in header; format not verified here | Can be reviewed if visible |
| Match time, raw build, stage | Available in Wavu sample | Must verify actual header/clock | Metadata/reviewer confirmation required |
| Complete player history / no missing matches | Not guaranteed; delays, caps and collector gaps | One payload cannot establish history completeness | User capture log required |
| Inputs and ordered gameplay timeline | Not supplied by inspected interface | A compatible runtime can play native replay; exportable inputs/schema unverified | Visible input overlays can be reviewed |
| Positions, resources, block/hit/recovery, move identity | Not supplied | Would require validated decoding or version-compatible game simulation | Narrow reviewed/CV evidence possible |
| Eligible punish and success/failure | Cannot infer from result/rank/round counts | Requires verified observations + our deterministic situation rules | Same situation rules |
| Video / browser-playable stream | Not supplied | Do not assume native payload is media or browser-playable | Yes, if supported encoding |
| Practice adherence/outcomes | Not established | Only if it is an actual verified practice recording/payload | Separate practice recording supported |

Payload internals remain explicitly UNVERIFIED. This investigation cannot honestly say
exactly which bytes encode inputs, simulation state, seeds or authoritative contacts.
No reviewed source offers a supported standalone Tekken replay decoder. Native replay bytes,
if later permitted, still require format/version/validation work before they can create events.
Metadata is sufficient for match-history import today in principle; it is insufficient for
the existing measured-punish loop.

## Activation questions

For every operation: permitted interface and authentication; service terms and commercial scope;
rate/concurrency/byte limits; caching/redistribution/attribution; identity and deletion duties;
schema and version support; payload retrieval/expiry; source gaps and operational owner.
For undocumented game access also require an explicit technical/security/usage decision,
account/anti-cheat implications, credentials handling, platform entitlement and a supported
alternative assessment. User permission to design adapters does not approve these operations.

No provider was commercially cleared by this research. No communication was sent to providers.
A documented API is the preferred evaluation path; the user-upload path remains available.

Follow-up: [EWGF activation review, 2026-09-19](ewgf-activation-review-2026-09-19.md)
records the rechecked public interface, unresolved rights/fixture requirements and disabled
activation decision. The local player-link/sync/history flow now exists independently of live access.
