# ADR-017 — Local pilot consent, independent review and evidence packs

Date: 2026-10-02. Status: accepted for local synthetic engineering only.

M18 needs a coherent study workflow while real participants, captures, reviewers,
game knowledge and hosted release remain gated. Keep study administration in a
separate Django module with explicit self-consent, one role/account, pseudonyms,
prospective logs, source provenance and player-disjoint splits. Freeze source
inputs before reporting; blind reviewers to predictions and managers to held-out
labels until freezing. Independent dual review and third-party adjudication export
through the existing annotation contract, with no automatic GameplayEvents.

Generate G1–G6 evidence packs with missing/adverse denominators and source-linked
canonical evaluations. Expert decisions are separate from protocol approval,
recognition release, model training and commercial release. Code-gate real intake;
synthetic success remains NOT_RUN. Extend account/asset/consent erasure, private
export, streaming revocation and signed restore controls to study evidence.
Original workspace retention stays separate from study grants; restore revokes
all study grants before reads.

Actual studies still need reviewed rights/cohort/experts, sampling/comparator
design, hosted retention/access and scientific decisions. Null/sample guards can
reject evidence requiring manual review. Bounded scans and per-chunk checks are
local correctness controls, not qualified hosted performance.

See [contract](../architecture/pilot-tools.md), [protocol](../pilot-protocol.md)
and [qualification](../experiment-results/m18-pilot-tools.md).
