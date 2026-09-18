# ADR-007 — Game data versioning

Date: 2026-09-18. Status: accepted for local implementation; gameplay release gates remain open.

## Context

Game patches and knowledge corrections differ.

## Options

Latest scraped values; effective-date guesses; immutable snapshots.

## Decision

Stable move IDs, immutable build-specific knowledge; no runtime scraping.

## Reasoning

Historical results must resolve the exact knowledge used.

## Consequences

Unverified fields stay null; public references are leads, not release approval.

## Reconsideration trigger

Only internal storage representation may change; historical pinning remains.

