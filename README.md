# Performance Training Platform

A local research prototype for **one measured Tekken improvement loop**.

**Project status and full delivery checklist:** [PRODUCT_PROGRESS.md](PRODUCT_PROGRESS.md).
It lists milestones, requirements, acceptance criteria, current status, blockers and next work.
Update it after every implementation; [docs/progress.md](docs/progress.md) retains the work history.

Architecture V2, dataset contracts, the bounded extraction CLI, Django/PostgreSQL domain,
frozen evaluations, verified-practice import and a thin Next.js UI are implemented.
**Tekken detection quality and player improvement have not been validated.**
The sole drill is deliberately a draft; assignment requires an approved version.
No LLM or hosted service is enabled.

DojoPulse now has a [provider-neutral match-ingestion design](docs/architecture/match-ingestion.md)
and [source investigation](docs/research/tekken-match-sources.md). It covers player-name/TEKKEN-ID
resolution, stable identities, automatic metadata imports and replay/video fallback. Typed adapter
contracts, the relational cutover, an offline Wavu normalizer and two synthetic import adapters
are tested. Live transports, name lookup and native replay decoding remain disabled;
public metadata cannot establish a missed punish.

Start with [Architecture V2](docs/architecture/architecture-v2.md),
[verification results](docs/experiment-results/software-validation.md),
[progress](docs/progress.md), and [pilot protocol](docs/pilot-protocol.md).
The original [V1 proposal](docs/architecture.md) is retained as superseded history.

## Local setup

Requires Python 3.12, Node 22, PostgreSQL 17, and FFmpeg/FFprobe on PATH.
Commands below use PowerShell from the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

Use an isolated development database. Docker option:

```powershell
docker compose -f infrastructure/compose.yaml up -d
$env:DATABASE_URL = 'postgresql://ptp:ptp_local_only@127.0.0.1:5432/ptp'
```

This workspace already has a separate PostgreSQL 17 cluster at private_data/postgres,
on **127.0.0.1:55432**, database/user ptp. It does not use the existing system service.

```powershell
.\tools\dev_postgres.ps1 status
# Start only if stopped:
.\tools\dev_postgres.ps1 start
$env:DATABASE_URL = 'postgresql://ptp@127.0.0.1:55432/ptp'
```

That cluster uses local trust authentication and must remain bound to loopback on this
single-user development machine. To initialize a NEW local cluster on another machine,
use PostgreSQL initdb/createdb with a dedicated path and authentication suitable for that
machine; the helper intentionally never initializes or removes a cluster.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py load_contracts
.\.venv\Scripts\python.exe manage.py createsuperuser
$env:LOCAL_OPERATOR_UPLOADS = '1'
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Only enable local ingestion for trusted, consented operator recordings. Hostile media needs
the isolation/storage release checks first. Settings read environment variables; .env.example
is a reference, not automatically loaded. Do not expose Django's development server.

In a second terminal, set DATABASE_URL again and run the worker:

```powershell
.\.venv\Scripts\python.exe manage.py process_runs --once
# Omit --once for the polling worker.
```

In a third terminal:

```powershell
cd frontend
npm ci --ignore-scripts
npm run dev
```

Open http://127.0.0.1:3000 and sign in with the local operator account. The frontend proxies
/api to the local Django API; the database and media never go through browser storage.
Uploads return 202 and queue work. No accounts/passwords have been created for you.
Stop this workspace's PostgreSQL with tools/dev_postgres.ps1 stop when it is no longer needed.

## Local capture and review workflow

Read the [capture contract](docs/architecture/capture-contract.md) first. Exact game build,
session, original play time and source kind must be recorded; the date of a replay export
is not the date the match was played.

```powershell
.\.venv\Scripts\python.exe -m tools.analyze_capture private_data/capture.mp4 --metadata private_data/metadata.json --output reports/capture.json
.\.venv\Scripts\python.exe -m tools.annotate private_data/capture.mp4 --help
.\.venv\Scripts\python.exe -m tools.validate_dataset private_data/manifest.json --root private_data
.\.venv\Scripts\python.exe -m tools.evaluate_detector private_data/truth.json private_data/predictions.json --output reports/perception.json
.\.venv\Scripts\python.exe -m tools.benchmark private_data/capture.mp4 --output reports/benchmark.json
```

The annotation CLI creates a source-hashed blank sidecar. Two independent reviewers fill it;
a third adjudicates critical disagreement. Validate conditions, exact build, chronology,
standing/reach/axis/wall/resource state and full-resolution frame timing. Coarse thumbnails
are navigation aids and cannot establish a one-frame punish boundary.

Optional template configuration supplies label, file, region [x,y,width,height], threshold
and max_gap_us; pass --templates to the analyzer. Template similarity is **not confidence**.
There are no calibrated Tekken templates in this repository.

For a capture ingested into Django, obtain its run UUID from /api/overview; then:

```powershell
.\.venv\Scripts\python.exe manage.py import_reviewed --operator YOUR_USERNAME --run RUN_UUID --annotations private_data/annotations.json --confirm-chronology
```

Review import is operator-only, source-hash checked and atomic. It creates sparse evidence
and replaces one active contribution per match. Reimporting identical content is idempotent;
changed facts require a new AnalysisRun. Tests exercise this reprocessing path. Direct SQL is
trusted maintenance access, not an end-user interface.

The draft knowledge/situation/metric/drill records cannot be assigned as a released drill.
After real validation, create new immutable versions with expert provenance and corresponding
build/metric approval through a reviewed migration/curation change. Do not overwrite draft
keys or edit status in the database to bypass release decisions.

## Local match-import rehearsal

Apply migrations, then import fake metadata for an existing local staff account. This does not
contact Wavu, EWGF or Tekken services, create a user, or produce gameplay judgments.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_synthetic_matches --operator YOUR_USERNAME --confirm-synthetic-consent
.\.venv\Scripts\python.exe manage.py import_synthetic_matches --operator YOUR_USERNAME --provider synthetic-b --confirm-synthetic-consent
```

Each provider supplies two synthetic matches. Repeating the command refreshes the same records;
the second provider retains separate matches even with identical external ID strings. Metadata
keeps unknown build, session and character mappings null. The existing video workflow continues
to produce a USER_UPLOAD ReplaySource. Match.asset remains an optional compatibility pointer.

The player-link, queued-sync and history flow is also available in the local UI. Enable it only
for the existing local staff account, start Django with the same environment, then run the
separate match worker alongside the existing capture worker:

```powershell
$env:LOCAL_MATCH_IMPORTS="1"
.\.venv\Scripts\python.exe manage.py process_match_syncs
# For a single bounded batch instead:
.\.venv\Scripts\python.exe manage.py process_match_syncs --once
```

In **Player & matches**, choose **Demo source A**, enter **ExamplePlayer-A**, select the returned
fictional profile, consent, and link it. **Import matches** queues discovery; history refreshes
automatically when the worker commits the two fixture pages. Repeating an import does not
duplicate matches. **Stop syncing** revokes consent while retaining history. The history table
shows unknown mappings, source revisions, incomplete coverage and evidence requirements.

The flag also requires DEBUG and staff status; it never activates a live provider. No provider
key is needed for this rehearsal. [EWGF access review](docs/research/ewgf-activation-review-2026-09-19.md)
records what must be resolved before real player lookups: purpose-specific usage rights,
private server credentials, permitted live fixtures and identity/schema validation.

Deleting a metadata-only match through `delete_metadata_match` revokes that identity's local sync
consent, fences outstanding jobs and removes that match's source/participant records. The revoked
link prevents automatic reimport until account deletion removes it; local relinking is disabled.
Production suppression retention remains future work. Local reviewed recording attribution is
available as described below.

Session-authenticated endpoints: `GET /api/match-providers`, `POST /api/player-candidates`,
`GET|POST /api/player-identities`, `DELETE /api/player-identities/{id}`,
`POST /api/player-identities/{id}/sync`, `GET /api/match-syncs/{id}`,
`GET /api/matches?identity={id}&offset=0&limit=20`, and `DELETE /api/matches/{id}`.
Mutations require CSRF. Candidate tokens expire after five minutes and are bound to their owner;
clients cannot submit arbitrary provenance or claim verified ownership.

## Attach a recording to imported history

With `LOCAL_OPERATOR_UPLOADS=1` and an active local staff account, choose **Attach recording**
on an imported match. Confirm the player/opponent IDs, slot, original match time, exact build,
session, purpose and real/synthetic content. The current profile is Jin vs Jin, 1080p60 SDR
H.264 MP4, at most 10 minutes / 512 MiB. A synthetic match accepts only synthetic recordings.
Known facts must agree; unknown facts remain unverified until review. Upload queues work and
does not create another match or publish gameplay evidence.

Run `process_runs --once` in the worker terminal. Inspect **Review recording**, then use the
source UUID and SHA-256 under **Operator review reference** to attest attribution:

```powershell
$env:LOCAL_OPERATOR_UPLOADS = '1'
.\.venv\Scripts\python.exe manage.py review_recording --operator YOUR_USERNAME --source SOURCE_UUID --source-hash SHA256 --knowledge KNOWLEDGE_VERSION --note "Reviewed both identities, slots, original time, build and purpose" --confirm-reviewed
```

The knowledge version must match the declared build; real evidence additionally requires
approved knowledge and a verified build. Do not promote drafts to bypass those gates. This
command confirms match attribution only. Publish independently reviewed annotations afterward
with `import_reviewed` and the recording's run UUID, using the existing review workflow above.

**Reprocess recording** creates a new run for the same source. **Remove recording** withdraws
its evidence and dependent conclusions while retaining imported match history. Remove the
recording before deleting match metadata. Replacement recordings cannot rewrite historical
gameplay context or knowledge. A source correction after upload requires removing and
resubmitting the recording against refreshed metadata.

Endpoints: `POST /api/matches/{id}/recordings` (multipart file, metadata JSON, request UUID and
explicit consent), and `POST /api/matches/{id}/recordings/{source}/reprocess` (request UUID).
Both are owner-scoped local operator operations. Hosted uploads remain disabled.

## Evaluation and retention

Freeze a complete baseline capture selection before practice. Submit recorded practice,
have it independently reviewed, then link the resulting events to the assignment. Record later
ranked matches under the frozen capture/build/metric policy. Real follow-up windows must be
prospective and must end before evaluation; all recorded target opportunities in the window
must be selected. Recording/session completeness still needs the pilot log and operator audit.

Evaluation reports numerator/denominator, unknowns, coverage, versions, practice membership,
raw change, uncertainty, next action and a legitimate nonpositive status where appropriate.
The synthetic integration test exercises the entire API loop; it is not gameplay evidence.

Local media expire after at most 60 days by default. Run the retention worker regularly:

```powershell
.\.venv\Scripts\python.exe manage.py purge_expired
```

Capture deletion cancels jobs, removes local derived artifacts and invalidates evaluations
depending on baseline, practice or follow-up evidence. Failed purges retain tombstones for retry.
An account-deletion domain service exists; complete provider/backup deletion is a hosted gate.

## Verification

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\mypy.exe
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run lint
npm run build
npm run typecheck
npm test
```

Browser tests use installed Microsoft Edge on Windows, Playwright Chromium on Linux.
On Linux run npx playwright install --with-deps chromium once.
CI runs PostgreSQL-backed tests, Python checks, the frontend build and browser smoke tests.
CI has been authored; a hosted GitHub runner has not been executed from this workspace.

## Boundaries and next evidence

No real gameplay dataset is included. Do not put footage, personal identifiers, credentials,
reviewer names or derived private screenshots in Git. Keep media/review artifacts under an
access-controlled private root and reference them with pseudonyms and hashes.

G1–G6 are NOT_RUN: human observability, deterministic detection, capture friction,
practice measurement, natural frequency and comparable complete loops.
[The pilot protocol](docs/pilot-protocol.md) specifies required data and stop decisions.
Cloud storage/resumable upload adapters and Cloud Run deployment are intentionally not enabled.
The Docker parser file is an unvalidated isolation candidate; local subprocess limits alone
do not certify safe external uploads.
