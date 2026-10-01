# M14 accounts, consent and data ownership

2026-10-01; Architecture 2.6.0; decision D025. Implemented for loopback research use.
This is not approval for public registration, production email, legal terms or provider access.

## Account access

Django remains the application identity authority. PlayerGameIdentity remains an owner-scoped
claim about a game profile; a TEKKEN/Polaris ID never authenticates an application account.
`LOCAL_ACCOUNT_SIGNUP=1` and DEBUG are both required for registration and all email challenges.
New registrations are inactive, non-staff accounts until verification. Existing operator accounts
remain usable; their pre-existing email values are not automatically marked verified.

AccountEmail stores a unique normalized address and its verification time. AccountChallenge
stores a SHA-256 digest of a random 256-bit token, purpose, target address, password-state binding,
expiry, consumption time and whether it may activate a new registration. Tokens expire after
30 minutes and are consumed once under an owner lock; concurrent verification has one winner.
Replacing a challenge invalidates its predecessor. Password changes invalidate challenges and
all sessions; a reset link for an old email cannot reset an account after its address changes.
Email-change links cannot reactivate a disabled existing account. Password changes and email
changes require the current password. Public replies do not disclose account existence.

There is no external mail transport. Development delivery writes a private JSON envelope under
`PRIVATE_DATA_ROOT/account-mail/<owner>/<challenge>.json`. The envelope contains the bearer link,
so it is private credential material, not an export or log. The fixed trusted origin is
`http://127.0.0.1:3000`; request Host cannot change it. Links carry tokens in fragments; the UI
removes the fragment and requires an explicit POST before consuming a link. It never automatically
confirms a GET. CSRF protects anonymous mutations as well as authenticated ones. Budgets allow
10 public account requests per source-IP minute and 3 challenge deliveries per account hour,
plus the existing authenticated limits. No production abuse resistance is claimed.

Passwords use Django hashing/validators with a 12-character minimum. Test fixtures use the fast
test hasher only. Session cookies remain HttpOnly and CSRF protected, with a seven-day lifetime.
AccountSession exposes UUIDs and dates, never cookie keys, addresses or device fingerprints.
Its key is hashed; per-session revocation and Profile.session_epoch invalidate sessions on the
next request. Normal Django logout revokes the inventory entry. Login and legacy-session
registration serialize with password changes/deletion through the owner lock. In-flight work
already authorized is not recalled; processing mutations have their own owner locks/fences.

## Consent and work cancellation

`local-research-2026-09/1` is a local draft policy, served by `/api/account/policy`.
ConsentReceipt records scope (TERMS, PROCESSING, TRAINING), action, version, text digest,
source, time and an owner-unique request UUID. Application updates are append-only;
account deletion removes the receipts. Matching retries return the same receipt; a conflicting
request UUID is rejected. Optional model training defaults off and no training service runs.

Migration 0008 captures pre-existing consent timestamps as `legacy-unversioned` with an empty
digest and `LEGACY_CAPTURED` source. It preserves their times without inventing accepted wording,
email verification or retrospective approval. New uploads/links record their local processing
confirmation. Onboarding acknowledgement remains separate from consent.

Processing withdrawal atomically records a receipt, revokes upload reservations, cancels/fences
queued or processing analysis, and revokes player links/syncs. Uploads, reprocessing, annotation
publication, training-loop mutations and new sync requests reject withdrawn consent. A running
parser may finish its bounded computation, but stale results cannot publish. Retained evidence
remains readable/exportable/deletable. Re-grant does not restart jobs; player re-linking and
starting an import are separate explicit actions. Training withdrawal changes future eligibility
only; there are no trained models to unlearn in this implementation.

## Deletion, re-linking and retention

Match deletion still revokes identity-wide sync and fences work first. Before source assertions
are removed, MatchSuppression retains HMACs of owner/game/provider/namespace/external-match-ID.
An explicitly confirmed re-link can import other matches while these known source IDs stay
suppressed. No raw external match ID is retained in the suppression table. HMACs are still
owner-linked personal data, not anonymous data. They persist while the account exists and are
erased on account deletion. Unknown cross-provider aliases cannot be suppressed by inference;
production alias/retention policy remains unapproved.

The local suppression key defaults to DJANGO_SECRET_KEY. Deployments need a separate, stable
DATA_SUPPRESSION_KEY and a reviewed key-version/rotation strategy before use: changing the key
without migrating suppression receipts would allow old IDs to reappear. Setting a flag alone
does not authorize production use.

Account export includes verified email, consent receipts and suppression dates/provider names,
within the existing 10,000-record cap. It excludes challenge tokens/digests, session keys,
suppression hashes, storage paths and opponent identifiers. Media export remains separate.
Self-service deletion rechecks the current password under the owner lock, including after a
concurrent reset. Account deletion erases account email/challenges/sessions/consent/suppression rows, pseudonymizes
login and tombstones media before physical IO. It then removes private mail and media. If disk
cleanup fails, the tombstone remains; `purge_expired` retries orphan/expired/consumed mail files
even when the account has no media. `security_maintenance` also removes these files and expired
challenge/session rows. Cleanup uses the owner lock and a 30-minute grace period for mail whose
owner is not yet visible, so it cannot erase an uncommitted registration's delivery. Run maintenance
at least hourly. Unverified local account reservations
currently persist until operator cleanup; public signup needs a reviewed expiry/abuse policy.

## Release gates

Before hosting: reviewed terms/privacy and jurisdiction-specific retention; authenticated email
transport/sender/reputation/bounce controls; account recovery and abuse review; HTTPS/cookie and
host configuration; privileged-account MFA decision; backup/restore erasure and provider deletion
rehearsals; hosted export/media authorization and scale tests; stable suppression-key management
and cross-provider alias policy. Repository access and possible execution of the previously
removed remote configuration payload still need owner review. No credentials or live services
were provisioned during M14. Local verification: [M14 results](../experiment-results/m14-accounts.md).
