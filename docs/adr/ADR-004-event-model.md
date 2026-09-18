# ADR-004 — Event model

Date: 2026-09-18. Status: accepted for local implementation; gameplay release gates remain open.

## Context

Perception is uncertain and reprocessing must be correctable.

## Options

Mutable facts; full event sourcing; revisioned evidence/events.

## Decision

Revisioned analysis; separate observations, gameplay events and derived conclusions.

## Reasoning

Auditability without event-sourcing all product state.

## Consequences

Opportunity is a typed sparse event; unknown is explicit; publication replaces contribution.

## Reconsideration trigger

A concrete domain needs a full command history beyond analysis.

