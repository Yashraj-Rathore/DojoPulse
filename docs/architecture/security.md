# Security, privacy and reliability boundary

Version 1, 2026-09-29. Applies to M15.01–M15.07 and architecture 2.5.0.
This is an implemented local engineering boundary, not approval to expose the service.

## Assets and trust boundaries

Private video, opponent/player identifiers, account credentials, processing consent,
review evidence and immutable evaluation lineage are sensitive. A signed-in account,
a provider response and a media decoder are separate trust domains. Staff status does
not grant another account's evidence. Direct database administration, the local machine
and the Docker coordinator remain privileged operator surfaces.

| Threat / entry point | Implemented control | Remaining release evidence |
|---|---|---|
| Cross-account IDs or inconsistent nested relations | Owner-scoped APIs; owner-first write locks; run/asset ownership at claim and completion; recording review/reprocess checks; annotation publication restricted to the operator's own workspace | Hosted private object access, independent adversarial review; coach/delegated reviewer roles need explicit grants |
| Credential guessing / request amplification | PostgreSQL atomic fixed-window login and per-account API budgets; JSON-only API responses; bounded JSON/form bodies; private/no-store responses | Trusted proxy configuration, edge connection limits, distributed abuse signals and legitimate shared-IP testing |
| Media exploit, fork/memory/disk exhaustion | Immutable image ID, UID 10001, no network, read-only root and two input files, no capabilities, no privilege escalation, default Docker seccomp, no credentials/socket, 64 PIDs, 1 CPU, 1 GiB including tmpfs, no swap, 512 MiB work and 64 MiB temp | Actual deployment kernel qualification, hostile corpus/fuzzing, high-complexity media, independent sandbox review |
| Decoder output forges coaching | Only FAILED/REVIEW_REQUIRED accepted; no opportunities or automatic validation; bounded JSON, shaped facts, redacted error codes; coordinator hashes original bytes independently | Human review and all real-game measurement gates remain mandatory |
| Queue/storage amplification | Owner/global queue and storage budgets, daily analysis budget, early upload reservations and absolute expiry, aggregate streaming byte cap, owner/global active-job cap | Ingress deadlines and filesystem quotas must bound request spooling and interrupted uploads before external access |
| Deleted/cancelled worker publishes late | Poll lease/fence during subprocess execution; kill descendants and remove the exact parser container; final owner lock/fence checks and hash publication in one transaction | Hosted dispatcher/storage fault injection, job reconciler and restore suppression |
| Provider SSRF, zip bomb, ambiguous payload | Offline reviewed-origin/path/DNS checks; disabled operations fail closed; redirects/compression rejected; streamed byte cap, UTF-8/unique keys/finite numbers/depth/node checks | No transport is enabled. A permitted adapter must pin approved public DNS addresses to TLS connections, disable ambient proxies/redirects, validate query/schema, enforce connect/read/total deadlines and credential redaction |
| Secret or evidence leakage through logs | Fixed security event/reason codes; no user, IP, URL, request body, credentials or private path in security log records; keyed request-budget digests expire | Managed secrets, restricted/retained production log sinks, key rotation and incident alerting |

## Local execution contract

`PARSER_BACKEND=docker` is the default. `PARSER_IMAGE` must be a locally available
`sha256:` image ID; the worker never pulls an image when processing media. Missing
configuration/runtime fails closed. No host output directory is mounted: samples are
ephemeral and only a bounded report returns. The original private video remains the
review/playback source. Standalone annotation/extraction CLIs are trusted local tools.

The parser has an explicit SIGALRM handler at PID 1 (300 seconds); the coordinator
waits at most 330 seconds and attempts exact-container cleanup for at most 15 seconds.
The in-container alarm is crash cleanup for trusted parser code, not a security boundary
against compromised code that disables its own handler. Production needs an independent
orchestrator kill deadline and host/container reconciliation. Docker access itself is
privileged: never expose the daemon or mount its socket into the API/parser.

An explicit `PARSER_BACKEND=local` escape hatch requires DEBUG and LOCAL_OPERATOR_UPLOADS,
and is solely for trusted development fixtures. It retains host-side extraction artifacts;
the ordinary database worker/report interface remains the same. External uploads stay disabled.

All capacity transactions acquire owner then global capacity locks; no code holding
the capacity lock may acquire another owner lock. Storage includes assets awaiting physical
purge. Uploads reserve a full 512 MiB before multipart parsing, one per owner and four globally,
for 15 minutes. Commit validates the reservation and actual bytes again. Logical source quotas
are 2 GiB/owner and 16 GiB/global. Multipart temporary and destination copies can coexist;
these are not physical disk quotas. Expired/stalled requests may retain temporary files until
the web server terminates them. Run `security_maintenance` hourly. Dedicated ingress/temp
quotas and process timeouts are mandatory for deployment.

M06 resumable sessions reserve declared bytes before transfer for one hour and share
the four global/one owner upload slots with multipart requests. LOCAL chunks are
bounded to 8 MiB with exact offsets; cancelled/failed sessions retain quota until
physical purge. Background integrity verification has fenced leases, deadlines and
bounded retries. GCS bearer session URIs are owner-scoped and excluded from logs,
exports, browser storage and signed recovery controls. Upstream-expiry metadata
prevents false erasure acknowledgements after a lost capability. See
[evidence storage](evidence-storage.md); actual GCS/ingress isolation remains gated.

Analysis admission allows four pending/processing jobs per owner, 32 globally, 20 new runs
per owner per rolling day; execution allows one active per owner, two globally. Synthetic
match-sync admission uses four/32 outstanding limits. Existing idempotent requests do not
create another run. Retries retain the three-attempt analysis/five-attempt sync budgets and
fencing. API budgets are 300 reads and 60 writes/account/minute; login allows ten attempts
per direct socket address/minute. Forwarded IP headers are deliberately not trusted.
Fixed windows allow a boundary burst; these are local controls, not a distributed perimeter.

## Dependencies and maintenance

The parser uses a smaller runtime-only lockfile and a pinned Python base digest. Keep
`requirements-analysis.lock` pins aligned with `requirements.lock`; rebuild, audit and
rerun sandbox qualification after updates. OS/FFmpeg packages are installed from Debian
repositories at build time, so the resulting image ID, OS package inventory and scanner
receipt must accompany a release. A pinned base does not establish vulnerability freedom.
Dependabot and CI audit configuration are included; remote execution of this change is
not yet claimed. Python/npm advisory checks are point-in-time evidence only.

DRF was updated from 3.16.1 to 3.17.2 after PYSEC-2026-3827/3828 were found locally.
The upstream [3.17.2 release](https://github.com/encode/django-rest-framework/releases/tag/3.17.2)
describes request-body-limit and AdminRenderer disclosure fixes. Application-level bounded
JSON/form parsers and JSON-only rendering provide independently tested protections.

See Docker's [resource limits](https://docs.docker.com/engine/containers/resource_constraints/),
[run options](https://docs.docker.com/engine/containers/run/) and
[tmpfs behavior](https://docs.docker.com/engine/storage/tmpfs/) for the underlying controls.
Actual host enforcement is checked by `tests/test_parser_sandbox.py`, not inferred from flags.

## Remaining security/privacy acceptance

No production IAM, secret store, public abuse perimeter, permitted network provider,
backup/restore suppression or independent penetration test has been completed. The privacy
review must settle opponent data, provider retention, backup expiry and research consent;
provider permission cannot be inferred from public accessibility. Named incident/security/
privacy deputies must accept ownership before an external pilot. Operational procedures are
in [the incident runbook](../operations/security-runbook.md); dated local results are in
[M15 validation](../experiment-results/m15-security.md).
