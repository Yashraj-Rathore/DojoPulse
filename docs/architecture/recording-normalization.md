# Recording normalization and timing quality

Architecture 2.21.0; 2026-10-12. [ADR-028](../adr/ADR-028-source-preserving-recording-normalization.md).
Scope: trusted local operator CLI. Architecture 2.22.0 separately integrates
[private preview engineering](private-recording-previews.md) (M06.12); actual hosted delivery
remains M06.11. This CLI itself still creates no website/storage/canonical records.

`python -m tools.normalize_recording SOURCE.mp4 --output-dir NEW_PRIVATE_DIRECTORY`
creates `preview.mp4`, `timeline.json` and `report.json`. Optionally pass `--game-build`
as an unverified operator declaration. Inputs and outputs contain private recordings;
use ignored `private_data/`. The command prints only a small status/quality summary and
never prints the source path, participant names or checksums.

The [versioned policy](../../contracts/recording-normalization-v1.json) bounds MP4 input
to one H.264/HEVC 1920 x 1080 8-bit SDR progressive video stream, nominal 60 fps, at most
one AAC mono/stereo stream (8-48 kHz), 600 seconds, 512 MiB and 36,000 video frames.
Variable recorded periods are accepted for preview and audited, never repaired. Unsupported
resolution, HDR, rotation, stream layouts and nominal rates fail; no silent rescaling.

The source is copied into private temporary scratch with a streaming checksum and size
cap. Stat identity is checked across copying and the selected original checksum is checked
again after conversion. Symbolic links and Windows reparse points in path ancestors fail.
Destination must be new; no source or prior result is overwritten. Temporary source bytes
and partial output files are removed on failure, with no successful report published.
An interrupted process/host crash can leave an incomplete directory; only a report plus
matching policy/source/derivative/timeline pins establishes a completed bundle. Rerun in
a new directory. No automated cleanup of arbitrary user directories is performed.

FFprobe scans every video frame and AAC packet, under bounded process execution. FFmpeg
uses `-copyts`, passthrough frame mode, a 60 MHz video time base (representing both
microsecond timestamps and 60 Hz periods), H.264 CRF 18/veryfast
with two threads, explicit color range handling and AAC stream copy. Input metadata and
chapters are stripped from the derivative. Output size is checked during execution and
after process exit. Each process is limited to 1 GiB RSS; probes to 120 seconds and the
encoder to 900 seconds. Scratch peaks at one <=512 MiB source plus one <=512 MiB derivative
and bounded JSON. These are per-operation local limits, not a hosted concurrency guarantee.

The output is decoded again. Acceptance requires equal frame counts, <=2 microseconds
video timestamp error, identical recorded coverage intervals, AAC packet count/payload
preservation and <=22 microseconds audio timing error (one 48 kHz sample), with matching
color declarations. The full timestamp vectors are hashed in `timeline.json`. This verifies
frame ordering/time coverage, not pixel equality: H.264 encoding is explicitly lossy.

The quality report lists intervals between recorded frames where gaps exceed 25 ms or
periods differ from 1/60 second by more than 1 ms. These are recording continuity limits;
the tool does not infer their cause or a precise number of missing game frames.
`analysis.timing.timing_window_supported` rejects overlap and out-of-coverage windows,
independently of provider or canonical match. True checks continuity only, not evidence
eligibility. All gameplay/scientific/canonical approval flags remain false.

`strict_capture_profile_media_compatible` reports only current codec/timing media checks;
it is not automatic gameplay validation. The existing strict parser/profile is unchanged.
A gapped derivative remains unsupported there. No authenticated website playback, storage
asset, canonical match, event, dataset approval or player contribution is created by this CLI.

The [official FFmpeg documentation](https://ffmpeg.org/ffmpeg.html) describes passthrough
timestamps and warns that muxers may still change them. The full output comparison is
therefore mandatory; flags alone are insufficient evidence of preserved recording time.
