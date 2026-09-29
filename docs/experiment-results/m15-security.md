# M15 local security qualification — 2026-09-29

Scope: M15.01–M15.07. Local synthetic correctness and Docker enforcement only.
No live provider, public service, real-player recognition or production readiness is claimed.

## Runtime and sandbox receipt

Windows host, Python 3.12.2, PostgreSQL 17 on the existing loopback workspace cluster,
Docker Desktop engine 24.0.6 with Linux cgroup v1. The cluster recovered its existing WAL
after its earlier unclean shutdown; it was not initialized, replaced or restored.

Final parser image:
`sha256:bbc52f5c402dfadef2eb4be97246179185b4581e10c3236c1e8ae57a6809ab9e`.
Built from the pinned Python base and `requirements-analysis.lock` using
`infrastructure/Dockerfile.analysis`. This image ID is a local receipt, not a published artifact.

`PARSER_TEST_IMAGE=<image ID> PARSER_MAX_PROFILE=1 pytest tests/test_parser_sandbox.py -v -s`
completed **7 passed in 153.86 seconds**. It verified:

- Actual UID, zero effective capabilities, no-new-privileges, protected root/input mounts,
  no non-loopback network interface, absent application credentials and Docker socket.
- Actual 1 GiB memory and combined memory/swap limit, one CPU quota, 64-PID limit,
  512 MiB work tmpfs and 64 MiB temp tmpfs. Both cgroup v1/v2 layouts are understood;
  this host exercised v1. PID exhaustion, OOM termination and scratch ENOSPC were exercised.
- Explicit PID-1 lifetime handler, cancellation and exact-container cleanup.
- Malformed MP4 rejection; valid 1080p60 synthetic capture stays REVIEW_REQUIRED.
- Exact 600-second, 36,000-frame, 512-MiB synthetic maximum-duration/byte fixture accepted;
  one additional byte rejected as FILE_TOO_LARGE.

The maximum fixture was a black H.264 clip padded with a valid MP4 free box. Its source SHA-256
was `f72c4157722b109af022c56af3340f419d2dc0136dc3a0f53a16ac32b450d5e3`.
Parser processing took **60.80 seconds**, decoder CPU **58.45 seconds**, sampled peak decoder
RSS **239,579,136 bytes**, ephemeral sample bytes **738,480**. RSS is a sampled decoder-tree
metric, not whole-container peak usage; the kernel allocation limit was independently checked.
Low-complexity synthetic video is not a worst-complexity gameplay corpus or a decoder exploit
certification. No automatic opportunities were emitted and no gameplay validation was asserted.

Initial isolation assertions assumed cgroup v2 and treated Linux's `bonding_masters` sysfs
control file as a network interface. The test now reads the actual cgroup generation and
socket interface inventory. All final assertions passed without weakening the required limits.

## API, concurrency and dependency checks

The main PostgreSQL suite and final check results are recorded in PRODUCT_PROGRESS.md and
the implementation log. New regression coverage includes atomic competing owner claims,
competing upload reservations, concurrent rate consumption, stale hash publication, nested
ownership, early multipart rejection, expired reservations, physical-purge accounting,
deletion revocation, JSON size limits, parser report filtering and cancellation.

Offline provider cases reject unapproved URLs, private/mixed DNS answers, disabled operations,
redirects, compressed/truncated/oversized responses, duplicate JSON keys, nonfinite numbers,
invalid UTF-8 and excessive depth. Existing adapter tests retain schema-drift quarantine,
provider retry/cooldown, duplicate delivery, corrections and deletion lineage checks.
No HTTP provider adapter was added or enabled; connection pinning and actual transport remain open.

`pip-audit 2.10.1 --disable-pip --no-deps -r requirements.lock` initially found two advisories
in DRF 3.16.1 (PYSEC-2026-3827 / CVE-2026-73228 and PYSEC-2026-3828 / CVE-2026-73229).
After upgrading to 3.17.2, the same scan reported **no known vulnerabilities** for the pinned
lockfile. `npm audit --omit=dev --json` reported **zero production dependency advisories**.
`pip check` passed after refreshing the editable project metadata. The audit tool was installed
only into the development environment; parser/runtime dependencies do not include it.

The upstream [DRF release receipt](https://github.com/encode/django-rest-framework/releases/tag/3.17.2)
documents both fixes. Application-level body caps and JSON-only rendering are also configured.
No OS image vulnerability scan, independent security review or production secret/IAM review was
performed. New CI sandbox/audit jobs and Dependabot configuration are present but have not been
run remotely for this implementation. Frontend source was unchanged; its prior 2026-09-23 checks
are historical evidence, not rerun M15 browser qualification.

Local XML/JSON receipts are in ignored `reports/m15-python.xml`, `reports/m15-sandbox.xml`
and `reports/m15-python-audit.json`; no private media or generated fixture is committed.
See [security architecture](../architecture/security.md) and
[incident runbook](../operations/security-runbook.md) for limits and external release gates.
