# M13 player experience — local implementation contract

Updated 2026-10-06; Architecture 2.20.0. Available local M13 engineering is implemented.
M13's release exit still requires permitted real providers, production accounts, validated
knowledge/measurement and real usability/accessibility studies.

## Journey and scope

The [original visual system](../design/visual-system.md) uses graphite panels, ember accents,
self-hosted fonts and decorative generated dojo art. Visitor entry links to real local access
controls; authenticated entry leads with training tools and retains account/privacy section links.
The reference-inspired presentation never changes provider, consent, scientific or release gates.

The workspace explains the candidate Jin/Jin scope, capture requirements, unavailable live
identity services and the difference between metadata, attribution and reviewed gameplay.
Onboarding persists acknowledgement; it grants neither processing nor training consent.
Existing per-operation processing consent remains necessary. Authentication uses existing local
Django accounts. M14 adds optional local signup/verification/recovery and account-security controls
using a private test mailbox; no external mail transport or operator credential is provisioned.
See [account lifecycle](accounts-consent.md) for consent withdrawal and session revocation.

The ordered journey is baseline -> approved drill -> frozen plan -> reviewed practice -> later
matches -> comparison. Baseline summaries show successes/known eligible outcomes and unknowns;
small samples do not establish a weakness. The UI requires a frozen assignment plan before
linking practice. Canonical services enforce definitions, chronology, full-capture selection,
exposure and immutable memberships. All six outcomes and withdrawn results remain visible.

## Search and evidence

The primary target is [browser-only acquisition](replay-acquisition-feasibility.md): sign in,
confirm TEKKEN ID once, choose an available match and Analyze without installing/pairing tools,
choosing folders or creating/uploading recordings. M13.10 stays blocked on real permitted
acquisition and M22 console/managed-service qualification. Prepare actual proof before adding
a capture queue or promising video from metadata. Existing missing/pending/expired/incompatible
states remain honest. Public IDs never expose another owner's private videos. The qualified local
[recording companion/inbox](recording-companion.md) and manual upload remain optional fallbacks.

History supports owner/player, inclusive UTC date range, character, reviewed situation/outcome
and evidence state. Event search supports match, UTC dates, character, purpose, situation,
eligibility and outcome. Typed bounded queries paginate results. Character matches either slot;
unreviewed raw source fields never silently fill unknown canonical values. Metadata-only matches
cannot satisfy a reviewed outcome filter.

The timeline uses current AnalysisPublication events and their original run asset. Deleted or
replaced sources are absent. Disputed metadata remains inspectable but cannot be selected or
satisfy history's gameplay filters. Provenance includes build, knowledge, detector, source hash
and review count, excluding private paths and reviewer identities. The video player seeks to the
event window and offers original-source access and correction requests. Authenticated media
supports bounded single byte ranges; malformed/unsatisfiable ranges return 416. Responses are
private/no-store. Removed files may be unavailable; this is local file serving, not a hosted CDN.

Selection persists across filters/pages with explicit counts. Complete-match selection collects
current selectable events up to the local 2,000-event request bound. Server full-capture rules
remain authoritative. UTC is the default display zone; users can choose the browser's named
timezone. Date searches always use labeled UTC days. Capture/plan datetime inputs explicitly
use device-local time and serialize to UTC. Play time is never replaced by export time.

## Privacy and feedback

Profile stores onboarding, display timezone and three notice booleans. Owner-only JSON export
uses explicit field allowlists and a 10,000-record local bound. It includes structured match,
evidence, training, evaluation and preference records. Media bytes are downloaded separately.
Password hashes, private paths/upload sessions, raw assertions and reviewer/opponent snapshots
are excluded. Oversized exports return 413 with operator-help guidance. Hosted asynchronous
export and comprehensive provider data portability remain M14 requirements.

Account deletion requires current password, CSRF and DELETE MY WORKSPACE confirmation. The
owner lock serializes deletion with imports/publication/preferences/export. Before filesystem IO,
all assets are tombstoned, runs cancelled/fenced, matches withdrawn, source links removed and
feedback/receipts erased. Login identity is pseudonymized, personal account fields cleared and
password made unusable; audit facts remain. Then local source/derived files are purged and the
session logged out. A filesystem failure returns purge_pending; purge_expired retries every
tombstoned asset, including those not reached initially. This does not erase manually downloaded
copies, hosted backups or third-party provider data.

Feedback stores an owner, UUID retry key, category, bounded message, optional owned event and
status. Identical retries are idempotent; changed content under the same key is rejected.
Correction requests do not relabel evidence. Local staff review the admin queue and update status.
Players see their latest 50 requests; bounded export includes the full set. No email, provider
contact or guaranteed support response time is implied.

## Notices

Only in-app notices are implemented. Analysis/review readiness, assigned practice and opened/
ended follow-up windows derive from durable canonical records. The page polls while visible;
reloads cannot lose a current pending notice. Unique owner/key receipts persist dismissals.
State transitions use distinct keys. Deleted sources disappear; preferences suppress categories
without changing processing/training consent.

The feed considers the newest 100 records per category and displays 50 undismissed items with
a remaining count. It is a bounded current-state inbox, not immutable delivery history. External
push/email, older-state history, quotas and hosted delivery targets need separate decisions.
No notification credentials or outbound sending tools were used.

## Verification and remaining release work

PostgreSQL tests exercise API ownership/CSRF, filters, export redaction, idempotency, deletion
failure/retry, source byte ranges and notice-window transitions. Headless Edge tests mock HTTP
and cover onboarding, preferences, timeline selection, correction requests, export, deletion,
mobile keyboard flow and the synthetic training path. Desktop/mobile screenshots were inspected.
UTC and America/Toronto display are exercised. Media tooling is tested separately; browser tests
do not establish real Tekken accuracy or actual media decoder/browser compatibility.

Remaining: permitted IDs/providers (M04/M05), hosted accounts/recovery/privacy (M14–M16), approved
knowledge/measurement and real participant adherence/comparison (M07–M12/M18), manual screen-reader
checks, real mobile devices, additional browsers, caption/visual-evidence accessibility review,
hosted query/load limits and beta usability. No release gate is waived.

The local [recording-sync inbox](recording-companion.md) adds explicit paired-computer controls,
private validated playback and reuse of existing attribution forms. Unassigned recordings
create no canonical match facts; upload time is not original play time. Companion admission
stays disabled by default and real Windows/hosted acceptance remains separate.
