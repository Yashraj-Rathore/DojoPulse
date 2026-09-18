# ADR-002 — Modular monolith

Date: 2026-09-18. Status: accepted for local implementation; gameplay release gates remain open.

## Context

Two developers need atomic domain changes.

## Options

Shared monolith; microservices; duplicated worker backend.

## Decision

One repository and PostgreSQL database, separate worker entrypoint.

## Reasoning

Deployment scaling does not require service boundaries.

## Consequences

Explicit application commands; cross-module FKs permitted.

## Reconsideration trigger

Independent team/runtime/scaling ownership is demonstrated.

