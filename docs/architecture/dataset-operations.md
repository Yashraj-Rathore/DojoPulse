# Dataset and annotation operations

Architecture 2.12.0 / 2026-10-05. [ADR-020](../adr/ADR-020-versioned-dataset-operations.md).
Local software only; M08 real qualification remains open.

Use `/datasets` with an active local staff account. Publish a governed synthetic M07
knowledge bundle first; legacy fixtures and drafts cannot create a collection. Creation
pins build/platform, knowledge/situation/metric/build/move IDs and hashes. Collection
specification and sampling checklist cannot be edited; create a new collection for
different measurement or protocol. Limits: 20 collections/operator, ten studies per
collection, 4,000 sessions/sources and 10,000 tasks per snapshot, 100 receipts/collection.
Existing pilot and request admission caps also apply. Maximum-scale hosted performance
has not been qualified.

1. Create a collection and a new linked review study. Existing studies cannot be attached
   because their consent did not specify this measurement or persistent split guards.
2. Open the linked `/pilots` study. Invite two reviewers and a distinct adjudicator;
   participants accept the complete protocol themselves. Assign their split before play.
3. Register owned validated sources with exact original chronology, Jin/Jin context,
   dataset kind and platform. Build and metadata hashes, object generation, bytes and
   duration are pinned. A hash cannot be assigned to another player/session or split
   within the collection, including after withdrawal. Workspace data and provider
   metadata alone cannot fabricate a recording.
4. Assign full-source QC and non-overlapping target/practice windows. Freeze detector
   predictions before review. Explicitly include failures, excluded near misses,
   uncertain/unobservable windows and full-source target-absent controls. An absence
   label cannot coexist with a reviewed eligible opportunity from the same source.
5. Freeze dataset inputs. All linked study memberships, sessions, source assignments,
   splits, tasks and predictions are now immutable. Reviewers may finish; any structured
   difference, including timestamp audits, needs the distinct third reviewer. Held-out
   manager labels remain hidden until this freeze.
6. Seal a snapshot after every source has resolved independent QC and every selected
   window has resolved labels. The UI exposes category counts, missing categories,
   adjudication/time, uncertainty and timestamp/frame agreement by split. Prediction
   slices use TARGET windows with explicit reviewed timing and one detector version;
   practice windows and unaudited timing cannot establish G2. Missing/invalid/zero
   sessions and unknown durations remain in the manifest. Sparse coverage is reported
   as incomplete; a snapshot never changes NOT_RUN or approves a detector.
7. Download the current receipt. Export checks permissions and current sources again.
   Withdrawals invalidate old receipts permanently, erase private JSON and invalidate
   derived canonical measurements. Keep exported private files under the approved
   private retention policy; the app cannot erase an offline copy remotely.

Dataset labels add an explicit timing audit: observed `start_us`/`end_us` inside the
assigned window, and measured `frame_duration_us`, or null unknowns. Do not estimate
missing timing. Existing deterministic conditions still derive eligibility/outcome;
labels never bypass unknown/exclusion rules. Canonical `annotation/1` batches retain
the existing schema and exact governed situation; timing audits and full-source QC
remain in the separate dataset receipt. Target-absent sources export an empty batch.

`dataset-snapshot/1` wraps `data` with `content_hash`. It includes version/sampling
pins, frozen study input hashes/revisions, pseudonymous session inventory, source
hash/provenance/consent/retention, QC, structured independent reviews/adjudication,
frozen predictions, canonical batches and reproducible QA. No storage paths, transfer
capabilities, passwords, contact identities or model-training permissions are included.

```powershell
python -m tools.validate_dataset private_data/snapshot.json --root private_data
```

Portable validation checks hashes, split disjointness, independent reviews, timing,
canonical labels and QA. It explicitly reports `source_bytes_verified=false` and
`current_permissions_verified=false`: offline files cannot establish current rights,
retention or source bytes. The existing `dataset/1` file-manifest validator still
supports actual private file hashing; old schema behavior remains compatible.

Canonical publication is a separate explicit owner/operator step:

```powershell
python manage.py import_dataset_annotations --owner <own-staff-account-id> --run <owned-run-id> --match <owned-match-id> --snapshot <current-snapshot-id> --confirm-owned-reviewed-source
```

The command imports the snapshot's exact reviewed source batch through
`publish_annotations`. It cannot substitute labels, publish foreign sources or provide
workspace-wide knowledge/drill approval. Events pin snapshot and knowledge hashes;
the original match build/initial knowledge and old frozen plan membership remain
historical. Snapshot invalidation tombstones dependent active events, removes current
contributions and invalidates dependent evaluations. Canonical core processing remains
provider-independent.

Session/CSRF/private-no-store API: `GET/POST /api/datasets`, owned dataset detail/DELETE,
`study`, `freeze`, `seal` commands and owned snapshot GET. Review access stays under
the assigned role/media grants in `/api/pilots`; only managers export whole datasets.
Own account exports include owned collection specifications and receipt metadata,
excluding other participants' full labels. Knowledge withdrawal blocks new uses and
export; closure can still erase the collection. Quarantine closes restored collections,
erases every private receipt/partition and replays existing signed study controls before
reads. Source/account/processing/reviewer withdrawal integrates with existing erasure.

Collection-specific guards are not an independence claim across unrelated collections,
cross-account aliases, previously seen footage or outside-the-app reviewer contact.
Real sampling/rights/consent, expert qualification, timestamp audits, deletion audits,
actual storage/hosting and scientific G1/G2 remain gated. There is no training job,
live replay fetch, automatic detection release or real participant activation here.

The [G1 observability assessment](observability-assessment.md) derives an aggregate, hashed
proposal report from a current owned snapshot through the existing revocation checks, or
reproduces it offline. It preserves the immutable dataset-snapshot/1 QA contract and adds no
persistent label store or scientific approval. See ADR-025 for acquisition boundaries.
