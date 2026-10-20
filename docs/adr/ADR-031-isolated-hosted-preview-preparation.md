# ADR-031: Prepare hosted previews with independent journals and isolated Batch workers

Date: 2026-10-20. Accepted for controlled engineering; live activation gated.

Cloud Run cannot host the existing Docker isolation boundary. A database restore
can also omit a post-backup worker or write, so SQL slots and local journal files
alone cannot establish safe hosted recovery.

Keep the website and private API on Cloud Run. Prepare a dedicated Google Batch
VM per preview attempt with a trusted, credentialed coordinator. Only the
existing offline, unprivileged Docker decoder handles media. The decoder receives
no network, cloud/database secrets, Docker socket or host output mount.

Use separate protected GCS buckets for preview-write, control and execution
journals. Explicitly bootstrap signed genesis records. Create-only consecutive
sequence objects arbitrate writers without a mutable head. Verify fresh inventory,
generations, signatures and the complete chain before applying a transition.
These stores are independent of SQL/media restore; append principals cannot
overwrite/delete. Actual IAM, geography, CMEK, retention, freshness and failure
behavior still require cloud qualification. HMAC alone cannot prove freshness
against an administrator replacing the entire archive.

Record worker intent before creation. Never blindly repeat an ambiguous create.
Cancellation survives SQL rollback. Release physical capacity only after verified
job deletion, an empty complete VM inventory and an absent job. Restore discovers
orphan workers from the independent journal and remains quarantined on uncertainty.
Untracked original bytes retain quota until verified source/deletion reconciliation.

Add a server-only website bridge to invoke the private API using service identity
while preserving end-user sessions, ownership, CSRF and private ranges. Maintenance
is separate from conversion, bounded, overlap-locked and initially paused.

All production qualification flags remain false. Terraform is optional,
approval-gated and quarantined; no project, region, spending, resources or real
hosted operation is approved by this change. Staff-only preview preparation does
not enable general signup, canonical analysis, game/provider acquisition or G1-G6.

Architecture 2.24.0; decision D046. See the
[contract and activation procedure](../architecture/hosted-recording-previews.md)
and [qualification record](../experiment-results/hosted-recording-previews.md).
