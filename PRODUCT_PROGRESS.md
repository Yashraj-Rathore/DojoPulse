# DojoPulse product progress

Last updated: **2026-09-23** · Architecture: **2.4.0** · Current stage: **local research prototype**

This is the authoritative current milestone and requirements tracker. Update it after **every
implementation**, including fixes, migrations, integrations, UI changes and operational changes.
[docs/progress.md](docs/progress.md) preserves the chronological work log. Neither file replaces
the other. Requirements and release gates below cover the currently agreed product vision;
new requirements must be added here when scope changes.

## Where we are now

**The local software flow works with synthetic data and reviewed annotations. The real-player
product has not been validated or released.** Milestones M01–M03 are complete within their
explicitly local scope. Most remaining milestones have foundations or designs, not release approval.

| Area | Current position |
|---|---|
| Core loop | Baseline → drill assignment → reviewed practice → later-match comparison implemented and tested synthetically |
| Match acquisition | Player confirmation, consent, queued sync, source history and deletion work with two fictional providers |
| Recording attribution | Local UI/API attaches video to imported history; media validation and operator attribution precede separate gameplay review; removal retains match metadata |
| Player experience (M13) | Local onboarding, searchable timeline/history, guided training, export/deletion, feedback and in-app preferences implemented; real-user release acceptance remains open |
| Real player IDs / providers | No live identity resolver or match transport enabled; EWGF usage rights, credentials and current authenticated schema unresolved |
| Gameplay recognition | Bounded media tooling and deterministic rules exist; no released Tekken detector or calibrated templates |
| Knowledge and drills | One provisional Jin/Jin uf+4 target and one draft drill; expert approval and current-build verification missing |
| Scientific validation | G1–G6 are all NOT_RUN; no completed real-player improvement study |
| Hosting and release | Loopback development only; external uploads and paid/cloud production services not enabled |
| Latest recorded checks | 163 Python tests; 11 headless Edge tests; frontend build/lint/types; Ruff/mypy; Django system/migration checks passed; migration 0006 applied locally |
| Evidence for those checks | [Software validation](docs/experiment-results/software-validation.md), recorded 2026-09-23; synthetic/local software validation only |

There is deliberately no overall completion percentage: implemented scaffolding, approved
data access and demonstrated player benefit are different kinds of progress.

## Status and completion rules

| Status | Meaning |
|---|---|
| DONE | Requirement met and checked for the exact scope stated, with evidence |
| PARTIAL | Useful implementation/design exists, but acceptance criteria remain unmet |
| NOT_STARTED | Required work has not been implemented |
| BLOCKED | Missing evidence, permission, credential, person or external capability prevents completion; independent work can continue |
| DECISION | Optional/conditional scope or a product choice needs an explicit recorded decision |

An entire milestone is DONE only when every required row and its exit condition is satisfied.
Do not call real recognition DONE because a synthetic test passes, call an integration DONE
because its interface exists, or call hosting DONE because a Dockerfile exists. Record a
dated evidence-based waiver before removing a release requirement. Preserve stable requirement IDs.

## Product completion boundaries

| Release boundary | Required outcome | Current state |
|---|---|---|
| Local engineering prototype | M01–M03; reproducible local services and synthetic workflows | Reached |
| Real closed-loop proof | Relevant M06–M12 requirements plus G1–G6 decisions and M18; credible real baseline/practice/follow-up, including nonpositive outcomes | Not reached |
| Permitted real match import | M04–M05; real player identity and recent history without upload when metadata suffices | Not reached |
| Hosted private beta | M13–M19 requirements for the declared supported scope, plus real-data/provider gates | Not reached |
| Complete supported Tekken product release | M01–M20 exit conditions; permitted ingestion, evidence-backed coaching, verified practice, comparison, usable account lifecycle, secure hosting and support | Not reached |
| Broader Tekken offering | M21; each additional character/situation/capture profile validated and explicitly released | Not started |
| Optional wider platform | X01–X12 below, each separately approved; not prerequisites for the first complete supported release | Decisions deferred |

The initial supported scope remains one validated situation and drill. "Complete" does not
silently promise all characters, all move situations, perfect recognition, causal efficacy,
or access to native replay data. Expansion belongs to M21. The superseded V1's approximately
30 situations/two characters and larger upload limits are not current release commitments.

## Milestone overview

| ID | Milestone | Status | Main dependency / remaining exit |
|---|---|---|---|
| M01 | Product architecture and delivery governance | DONE | Maintain decisions, contracts and this tracker |
| M02 | Local canonical domain and evidence lifecycle | DONE | Local scope; hosted equivalents tracked separately |
| M03 | Local UI, workers and synthetic integration | DONE | Local scope; live providers and real measurements separate |
| M04 | Permitted real player identity linking | BLOCKED | Approved resolver, identity mapping and permitted fixtures |
| M05 | Live provider-neutral match discovery/import | BLOCKED | M04 plus provider usage rights, credential and response schema |
| M06 | Production video fallback and evidence attribution | PARTIAL | Local reviewed attachment implemented; secure hosted uploads and real attribution/capture validation remain |
| M07 | Reviewed game knowledge and supported situation | BLOCKED | Current-build evidence and Tekken expert |
| M08 | Consented golden dataset and annotation operations | PARTIAL | Real captures, independent reviewers and held-out labels |
| M09 | Validated observation/event recognition | PARTIAL | M07–M08 and G1/G2; no released automatic detector yet |
| M10 | Player model and weakness prioritization | PARTIAL | Real event validation and useful evidence-backed diagnosis |
| M11 | Reviewed drills and measured practice | PARTIAL | Expert-approved drill and G4 |
| M12 | Trustworthy longitudinal evaluation | PARTIAL | Real prospective chronology, comparability and G5/G6 |
| M13 | Complete player-facing product experience | PARTIAL | Local engineering delivered across M13.01–M13.08; real provider/account/reviewer flows, participant usability, screen readers and real devices remain release dependencies |
| M14 | Accounts, consent and data ownership | PARTIAL | Hosted identity/account recovery and full user data lifecycle |
| M15 | Security, privacy and reliability hardening | PARTIAL | Isolation, abuse, deletion/restore and third-party review |
| M16 | Hosted asynchronous delivery and deployment | PARTIAL | Real cloud/storage integrations and release prerequisites |
| M17 | Operations, performance and unit economics | PARTIAL | Representative load, operational telemetry and actual costs |
| M18 | Prospective real-player pilot | BLOCKED | Participants, consent, reviewers, expert and accepted measurement |
| M19 | Hosted private beta and release qualification | NOT_STARTED | Pilot decisions plus operational/security readiness |
| M20 | Public supported release and commercial readiness | NOT_STARTED | Beta evidence, supported scope, support and commercial decisions |
| M21 | Broader validated Tekken coverage | NOT_STARTED | First complete loop and measured value before expansion |

## M01 — Product architecture and delivery governance

Owner: technical/product owner. Exit: approved narrow architecture, traceable decisions and a maintained delivery record.

| Requirement | Status | Acceptance / evidence |
|---|---|---|
| M01.01 Reconcile V1, review and loop-first scope | DONE | [Architecture V2](docs/architecture/architecture-v2.md), [reconciliation](docs/architecture/review-reconciliation.md) |
| M01.02 Record domain, pipeline, statistical, deployment and privacy decisions | DONE | [Architecture documents](docs/architecture/architecture-v2.md), [ADR directory](docs/adr) and [decision log](docs/decision-log.md) |
| M01.03 Define provider classes and preserve source-neutral canonical models | DONE | [Match-ingestion architecture](docs/architecture/match-ingestion.md), [ADR-013](docs/adr/ADR-013-provider-neutral-match-ingestion.md) |
| M01.04 Define experiments, continuation/narrowing/stop rules | DONE | [Experiment plan](docs/architecture/experiment-plan.md), [pilot protocol](docs/pilot-protocol.md) |
| M01.05 Maintain full requirements and implementation progress | DONE | This tracker, [work log](docs/progress.md), [repository instructions](AGENTS.md); continuing obligation |

## M02 — Local canonical domain and evidence lifecycle

Owner: backend/analysis owner. Exit: local invariants hold under reprocessing, concurrency, deletion and migration.

| Requirement | Status | Acceptance / evidence |
|---|---|---|
| M02.01 Canonical match, participant, evidence, run, event and practice/evaluation records | DONE | [Models](backend/core/models.py), [data model](docs/architecture/data-model.md); local supported scope |
| M02.02 Owner-scoped PlayerGameIdentity, source assertions and optional match media | DONE | Migrations 0003/0004, [import service](backend/core/match_ingestion.py); unknown mappings remain null |
| M02.03 Version/hash knowledge, annotations, immutable events, plans and result revisions | DONE | Existing definition/event/plan constraints and regression tests |
| M02.04 Replace active contributions without counting an opportunity twice | DONE | Publication/reanalysis and practice-idempotency tests |
| M02.05 Fenced workers, owner-first locks, deletion invalidation and late-job rejection | DONE | Local lifecycle and PostgreSQL concurrency tests; attachment commit rechecks deletion, events retain original run-asset hashes after replacement |
| M02.06 Preserve historical upload/event/plan facts during schema cutover | DONE | [Migration rehearsal](tests/test_match_migration.py), upload-source backfill |

## M03 — Local UI, workers and synthetic integration

Owner: frontend/backend owner. Exit: a local operator can exercise the implemented flows without live services.

| Requirement | Status | Acceptance / evidence |
|---|---|---|
| M03.01 Reproducible Django/PostgreSQL/Next.js setup | DONE | [README](README.md), isolated workspace PostgreSQL, local management commands |
| M03.02 Candidate confirmation, consent, linked profiles and queued match imports | DONE | [Match API](backend/core/match_api.py), [UI](frontend/app/match-history.tsx); signed owner-bound selection |
| M03.03 Two synthetic adapters, idempotent pages, corrections, coverage, retries and revocation | DONE | [Synthetic adapter](ingestion/synthetic.py), import/API/concurrency tests |
| M03.04 Private paginated history with provenance, unknowns, expiry and mobile layout | DONE | Browser tests and inspected desktop/mobile screenshots; disputed outcomes remain unknown |
| M03.05 Capture → review → practice → comparison local UI and services | DONE | Complete synthetic loop test; actual measurement validation remains open |
| M03.06 Local verification commands and CI definition | DONE | 163 Python/11 browser checks recorded; CI authored, remote runner qualification tracked under M19 |

## M04 — Permitted real player identity linking

Owner: integration owner + product owner. Exit: a real submitted ID resolves to a persistent identity through an approved source, with explicit selection and no ownership overclaim.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M04.01 Review allowed identity lookup, purpose, upstream lineage and terms | BLOCKED | Dated approval/reference and expiry; [EWGF review](docs/research/ewgf-activation-review-2026-09-19.md) is not activation approval |
| M04.02 Verify TEKKEN ID, Polaris ID, numeric user ID, platform and formatting mappings | BLOCKED | Permitted current fixtures establish namespace/case/alias behavior; archived source is insufficient |
| M04.03 Implement real exact-ID resolver and missing/ambiguous-profile behavior | NOT_STARTED | No invented endpoint, silent casing change, lossy IDs or first-result selection |
| M04.04 Add permitted player-name lookup or expose its absence | PARTIAL | UI explicitly says unsupported now; actual name lookup needs a documented resolver and ambiguous-name tests |
| M04.05 Track alias changes, identity conflicts, revocation and re-link policy | PARTIAL | Claimed/revoked local links exist; reviewed alias/conflict/re-link lifecycle still needed |
| M04.06 Keep linking distinct from authentication and proof of control | PARTIAL | Local claims are unverified; real flow must retain this property; only add VERIFIED with an approved proof method |

## M05 — Live provider-neutral match discovery/import

Owner: integration/backend owner. Depends on M04. Exit: real recent matches import without video when metadata suffices; access and reliability constraints are explicit.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M05.01 Approve one concrete public provider operation and product usage scope | BLOCKED | Usage/caching/retention/attribution/deletion terms, allowed endpoint, review owner and expiry |
| M05.02 Configure private server credential and verify effective service tier | BLOCKED | Owner-managed credential outside source/logs/browser; no purchased tier inferred or provisioned |
| M05.03 Validate real response schema and provider error cases | BLOCKED | Permitted redacted fixtures for normal, zero matches, unknown ID, delayed/capped data and errors |
| M05.04 Implement allowed transport and normalization adapter | NOT_STARTED | Allowlisted origin/routes; bounded redirects, compression, bytes and timeout; preserve external IDs and raw versions |
| M05.05 Enforce shared quotas, Retry-After, bounded retries and sync freshness | PARTIAL | Offline policy/local retries exist; global credential quota, reset handling and outage recovery need live integration tests |
| M05.06 Keep provenance, immutable corrections, source coverage and pagination checkpoints | PARTIAL | Local persistence tested; validate actual provider caps/gaps and permitted raw-snapshot retention |
| M05.07 Reconcile cross-provider duplicates and video attribution | PARTIAL | Local reviewed video attribution preserves match UUID and historical facts; cross-provider merging remains unimplemented and requires reviewed shared identity/consistent facts |
| M05.08 Handle patch changes, replay expiry, unavailable payloads and provider withdrawal | PARTIAL | Local states exist; real scheduling, alerting, deletion obligations and source-switch compatibility remain |
| M05.09 Keep metadata out of the gameplay-event denominator | DONE | Metadata imports generate no GameplayEvent/AnalysisRun/ReplayAsset; regression covered |
| M05.10 Retain all four provider classes and private-endpoint prohibition | DONE | OFFICIAL, COMMUNITY_PUBLIC_API, REVERSE_ENGINEERED, USER_UPLOAD; no undocumented transport implemented |

Actual native replay retrieval/decoding is conditional on a permitted source and validated
format. It is not required when metadata or video meets the supported feature's evidence needs;
see X01. Never present replay-list metadata as a playable payload.

## M06 — Production video fallback and evidence attribution

Owner: media/backend owner. Exit: permitted recordings can safely supply evidence for imported or upload-only matches.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M06.01 Strict capture profile, preview and media validation | PARTIAL | Local 1080p60 SDR H.264 MP4, ≤10 min/512 MiB contract enforced; real capture support must pass G1/G3 |
| M06.02 Secure direct/resumable upload, completion verification and quotas | NOT_STARTED | Private hosted object adapter; validate final size/hash/owner; enforce limits before costly processing |
| M06.03 Attach a reviewed recording to an existing canonical match | PARTIAL | Local UI/API + operator review implemented and tested: exact identity/slot/time/build/mode checks, stale metadata rejection, idempotency, reprocessing and preserved UUID/history; real attribution validation and hosted flow remain. [ADR-014](docs/adr/ADR-014-recording-attribution.md) |
| M06.04 Separate played match, viewing pass, round, rewind and practice/takeover | PARTIAL | Basic local mode/segment contracts exist; real multi-segment handling or explicit supported-input rejection required |
| M06.05 Retain original timestamps and bounded evidence clips/artifacts | PARTIAL | Local native-PTS tooling exists; timestamp playback, derived retention and hosted retrieval need validation |
| M06.06 Cancel unfinished uploads and reconcile late objects/deleted accounts | PARTIAL | Local attachment cleanup after target deletion and pending-attachment account deletion tested; actual resumable provider integration/cleanup rehearsal required |
| M06.07 Enforce retention through comparison/audit and invalidate expired evidence | PARTIAL | Local attached-video purge withdraws evidence while retaining imported metadata and original event hashes; hosted objects, backups and consent renewal need verified operation |

## M07 — Reviewed game knowledge and supported situation

Owner: Tekken expert + analysis owner. Exit: one current-build situation and valid response have reviewed, reproducible definitions.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M07.01 Select target based on importance, observability, frequency and trainability | PARTIAL | Jin/Jin uf+4 provisional ranking exists; confirm with G1/G5 or choose the documented backup |
| M07.02 Verify exact build/platform and capture overlays in-game | BLOCKED | Actual build evidence; do not inherit the research date's patch as a capture's build |
| M07.03 Verify move identity, frame facts, response reach and timing | BLOCKED | Expert-reviewed permitted evidence; current draft intentionally contains unverified facts |
| M07.04 Define trigger, actors, eligibility, response window and unknown/exclusion rules | PARTIAL | Draft contract exists; validate wall/axis/stance/resources/reach and outcome observability |
| M07.05 Publish approved knowledge/situation/metric/drill versions | BLOCKED | Independent review recorded; new immutable versions rather than editing draft approval flags |
| M07.06 Manage patch mappings, incompatible evidence and targeted reanalysis | PARTIAL | Version fields/checks exist; actual patch-change/release workflow remains to be exercised |

## M08 — Consented golden dataset and annotation operations

Owner: dataset lead + two independent reviewers + adjudicator. Exit: an auditable real held-out dataset supports the declared recognition task.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M08.01 Consent, pseudonyms, manifests, source hashes and private storage | PARTIAL | Schemas/validator/protocol implemented; recruit consented participants and collect real captures |
| M08.02 Representative positives, failures, near misses and target-absent controls | BLOCKED | Initial 20 captures and later gate-sized data; include adverse/uncertain contexts rather than selected successes |
| M08.03 Independent dual labels and third-party adjudication | PARTIAL | Annotation tools and validation exist; reviewers, disagreements and actual review-time records missing |
| M08.04 Player/session/source-disjoint development, validation and test splits | PARTIAL | Split validator exists; freeze actual manifest revisions and held-out access policy |
| M08.05 Measure frame/timestamp uncertainty and critical outcome slices | PARTIAL | Harness exists; sufficient success/failure samples, timing audits and uncertainty labels still needed |
| M08.06 Honor withdrawals, retention and reproducibility constraints | PARTIAL | Local lineage exists; complete dataset/export inventory and deletion audit with real data |

## M09 — Validated observation/event recognition

Owner: analysis owner. Depends on M07–M08. Exit: released event classes meet their own real-data gates; abstention remains explicit.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M09.01 Bounded decode, probing, timestamps and candidate navigation | DONE | Local FFmpeg watchdog/probe tooling; hostile hosted isolation tracked under M15 |
| M09.02 Recognize required HUD/input/actor/contact observations | PARTIAL | Uncalibrated template tooling exists; actual reviewed templates/OCR and temporal alignment are unvalidated |
| M09.03 Convert observations to eligible opportunities and verified outcomes | PARTIAL | Deterministic rules tested synthetically; need real end-to-end predictions and evidence spans |
| M09.04 Report precision, recall, abstention, coverage and timing separately | PARTIAL | Evaluation harness exists; held-out G2 must pass in both success/failure slices |
| M09.05 Version detector/configuration/artifacts and replace current analysis safely | PARTIAL | Local publication/version semantics implemented; real detector release/rollback and selective reanalysis remain |
| M09.06 Reject unsupported profiles/builds and detect drift | PARTIAL | Local validation/gates exist; establish real failure categories, drift audit and release kill switch |
| M09.07 Maintain a human-reviewed fallback when automation is not justified | PARTIAL | Operator import exists; approved manual pilot procedure, review capacity and measured cost required |

## M10 — Player model and weakness prioritization

Owner: analysis/product owner. Exit: supported weaknesses are measurable, contextual, actionable and traceable to actual evidence.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M10.01 Binary/categorical rates with counts, uncertainty and unknowns | DONE | Local Beta/Dirichlet summaries; no global invented skill score |
| M10.02 Context/version-specific selected contributions without double counting | DONE | Local contribution/evaluation tests; live comparability validation remains under M12 |
| M10.03 Diagnose supported weakness from sufficient eligible observations | PARTIAL | Recommendation records and target logic exist; validate diagnosis against expert-reviewed real data |
| M10.04 Rank a small number of priorities by frequency, value, certainty and trainability | NOT_STARTED | Explicit scoring policy, minimum samples, reviewer agreement and user utility; no rank-derived competence claims |
| M10.05 Explain each priority using denominator, context, unknowns and timestamp evidence | PARTIAL | Local evidence/count UI exists; complete diagnostic cards and usability validation needed |
| M10.06 Separate result-history metrics from conditional gameplay metrics | PARTIAL | Separation enforced; broader descriptive history trends/filters still need implementation and validation |

## M11 — Reviewed drills and measured practice

Owner: Tekken expert + product/analysis owner. Exit: one approved drill produces observable, attributable practice attempts.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M11.01 Version drill setup, valid response, alternatives and success criteria | PARTIAL | Exactly one draft exists; expert review and current-build reproducibility required |
| M11.02 Assign the appropriate drill to an evidenced weakness | PARTIAL | Local approved-definition gate exists; release a genuinely reviewed drill and validate assignment behavior |
| M11.03 Provide usable native training instructions without requiring a mod | PARTIAL | Draft local UI/instructions; player trial must show correct setup and completion |
| M11.04 Record sessions/attempts and separate self-report from verified outcomes | PARTIAL | Reviewed local attempts implemented; real practice capture and G4 validation pending |
| M11.05 Count practice once with provenance and correct chronology | DONE | Local deduplication, source links and deletion-dependent evaluation tests |
| M11.06 Adapt progression/next action only using validated practice evidence | NOT_STARTED | Reviewed progression rules, adherence handling and real usability/effectiveness evidence |

## M12 — Trustworthy longitudinal evaluation

Owner: measurement/analysis owner. Exit: real baseline and later-match comparison can be reproduced without cherry-picking or incompatible measurements.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M12.01 Freeze baseline, metric, versions, windows and stop policy | DONE | Immutable EvaluationPlan and complete-selected-capture checks |
| M12.02 Freeze follow-up and practice memberships per result revision | DONE | Append-only results, canonical hashes, lineage/invalidation tests |
| M12.03 Enforce exposure, independent sessions, coverage and compatibility | PARTIAL | Local gates implemented; validate real play logs/sessionization and missing-source coverage |
| M12.04 Return all six legitimate outcomes with uncertainty and next actions | DONE | Local statistical engine; observed improvement is not a causal assertion |
| M12.05 Run prospective real baseline → practice → follow-up comparisons | BLOCKED | Consented cohort, approved measurement/drill and G5/G6 |
| M12.06 Compare source/decoder changes and verify retention of gains | NOT_STARTED | Predeclared compatible-source policy, bias audit and later retention measurement |
| M12.07 Validate statistical power/assumptions for broader claims | NOT_STARTED | Observed session variance and powered follow-up study; five sessions/40 outcomes are exploratory floors |

## M13 — Complete player-facing product experience

Owner: frontend/product owner. Exit: supported players can complete the real workflow without operator-only shortcuts.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M13.01 Explain supported game/build/capture scope and onboard a real player | PARTIAL | Persisted scope acknowledgement, capture guide and next steps implemented; no implied consent/build approval. Real accounts, released scope and unaided onboarding validation remain |
| M13.02 Find/confirm identity, show sync/coverage and browse source-aware history | PARTIAL | Local consent/selection/sync/coverage/error/expiry flow and match-to-evidence navigation implemented; approved real provider and real ambiguous-profile fixtures remain M04/M05 dependencies |
| M13.03 Review timestamped evidence and understand corrections/unknowns | PARTIAL | Paginated timeline, authenticated range playback, source provenance, disputed-event exclusion, complete-match selection and correction requests implemented; real media/player/reviewer usability and accessibility validation remain |
| M13.04 Present weakness, drill, measured practice and follow-up plan coherently | PARTIAL | Ordered journey, measured baseline summaries, frozen-plan details and practice gating implemented; synthetic browser path returns honest insufficient exposure. Real adherence and comparison usefulness remain unvalidated |
| M13.05 Search/filter supported matches and events | DONE | Current local supported scope: owner/player, UTC dates, character, situation/outcome, purpose/eligibility and history evidence state with typed pagination. Metadata-only records cannot satisfy gameplay filters; backend/browser checks pass |
| M13.06 Account/privacy controls, export, deletion and understandable support states | PARTIAL | Local private JSON export, password/CSRF-confirmed deletion, purge retry, sign-out, consent explanation, help and correction queue implemented; hosted signup/recovery/provider/backup/export operations remain M14–M16 dependencies |
| M13.07 Keyboard, screen-reader, mobile, timezone and supported-browser validation | PARTIAL | Skip link/focus, labeled controls, mobile overflow, reduced motion and UTC/America-Toronto checks pass in headless Edge; manual screen-reader, real-device, captions/visual-evidence accessibility and additional browser qualification remain |
| M13.08 User feedback and notification preferences | DONE | Agreed local channel: in-app only. Durable-state analysis/practice/follow-up notices, persistent dismissal/category opt-out, idempotent feedback and operator queue implemented/tested; no external sends. Bounded feed is explicit in [contract](docs/architecture/player-experience.md) |

## M14 — Accounts, consent and data ownership

Owner: backend/security/product owner. Exit: users control their account and permitted data in a hosted environment.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M14.01 Secure sign-up/sign-in, session lifecycle and recovery | PARTIAL | Local Django sessions/CSRF exist; production identity provider or equivalent verified/recovery flow needed |
| M14.02 Separate player identity claims from authenticated application ownership | DONE | Owner-scoped claimed links and cross-owner tests; no ID-as-password behavior |
| M14.03 Version processing consent, optional training consent and withdrawals | PARTIAL | Local consent separation exists; hosted policy versions, receipts and user controls needed |
| M14.04 Private data access, minimal opponent information and export | PARTIAL | Owner-only range playback and allowlisted JSON export tested locally; private storage/session fields and other people's identity snapshots excluded. Hosted download/export authorization and scale still need verification |
| M14.05 Account deletion across media, metadata, caches, backups and providers | PARTIAL | Self-service local password-confirmed deletion pseudonymizes login, clears feedback/receipts and tombstones every asset before purge; failure/retry tested. Provider/backup retention and restore suppression remain unverified |
| M14.06 Review identity re-linking and per-match suppression retention | BLOCKED | Current local deletion revokes identity-wide sync; approve production policy and narrower suppression if appropriate |

## M15 — Security, privacy and reliability hardening

Owner: security/backend owner. Exit: the externally exposed workload has tested containment, authorization and recovery behavior.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M15.01 Tenant isolation and nested ownership checks | PARTIAL | Local regression suite passes; hosted object/worker/download boundaries and adversarial review required |
| M15.02 Isolate hostile media and bound maximum-profile CPU/RAM/scratch/time | BLOCKED | Docker parser is an unvalidated candidate; run sandbox and malicious/maximum-size fixtures |
| M15.03 Harden provider fetches against SSRF, oversized payloads and schema drift | NOT_STARTED | Validate actual permitted transport with bounded error handling; no arbitrary URLs |
| M15.04 Secrets, least privilege, dependency maintenance and security logging | PARTIAL | Local configuration/lockfiles exist; production secret management, IAM, rotation and review required |
| M15.05 Abuse/rate limits, admission quotas and cancellation under load | PARTIAL | Local size/fencing guards exist; hosted abuse/admission enforcement and race tests needed |
| M15.06 Test provider outages, duplicate deliveries, stale workers and partial failure | PARTIAL | Local fault/concurrency tests exist; deployed integrations need failure injection |
| M15.07 Security/privacy review, incident response and vulnerability process | NOT_STARTED | Named operational owners, reviewed threat model, remediation criteria and incident rehearsal |

## M16 — Hosted asynchronous delivery and deployment

Owner: infrastructure/backend owner. Exit: approved workload operates in a private, recoverable hosted environment.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M16.01 Choose/provision region, cloud account and environments | NOT_STARTED | Recorded cost/privacy decision and authorized resource provisioning; separate development/staging/production |
| M16.02 Deploy web/API, managed PostgreSQL and private object storage | NOT_STARTED | TLS, secrets, IAM, migrations and health checks; storage adapter integration verified |
| M16.03 Implement durable dispatch/outbox/reconciler and bounded background execution | PARTIAL | Local polling/fences implemented; real dispatch/job/reconciliation adapters and total active-job cap needed |
| M16.04 Add worker heartbeats/progress, cancellation and stale-execution recovery | PARTIAL | Local job states exist; hosted failure/heartbeat/publication tests required |
| M16.05 Rehearse backup, restore, migration and rollback | NOT_STARTED | Restore evidence, recovery objectives and tombstones reapplied before data is exposed |
| M16.06 Deploy with approved release flags and real-data decisions | NOT_STARTED | No external media or automatic gameplay release before applicable scientific/security gates |

## M17 — Operations, performance and unit economics

Owner: operations/product owner. Exit: actual workload reliability and total cost are measured and controlled.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M17.01 Instrument run latency, CPU/RAM, bytes, failures, retries and review time | PARTIAL | Local synthetic benchmark exists; real provider/storage/network/support/reviewer measurements absent |
| M17.02 Set supported-workload latency, completion and availability objectives | DECISION | Define and approve numeric targets before beta; re-evaluate V1 assumptions rather than claiming them measured |
| M17.03 Load-test realistic history, uploads, jobs and concurrent owners | NOT_STARTED | Maximum supported files, source outages, query plans and capacity saturation; no extrapolation from a 0.5-second black clip |
| M17.04 Measure costs per capture, analysis, completed loop and comparable evaluation | BLOCKED | Actual infrastructure/egress/provider/reviewer rates and time; unknown inputs stay null |
| M17.05 Enforce storage/minutes/reanalysis/job budgets and hard admission caps | NOT_STARTED | Reserve/settle quotas idempotently and stop optional work at caps |
| M17.06 Monitoring, redacted logs, alerts, support runbooks and patch response | NOT_STARTED | Actionable dashboards, accountable responders and rehearsed recovery/provider-disable procedures |
| M17.07 Validate willingness to pay and recurring unit economics | BLOCKED | Approved actual offer and real use; evaluate pilot COGS targets from the experiment plan |

## M18 — Prospective real-player pilot

Owner: product/measurement owner + expert/reviewers. Exit: all G1–G6 have real results and an explicit continue, narrow or stop decision.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M18.01 Recruit permitted cohort, record consent and assign reviewers/expert | BLOCKED | [Pilot protocol](docs/pilot-protocol.md); no real participant/reviewer assignments recorded |
| M18.02 Run observability and reviewed-practice studies | BLOCKED | G1/G4; source manifests, denominators, uncertainty, reviewer disagreement and costs |
| M18.03 Run held-out recognition and unaided-capture studies | BLOCKED | G2/G3; do not tune on held-out outcomes or label a demo as a user study |
| M18.04 Run natural-frequency and prospective complete-loop study | BLOCKED | G5/G6; include zero-opportunity/missing sessions and adverse results |
| M18.05 Compare against native replay/training and usual practice | PARTIAL | Comparator protocol prepared; actual usefulness/adherence/time-to-insight evidence missing |
| M18.06 Record decisions and revise scope from negative evidence | PARTIAL | Result templates/stop rules exist; complete evidence-backed gate decisions before release |

### Scientific gates — all NOT_RUN

These thresholds come from the existing [experiment plan](docs/architecture/experiment-plan.md).
Do not silently change them after seeing results; record a revised protocol first.

| Gate | Required study / proposed pass criteria | State |
|---|---|---|
| G1 Human observability | 20 consented captures; ≥90% critical windows resolvable; >20% unobservable triggers narrowing | NOT_RUN |
| G2 Automatic correctness | ≥300 accepted critical held-out predictions plus negatives; precision ≥.98, one-sided 95% lower bound ≥.95, recall ≥.60 in success and failure slices | NOT_RUN |
| G3 Capture adoption | 15–20 users; ≥80% valid unaided captures, median setup ≤10 min; <50% after revision changes ingestion | NOT_RUN |
| G4 Practice measurement | 10 players × ≥40 attempts; ≥90% coverage and ≥95% outcome agreement; <80% coverage or systematic bias blocks verified practice | NOT_RUN |
| G5 Natural occurrence | 20 prospective histories over four weeks; ≥60% meet exploratory exposure feasibility; <30% changes target | NOT_RUN |
| G6 Comparable useful loop | ≥60% evaluable; compare native/usual workflow and retain inconclusive results; <30% comparable or no additional utility revises proposition | NOT_RUN |

G2 failure blocks automatic judgments. Human-reviewed measurement may proceed only through a
recorded manual-pilot decision. Insufficient data never becomes a pass by waiver or optimism.

## M19 — Hosted private beta and release qualification

Owner: technical/product owner. Exit: real supported users complete the hosted flow with demonstrated safety and operational quality.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M19.01 Record pilot continuation decision and beta-supported scope | NOT_STARTED | M18 findings and applicable M04–M17 requirements accepted |
| M19.02 Execute remote CI and staging end-to-end tests | NOT_STARTED | Hosted runner evidence; real auth/storage/job/provider integrations with permitted test data |
| M19.03 Test onboarding → import/upload → coaching → practice → later evaluation | NOT_STARTED | Real participant paths and accessible error recovery; no staff-only bypass as user workflow |
| M19.04 Exercise deletion, consent withdrawal, outage, rollback and restore | NOT_STARTED | Traceable operational evidence and resolved release-blocking defects |
| M19.05 Measure beta usability, retention, useful decisions and support burden | NOT_STARTED | Predeclared denominators and adverse outcomes; product value beyond native workflow |
| M19.06 Approve release candidate, known limitations and incident owners | NOT_STARTED | Completed acceptance review; monitoring and rollback enabled |

## M20 — Public supported release and commercial readiness

Owner: product/technical owner. Exit: a clearly scoped, supported and sustainable release is available to its intended users.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M20.01 Publish accurate supported coverage and evidence limits | NOT_STARTED | Approved builds/situations/providers/profiles and accessible help; no unsupported all-Tekken or causal-improvement promises |
| M20.02 Finalize user terms/privacy, provider rights and retention obligations | BLOCKED | Review for actual operating model and data flows; no commercial clearance inferred from public API/source availability |
| M20.03 Choose access/pricing model after observed usefulness and cost | DECISION | Free/paid/invite policy and limits based on M17/M19 evidence; no invented revenue assumptions |
| M20.04 Implement billing/entitlements if the chosen launch is paid | DECISION | Use established payment service; test webhook idempotency, cancellation/refunds, quota changes and applicable receipts before charging |
| M20.05 Provide support, feedback, incident communication and operator ownership | NOT_STARTED | Published support path, operational coverage and maintenance/patch procedures |
| M20.06 Complete launch review and controlled rollout | NOT_STARTED | Security/quality/data-rights/operations sign-off, real deployment checks, rollback and post-launch monitoring |

## M21 — Broader validated Tekken coverage

Owner: gameplay/product/analysis owners. Exit: each advertised expansion is independently supported and maintains trustworthy comparisons.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M21.01 Prioritize additional characters and high-value situations | NOT_STARTED | Real user demand, frequency, observability, knowledge rights and training value; no arbitrary catalog count |
| M21.02 Add per-situation knowledge, datasets, detectors and uncertainty policies | NOT_STARTED | Reapply G1/G2-style validation and release flags; declare measured coverage |
| M21.03 Add expert-reviewed drill catalog and validated progression | NOT_STARTED | Reproducible setup, measured attempts and real-match transfer for each supported task |
| M21.04 Add broader context/habit/search capabilities without sparse-data overclaims | NOT_STARTED | Sufficient samples, contextual rates and meaningful player decisions |
| M21.05 Support additional capture profiles/platforms only after measurement | NOT_STARTED | New timing/visibility/error tests and known incompatibility rules |
| M21.06 Operate ongoing patch updates and backward-compatible historical interpretation | NOT_STARTED | Compatibility matrix, targeted reanalysis, retired capabilities and re-baseline guidance |

## Wider product vision — explicit optional requirements

These preserve the broader original vision without making speculative features prerequisites
for the first credible product. Each needs a recorded scope decision, its own acceptance tests
and a new milestone before implementation. None is currently released.

| ID | Capability | Status | Required decision / completion conditions |
|---|---|---|---|
| X01 | Permitted native replay / structured-event source | BLOCKED | Technical and usage review, allowed payload acquisition, verified format/version/expiry, validated decoder; same canonical event gates as video |
| X02 | Personal AI explanations/chat | DECISION | Deterministic reports useful first; evidence-only bundles, no invented facts, prompt-injection defenses, numeric/ID validation, cost cap and deterministic fallback |
| X03 | Browser mechanics lab | DECISION | Define what the exercise actually measures, input/display latency and transfer; do not call browser performance verified in-game skill |
| X04 | Advanced semantic replay search | DECISION | Typed filters/timestamp search first; evaluate semantic search only where it improves real retrieval, with owner/version/deletion constraints |
| X05 | Skill passport / benchmark scores | DECISION | Validated comparable cohorts and calibrated definitions before normalized scores; preserve rates/uncertainty and game scope |
| X06 | Adaptive combo lab | DECISION | Versioned combos, permitted measurement, verified drops/success, contextual resource/position utility and reviewed drills |
| X07 | Personalized patch impact | DECISION | Trusted patch deltas × actual move usage; historical facts retain original build and source provenance |
| X08 | Evidence-based puzzles | DECISION | Curated clips/answers, ambiguity handling, attempts and measured value; no unsupported unique-optimal-answer claim |
| X09 | Smart sparring | DECISION | Mutual opt-in, matchmaking constraints, privacy/abuse controls and enough participants; separate from core coaching |
| X10 | Coach OS / multi-student workflows | DECISION | Explicit revocable grants, tenant isolation, notes/assignments/report permissions and evidence of coaching demand |
| X11 | Creator clips/tools | DECISION | Separate consent, opponent redaction, licensed media/export and retention workflow |
| X12 | Additional games and optional in-game drill adapters | DECISION | Actual second-game requirements or permitted integration, distinct rule/knowledge/measurement contracts, security review and demonstrated utility |

Live coaching, game-process access, anti-cheat-risk integrations, a marketplace/social network,
foundation-model training and large distributed infrastructure are not authorized requirements.
Reconsider them only through an explicit product/architecture decision with supporting evidence.

## Immediate next work and blockers

| Priority | Next concrete outcome | Requirements | Needed input / owner |
|---|---|---|---|
| 1 | Prepare activation of one documented public provider | M04.01–M04.03, M05.01–M05.04 | Product owner obtains applicable usage evidence and privately configures a key; integration owner verifies permitted fixtures; never paste secrets into this tracker |
| 2 | Acquire first consented captures and expert review | M07.02–M07.05, M08.02–M08.03 | Participants, exact-build evidence, Tekken expert, two reviewers and adjudicator |
| 3 | Validate observability/practice before promoting recognition | M09, M11, G1/G4 then G2 | Dataset/review findings; select backup/narrow if required |
| 4 | Qualify the completed local player journey and harden media processing | M13.01–M13.04/M13.06–M13.07, M15.02 | M13 local engineering is delivered. Next: manual screen-reader/real-device and participant checks; rehearse parser isolation when a runtime is available; retain real-provider/account gates |
| 5 | Run prospective real loop, then qualify hosting/beta | M12, M16–M19 | Measurement decisions, permitted data and validated security/operational integrations |

The tracker is not authorization to purchase, contact providers, collect new personal data,
enable undocumented endpoints or deploy externally. Existing user authorization and applicable
release gates still govern those actions. Do not let one external blocker stop independent work.

## Update protocol — required after every implementation

1. Before coding, read this file and identify the milestone/requirement IDs affected.
2. If work introduces a new requirement, add a stable ID and acceptance criterion first or
   alongside the implementation. Do not quietly expand scope.
3. After implementation, update every affected requirement status and its remaining work or
   evidence. Regressions reopen previously completed requirements.
4. Update the milestone overview, current-position snapshot, last-updated date, blockers and
   next work when affected. Keep local implementation separate from real-world validation.
5. Record actual checks run and their result/scope. If checks were not run, say so; do not
   reuse an old test count as a fresh result. Link detailed validation instead of duplicating logs.
6. Append an entry to [docs/progress.md](docs/progress.md) with completed work, changed files,
   tests, validated/unvalidated assumptions, blockers, next step and requirement IDs.
7. Update [docs/decision-log.md](docs/decision-log.md), architecture/ADRs or release evidence
   when the change affects scope, policy, definitions or architecture.
8. Before the final handoff, check links and status consistency. An implementation is not
   finished until this tracker and the work log reflect it. No new approval is needed for updates.

## Tracker change record

| Date | Requirements | Change | Validation |
|---|---|---|---|
| 2026-09-19 | M01.05; baseline M01–M21 and X01–X12 | Established the comprehensive current-status tracker from Architecture 2.2, the implementation brief, provider addition and recorded work | Documentation/requirement-ID/link checks; software results referenced from the preceding implementation |
| 2026-09-23 | M06.03/M06.06/M06.07, M13.03 | Delivered local reviewed recording attachment and immutable evidence lineage | 145 Python / 7 browser tests; migration 0005 |
| 2026-09-23 | M13.01–M13.08, M14.04/M14.05 | Delivered available local M13 product flows; kept external release dependencies explicit | 163 Python / 11 browser tests; migration 0006; build/static/schema checks |
