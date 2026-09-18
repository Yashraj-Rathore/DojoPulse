# ADR-006 — Client versus cloud

Date: 2026-09-18. Status: accepted for local implementation; gameplay release gates remain open.

## Context

Browser complexity must earn its cost.

## Options

All cloud; browser ML; light hybrid.

## Decision

Local preflight and preview; one authoritative Python pipeline.

## Reasoning

Avoid duplicate perception implementations before device benchmarks.

## Consequences

Selective crops cannot discard evidence needed for reach/context.

## Reconsideration trigger

Client spike yields >=50% bytes or >=30% latency gain without quality loss.

