# ADR-030: Keep preview write uncertainty outside database restores

Date: 2026-10-13. Accepted for controlled engineering; hosted activation gated.

Database-only write flags lose post-backup conversions and upload capabilities.
Timeout refunds and prefix erasure without upload cancellation can recreate
supposedly erased objects. Old ambiguous media POSTs have no cancellable receipt
and cannot retroactively be considered safe.

Use independent signed bounded attempt/session/stop/erasure records, projected
into SQL quota without foreign keys or secrets. Publish with create-only official
resumable uploads. Persist initialization before RPC and session before PUT;
probe the same session after an uncertain PUT. Fence every operation and retain
current SQL publication authority. Revocation precedes SQL changes irreversibly.
Cancel sessions, delete all generations and confirm empty inventory before
refund. Unknown handles retain quota/quarantine. Preserve execution-stop rules.

The file backend proves controlled contracts, not replicated hosted correctness.
No implicit initialization, compaction, guessed expiry or forged erasure is
allowed. Entire-store freshness, multi-host CAS, encryption/key custody, Windows
ACL/durability, independent replication and actual GCS late-write/failure tests
remain gates. Migration 0025 protects independent and projected reservations.

See [contract](../architecture/preview-write-recovery.md) and
[qualification](../experiment-results/preview-write-recovery.md). The canonical
provider-independent pipeline and gameplay/provider gates remain unchanged.
Architecture 2.23.0; decision D045.
