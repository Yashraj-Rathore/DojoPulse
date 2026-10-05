# DojoPulse product progress

Last updated: **2026-10-05** · Architecture: **2.17.0** · Current stage: **local research prototype**

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
| Player diagnosis (M10) | Coherent local diagnosis/priority/card/history module qualified (M10.07 DONE); code 687f0f2 passed all six CI jobs. Real expert thresholds, reviewer agreement, relative assessments and player utility remain unvalidated |
| Guided practice (M11) | Coherent local module qualified (M11.07 DONE); fd816af passed all six CI jobs. Reviewed native workflows, current diagnosis-pinned prescription, complete/current exact-scope practice, separate reports and conservative next action. Real drill reproducibility, expert/player approval and G4 remain open |
| Longitudinal evaluation (M12) | Coherent local module qualified (M12.08 DONE): scheduled follow-up/retention, gap receipts, exact source/decoder pins, safe reproducible reports and baseline-only planning. Published code 8f2f57b passed all six CI jobs. Real cohort/source bias/retention/power/G5/G6 remain unvalidated |
| Core loop | Baseline → drill assignment → reviewed practice → later-match comparison implemented and tested synthetically |
| Match acquisition | Player confirmation, consent, queued sync, source history and deletion work with two fictional providers |
| Recording attribution | Resumable local UI/API preserves imported history, verifies bytes before queuing media validation and separate attribution/gameplay review; removal withdraws evidence |
| Player experience (M13) | Local flows plus original graphite/ember visual system, dojo artwork, self-hosted fonts and responsive player/operator surfaces implemented (M13.09 locally qualified). Training tools lead; account/privacy controls remain available. Real-user/device/accessibility release acceptance remains open |
| Accounts and consent (M14) | Local signup/verification/recovery, email/password changes, session revocation, versioned consent and withdrawal, export/deletion extensions and explicit re-linking with known-match suppression implemented. External mail, policy approval and backup/provider erasure remain gated |
| Security and reliability (M15) | Local engineering implemented across M15.01–M15.07: real Docker isolation, admission/rate limits, ownership/fencing, offline provider guards, dependency fixes and incident procedures; production qualification remains open |
| Real player IDs / providers | No live identity resolver or match transport enabled; EWGF usage rights, credentials and current authenticated schema unresolved |
| Gameplay recognition | Coherent M09 local candidate/version/benchmark/review/rollback/drift/erasure module qualified (M09.08 DONE), source 621a161 all six CI jobs green. Actual Tekken detector, observation calibration and G1/G2 remain unvalidated |
| Knowledge and drills | M07 local evidence/independent review/publication/lifecycle/patch module implemented; real current-build facts, response and expert approval remain missing |
| Scientific validation | G1-G6 remain NOT_RUN. M08 adds a non-promoting G1 observability report, owned API/UI and offline reproduction (M08.08 DONE for local tooling); source e674342 passed all six CI jobs. Public-source/install investigation acquired zero qualifying captures; real build/expert/reviewer evidence remains missing |
| Pilot preparation (M18) | Local consent, pseudonyms, prospective intake/allocation, blinded review/adjudication, canonical links, evidence packs and withdrawal/restore erasure delivered; `135464f`/clean reconciliation `2bbb645` passed all six CI jobs; real studies remain unrun |
| Operations and economics (M17) | Local resource ledger, fenced measurements, staff dashboard/CLI alerts, time/cost observations, retention and synthetic saturation/outage checks implemented. Objectives are proposed; actual hosted costs, named response, real workloads and payment evidence remain open |
| Hosting and release | M06 resumable/private storage engineering and M16 dispatch/recovery are implemented locally with controlled GCS/Terraform contracts. Native PostgreSQL recovery now includes pending upload erasure. Actual GCS, cloud media isolation, region/budget/IAM/CORS and production release remain gated |
| Latest recorded checks | UI source ec5e102 passed all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37385253136) first attempt, completed 2026-10-05 23:04:25 UTC: 519 PostgreSQL (550.314s), 54 Chromium (39.4s), seven actual Docker/max-profile (90.925s), three Terraform, audits/static/build/unprivileged startup/asset HTTP byte checks and native recovery. Local 54 Edge plus final two entry checks, desktop/mobile previews, links/YAML and selected token contrast also pass. [UI qualification](docs/experiment-results/m13-visual-system.md); real gameplay/accessibility/hosting remain unvalidated |
| Evidence for those checks | [UI qualification](docs/experiment-results/m13-visual-system.md), [visual system and asset provenance](docs/design/visual-system.md), [G1 qualification](docs/experiment-results/g1-preparation.md); earlier receipts retain dated scopes. Synthetic software does not establish real gameplay or hosted readiness |
| Published delivery | UI source ec5e10217918b1bb3245bdd65dc5d99f08201ace pushed directly to main with all six jobs successful first attempt. Final qualification receipt retains ordinary CI and requires exact latest-tip monitoring. Only main exists; prior G1 delivery remains separately dated historical evidence |
| Repository delivery policy | Only `main` remains; all 15 inspected bot proposals closed/deleted and 16 stale local tracking entries pruned. Four Dependabot version-PR streams disabled and GitHub validator passed; automatic security PRs already off and unchanged. Audits remain active with weekly reviewed/tested patches directly on main. Previous receipt `e70a83e` skipped CI; current policy requires checks on every published tip, including progress receipts |
| Source integrity finding | Remote `301ed0b` injected obfuscated Next config code, repaired by `1771eba`. Rewritten receipt `2a20380` reintroduced an obfuscated eval payload; its sole difference from verified `5c1e78c` was Next config. `2bbb645` retains remote ancestry with the qualified clean M18 tree; current main head verified after CI. Repository-access/prior-execution review remains open |
| Publication validation | UI exact source ec5e102 six-job success, watcher exit 0, backend/sandbox XML and frontend/Terraform/container logs verified. Fresh remote source head/only-main inventory match. Final ordinary receipt must also be monitored on its exact SHA; source-access/dev advisory/real/provider/hosted gates remain open |

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
| M01 | Product architecture and delivery governance | DONE | Architecture/tracking and main-only checked delivery implemented; maintain decisions, audits and this tracker |
| M02 | Local canonical domain and evidence lifecycle | DONE | Local scope; hosted equivalents tracked separately |
| M03 | Local UI, workers and synthetic integration | DONE | Local scope; live providers and real measurements separate |
| M04 | Permitted real player identity linking | BLOCKED | Approved resolver, identity mapping and permitted fixtures |
| M05 | Live provider-neutral match discovery/import | BLOCKED | M04 plus provider usage rights, credential and response schema |
| M06 | Production video fallback and evidence attribution | PARTIAL | Coherent M06 local/controlled storage engineering delivered (M06.08 DONE); actual hosted IAM/CORS/erasure, real captures and attribution remain release gates |
| M07 | Reviewed game knowledge and supported situation | BLOCKED | Local governance module implemented; real current-build footage, permitted facts and independent Tekken experts still required |
| M08 | Consented golden dataset and annotation operations | PARTIAL | Coherent local module qualified (M08.07 DONE); G1 assessment and official-client capture procedure locally checked (M08.08 DONE). Permitted representative real footage and qualified independent reviewers still needed |
| M09 | Validated observation/event recognition | PARTIAL | Coherent local candidate engineering qualified (M09.08 DONE); actual released observation classes require permitted M07-M08 evidence, calibration and G1/G2 |
| M10 | Player model and weakness prioritization | PARTIAL | Coherent local diagnosis/priority/card/history engineering qualified (M10.07 DONE); real expert thresholds/assessments, agreement, selection bias, player utility and hosted qualification remain |
| M11 | Reviewed drills and measured practice | PARTIAL | Expert-approved drill and G4 |
| M12 | Trustworthy longitudinal evaluation | PARTIAL | Coherent local comparison module qualified (M12.08 DONE); actual prospective cohort, source/decoder bias, retention, power and G5/G6 remain unvalidated |
| M13 | Complete player-facing product experience | PARTIAL | Local engineering delivered across M13.01–M13.09, including the original responsive visual system; real provider/account/reviewer flows, participant usability, screen readers and real devices remain release dependencies |
| M14 | Accounts, consent and data ownership | PARTIAL | Local account module implemented; production mail/abuse/policy, hosted authorization and backup/provider erasure qualification remain |
| M15 | Security, privacy and reliability hardening | PARTIAL | Local controls and Docker qualification delivered; deployment-specific isolation/abuse/restore and independent security/privacy review remain |
| M16 | Hosted asynchronous delivery and deployment | PARTIAL | Local dispatch/recovery and mocked Google/Terraform preparation delivered; approved region/budget, equivalent hosted media isolation, durable journal and staging integration remain |
| M17 | Operations, performance and unit economics | PARTIAL | Local engineering module delivered; approved objectives, representative hosted workload, external alert/response ownership, actual costs and recurring payment evidence remain |
| M18 | Prospective real-player pilot | PARTIAL | Local consent/review/report preparation implemented; real participants, approved protocol/rights, expert and G1–G6 observations remain blocked |
| M19 | Hosted private beta and release qualification | PARTIAL | First remote software CI jobs passed; pilot decisions, staging and operational/security qualification remain |
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
| M01.06 Maintain the requested single-branch delivery and checked publication | DONE | 2026-10-02: 15 bot PRs closed/branches deleted, 16 stale local tracking refs pruned, only main remains. Four version-PR streams disabled in published `c7d60ee`; automatic security PRs already off and unchanged. All six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37045159974) plus GitHub YAML validation passed on that exact tip. Existing audits/weekly manual patch review retained; [instructions](AGENTS.md), D029 and [work log](docs/progress.md). Continuing obligation: publish/monitor ordinary receipts with CI enabled |

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
| M03.06 Local verification commands and CI definition | DONE | 163 Python/11 browser checks recorded; first Linux frontend and PostgreSQL CI jobs passed; hosted staging qualification remains M19 work |

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
| M06.01 Strict capture profile, preview and media validation | PARTIAL | Local preview and parser enforce 1080p60 SDR H.264 MP4, <=10 min/512 MiB; resumable UI requires consent and continuous-capture declaration. Declaration is not automatic cut/rewind detection; real capture support still needs G1/G3 |
| M06.02 Secure direct/resumable upload, completion verification and quotas | PARTIAL | Durable owner/idempotency sessions, declared-byte reservations, bounded local chunks, official GCS create-only/observed-offset contracts and background exact size/SHA-256/MD5/generation checks implemented. Actual GCS/IAM/CORS and hosted load qualification remain; [M06 receipt](docs/experiment-results/m06-storage.md) M07 adds explicit capture platform for governed build evidence. |
| M06.03 Attach a reviewed recording to an existing canonical match | PARTIAL | Legacy/resumable transfer share pending-attribution source creation; identity/slot/time/build/mode/revision checks are repeated after byte verification. Imported UUID/history remain and no gameplay is auto-approved. Stale claims, deletion, status-probe revocation and duplicate races checked; actual attribution/hosted flow remain. [ADR-014](docs/adr/ADR-014-recording-attribution.md), [ADR-018](docs/adr/ADR-018-resumable-private-evidence.md) |
| M06.04 Separate played match, viewing pass, round, rewind and practice/takeover | PARTIAL | Local purpose/segment contracts and explicit supported continuous uncut capture declaration implemented. No automatic multi-segment/rewind detection or real-input rejection qualification claimed; unsupported-input observation/review remains |
| M06.05 Retain original timestamps and bounded evidence clips/artifacts | PARTIAL | Native-PTS tooling and authenticated local/suffix/open range playback implemented; controlled GCS generation-pinned range headers/byte bounds/stream closure checked. Real timestamp/clip support, storage CORS and hosted artifact retention remain |
| M06.06 Cancel unfinished uploads and reconcile late objects/deleted accounts | PARTIAL | Durable cancel/expiry/withdrawal/account/target-match deletion fences sessions; failure retains bytes/slots. Controlled initialization/deletion race, capability cancellation, bounded retries, post-backup unknown deadline and native restore erasure checked. Actual provider late-finalization/all-version erasure qualification remains |
| M06.07 Enforce retention through comparison/audit and invalidate expired evidence | PARTIAL | Local purge withdraws lineage; retention now blocks playback, enqueue/claim/heartbeat/finish, attribution/publication, newly computed practice/comparison eligibility before purge. Existing expired-source maintenance invalidates dependent reports. Hosted objects/backups/renewal/current controls and actual operation remain unverified |
| M06.08 Deliver coherent resumable-upload and private-playback engineering | DONE | Defined local/controlled-client scope delivered: durable sessions/quota, bounded chunks and official GCS contracts, background byte verification before canonical analysis/attribution, pause/resume/refresh/cancel UI, expiry/late-initialization/restore cleanup and generation-pinned private playback. See [contract](docs/architecture/evidence-storage.md) and [qualification](docs/experiment-results/m06-storage.md). Does not complete actual hosting or real-capture release gates |

## M07 — Reviewed game knowledge and supported situation

Owner: Tekken expert + analysis owner. Exit: one current-build situation and valid response have reviewed, reproducible definitions.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M07.01 Select target based on importance, observability, frequency and trainability | PARTIAL | Jin/Jin uf+4 provisional ranking exists; confirm with G1/G5 or choose the documented backup |
| M07.02 Verify exact build/platform and capture overlays in-game | BLOCKED | Local registration/pinned review implemented. 2026-10-05 bounded Steam inventory found Tekken 8 installed, but no in-game version/overlay evidence verified; Steam build number is not the game version. [Capture procedure](docs/architecture/observability-assessment.md) prepared; actual evidence missing |
| M07.03 Verify move identity, frame facts, response reach and timing | BLOCKED | Local bounded fact/reach/timing candidate and dual-review trail implemented; expert-reviewed permitted actual evidence missing; draft facts stay unverified |
| M07.04 Define trigger, actors, eligibility, response window and unknown/exclusion rules | PARTIAL | Local versioned bounded Jin semantics, mandatory observations and unknown/exclusion gates implemented; real wall/axis/stance/resources/reach/outcome validation remains |
| M07.05 Publish approved knowledge/situation/metric/drill versions | BLOCKED | Local two-reviewer publication creates new immutable versions, rechecks dependency/build/scope grants, and supports retirement/withdrawal. Actual current-build expert/rights release is code-gated; synthetic approval cannot promote real evidence M08 adds an explicit revocable exact-source measurement grant for reviewed dataset import, without workspace-wide knowledge/drill approval. M11 also reviews bounded native workflow/progression payloads only in new immutable versions; real approval remains gated. |
| M07.06 Manage patch mappings, incompatible evidence and targeted reanalysis | PARTIAL | Local immutable three-disposition mapping, impact preview, budgeted owner-requested canonical reanalysis and reviewed replacement implemented; source build/original event hashes/frozen plans preserved. Actual patch compatibility remains unvalidated |
| M07.07 Complete local knowledge governance module | DONE | Local API/UI, sealed source/dependency review, independent decisions, immutable scoped publication, lifecycle/privacy/restore and reviewed reanalysis delivered; 371 Python/30 Chromium/seven Docker, guarded migrations/recovery/static/audits and forced PostgreSQL races pass on main dcda2bd. [Contract](docs/architecture/knowledge-governance.md), [qualification](docs/experiment-results/m07-knowledge.md). Real M07 and hosted review remain gated |

## M08 — Consented golden dataset and annotation operations

Owner: dataset lead + two independent reviewers + adjudicator. Exit: an auditable real held-out dataset supports the declared recognition task.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M08.01 Consent, pseudonyms, manifests, source hashes and private storage | PARTIAL | M08 reuses M18 self-consent/private review with newly created exact-measurement studies, immutable definition/source/consent/retention pins and manifests. Existing consent is not extended retroactively; real rights/protocol/intake/storage qualification remains gated |
| M08.02 Representative positives, failures, near misses and target-absent controls | BLOCKED | Existing coverage/absence checks plus G1 aggregate categories, ranked/practice/control separation, session gaps and all unresolved target windows. [Public-source research](docs/research/capture-acquisition-2026-10-05.md) found no qualified set; zero qualifying captures acquired. Actual 20 initial captures and gate-sized representative/adverse evidence missing |
| M08.03 Independent dual labels and third-party adjudication | PARTIAL | Existing blinded dual/third review plus G1 unresolved-reason, dual/reference timing and review-time reporting; known outcomes rederived conservatively. No expert/reviewers/adjudicator assigned or qualified by public discovery; actual independent adverse labels and measured real review time still needed |
| M08.04 Player/session/source-disjoint development, validation and test splits | PARTIAL | Dataset-wide keyed split/source assignment guards span linked studies, snapshots and withdrawals; freeze source inputs/predictions before held-out manager label access, validate disjoint portable receipts. Representative real manifests, aliases/prior exposure and external blindness remain unqualified |
| M08.05 Measure frame/timestamp uncertainty and critical outcome slices | PARTIAL | Existing explicit timing/frame audits and prediction slices plus reproducible G1 all-target resolvability, per-split/source concentration and separate missing-timing checks. Practice/control counts cannot inflate critical windows. Actual frame accuracy, sufficient real slices and G1/G2 remain missing |
| M08.06 Honor withdrawals, retention and reproducibility constraints | PARTIAL | Immutable hashed snapshot/QA receipts, exact-source owner/operator canonical import, current permission/source checks, withdrawal/expiry/definition/restore erasure and derived event/result invalidation implemented. Minimal keyed leakage guards last until collection closure. Real deletion audit, hosted/offline retained-copy erasure and any training rights/use remain separate |
| M08.07 Complete local dataset and annotation operations module | DONE | Coherent API/UI, M07 pins, linked M18 review, immutable split/source/snapshot lineage, portable validation, source-scoped canonical import and privacy/recovery delivered; 394 PostgreSQL/Python, 35 Chromium, seven Docker/max-profile, three Terraform mocks, build/static/schema/audits and guarded native recovery passed on main d83f342; all six CI jobs verified first attempt. [Contract](docs/architecture/dataset-operations.md), [qualification](docs/experiment-results/m08-datasets.md). Local engineering does not complete the real golden dataset |
| M08.08 Prepare capture acquisition and reproducible G1 observability assessment | DONE | Local tooling acceptance met: dated source research, official-client capture/review procedure, owned revocable snapshot API/UI/CLI, explicit target/unknown/practice/control denominators, exact proposed thresholds, timing/category/session gaps and hashed aggregate receipt without identities or approval. Source e674342 passed all six CI jobs: 519 PostgreSQL, 52 Chromium, seven actual Docker/max-profile, three Terraform, audits/static/build/startup/native recovery. [Qualification](docs/experiment-results/g1-preparation.md) records scoped local checks, initial browser synchronization fix and optional OpenAPI limitation. Final ordinary-CI receipt needs exact-tip monitoring; zero qualifying captures or reviewers, G1/G2 NOT_RUN. [Contract](docs/architecture/observability-assessment.md), [ADR-025](docs/adr/ADR-025-capture-acquisition-and-observability-assessment.md) |

## M09 — Validated observation/event recognition

Owner: analysis owner. Depends on M07–M08. Exit: released event classes meet their own real-data gates; abstention remains explicit.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M09.01 Bounded decode, probing, timestamps and candidate navigation | DONE | Local FFmpeg watchdog/probe tooling; hostile hosted isolation tracked under M15 |
| M09.02 Recognize required HUD/input/actor/contact observations | PARTIAL | Fixed-engine manifests pin code/template/config artifacts; bounded offline template bridge produces timestamped LOW-support UNKNOWN candidates. Real reviewed HUD/input/actor/contact implementations and calibration remain unvalidated |
| M09.03 Convert observations to eligible opportunities and verified outcomes | PARTIAL | Typed evidence spans, explicit nullable/ordinal support and conservative rules produce synthetic unverified candidates; real/missing/conflicting/unsupported observations abstain. No automatic canonical writes; real validated end-to-end recognition remains required |
| M09.04 Report precision, recall, abstention, coverage and timing separately | PARTIAL | Owned immutable all-held-out-source benchmark/reproduction receipts, one-to-one eligibility/success/failure slices, bounds, abstention/coverage/timing and negative controls implemented. Retrospective software checks do not establish prospective real G2 |
| M09.05 Version detector/configuration/artifacts and replace current analysis safely | PARTIAL | Immutable exact-measurement manifests and report hashes, two assigned independent approvals, one synthetic active version/dataset, latest-receipt activation/replacement/rollback and current owner reproduction implemented. Real release/selective reanalysis and canonical replacement remain gated |
| M09.06 Reject unsupported profiles/builds and detect drift | PARTIAL | Exact build/platform/profile checks, explicit UNKNOWN, bounded uncertainty/abstention, operator stop and failing-active-benchmark DRIFT_STOP implemented. Actual video drift audits, thresholds and hosted alert/kill-switch qualification remain required |
| M09.07 Maintain a human-reviewed fallback when automation is not justified | PARTIAL | Recognition console links existing blinded M08/M18 review and exact-source canonical import; candidates cannot enter verified events/diagnosis/practice/effectiveness. Actual approved manual pilot capacity, cost and usability remain required |
| M09.08 Complete local recognition and validation engineering module | DONE | Fixed version/code/template/config and exact measurement pins; bounded evidence/UNKNOWN rules; all-source reproducible benchmark; independent latest-report activation/replacement/rollback/drift stop; owned UI/API; manual fallback and withdrawal/expiry/export/restore erasure with guarded native 0021 migration. Source 621a161 passed all six CI jobs: 499 PostgreSQL, 51 Chromium, seven actual Docker/max-profile, three Terraform mocks, audits/static/build/startup/recovery. Media first attempt cancelled before runner/steps; same-source retry passed. [Contract](docs/architecture/recognition-validation.md), [ADR-024](docs/adr/ADR-024-versioned-recognition-candidates-and-revocable-benchmarks.md), [qualification](docs/experiment-results/m09-recognition.md). Real M09/G1/G2 remain unvalidated |

## M10 — Player model and weakness prioritization

Owner: analysis/product owner. Exit: supported weaknesses are measurable, contextual, actionable and traceable to actual evidence.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M10.01 Binary/categorical rates with counts, uncertainty and unknowns | DONE | Local Beta/Dirichlet summaries; diagnosis cards add descriptive failure intervals, both coverages and explicit unknowns; no global invented skill score |
| M10.02 Context/version-specific selected contributions without double counting | DONE | Current canonical publications only; situation/metric/context/build/knowledge/hash/detector/platform/scope buckets, reanalysis evidence hashes and incompatible-profile abstention. Live comparability remains under M12 M11 server-recomputes/pins exact card evidence and membership at prescription; unchanged current projection and no favorable filters. |
| M10.03 Diagnose supported weakness from sufficient eligible observations | PARTIAL | Versioned proposed sample/session/coverage/independent-review policy and descriptive states implemented; real diagnosis remains gated on expert-reviewed real data and threshold qualification |
| M10.04 Rank a small number of priorities by frequency, value, certainty and trainability | PARTIAL | Transparent versioned synthetic research score, at most three priorities within one compatible profile, immutable independently reviewed drill assessments; missing/ambiguous ratings remain null. Actual expert ratings, representative frequency, agreement and player utility remain unvalidated |
| M10.05 Explain each priority using denominator, context, unknowns and timestamp evidence | PARTIAL | Local diagnostic cards show counts/coverage/uncertainty, context/version/hash pins, all reasons/factors and private timestamp samples/full-match links. Real participant usability/accessibility and expert explanation acceptance remain |
| M10.06 Separate result-history metrics from conditional gameplay metrics | PARTIAL | Local date/context/build filters, recorded wins/losses/unknowns and monthly gameplay summaries are separate; versions are not pooled and frozen M12 comparisons remain unchanged. Real selection/retention bias and history utility still need validation |
| M10.07 Complete local diagnosis, reviewed prioritization and history engineering | DONE | Bounded owner/consent/grant-safe current projections, versioned policy/independently reviewed assessments, cards/filter/trend UI, source/reanalysis/reviewer-withdrawal/bounds tests and checked main publication. [Contract](docs/architecture/player-model.md), [ADR-021](docs/adr/ADR-021-evidence-backed-player-diagnosis.md), [qualification](docs/experiment-results/m10-player-model.md); 687f0f2 all six CI jobs, 424 Python/40 Chromium/seven Docker. Real gameplay/product/hosting qualification excluded |

## M11 — Reviewed drills and measured practice

Owner: Tekken expert + product/analysis owner. Exit: one approved drill produces observable, attributable practice attempts.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M11.01 Version drill setup, valid response, alternatives and success criteria | PARTIAL | New immutable practice-workflow/1 payload pins native steps, response, alternatives, success criteria and conservative rules under existing source-pinned independent reviews; tested new-version publication. Actual expert-approved current-build setup/response and reproducibility remain required |
| M11.02 Assign the appropriate drill to an evidenced weakness | PARTIAL | Current server-recomputed M10 card/policy/evidence/scope/membership and drill hash pinned at UUID-idempotent assignment; stale/unqualified proof rejected. Legacy setup-only assignments remain separate. Genuinely reviewed real drill and player assignment utility still required |
| M11.03 Provide usable native training instructions without requiring a mod | PARTIAL | Reviewed-version-only native guide, setup/alternatives/capture/success criteria, evidence links and labeled mobile controls pass Edge tests; no invented setup for legacy versions. Real unaided player setup/completion/accessibility trial required |
| M11.04 Record sessions/attempts and separate self-report from verified outcomes | PARTIAL | Immutable measured session/source pins plus separate COMPLETED/INTERRUPTED/SKIPPED adherence reports; reports add zero verified exposure. Owner/CSRF/consent/retry/delete/export/account/restore tests pass. Real practice capture and G4 pending |
| M11.05 Count practice once with provenance and correct chronology | DONE | Reopened and corrected 2026-10-05: require frozen complete/current baseline, every row of current practice captures, exact metric/context/build/knowledge hash/detector/platform/scope, live source rights/retention, independent review and full source end inside frozen dates. UUID/played-key dedupe, stale/expired exposure abstention and retained original result-membership hashes pass locally; [M11 evidence](docs/experiment-results/m11-practice.md) |
| M11.06 Adapt progression/next action only using validated practice evidence | PARTIAL | Reviewed immutable rules gate current source/sample/session/coverage/agreement/uncertainty guidance; sufficient real trials remain G4/expert-gated. Adherence never qualifies exposure; no automatic difficulty change, frozen-date rewrite or causal claim. Real usability/effectiveness remains unvalidated |
| M11.07 Qualify the coherent local practice module | DONE | Reviewed workflow, current diagnosis-bound prescription, complete current exact-scope practice links, source-end chronology, conservative guidance, separate immutable reports, retry/owner/CSRF/consent/withdrawal/export/deletion/restore and usable mobile UI qualified. fd816af all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37346263824) pass: 447 Python, 43 Chromium, seven Docker, three Terraform mocks and native recovery. [Contract](docs/architecture/practice-workflow.md), [ADR-022](docs/adr/ADR-022-reviewed-practice-and-conservative-progression.md), [evidence](docs/experiment-results/m11-practice.md). Real release excluded |

## M12 — Trustworthy longitudinal evaluation

Owner: measurement/analysis owner. Exit: real baseline and later-match comparison can be reproduced without cherry-picking or incompatible measurements.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M12.01 Freeze baseline, metric, versions, windows and stop policy | DONE | Immutable EvaluationPlan and complete-selected-capture checks M11 requires current complete baseline scope/hash/platform and optional diagnosis membership before freezing; source-end practice dates cannot rewrite the spec.  M12 pins original schedule, exact source/decoder/platform/knowledge/review manifests and idempotent plan requests; legacy specification hashes stay unchanged. |
| M12.02 Freeze follow-up and practice memberships per result revision | DONE | Append-only results, hashes/lineage/invalidation; M07 synthetic reanalysis preserves old event knowledge hashes and frozen plans, withdrawal invalidates dependent results M08 snapshot revocation invalidates dependent results and preserves historical membership hashes. M11 stale/expired practice affects a new result revision, preserving original frozen memberships; unavailable links cannot silently qualify positive exposure.  M12 adds FOLLOWUP/RETENTION revisions, original practice/reference manifests and hashed private reproducible reports; current source/publication/collection changes revoke active use without rewriting result JSON. |
| M12.03 Enforce exposure, independent sessions, coverage and compatibility | PARTIAL | Local gates implemented; validate real play logs/sessionization and missing-source coverage M11 current complete exact-scope independently reviewed practice uses full source-end chronology; self-reports add zero exposure.  M12 includes all current recorded target events and conservatively blocks missing/expired/unattributed/unpublished/expected-session gaps; reports add zero exposure. Real sessionization and unsubmitted-match bias remain open.  Historical real plans lacking the new prospective source protocol cannot qualify; five targeted guard tests and exact 8f2f57b six-job CI passed. |
| M12.04 Return all six legitimate outcomes with uncertainty and next actions | DONE | Local statistical engine; observed improvement is not a causal assertion  M12 UI exposes frozen thresholds, unknowns/coverage/counts/uncertainty, next action, unavailable history and baseline-only adequacy; no causal or power assertion. |
| M12.05 Run prospective real baseline → practice → follow-up comparisons | BLOCKED | Consented cohort, approved measurement/drill and G5/G6 |
| M12.06 Compare source/decoder changes and verify retention of gains | PARTIAL | Local exact-source/pipeline policy, predeclared retention and auditable phased reports implemented; locally tested; actual source-change bias and retention observations remain NOT_RUN |
| M12.07 Validate statistical power/assumptions for broader claims | PARTIAL | Baseline-only session variance/planning diagnostics implemented; locally tested; actual independence/variance/power validation and broader study remain NOT_RUN. Five sessions/40 outcomes remain exploratory floors |
| M12.08 Qualify the coherent local comparison module | DONE | Owned scheduled follow-up/retention, complete current evidence/gap accounting, immutable revisions/source/decoder pins, safe reproducible reports, planning/uncertainty, retries/concurrency/withdrawal/export/restore/UI implemented. Final code 8f2f57b passed all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37355869813); [evidence](docs/experiment-results/m12-comparisons.md). Local engineering only; real effectiveness/power/hosted approval remain gated. Final tracking receipt publication pending reviewer usage limit |

## M13 — Complete player-facing product experience

Owner: frontend/product owner. Exit: supported players can complete the real workflow without operator-only shortcuts.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M13.01 Explain supported game/build/capture scope and onboard a real player | PARTIAL | Persisted scope acknowledgement, capture guide and next steps implemented; no implied consent/build approval. Real accounts, released scope and unaided onboarding validation remain The M13.09 visual entry retains explicit prototype/validation states; actual released scope and participant onboarding remain open. |
| M13.02 Find/confirm identity, show sync/coverage and browse source-aware history | PARTIAL | Local consent/selection/sync/coverage/error/expiry flow and match-to-evidence navigation implemented; approved real provider and real ambiguous-profile fixtures remain M04/M05 dependencies |
| M13.03 Review timestamped evidence and understand corrections/unknowns | PARTIAL | Paginated timeline, authenticated range playback, source provenance, disputed-event exclusion, complete-match selection and correction requests implemented; real media/player/reviewer usability and accessibility validation remain M06 adds resumable progress/recovery and controlled generation-pinned private playback; actual hosted/media/accessibility qualification remains. |
| M13.04 Present weakness, drill, measured practice and follow-up plan coherently | PARTIAL | Ordered journey, measured baseline summaries, frozen-plan details and practice gating implemented; synthetic browser path returns honest insufficient exposure. Real adherence and comparison usefulness remain unvalidated M11 reviewed native guide, separate adherence reports, current evidence counts, conservative next action and cancellation now implemented/tested locally.  M12 adds prospective retention planning, collection gap reports, source provenance and result/report history. M13.09 presents training before account tools with working path/match/capture entry links; measured outcomes and gates are unchanged. |
| M13.05 Search/filter supported matches and events | DONE | Current local supported scope: owner/player, UTC dates, character, situation/outcome, purpose/eligibility and history evidence state with typed pagination. Metadata-only records cannot satisfy gameplay filters; backend/browser checks pass |
| M13.06 Account/privacy controls, export, deletion and understandable support states | PARTIAL | M14 adds local signup/recovery, account-security UI, revocable sessions, consent receipts/withdrawal and mail cleanup to existing export/deletion/support flows. Hosted email/provider/backup/export operations and real-user acceptance remain M14–M16 dependencies M11 adds owned report export/deletion and diagnosis/report erasure without resurrecting deleted retries.  M12 private comparison download and session tombstone/account erasure are implemented; hosted qualification remains open. |
| M13.07 Keyboard, screen-reader, mobile, timezone and supported-browser validation | PARTIAL | Skip link/focus, labeled controls, mobile overflow, reduced motion and UTC/America-Toronto checks pass in local Edge and Linux Chromium CI; manual screen-reader, real-device, captions/visual-evidence accessibility and further browser qualification remain M11 labeled guide/session controls and 390px overflow/screenshot checks pass; actual screen-reader/real-player acceptance remains open.  M12 mobile source/hash view and failure/retry paths have local browser evidence; real usability/device qualification remains open. M13.09 local theme/entry checks add 320/390/768/1440px overflow and desktop/mobile previews; selected contrast pairs checked, not full accessibility acceptance. |
| M13.08 User feedback and notification preferences | DONE | Agreed local channel: in-app only. Durable-state analysis/practice/follow-up notices, persistent dismissal/category opt-out, idempotent feedback and operator queue implemented/tested; no external sends. Bounded feed is explicit in [contract](docs/architecture/player-experience.md) |
| M13.09 Original, coherent fighting-game visual system | DONE | Local acceptance met: original self-hosted art/fonts, graphite/ember tokens, responsive entry/training and player/operator controls; working navigation, readable unknown/prototype states, keyboard focus and reduced-motion support. Lint/types/build, 54 Edge plus final two entry checks, 320–1440px overflow and desktop/mobile visual review pass. [Qualification](docs/experiment-results/m13-visual-system.md), [design/provenance](docs/design/visual-system.md). Published source ec5e102 passed all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37385253136); final receipt retains latest-tip checks. Real-player/device/screen-reader acceptance remains M13.07, overall M13 PARTIAL |

## M14 — Accounts, consent and data ownership

Owner: backend/security/product owner. Exit: users control their account and permitted data in a hosted environment.

Local implementation and evidence: [account lifecycle](docs/architecture/accounts-consent.md),
[M14 qualification](docs/experiment-results/m14-accounts.md). Hosted exit is not yet satisfied.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M14.01 Secure sign-up/sign-in, session lifecycle and recovery | PARTIAL | Local verification/recovery, current-password changes, owned session inventory/revocation and logout-all implemented; expiring one-use challenges, CSRF, rate limits and concurrency checked. Production mail transport, abuse/registration-expiry policy, recovery review and hosted HTTPS qualification remain |
| M14.02 Separate player identity claims from authenticated application ownership | DONE | Owner-scoped claimed links and cross-owner tests; no ID-as-password behavior |
| M14.03 Version processing consent, optional training consent and withdrawals | PARTIAL | Version/digest receipts, legacy-unversioned backfill, independent optional training control and explicit withdrawal UI implemented. Withdrawal fences analysis/sync and clears upload admissions; re-grant restarts nothing. Legal policy approval, hosted audit/retention and any future real training eligibility enforcement remain M06 withdrawal also revokes/tombstones pending sessions for physical cleanup. |
| M14.04 Private data access, minimal opponent information and export | PARTIAL | Own export includes account/consent receipts and own M18 memberships, sessions, source pins and reviews. Assigned study media checks current consent/role/retention/chronology. Secrets/opponent/foreign account identities excluded; hosted access, portability and scale remain M06 own export adds allowlisted session IDs/state/offset/expiry and excludes capability URLs and expected checksums. M07 adds own proposals/reviews/reanalysis export and assigned-only grant-checked source playback; foreign review notes/identifiers excluded. M08 own exports add collection specifications and receipt metadata, excluding foreign whole-dataset labels. M11 allowlisted own report and assignment diagnosis/hash export excludes foreign reviewers and free-text private notes.  M12 owned session/protocol/phased-result export extends safe allowlists. |
| M14.05 Account deletion across media, metadata, caches, backups and providers | PARTIAL | Tombstone/purge covers account/provider/resource records; M18 consent/source/account deletion and expiry erase study labels, grants and dependent reports. Signed withdrawal/closure restores revoke stale study evidence before reads. Hosted provider/backup retention/current controls and retained-copy erasure remain unverified M06 pending uploads retain durable cleanup state/quota; native restore erases pending files and controls preserve unknown upstream deadlines. M07 erases private candidates/notes/source grants on account, processing consent and source withdrawal; restores permanently revoke managed grants before reads. M08 source/reviewer/definition/account/restore erasure covers private snapshots and derived active measurements; hosted/offline copies remain separate. M11 account deletion erases reports/diagnoses; every restore purges them and cancels stale assignments before reads.  M12 session tombstones prevent retry resurrection; account deletion erases receipts and invalidates all results. |
| M14.06 Review identity re-linking and per-match suppression retention | PARTIAL | D025 implements explicit local re-link confirmation with owner-keyed HMAC suppression of known deleted source IDs. Identity-wide revocation remains the initial deletion stop. Production retention, stable key rotation and unknown cross-provider aliases still need review; local work no longer blocked M07 erases private candidates/notes/source grants on account, processing consent and source withdrawal; restores permanently revoke managed grants before reads. |

## M15 — Security, privacy and reliability hardening

Owner: security/backend owner. Exit: the externally exposed workload has tested containment, authorization and recovery behavior.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M15.01 Tenant isolation and nested ownership checks | PARTIAL | 2026-09-29: worker/asset ownership, recording relations and owner-only operator publication hardened; local regression passes. Hosted object/download boundaries and independent adversarial review remain M06 adds owner/nested-asset upload access, CSRF and real PostgreSQL admission/chunk/verification cancellation races. M08 adds owned collection/receipt and exact-owned-source import boundaries with a PostgreSQL foreign-reviewer withdrawal race. M11 guidance/report/link/cancel endpoints enforce owner, consent, CSRF and withdrawal locks; concurrent retry/delete checked.  M12 endpoints preserve private no-store/session-CSRF/owner/capacity/plan serialization and bounded histories. |
| M15.02 Isolate hostile media and bound maximum-profile CPU/RAM/scratch/time | PARTIAL | Docker runtime blocker resolved: pinned offline parser tested with actual memory/PID/scratch limits, cancellation/lifetime handler, malformed and exact 600s/512MiB fixtures. [Receipt](docs/experiment-results/m15-security.md). High-complexity/exploit corpus, independent review and hosted kill deadline remain |
| M15.03 Harden provider fetches against SSRF, oversized payloads and schema drift | PARTIAL | Offline reviewed-target/public-DNS and bounded strict-JSON guards tested; redirects/compression rejected. No network adapter enabled. Actual permitted transport, pinned connections, deadlines and authenticated schema validation remain gated by M04/M05 |
| M15.04 Secrets, least privilege, dependency maintenance and security logging | PARTIAL | Local least-privilege/logging/budget controls and DRF patch implemented. M14 publication audit found Next.js GHSA-vcvr-r3jv-pc5j; patch 16.3.6 passed local and remote audits/build/browser checks. 2026-10-02 owner-requested single-branch policy disables automatic version PRs; dependency audits unchanged, weekly patches reviewed/tested directly on main. Repository-access/exposure review, production secret store/IAM/rotation/log retention and OS image scan remain 2026-10-03: both Python locks and production npm audit pass; streaming hash dependency pinned. Full npm dev audit has five high findings through unpatched braces GHSA-vfj7-8cjw-p6xm in trusted lint globs; upstream patch remains tracked in the security runbook, with no suppression or force downgrade. |
| M15.05 Abuse/rate limits, admission quotas and cancellation under load | PARTIAL | Durable login/API budgets, early upload reservations, storage/queue/daily/active-worker caps, body limits and PostgreSQL capacity races tested. Hosted ingress/spooling/filesystem limits and distributed load qualification remain M06 shared upload slots and physical byte reservations remain through failed cleanup; bounded chunks and resumed offsets checked. |
| M15.06 Test provider outages, duplicate deliveries, stale workers and partial failure | PARTIAL | M16 controlled-client ambiguous launch/delivery/outage/storage, retained capacity, cancellation and signed recovery tests remain. M17 adds nine-owner/32-job saturation, eight-retry dispatch outage, atomic quotas, midnight/unknown settlement, permission revocation and measurement deletion checks. Real permitted transport and hosted failures remain untested M06 adds bounded verification crash/transport retries, malformed object metadata/range rejection and cancellation/restore failure cases. M07 covers review/source publication races, streamed revocation and worker-versus-foreign-reviewer lock ordering; actual hosting remains separate. M11 source expiry/reanalysis abstention, immutable practice pins and private report/diagnosis restore erasure verified locally.  M12 receipt erasure and comparison invalidation run before restored reads. |
| M15.07 Security/privacy review, incident response and vulnerability process | PARTIAL | [Threat model](docs/architecture/security.md), [incident runbook](docs/operations/security-runbook.md), SECURITY.md and automated local incident/failure rehearsal delivered. Named operator/deputy acceptance, private reporting channel and independent security/privacy review remain |

## M16 — Hosted asynchronous delivery and deployment

Owner: infrastructure/backend owner. Exit: approved workload operates in a private, recoverable hosted environment.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M16.01 Choose/provision region, cloud account and environments | PARTIAL | User confirmed Google Cloud; environment/project/namespace separation and approval-gated Terraform prepared. Region, account, cost/privacy decision, billing alerts and authorized provisioning remain |
| M16.02 Deploy web/API, managed PostgreSQL and private object storage | PARTIAL | Unprivileged WSGI/Next standalone images, readiness/quarantine, private SQL/GCS/Tasks/IAM/secret-version templates and bounded generation-pinned GCS adapter implemented. Linux builds/unprivileged quarantine and standalone startup passed remotely. Hosted runtime/TLS/routing, SQL/secrets, durable journal, playback/uploads and live storage acceptance remain; see [M16 evidence](docs/experiment-results/m16-delivery.md) M06 upload/playback GCS contracts now exist under GCS_STORAGE_QUALIFIED=False; actual IAM/CORS/erasure acceptance still required. M13.09 standalone public-asset packaging and actual CI HTTP byte comparisons passed on source ec5e102; hosted acceptance remains separate. |
| M16.03 Implement durable dispatch/outbox/reconciler and bounded background execution | PARTIAL | Atomic producer outbox, deterministic Tasks, bounded retry, one worker entry, retained per-owner/global physical slots and official Google control contracts tested locally. Ambiguous launches never blindly retry. Cloud Run cannot host the qualified nested Docker sandbox; equivalent isolation/runtime and live reconciliation remain gates |
| M16.04 Add worker heartbeats/progress, cancellation and stale-execution recovery | PARTIAL | 30s heartbeats bounded by 420s deadline, coarse progress API, fence/consent/cancellation guards and stop-confirmed stale recovery implemented. Unconfirmed cleanup retains capacity. Hosted total deadline, OIDC/operation fixtures and cancellation/publication fault qualification remain |
| M16.05 Rehearse backup, restore, migration and rollback | PARTIAL | Native synthetic PostgreSQL dump/restore/round-trip through 0015, signed pilot withdrawal and erasure/repeated replay before reads passed. Reverse guards protect study history/retention/allocation plus existing slots/budgets/dates. Production RPO/RTO/current controls, runtime shutdown/failover and retained-copy erasure remain 2026-10-03 native rehearsal extends forward/reverse/forward through 0016 and verifies pending-upload erasure/repeated replay; reverse guard requires physical purge. Native local rehearsal now round-trips through 0018 and erases private dataset receipts/partitions on restore; production remains unqualified. 2026-10-05 native rehearsal round-trips through guarded 0019 and verifies report/diagnosis erasure and cancelled assignments; hosted RPO/RTO remains unmeasured.  Native rehearsal now asserts migration 0020 rollback/forward and restored comparison receipt erasure/result invalidation. |
| M16.06 Deploy with approved release flags and real-data decisions | PARTIAL | Provisioning precondition/private ingress/quarantine and code-level managed-media gate implemented; external upload/live-provider/recognition gates preserved. No release deployed; applicable scientific/security/privacy/provider decisions and staging evidence still required |

## M17 — Operations, performance and unit economics

Owner: operations/product owner. Exit: actual workload reliability and total cost are measured and controlled.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M17.01 Instrument run latency, CPU/RAM, bytes, failures, retries and review time | PARTIAL | Fenced AttemptMetric, fixed-label HTTP buckets, failures/retries/missing coverage and scoped idempotent review/support time implemented. Export/deletion/retention and unknown historical dates protected. Real network/provider/storage/reviewer observations and hosted calibration remain; [contract](docs/architecture/operations-economics.md) |
| M17.02 Set supported-workload latency, completion and availability objectives | DECISION | Proposed p95 queue ≤120s/processing ≤390s, technical completion ≥95%, observed API response availability ≥99%; sample/truncation guards and dashboard implemented. Owner/workload/window/error-budget approval and representative external uptime evidence required before beta; within proposal is not approval |
| M17.03 Load-test realistic history, uploads, jobs and concurrent owners | PARTIAL | Synthetic 2,250-match/nine-owner indexed pages, 32-job/two-slot saturation, eight-retry controlled dispatch outage and cancellation passed locally/CI; actual 600s/512MiB fixture passed in separate Docker job. Representative content, simultaneous hosted max uploads, DB saturation/network/live-provider outage qualification remain; [evidence](docs/experiment-results/m17-operations.md) |
| M17.04 Measure costs per capture, analysis, completed loop and comparable evaluation | PARTIAL | Exact-window scoped four-component cost observations and null-safe allocated unit costs implemented; failed analyses/current nonpositive evaluation revisions count, zero denominators/missing inputs remain null. Actual invoices/rates/reviewer/support measurements and production reconciliation remain blocked by missing real observations |
| M17.05 Enforce storage/minutes/reanalysis/job budgets and hard admission caps | PARTIAL | Local atomic reserve/settle ledger holds through stop/midnight, snapshotted deadlines/three attempts, missing-attempt full charge, initial plus two daily reanalyses, upload preview and optional-work pause implemented with concurrent PostgreSQL tests. Existing storage/pending/physical/request caps retained. Hosted quota accounting/post-backup currentness/ingress and total-spend controls remain unqualified |
| M17.06 Monitoring, redacted logs, alerts, support runbooks and patch response | PARTIAL | Staff-only responsive dashboard, redacted API/CLI snapshots/nonzero alert status, fixed-code framework/worker logs, retention and [operations runbook](docs/operations/operations-runbook.md) implemented; synthetic outage/stop/recovery rehearsed. Named primary/deputy, external scheduler/missing-heartbeat/paging, real response, hosted redaction/retention and independent patch review remain |
| M17.07 Validate willingness to pay and recurring unit economics | BLOCKED | [Actual-offer/economics protocol](docs/operations/economics-protocol.md) prepared; no price, participant, payment, renewal, invoice or approval invented. Approved actual offer and real repeat use required; evaluate existing pilot median/p90 COGS targets using observed recurring cost/net revenue |

## M18 — Prospective real-player pilot

Owner: product/measurement owner + expert/reviewers. Exit: all G1–G6 have real results and an explicit continue, narrow or stop decision.

| Requirement | Status | Remaining acceptance |
|---|---|---|
| M18.01 Recruit permitted cohort, record consent and assign reviewers/expert | PARTIAL | [Local tools](docs/architecture/pilot-tools.md) implement self-consent/pseudonyms, signed invitations, separate roles and prospective allocation; real intake disabled pending rights/protocol/adult-retention review and an actual cohort/expert |
| M18.02 Run observability and reviewed-practice studies | BLOCKED | G1/G4 evidence packs, independent labels/adjudication, unknown denominators and review time implemented locally; actual 20 captures/10-player trials and expert approval absent |
| M18.03 Run held-out recognition and unaided-capture studies | BLOCKED | Local G2/G3 harness reports per-outcome exact bounds, frozen predictions, held-out labels and missing/setup data; actual detector/representative negatives/unaided participants remain absent |
| M18.04 Run natural-frequency and prospective complete-loop study | BLOCKED | Local original chronology/phase logs, missing/zero sessions, known exposure, duration coverage and source-linked canonical evaluation packs implemented; real four-week histories and complete reviewed loop absent |
| M18.05 Compare against native replay/training and usual practice | PARTIAL | Prospective allocation, native/usual/structured usefulness/time observations and conservative G6 candidate comparison implemented. Utility/group proposal needs real protocol approval; actual adherence/usability/comparator data absent |
| M18.06 Record decisions and revise scope from negative evidence | PARTIAL | Current revision-scoped independent expert WAIT/CONTINUE/NARROW/STOP decisions implemented, with sparse/stale guards and no release promotion. Real expert decisions/evidence and any scope revision remain unrun |
| M18.07 Deliver local pilot-management software | DONE | Role/consent/source/blinding/frozen-report/annotation/canonical-link, erasure/restore and responsive UI locally qualified. Pushed `135464f`/clean reconciliation `2bbb645`; all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37041450168) passed first attempt: 306 Python, 21 Chromium, seven Docker, recovery and static/build/audits. [Evidence](docs/experiment-results/m18-pilot-tools.md); local synthetic software scope only |

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
| M19.02 Execute remote CI and staging end-to-end tests | PARTIAL | Latest UI source ec5e102 passed all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37385253136) first attempt 2026-10-05: 519 PostgreSQL, 54 Chromium, seven actual Docker/max-profile, three Terraform, audits/static/build/unprivileged startup including real HTTP hero/icon byte comparisons, and native guarded recovery. Final documentation receipt retains ordinary latest-tip checks. Actual staging, hosted erasure, real participant paths and permitted real data remain untested; mocked browser/software checks do not complete staging acceptance |
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

M06/M07/M08/M10/M11 local modules are qualified for their stated scopes and their
published source commits passed all six CI jobs. M12's coherent local comparison module is
qualified on published 8f2f57b with all six CI jobs: scheduled retention, complete current
collections, source/decoder pins, owned gap receipts, safe reports and planning diagnostics.
Real M12.05-M12.07 and G5/G6 remain unrun; tracker qualification cannot approve effectiveness.
M12 final artifact receipts were recovered and published with M09 source. M09's coherent
local recognition engineering module is qualified on 621a161 with all six CI jobs: immutable
versions/artifacts, explicit UNKNOWN, all-source retrospective benchmarks, independent reviews,
replacement/rollback/drift stop, manual fallback and revocable owner reproduction. The final
tracking receipt preserves ordinary CI and actual latest-tip monitoring. No real detector is
released by this software qualification.
Current owner priority: original M13.09 visual system is locally and source-CI qualified on
ec5e102 with all six [jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37385253136) successful first attempt.
Publish the final normal-CI qualification receipt and verify its actual latest tip before
returning to real capture work. Then resume permitted exact-build footage/facts and qualified
independent reviewers for M07/M08 observability and G1/G2; predeclare true unseen evaluation
before label access. Actual Tekken recognition still requires reviewed observations/calibration and expert
reference timing. Hosting/provider access remains a separate decision and qualification.
M08.08 now prepares the official-client recording procedure and derived G1 assessment. User
confirmed no capture paths/reviewers and requested public/game discovery; 2026-10-05 research
found an installed game but zero qualifying public or local captures. Obtain purpose-consented
recordings and independent exact-build review using the qualified preparation tools.
Local M08.08 software and exact source e674342 are qualified with all six
[CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37380495040) successful
on the first attempt. Its final 20f74cc receipt was also verified on the actual latest tip.
The M13.09 UI delivery must independently follow the same normal-CI/latest-tip policy.
No game automation, YouTube downloader, private endpoint, real-intake or detector release added.
Then use the reviewed knowledge/dataset workflow to acquire permitted exact-build facts,
representative captures and qualified independent labels before releasing M09 recognition or real M10 diagnosis/priorities. Hosting/provider gates below
remain separate. Maintain weekly reviewed dependency patches and the tracked development
lint advisory. No purchase, external contact or activation is implied.

| Priority | Next concrete outcome | Requirements | Needed input / owner |
|---|---|---|---|
| 1 | Prepare activation of one documented public provider | M04.01–M04.03, M05.01–M05.04 | Product owner obtains applicable usage evidence and privately configures a key; integration owner verifies permitted fixtures; never paste secrets into this tracker |
| 2 | Acquire first consented captures and expert review | M07.02–M07.05, M08.02–M08.03 | Participants, exact-build evidence, Tekken expert, two reviewers and adjudicator |
| 3 | Validate observability/practice before promoting recognition | M09, M11, G1/G4 then G2 | Dataset/review findings; select backup/narrow if required |
| 4 | Qualify M16 hosting and account/security release boundaries | M13.01–M13.04/M13.06–M13.07, M14.01/M14.03–M14.06, M15.01–M15.07, M16 | Google Cloud confirmed; local M16 outbox/recovery and mocked adapters/templates delivered. Select region/budget/recovery objectives; review equivalent media isolation and independent durable controls, then authorize staging provisioning. Hosted routing/email/IAM/storage and source-integrity/privacy/security reviews remain; tracker alone authorizes no resources |
| 5 | Qualify M17 operations and actual economics | M17.01–M17.07 | Local ledger/telemetry/dashboard/load module implemented. Approve supported workload/objectives and named response; measure real hosting/reviewer/support amounts, qualify alert delivery and current quota recovery, then run an approved actual offer with payment/repeat-use evidence |
| 6 | Activate a reviewed real pilot using M18 tools, then qualify hosting/beta | M08, M12, M16–M19 | Local tooling implemented; approve rights/adult retention/sampling/comparator protocol, enroll permitted cohort and independent reviewers/expert, then collect real G1–G6 evidence |

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
| 2026-09-29 | M15.01–M15.07, M19.02 | Delivered local security/reliability module, unblocked real Docker qualification, patched DRF advisories; external review/deployment/provider gates retained | 209 PostgreSQL/Python tests; seven Docker checks including 600s/512MiB fixture; migration 0007; static/schema and dependency checks |
| 2026-10-01 | M14.01–M14.06, M13.06, M19.02 | Delivered local account/consent module; M14.06 BLOCKED → PARTIAL with explicit re-linking and known-match suppression. M15 remote CI now fully passed; M14 not pushed | 232 PostgreSQL/Python and 14 Edge tests; migration 0008; build/static/schema checks; [M14 evidence](docs/experiment-results/m14-accounts.md) |
| 2026-10-02 | M14.01–M14.06, M15.04, M19.02 | Verified M14 main publication and Next.js security follow-up; corrected CI fully passed after runner retry | Remote 232 PostgreSQL/Python, 14 Chromium and seven Docker tests; both dependency audits, build/static/schema checks; [CI receipt](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/36893320865) |
| 2026-10-02 | M16.01–M16.06, M14.05, M15.06, M19.02 | Implemented and published M16 dispatch/recovery/cloud preparation; retained hosted acceptance gates | [M16 evidence](docs/experiment-results/m16-delivery.md): all six [remote CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37023337650) passed; 255 Python, 14 Chromium and seven Docker tests, native recovery, mocked Terraform and application-container startup |
| 2026-10-02 | M17.01–M17.07, M14.05, M15.06, M16.05, M19.02 | Implemented and published available M17 engineering as one module, including safe unknown-history migration; retained actual workload/cost/payment and deployment gates | [M17 evidence](docs/experiment-results/m17-operations.md): all six [remote CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37031233040) passed first attempt; 282 Python, 17 Chromium, seven Docker and three Terraform tests, native recovery, audits and container startup |
| 2026-10-02 | M18.01–M18.07, M08.01/.03/.04/.06, M14.04/.05, M16.05, M19.02 | Delivered coherent local pilot tools, safe source-history reconciliation and progress records; kept real intake/studies and release approval separate | [M18 evidence](docs/experiment-results/m18-pilot-tools.md): all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37041450168) passed first attempt; 306 Python, 21 Chromium, seven Docker, three Terraform, native recovery, audits and startup |
| 2026-10-02 | M01.05/M01.06, M15.04, M19.02 | Removed 15 verified Dependabot proposals/branches, prepared main-only/no-skip publication policy and disabled four version-PR streams without merging upgrades or changing audit gates | GitHub verifies one unchanged main branch and zero open PRs; automatic security PRs already off. Dependabot YAML parsed with existing js-yaml; diff check passed. Publication/latest-tip CI pending |
| 2026-10-02 | M01.05/M01.06, M15.04, M19.02 | Published/qualified main-only delivery and pruned 16 stale local tracking refs; M01.06 and M01 DONE for ongoing delivery policy; retained ordinary CI on progress receipts | `c7d60ee` and all six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37045159974) passed first attempt at 18:10:02 UTC; GitHub configuration validator also passed. API verifies sole main at that head and security PRs off; prior application qualification remains separately dated |

| 2026-10-03 | M06.01-M06.08, M13.03, M14.03-.05, M15.01/.04-.06, M16.02/.05, M19.02 | Delivered coherent local/controlled resumable storage engineering, private playback and conservative restore erasure; migration 0016, ADR-018/D030, M06.08 DONE; release M06 PARTIAL | Local backend/browser/static/audit/native recovery evidence in M06 receipt; 340 Python/25 Chromium/seven Docker and all six CI jobs passed for 0588ce4; final follow-up has 35 local upload passes and ordinary latest-tip CI |

| 2026-10-03 | M06.02/.06/.08, M01.05/.06, M15.01/.04/.06, M19.02 | Qualified M06 main implementation and added current-state recheck after status-probe revocation; preserved independent gates and ordinary checked receipt | 0588ce4 all six CI jobs first attempt, downloaded JUnit; 35 focused local upload tests for final privacy fix; no live GCS |

| 2026-10-03 | M01.05/.06, M06.08, M19.02 | Verified final M06 revocation fix on main; recorded exact-head remote results and retained normal CI on this documentation receipt | 1d56929 all six jobs first attempt at 16:07:03 UTC; 341 Python/25 Chromium/seven Docker plus recovery/audits/build/static/startup and three Terraform mocks |

| 2026-10-03 | M07.02-M07.07, M06.02/.03, M11.01, M12.02, M14.04-M14.06, M15.06, M01.05/.06, M19.02 | Delivered coherent M07 local governance, scoped publication/lifecycle, reviewed patch reanalysis, active-view withdrawal and owner/capacity/domain/FK-safe concurrency; architecture 2.11.0 and migration 0017; M07.07 DONE, real M07 remains gated | 371 PostgreSQL/Python, 30 Edge, production build/static/schema/loader/audits and native guarded migration/dump/restore pass; exact main publication/CI pending; [M07 evidence](docs/experiment-results/m07-knowledge.md) |

| 2026-10-03 | M01.05/.06, M07.07, M15.06, M19.02 | Published and qualified M07 directly on main; recorded exact code-head CI/JUnit and ordinary final receipt | dcda2bd all six jobs first attempt at 17:53:53 UTC; 371 Python/30 Chromium/seven Docker, three Terraform mocks, native recovery, audits/static/build/schema/startup; final receipt keeps normal latest-tip CI |

| 2026-10-05 | M08.01-M08.07, M07.05, M09.04, M12.02, M14.04/.05, M15.01/.06, M16.05, M18.07, M01.05/.06, M19.02 | Delivered M08 local collection/version/split/snapshot/QA/canonical import/erasure module; ADR-020/D032 and guarded migration 0018. Real M08 remains partial/blocked | 394 PostgreSQL/Python, 35 Edge, static/build/schema/links/audits and native guarded migration/dump/restore/erasure passed; latest main publication/CI pending |

| 2026-10-05 | M01.05/.06, M08.07, M15.06, M19.02 | Verified M08 direct-main publication and complete first-attempt CI; recorded exact-head evidence and ordinary final receipt | d83f342 all six [jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37329783254) at 15:10:08 UTC: 394 Python/35 Chromium/seven Docker, three Terraform mocks, native recovery/erasure, audits/static/schema/build/startup; final receipt requires its own latest-tip checks |

| 2026-10-05 | M10.01-M10.07, M07.05, M13.05/.07, M14.04/.05, M15.01/.06, M01.05/.06, M19.02 | Implemented coherent local M10 projection/policy/governed assessments/cards/history module, ADR-021/D033 and architecture 2.13.0; no new cache/migration or real diagnosis release | Initial 61 targeted PostgreSQL, frontend lint/build/typecheck pass; complete regression/browser/static/schema/link and latest-main publication checks pending |

| 2026-10-05 | M01.05/.06, M10.07, M15.06, M19.02 | Verified coherent M10 direct-main publication and all six first-attempt CI jobs; local M10.07 DONE, real M10 remains PARTIAL; final receipt retains ordinary CI/latest-tip verification | 687f0f2 [run](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37338207922) completed 16:10:57 UTC: 424 Python/40 Chromium/seven Docker, three Terraform mocks, native recovery/erasure, audits/static/schema/build/startup; downloaded JUnit/logs substantiate actual scopes |

| 2026-10-05 | M11.01-M11.07, M07.05, M10.02, M12.01-M12.03, M13.04/.06/.07, M14.04/.05, M15.01/.06, M16.05, M01.05/.06 and M19.02 | Implemented coherent local reviewed practice module and fixed partial/stale/scope/source-end exposure gaps (M11.05 reopened then locally qualified); architecture 2.14.0, ADR-022/D034 and guarded migration 0019. Real M11 remains PARTIAL; published CI pending | 446 Python/seven separate Docker skips; final 114 focused PostgreSQL, 43 Edge, production build/lint/typecheck/static/schema, native migration/dump/restore/report/diagnosis erasure; [evidence](docs/experiment-results/m11-practice.md) |

| 2026-10-05 | M11.01-M11.07, M01.05/.06 and M19.02 | Published M11 fd816af directly on main with normal CI; coherent local engineering M11.07 DONE, real M11 remains PARTIAL. Final progress receipt retains normal CI/latest-tip verification | All six jobs pass first attempt; 447 PostgreSQL/Python, 43 Chromium, seven real Docker/max-profile, three Terraform mocks, native guarded migration/restore/report/diagnosis erasure, clean production audits/static/schema/build and unprivileged startup; [run](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37346263824) |

| 2026-10-05 | M12.01-M12.08, M13.04/.06/.07, M14.04/.05, M15.01/.06, M16.05, M01.05/.06 and M19.02 | Coherent local comparison module implemented; architecture 2.15.0, ADR-023/D035 and guarded migration 0020; real M12/G5/G6 remain gated | 50 final affected PostgreSQL, 47 Edge (four final M12), production build/static/schema/loader/docs and native migration/dump/restore/erasure pass. Initial full run 468 passes/one relocated mock-hook failure/seven separate Docker skips; fixed and race rechecked. Exact publication CI pending; [evidence](docs/experiment-results/m12-comparisons.md) |

| 2026-10-05 | M12.03/.06/.08, M01.05/.06 and M19.02 | 65bbc2d source publication passed all six jobs; added historical-real protocol guard, preserving synthetic legacy workflows | Source CI 469 PostgreSQL/47 Chromium/seven Docker/three Terraform and native restore/audits/static/container pass; five final targeted guard/legacy PostgreSQL pass in 19.43s. Guard/latest-tip CI pending |

| 2026-10-05 | M12.03/.06/.08, M01.05/.06 and M19.02 | Final code 8f2f57b passed all six jobs first attempt; M12.08 DONE for local engineering, overall real M12 PARTIAL. Final receipt saved locally; publication pending automatic-review usage limit | Guard CI job states and watcher exit 0 verify success; guard artifact counts not downloaded. Earlier 65bbc2d artifacts retain 469 PostgreSQL/47 Chromium/seven Docker/three Terraform scope; five final targeted local guard tests. Next recommended M09 engineering; real G5/G6 remain NOT_RUN |

| 2026-10-05 | M09.01-M09.08, M08.05/.06, M14.04/.05, M15.01/.06, M16.05, M18.07, M01.02/.05/.06, M19.02 | Implemented coherent local recognition candidates/version/review/benchmark/rollback/drift/privacy module; ADR-024/D036, architecture 2.16.0, guarded migration 0021. Real recognition remains gated | Corrected initial target suite 26 PostgreSQL passes; full suite/UI/native recovery/publication/CI pending; no real G1/G2 approval |

| 2026-10-05 | M09.01-.08, M15.01, M16.05 and M01.05/.06 | Local module qualified: 498 full PostgreSQL + one separate actual OpenCV template bridge, 51 Edge and guarded native 0021 migration/dump/restore/erasure; local dev schema applied | Final static226/mypy29/build/lint/types/schema/docs pass; main publication/exact-tip CI pending, seven actual Docker cases reserved for CI; real G1/G2 remain NOT_RUN |

| 2026-10-05 | M09.01-.08, M01.05/.06, M19.02 | Published source 621a16142a26105233c3c7d925faf43762cc5467 directly on main with ordinary CI, including recovered M12 receipt | Exact six-job source CI and final receipt/latest-tip checks pending; local 498+1 PostgreSQL/51 Edge/native 0021 checks retain dated scopes |

| 2026-10-05 | M09.01-.08, M15.01/.06, M19.02 | Source 621a161 first CI attempt passed five jobs; only media cancelled before runner/steps, same-source job retry requested | Downloaded 499 PostgreSQL/7 separate Docker skips (302.185s), 51 Chromium (49.5s), three Terraform; overall run not green and no actual Docker result yet. GitHub runner-assignment incident reported |

| 2026-10-05 | M09.01-.08, M08.05/.06, M14.04/.05, M15.01/.06, M16.05, M18.07, M01.02/.05/.06, M19.02 | Source 621a161 all six jobs verified on attempt 2; M09.08 DONE for local engineering, overall real M09 PARTIAL. Final ordinary-CI qualification receipt prepared | Actual 499 PostgreSQL/51 Chromium/seven Docker/three Terraform and native 0021 recovery; media-only retry followed hosted-runner cancellation with no steps. Real observation calibration/G1/G2 remain NOT_RUN |

| 2026-10-05 | M13.01/.04/.07/.09, M16.02, M19.02, M01.05/.06 | Delivered original MetaPunish-inspired DojoPulse visual system and self-hosted assets; all gates unchanged, M13.09 DONE for local engineering, overall M13 PARTIAL | Lint/types/build, 54 Edge (57.9s), final two entry rechecks (7.7s), desktop/mobile/operator previews and static contrast pairs. Source CI/publication pending; [UI receipt](docs/experiment-results/m13-visual-system.md) |

| 2026-10-05 | M13.09, M16.02, M19.02, M01.05/.06 | Published UI source ec5e102 directly to main with enabled CI after fresh remote-head review; only main exists | 133 local links, parsed CI YAML/six-job asset checks and packaging assertions pass. Python PyYAML unavailable; installed js-yaml used. Actual exact-source CI pending |

| 2026-10-05 | M13.01/.04/.07/.09, M16.02, M19.02, M01.05/.06 | Source ec5e102 all six CI jobs verified first attempt; final ordinary-CI qualification receipt prepared. M13.09 DONE locally, overall M13 PARTIAL | 519 PostgreSQL/54 Chromium/seven actual Docker/three Terraform plus audits/static/build/native recovery and actual standalone asset byte checks; downloaded XML/logs verified. Final receipt/latest-tip monitoring required |
