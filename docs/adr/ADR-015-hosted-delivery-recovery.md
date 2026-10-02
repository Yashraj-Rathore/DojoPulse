# ADR-015: retain physical execution capacity and replay independent controls

Date: 2026-10-02. Status: accepted local engineering; hosted qualification pending.

Google Cloud remains the chosen cloud design. Durable transactional dispatch,
deterministic task names, one fenced worker entry, retained physical execution
slots, heartbeats/deadlines and authoritative stop reconciliation protect admission
and result publication. Ambiguous non-idempotent job launches retain their slot
until resolved; lease expiry cannot establish physical termination.

Signed deletion/withdrawal intents and completeness checkpoints live outside
database/media backups. Recovery invalidates stale authentication, jobs and consent,
reapplies controls and purges under quarantine before a reviewed read handoff.
The local journal needs an independent durable hosted implementation/freshness
inventory before production.

The qualified Docker parser cannot be nested in Cloud Run. Managed media execution
remains disabled in code until an equivalent sandbox and independent stop/deadline
boundary passes review. Official adapters and Terraform preparation do not waive
usage rights, scientific decisions, privacy/security gates, region/budget approval
or staging acceptance. See [full contract](../architecture/hosted-delivery.md) and
[qualification evidence](../experiment-results/m16-delivery.md).
