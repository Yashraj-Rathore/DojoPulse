# ADR-001 — Primary backend

Date: 2026-09-18. Status: accepted for local implementation; gameplay release gates remain open.

## Context

Relational workflows and review dominate.

## Options

Django/DRF; FastAPI with assembled ORM/auth; separate services.

## Decision

Keep Django/DRF.

## Reasoning

Integrated auth/admin/migrations reduce assembly; HTTP speed is not the perception bottleneck.

## Consequences

Rules remain pure Python; views authorize then call services.

## Reconsideration trigger

Measured product API need not served by this framework.

