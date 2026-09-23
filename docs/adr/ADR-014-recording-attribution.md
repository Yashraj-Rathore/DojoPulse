# ADR-014: Reviewed recording attribution preserves imported match identity

Date: 2026-09-23. Status: accepted for the local operator workflow.

## Context

Imported metadata identifies a played match but does not establish gameplay opportunities.
Creating another Match for its recording would split history and risk duplicate contributions.
Treating an upload declaration as verified attribution would allow unrelated footage to alter
the player model. Replacing Match.asset must also leave old event and evaluation lineage intact.

## Decision

Create an owner-scoped USER_UPLOAD ReplaySource and private ReplayAsset against the existing
match. Store the submitted attribution claim, its digest, metadata revision and recording hash.
At submission the source is PENDING_REVIEW; canonical facts and Match.asset remain unchanged.
Require explicit processing consent and confirmation of player/opponent IDs, player slot,
original play time, build, purpose, session, characters and real/synthetic classification.
Reject conflicts with known canonical facts and reject stale metadata revisions.

Local staff uploads are gated by DEBUG/LOCAL_OPERATOR_UPLOADS. Stream bounded MP4 bytes outside
the transaction, then acquire the owner lock and recheck target ownership, availability and
metadata before committing. A request UUID and content/claim hashes make retries idempotent.
Known duplicate bytes and multiple active recordings for one match are rejected. Failed commit
removes the newly created file. Decoding remains in the existing bounded asynchronous worker.

After successful media validation, the owner/operator must inspect the recording and run
`review_recording` with its hash, an exact-build knowledge version and a review note. This is
an explicit human attestation, not automatic identity or chronology recognition. Real evidence
requires approved knowledge and a verified build. Approval fills previously unknown canonical
facts and selects Match.asset. Historical gameplay facts and knowledge membership cannot change.
Gameplay annotation still requires the separate independent-review publication workflow.

Migration 0005 adds ReplaySource.attribution_state and attribution JSON. Existing upload sources
default to NOT_REQUIRED to preserve their established review path. New imported-match sources
transition PENDING_REVIEW -> APPROVED -> WITHDRAWN on deletion. A failed/stale attribution is
removed and uploaded again; this local workflow does not implement a source-correction editor.

Reprocessing reuses the asset, creates a new AnalysisRun and preserves current published
contributions until another reviewed publication replaces them. The worker rejects a changed
source hash. GameplayEvent source identity is resolved through its immutable AnalysisRun.asset,
and a withdrawn/replaced source is ineligible even if the canonical match remains present.
Recording deletion cancels/fences jobs, redacts evidence, invalidates dependent conclusions and
detaches the optional asset. Imported match/source metadata survive; upload-only match deletion
keeps its prior behavior. Account deletion also tombstones matches with pending attachments.

## Consequences and limits

The canonical Match/GameplayEvent/player-model pipeline stays provider-independent. No live
provider, undocumented endpoint, native decoder or commercial clearance is introduced.
Current support is the single Jin/Jin capture profile and one continuous match/practice block.
Hosted direct/resumable uploads, hostile-media isolation, real attribution accuracy and capture
usability remain separate release requirements. Cross-provider match merging is not implemented.
Frozen evaluation memberships are not rewritten when a recording is attached or replaced.
