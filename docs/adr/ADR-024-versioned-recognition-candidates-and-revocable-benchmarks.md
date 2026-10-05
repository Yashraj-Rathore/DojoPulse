# ADR-024: Versioned recognition candidates and revocable benchmarks

Date: 2026-10-05. Status: accepted for local engineering only.

The existing media/template/rule tools lacked a coherent version, reproducible benchmark,
independent activation and drift-stop lifecycle. Synthetic labels must not accidentally become
real recognition evidence or provider-dependent canonical events.

Use immutable exact-measurement detector manifests, fixed code/image/config artifact hashes,
typed timestamped observations with explicit abstention, all-source held-out benchmark receipts,
two independent exact-report approvals and one active synthetic candidate version per dataset.
Known outcomes remain synthetic, unverified candidates. Real registration/release and automatic
publication are closed. Manual source-specific M08/M18 review remains the canonical fallback.
Keep portable retrospective software evaluation distinct from prospective real G2 evidence.

Version replacement/rollback and submitted-observation drift stop are explicit; old passing
reports cannot override a later failure. Erasure, expired grants and restoration revoke reports
and approvals before private reads. Independent reviewers receive aggregate metrics, with only
the owner allowed current reproduction exports. Preserve guarded migration history.

This adds three relational lifecycle tables and a local operator console; it does not add a
model runtime, remote endpoint, host-side media decode or production release. Further real
recognition requires permitted representative recordings, expert reference timing/labels,
reviewed observation implementations/calibration and technical/scientific release review.

Details: [recognition contract](../architecture/recognition-validation.md) and
[qualification](../experiment-results/m09-recognition.md).
