# EWGF public API activation review

Decision: **NOT ACTIVATED**. This is an engineering access review, not a grant of data rights.
Requested DojoPulse purpose: player-selected recent-match history and retained provenance for
a potential commercial training product. No provider messages, accounts or subscriptions were
created, no credential was requested in chat, and no authenticated endpoint was called.

## Rechecked public evidence

The [published API documentation](https://ewgf.gg/api-docs) describes bearer-key authentication,
ID-based battle lookup, and paid-tier profile lookup. Its free plan is described for personal
projects/experimentation. Its paid plan description does not by itself establish DojoPulse's
rights to retain, redistribute or commercially analyze the data. No documented name resolver
or replay-payload download appeared in the endpoint list.

The error reference documents a stable `error.code`, distinguishes an absent player from an
existing player with zero battles, restricts submitted IDs to alphanumeric strings of at most
20 characters, and describes hourly quota reset headers. These are provider-specific input and
error rules, not permission to change canonical ID casing or infer a live match schema.

The [terms page](https://ewgf.gg/terms) again yielded no substantive terms in text extraction.
The API page's expandable match examples/field reference were still absent from extracted text.
The available browser-control tool reported no available browser, so those panels could not be
inspected interactively. No protected route, documentation-bundle access workaround or legacy
private endpoint was used. The previous archived DTO remains unsuitable as a current contract.

## Activation decision and remaining inputs

| Requirement | Status | Concrete input needed |
|---|---|---|
| Published external interface | Verified documentation only | Use documented external routes exclusively |
| Intended usage rights | Unresolved | Provider terms or written approval covering intended product use, caching, retention, attribution and deletion |
| Credential and effective tier | Not provisioned | Owner configures a provider-issued server key in private runtime configuration after review; never paste it into source or chat |
| Current response schema | Unverified | Permitted, redacted authenticated fixtures: ordinary matches, unknown ID, zero battles, delayed/capped history and failures |
| Identity mapping | Unverified for current API | Evidence relating submitted TEKKEN ID to returned persistent IDs, case and formatting rules |
| Operational behavior | Unverified | Shared quota enforcement, bounded compressed responses, cancellation, error handling and coverage tests |
| Native gameplay payload | Not established | Separate permitted source and validated decoder; not part of metadata activation |

There is no transport implementation to enable by supplying a key alone. A subsequent change
must normalize approved fixtures, implement the allowed public transport, pin an expiring
purpose-specific approval, and validate it before exposing real lookups. Free or paid access
alone is not treated as commercial clearance.

## Work completed independently

The session-authenticated UI/API supports signed, expiring, owner-bound candidate confirmation,
explicit processing consent, queued imports, private paginated history, source provenance,
unknown version/character mappings, incomplete coverage, and revocation/deletion. Only local
synthetic adapters can resolve/import, with DEBUG, LOCAL_MATCH_IMPORTS and staff gates.
The worker is separate from HTTP. No backend or browser call accesses EWGF, Wavu or Tekken.
This validates the product flow while keeping provider activation an explicit later change.
