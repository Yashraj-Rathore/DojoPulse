# First owner-provided Steam replay recording inspection

Date: 2026-10-12. Requirements: M06.02/.03, M22.07/.09/.13 and M13.10.
Scope: trusted local operator inspection of user-provided media; no backend admission,
canonical event publication, approved scientific intake or automatic acquisition trial.
Capture alias: `capture-2026-10-12-01`. Raw paths, account/participant identifiers, video
bytes, extracted previews, checksums and detailed frame metadata remain outside public git.

## Acquisition and actual file

The owner supplied their Steam Game Recording directory, then exported an MP4 through
Steam and identified their Videos folder. Bounded inventory found one Tekken recording
and one saved-clip copy in the named Steam directory: standard static DASH manifests,
video/audio initialization files and 53 numbered segments per track. No standalone MP4
was present in that directory. No proprietary `.pb` files, account data or game endpoints
were accessed. This is recorded video supplied by the owner, not a native Tekken replay payload.

Before the owner's export, a local inspection-only HEVC MP4 was assembled from the
explicitly inspected manifest using stream copy and file-only protocol access. The command
returned zero but warned about a fragment at the manifest end. Its completeness is not
qualified. It is retained as an inspection artifact, not selected as product evidence.
The subsequent official Steam-exported MP4 is the selected source for the checks below.
The original Steam files and exported MP4 were not modified.

| Check | Measured result |
|---|---|
| Exported source bytes | 240,556,903; below the current 512 MiB limit |
| Container duration | 158.516667 seconds; below the current 600-second limit |
| Video | HEVC/H.265, 1920 x 1080, full-range 4:2:0 with BT.709 color declarations |
| Audio | AAC, two channels, 48 kHz in the recording manifest/probe |
| Nominal frame rate | 60/1; average metadata approximately 59.08 fps |
| Full decoded frame scan | 9,363 frames, all with timestamps; decoder exit zero and no decoder error output |
| Timestamp ordering | Strictly increasing; first 0, last 158.496212 seconds |
| Median inter-frame gap | 16,667 microseconds |
| Gaps above current 25,000-microsecond limit | 68; maximum 333,332 microseconds |
| Sampled visual inspection | Frames near 0, 15, 65, 110 and 155 seconds show changing Tekken replay scenes, visible 3.02.02, HUD and input/frame/status overlays during sampled combat, and an end-of-round cinematic near the end |
| Current capture-profile compatibility | FAIL: HEVC instead of H.264, and excessive/uneven frame gaps |

Measurements used FFprobe/FFmpeg on the explicitly identified trusted local capture with
file-only protocol access. Full timestamps and the private inspection receipt are under
ignored `private_data/captures/2026-10-12/`. Sparse previews are not an exhaustive audit of
cuts, pauses, rewinds, takeover, normal speed, all overlay coverage or original match completion.
Do not infer the cause of timestamp gaps or turn a display version into canonical source mapping.
The visible character pair remains outside the provisional Jin/Jin scientific target.

## Consequence and next work

This is the first actual owner-provided recorded-video inspection in the project. It advances
manual capture feasibility beyond the earlier screenshots. The unsupported codec and timing
gaps are real negative compatibility evidence, not grounds to declare the capture valid.
An MP4 extension or nominal 60 fps is insufficient for current M06/M09 acceptance.

A future separately reviewed H.264 derivative must preserve original source lineage and
timestamps; re-encoding cannot restore unseen game frames. Forced frame duplication or
retiming must not manufacture precise gameplay evidence or conceal gaps. Any broader
capture support requires a scoped compatibility/quality decision before implementation.

M22.13 remains BLOCKED: this is a manual USER_UPLOAD recording, not permitted public
TEKKEN-ID resolution/loading, zero-intervention capture, private service delivery or verified
existing-match attribution. M04/M05/X01 and purpose-specific runtime/usage/console gates
remain. G1-G6 NOT_RUN; no game facts, recognition release, coaching outcome or player-model
contribution was created. No automatic device sync or user-facing acquisition queue enabled.

Next independent work: define safe codec/timestamp compatibility handling with explicit
unknown intervals, or obtain a recording meeting the declared profile. Actual browser-only
acquisition and managed-service approval remain separate requirements.

## Implementation follow-up on 2026-10-12

[M06.09/.10 qualification](../experiment-results/recording-normalization.md) subsequently
created a trusted-local H.264 derivative: 496,940,978 bytes, all 9,363 source PTS and AAC
packets/payloads preserved with zero measured timing error, same color declarations and
unchanged original checksum. All 68 large gaps remain. The finer 1 ms period policy identifies
1,403 total irregular intervals, including those gaps; their full intervals/mapping stay private.
Two output previews were viewed, with readable sampled overlays. Strict analysis still fails
recorded timing/average rate; no frame synthesis, semantic approval or canonical publication.
The earlier inspection-only statements above retain their original scope/date. Hosted
private preview delivery is the newly tracked M06.11, separate from browser-only M22.13.
