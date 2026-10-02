# ADR-003 — Job processing

Date: 2026-09-18. Status: accepted for local implementation; gameplay release gates remain open.

## Context

Local feasibility precedes hosting; durable jobs later.

## Options

Local CLI; Cloud Tasks/Jobs; Celery/Redis; request-bound work.

## Decision

Local CLI now; preserve Cloud Tasks dispatch and Cloud Run Jobs for hosted pilot.

## Reasoning

No broker needed locally; batch must not live inside HTTP.

## Consequences

DB leases/fencing and bounded retries; hosted delivery adapter gated.

2026-10-02: [ADR-015](ADR-015-hosted-delivery-recovery.md) adds the transactional
outbox, retained physical-capacity slots and controlled Google adapters. Cloud Run
media activation remains disabled until equivalent isolation is qualified.

## Reconsideration trigger

Sustained workload or existing operations makes provisioned workers cheaper.
