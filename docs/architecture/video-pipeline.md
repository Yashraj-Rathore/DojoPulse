# Local video pipeline

`python -m tools.analyze_capture capture.mp4 --metadata metadata.json --output report.json`

Probe with FFprobe -> validate size/codec/duration/layout -> inspect frame timestamps ->
decode bounded samples -> extract configured regions -> optional template candidate detection ->
deduplicate temporal observations -> optional adjudicated annotation import -> conservative
opportunity rules -> structured report. No installed detector is presumed gameplay-validated.

Without authorized calibration/templates and valid adjudicated evidence the report contains
REVIEW_REQUIRED/unknown, not invented zero misses. The raw automatic candidate stream is
separate from reviewed opportunities. Metadata declarations are never proof of capture settings.

Use source time and record timestamp uncertainty. Reject remote paths/playlists and unsupported
containers. Cap size, duration, pixels, decoded frames, wall time and subprocess resources.
The local CLI processes operator-selected files; external untrusted media needs container
isolation and least-privilege credentials before release. Synthetic fixtures test plumbing only.

For hosted execution retain outbox, leases/fencing, checkpoints, bounded retries, admission
limits and atomic publication. Do not implement a second rule engine in workers or views.

## Role in provider-neutral ingestion

Video remains the supported local gameplay-evidence path. A metadata import can create
a canonical match without video, then attach this pipeline's recording to the same match.
Native replay bytes require a separate permitted, version-reviewed decoder; the FFmpeg path
must never treat them as a video. Provider metadata alone creates no gameplay opportunities.
The local attachment flow queues validation, requires explicit operator attribution, then uses
the existing independent annotation workflow. Upload alone publishes no gameplay opportunities.
Reprocessing retains the asset and creates a new run; the worker rejects changes to its pinned
source hash. Purging an imported match's recording withdraws its evidence while retaining match
history. See [match ingestion](match-ingestion.md) and [ADR-014](../adr/ADR-014-recording-attribution.md).
