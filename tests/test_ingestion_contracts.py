"""Synthetic public-schema fixtures. No live provider or player data is required."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ingestion.contracts import (
    ExternalId,
    IdentityCandidate,
    MatchMode,
    Operation,
    ProviderClass,
    Representation,
    select_candidate,
)
from ingestion.policy import ProviderPolicy, require_operation, retry_decision
from ingestion.wavu import Codebook, normalize_record, previous_window_end

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def raw_record():
    return json.loads(Path("tests/fixtures/wavu-metadata.synthetic.json").read_text())


def normalized():
    return normalize_record(raw_record(), retrieved_at=NOW, dataset_kind="synthetic")


def test_metadata_is_not_event_evidence_or_replay_payload():
    match = normalized()
    assert match.representation == Representation.MATCH_METADATA
    assert not match.event_evidence_sufficient
    assert match.replay_availability == "UNKNOWN"
    assert match.provenance.dataset_kind == "synthetic"
    assert match.canonical_game_build is None and match.mode == MatchMode.UNKNOWN
    assert match.participants[0].name_semantics == "current_at_retrieval"
    assert match.external_id.namespace == "wavu:battle_id"


def test_ids_preserve_integer_precision_case_and_namespace():
    match = normalized()
    ids = match.participants[0].identities
    assert ids[0] == ExternalId("tekken:polaris", "FakeCaseA123")
    assert ids[1] == ExternalId("tekken:user_id", "9007199254740993")
    assert ids[0] != ExternalId("tekken:polaris", "fakecasea123")
    assert ids[0] != ExternalId("other:id", "FakeCaseA123")


@pytest.mark.parametrize("bad", [float(9007199254740993), True, "9007199254740993", -1])
def test_lossy_or_uncontracted_numeric_ids_are_rejected(bad):
    row = raw_record()
    row["p1_user_id"] = bad
    with pytest.raises(ValueError):
        normalize_record(row, retrieved_at=NOW, dataset_kind="synthetic")


def test_build_and_mode_need_explicit_versioned_mapping():
    book = Codebook("synthetic-codebook/1", {"30201": "3.02.01"}, {"2": MatchMode.RANKED})
    match = normalize_record(
        raw_record(), retrieved_at=NOW, dataset_kind="synthetic", codebook=book
    )
    assert match.canonical_game_build == "3.02.01"
    assert match.version_mapping_revision == "synthetic-codebook/1"
    assert match.mode == MatchMode.RANKED
    changed = raw_record()
    changed["game_version"] = 99999
    assert (
        normalize_record(
            changed, retrieved_at=NOW, dataset_kind="synthetic", codebook=book
        ).canonical_game_build
        is None
    )


def test_future_winner_code_abstains():
    row = raw_record()
    row["winner"] = 99
    match = normalize_record(row, retrieved_at=NOW, dataset_kind="synthetic")
    assert match.winner_slot is None and match.raw_winner == "99"


def test_missing_required_schema_is_not_empty_history():
    row = raw_record()
    del row["battle_id"]
    with pytest.raises(KeyError):
        normalize_record(row, retrieved_at=NOW, dataset_kind="synthetic")


def test_source_digest_and_name_refresh_are_distinct_from_match_identity():
    first = normalized()
    row = raw_record()
    row["p1_name"] = "Renamed"
    second = normalize_record(row, retrieved_at=NOW, dataset_kind="synthetic")
    assert first.external_id == second.external_id
    assert first.provenance.record_digest != second.provenance.record_digest


def test_same_name_needs_explicit_selection_and_does_not_prove_ownership():
    match = normalized()
    candidates = tuple(
        IdentityCandidate(p.identities[0], p.identities, p.display_name, match.provenance)
        for p in match.participants
    )
    with pytest.raises(ValueError, match="Explicit"):
        select_candidate(candidates, None)
    chosen = select_candidate(candidates, candidates[1].canonical_id)
    assert chosen.canonical_id == match.participants[1].identities[0]
    assert not chosen.ownership_verified
    with pytest.raises(ValueError, match="ambiguous"):
        select_candidate((chosen, chosen), chosen.canonical_id)


def reviewed_policy(kind=ProviderClass.COMMUNITY_PUBLIC_API):
    return ProviderPolicy(
        key="fake",
        access_class=kind,
        capabilities=frozenset({Operation.DISCOVER_MATCHES}),
        enabled_operations=frozenset({Operation.DISCOVER_MATCHES}),
        technical_review="technical-test/1",
        usage_review="usage-test/1",
        approved_purpose="pilot",
        approval_expires_at=NOW + timedelta(days=30),
    )


@pytest.mark.parametrize("kind", list(ProviderClass))
def test_access_class_alone_never_grants_access(kind):
    policy = ProviderPolicy(
        key="fake", access_class=kind, capabilities=frozenset({Operation.DISCOVER_MATCHES})
    )
    with pytest.raises(PermissionError, match="DISABLED"):
        require_operation(policy, Operation.DISCOVER_MATCHES, "pilot", NOW)


def test_reverse_engineering_needs_an_additional_explicit_decision():
    policy = reviewed_policy(ProviderClass.REVERSE_ENGINEERED)
    with pytest.raises(PermissionError, match="EXPLICIT_REVERSE"):
        require_operation(policy, Operation.DISCOVER_MATCHES, "pilot", NOW)
    approved = replace(policy, reverse_engineering_decision="explicit-test-only-review")
    require_operation(approved, Operation.DISCOVER_MATCHES, "pilot", NOW)


def test_approval_is_bound_to_purpose_operation_and_time():
    policy = reviewed_policy()
    require_operation(policy, Operation.DISCOVER_MATCHES, "pilot", NOW)
    with pytest.raises(PermissionError, match="PURPOSE"):
        require_operation(policy, Operation.DISCOVER_MATCHES, "commercial", NOW)
    with pytest.raises(PermissionError, match="UNSUPPORTED"):
        require_operation(policy, Operation.FETCH_REPLAY, "pilot", NOW)
    with pytest.raises(PermissionError, match="EXPIRED"):
        require_operation(policy, Operation.DISCOVER_MATCHES, "pilot", NOW + timedelta(days=31))


@pytest.mark.parametrize("retry_after", ["3600", "Fri, 18 Sep 2026 01:00:00 GMT"])
def test_retry_honors_provider_cooldown(retry_after):
    decision = retry_decision(429, 1, NOW, retry_after=retry_after)
    assert decision.action == "RETRY" and decision.not_before == NOW + timedelta(hours=1)


@pytest.mark.parametrize(
    "status,action",
    [
        (401, "REVIEW_AUTH_OR_PERMISSION"),
        (403, "REVIEW_AUTH_OR_PERMISSION"),
        (404, "NOT_FOUND"),
        (400, "DO_NOT_RETRY"),
        (200, "ACCEPT"),
    ],
)
def test_terminal_statuses_do_not_retry(status, action):
    assert retry_decision(status, 1, NOW).action == action
    assert retry_decision(status, 1, NOW).not_before is None


def test_retry_budget_and_malformed_cooldown():
    assert retry_decision(503, 5, NOW).action == "RETRY_BUDGET_EXHAUSTED"
    assert retry_decision(429, 1, NOW, retry_after="invalid").action == "INVALID_RETRY_AFTER_REVIEW"
    assert retry_decision(None, 1, NOW).action == "RETRY"


def test_wavu_window_overlap_is_bounded_and_progresses():
    assert previous_window_end(2000) == 1360
    assert previous_window_end(2000, 0) == 1300
    with pytest.raises(ValueError):
        previous_window_end(2000, 700)


def test_all_network_provider_policies_ship_disabled():
    registry = json.loads(Path("contracts/match-sources-v1.json").read_text())
    for provider in registry["providers"]:
        if provider["access_class"] != "USER_UPLOAD":
            assert provider["enabled_operations"] == []
            assert provider["usage_approval"] is None
