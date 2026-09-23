# ADR-013 — Provider-neutral identity and match ingestion

Date: 2026-09-18. Status: accepted architecture; live provider activation pending review.

## Context

DojoPulse should support player-name/TEKKEN-ID entry and automatic match discovery.
The current Match requires an uploaded ReplayAsset. Reviewed public statistics sources expose
metadata, while the target punish metric requires richer time-resolved evidence. Provider
permissions, coverage and replay compatibility differ.

## Options

1. Keep video as the only representation of a match.
2. Couple Match and coaching directly to one community API or undocumented game endpoint.
3. Separate stable identity, match metadata and replay representations behind capability-gated
   adapters, retaining uploaded video as an evidence fallback.

## Decision

Choose 3. Introduce PlayerGameIdentity, versioned MatchSource policy, source-record assertions
and ReplaySource representation design. Keep canonical match/event/statistical contracts
provider-independent. Distinguish OFFICIAL, COMMUNITY_PUBLIC_API, REVERSE_ENGINEERED and
USER_UPLOAD access; record upstream ancestry separately. Approve operations and usage purpose,
not just provider names. No undocumented transport is implemented.

## Reasoning

Metadata can satisfy history/results without video but cannot establish a missed punish.
The archived EWGF implementation is useful research, not a contract for its current API.
Wavu provides a documented global metadata feed, not a documented per-player payload service.
A public identity match is not proof of ownership. Explicit unknowns prevent inaccurate
coaching and silent commercial/reliability assumptions.

## Consequences

Add neutral typed contracts and offline schema tests now. Keep adapters free of ORM/domain
conclusions. Before live ingestion, migrate the mandatory Match.asset relation and its
lifecycle callers, backfill upload provenance, review live permissions and test fixtures.
Preserve source-scoped IDs, raw/canonical versions, expiration, coverage gaps and immutable
provenance. A metadata import is successful even when deeper analysis needs a video.
Do not add a broker, scraping service, native game integration or replay simulator now.

## Reconsideration trigger

Publisher-supported API/export; reviewed community contract; stable name-resolution endpoint;
permitted native payload with validated decoder; demonstrated metadata coverage gap/cost;
provider terms or upstream protocol changes. Revisit a provider decision without redesigning
the canonical event/player-model pipeline.

See [research](../research/tekken-match-sources.md) and
[architecture and migration contract](../architecture/match-ingestion.md).
