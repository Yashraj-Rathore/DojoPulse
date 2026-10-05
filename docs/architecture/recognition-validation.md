# Local recognition and validation module

M09.01-M09.08, architecture 2.16.0. This module manages **local software candidates**.
It does not contain a released Tekken detector, calibrated confidence, a qualified real
benchmark, model-training permission or automatic canonical publication. G1/G2 remain NOT_RUN.

`DetectorVersion` pins an immutable `detector-manifest/1`: engine `observation-rules/1`,
unique owner/version, exact M08 collection measurement (build/platform/knowledge/situation/
metric and every definition hash), capture profile, code artifact hash, observation artifact
hashes, timestamp uncertainty ceiling (at most 16,667 microseconds), and abstention stop limit
(at most 20%). Engine hashes use UTF-8 text with normalized line endings for portability.
There are no dynamic plugins, executable uploads, remote weights or endpoint requests.
The fixed code artifact covers recognition, rules, metrics, evidence contracts and vision.

Register with two distinct active staff operators other than the author. Registration may
precede dataset input freeze/review completion. Changes during blind annotation preserve an
unbenchmarked configuration; they erase dependent receipts and invalidate versions that
have consumed a snapshot. Version identifiers cannot be overwritten or reused by that owner.
Real registration/activation is closed in code even if pilot intake settings change.

An `observation-batch/1` pins the manifest and observation artifacts. Every source supplies
ID, claimed full-byte SHA-256, build/platform/profile, duration, provenance and candidate
windows. A window supplies bounded timestamped observations of rule conditions, nullable
Boolean values, ordinal HIGH/LOW/UNKNOWN support, uncertainty and bounded evidence codes.
The parser rejects extra fields, duplicate IDs, Boolean timestamps, nonfinite limits,
out-of-source spans, over-capacity data and inconsistent hashes. Limits: 1,000 sources,
100 windows/source, 1,000 windows total, 64 observations/window and 100 receipts/version.
Receipts pin source metadata; they do not independently verify video bytes or observation truth.

Known candidates are restricted to `SYNTHETIC_FIXTURE` provenance and synthetic scope with
the exact supported build/profile. Missing or low-support conditions, conflicting evidence,
unobserved outcomes and timing gaps retain UNKNOWN; an absent input/status never proves
failure. Explicit confidently observed exclusions can make a synthetic opportunity INELIGIBLE.
Real/operator/template inputs always require review and remain UNKNOWN. Similarity remains
uncalibrated; `confidence` is null. Every candidate is `verified: false`.

The offline capture tool can produce a template-derived observation batch using
`--templates` and `--detector-manifest`. The manifest must pin the exact template configuration
digest and each image SHA-256. Labels corresponding to rule conditions become LOW-support
timestamped observations, so even a perfect template match cannot establish gameplay truth.
Existing isolated media execution is unchanged: no new observations, templates or executable
inputs cross into the credentialed coordinator. No video decode runs in an HTTP request.

`RecognitionRun` benchmarks **all** held-out snapshot sources, including target-absent clips;
omission, unknown membership and mismatched hash/duration are rejected. Independently reviewed
TARGET timing supplies reference events. One-to-one scoring separates eligibility, success and
failure precision/recall/F1, one-sided precision bounds, abstention, observable outcome coverage
and timing median/p95. Negative-control false positives are explicit. Software activation needs
predictions, at least 80% observable coverage, no slice FP/FN, no unsupported source and acceptable
abstention. Sparse synthetic success is a software check; it never satisfies real sample-size,
representativeness, calibration, prospective hold-out or event-class release criteria.
These replayable evaluations are explicitly retrospective and repeated held-out inspection
cannot qualify G2. A future qualified real release needs a separately approved prospective
protocol, sealed configuration before label access, permitted representative video, expert
truth, released observation implementations and per-class performance decisions.

Two assigned operators approve/reject the exact current report hash. They receive aggregate
metrics only; private source IDs, observation evidence and reproduction data remain owner-only.
Activation requires two approvals of the latest passing receipt. Only one synthetic candidate
version can be active per dataset. Replacing it disables the former version; rollback explicitly
selects an independently approved current version. A subsequent failing benchmark disables the
active version with DRIFT_STOP; an older pass cannot override that failure. Operator stop is
immediate. This local drift control measures submitted observations, not unattended video drift.
Actual production drift sampling, alert objectives and selective real reanalysis remain open.

Candidates never write `Match`, `GameplayEvent`, player diagnosis, practice exposure or improvement
results. Existing M08/M18 independent media review and exact-source canonical import are the
fallback. Those reviewed events retain their normal detector/knowledge/source provenance.
Candidate activation cannot replace current canonical analysis or authorize real gameplay.

## Operations and reproduction

Use the staff-only `/recognition` console for registration, bounded observation submission,
report/review history, version selection, stop/rollback and current owner exports. Existing
session/CSRF, processing consent, ownership, local-debug, restore quarantine, body-size and
capacity controls apply. Lock only the detector row after the shared capacity lock; do not lock
another account row during assigned review. Read/download rechecks current permissions and
snapshot inputs. Source withdrawal/expiry, dataset/definition closure, account/reviewer withdrawal,
stale input or engine changes erase dependent private inputs/reports and withhold configuration.
Portable copies cannot prove current consent and require separate deletion.

Download an owned benchmark reproduction receipt, then run:

```powershell
.venv/Scripts/python.exe -m tools.recognize_observations --receipt receipt.json --output reproduced.json
```

The CLI checks input/report hashes and regenerates the report. Or supply manifest/observation
JSON positionally with optional `--snapshot`. Inputs are capped at 2 MB each. No network is used.
Workspace export includes owned version configuration and receipt/review tombstones; it omits
other operators' identities and private participant observation batches. The dedicated owner
download requires a current grant to the reviewed dataset.

Guarded migration 0021 refuses reversal once detector/run/review history exists. Native PostgreSQL
rehearsal includes schema forward/reverse/forward on empty tables plus seeded private detector/
observation/review dump/restore and erasure before quarantined reads. Recovery invalidates all
versions, erases runs and deletes approvals; old backups cannot reactivate candidate releases.

Real HUD/input/actor/contact recognition, reviewed templates, actual calibration, expert timing,
G1/G2, review capacity/cost and equivalent hosted qualification remain required release work.
