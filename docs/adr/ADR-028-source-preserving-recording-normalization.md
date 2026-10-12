# ADR-028: Preserve recorded evidence during codec normalization

Date: 2026-10-12. Status: accepted for trusted local operator tooling only.
Requirements: M06.01/.05/.09/.10/.11; M22.07/.13. Decision: D043.

## Context

The first owner-provided Steam export contains actual 1080p replay video in HEVC with
uneven timestamps. The strict H.264 1080p60 analysis profile rejects it. Re-encoding to
constant 60 fps would manufacture or drop recorded frames and conceal missing evidence.
Video decoding/normalization and approval of gameplay observations must remain separate.

## Decision

Implement a bounded trusted-local CLI and provider-independent `analysis` primitives.
Normalize an explicitly selected local MP4 to a new H.264 preview bundle. Preserve every
decoded frame and its recorded presentation timestamp, source color declarations, and
AAC audio packet payload/timing. Preserve a nonzero video start; do not reset timestamps,
interpolate, duplicate, drop, crop, retime or change playback speed.

Keep the immutable source checksum/bytes separate from the derivative checksum/bytes.
Record policy/version hashes, actual FFmpeg version, encoding parameters, lossy-video
declaration and a hashed source/derivative timestamp mapping. The source is snapshotted
for decoding and checked again before success. Game build remains an operator declaration;
codec conversion cannot verify it. Local owner files are USER_UPLOAD provenance and do
not prove an OFFICIAL external replay API or automatic acquisition.

Scan all frames before and after conversion. Reject frame-count/timestamp, audio payload,
audio timing, color or coverage changes. Report irregular/gap intervals explicitly and
offer a shared timing-window check that cannot confer semantic/gameplay eligibility.
Even a continuous recording does not prove absence of cuts, rewinds, pauses or takeover.
Keep canonical/scientific/precise-gameplay approval false. Existing strict admission and
Match/GameplayEvent/player-model pipelines stay unchanged.

This operator tool uses file-only protocols, no shell/stdin, rejected links/reparse ancestors,
fixed stream/dimension/codec/color limits, bounded decoder process trees, output-file size
monitoring, create-only output directories and cleanup of owned partial outputs. The local
limits are not a production hostile-media isolation boundary.

## Consequences and remaining work

The owner can inspect a compatible private H.264 preview and the preserved timing gaps.
Missing recorded game frames remain missing. A source with gaps stays rejected by current
strict worker admission; no automatic evidence/diagnosis is published.

Hosted normalization requires separately qualified container output retrieval, job fencing,
derivative quota reservations, original/derivative retention and erasure, authenticated
preview, and explicit quality UI. M06.11 tracks that unmet scope. Do not call this local
CLI from an HTTP handler or public upload worker. No automatic game recording, provider
endpoint, installer or cloud runtime is enabled by this decision.
