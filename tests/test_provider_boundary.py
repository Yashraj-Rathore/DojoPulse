from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ingestion.boundary import FetchBoundary
from ingestion.contracts import Operation, ProviderClass
from ingestion.policy import ProviderPolicy

NOW = datetime(2026, 9, 29, tzinfo=UTC)
OP = Operation.DISCOVER_MATCHES
POLICY = ProviderPolicy(
    "fictional-test",
    ProviderClass.COMMUNITY_PUBLIC_API,
    frozenset({OP}),
    frozenset({OP}),
    "test-only",
    "test-only",
    "fixture",
    NOW + timedelta(days=1),
)
BOUNDARY = FetchBoundary(POLICY, "example.com", frozenset({"/matches"}))


def test_exact_reviewed_target_and_disabled_policy():
    assert BOUNDARY.validate_target(
        "https://example.com/matches?page=1", OP, "fixture", NOW, ["8.8.8.8"]
    ) == ("8.8.8.8",)
    disabled = replace(BOUNDARY, policy=replace(POLICY, enabled_operations=frozenset()))
    with pytest.raises(PermissionError, match="OPERATION_DISABLED"):
        disabled.validate_target("https://example.com/matches", OP, "fixture", NOW, ["8.8.8.8"])


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/matches",
        "https://example.com:443/matches",
        "https://example.com.evil/matches",
        "https://user:secret@example.com/matches",
        "https://example.com./matches",
        "https://127.0.0.1/matches",
        "https://example.com/%2e%2e/matches",
        "https://example.com/matches#fragment",
        "https://example.com/other",
        "https://example.com/matches\n",
        "https://example.com\\@evil/matches",
    ],
)
def test_rejects_url_ambiguity_and_unapproved_origins(url):
    with pytest.raises(ValueError):
        BOUNDARY.validate_target(url, OP, "fixture", NOW, ["8.8.8.8"])


@pytest.mark.parametrize(
    "addresses",
    [
        [],
        ["127.0.0.1"],
        ["169.254.169.254"],
        ["10.0.0.1"],
        ["::1"],
        ["fc00::1"],
        ["::ffff:8.8.8.8"],
        ["224.0.0.1"],
        ["8.8.8.8", "192.168.1.1"],
    ],
)
def test_rejects_private_or_mixed_dns_answers(addresses):
    with pytest.raises(ValueError):
        BOUNDARY.validate_target("https://example.com/matches", OP, "fixture", NOW, addresses)


@pytest.mark.parametrize(
    "body",
    [
        b'{"a":1,"a":2}',
        b'{"value":NaN}',
        b'{"value":1e9999}',
        b"\xff",
        b"{",
        b"[" * 40 + b"0" + b"]" * 40,
    ],
)
def test_strict_json_and_complexity(body):
    with pytest.raises(ValueError):
        BOUNDARY.decode_json([body], status=200, content_type="application/json")


def test_stream_cap_truncation_compression_and_redirects():
    boundary = replace(BOUNDARY, max_bytes=8)
    assert boundary.decode_json(
        [b'{"a":', b"1}"], status=200, content_type="application/json", content_length=7
    ) == {"a": 1}
    for options in (
        {"status": 302},
        {"content_encoding": "gzip"},
        {"content_length": 8},
        {"content_length": 99},
        {"content_type": "text/html"},
    ):
        with pytest.raises(ValueError):
            boundary.decode_json(
                [b'{"a":1}'], **({"status": 200, "content_type": "application/json"} | options)
            )
    with pytest.raises(ValueError, match="LIMIT"):
        boundary.decode_json([b"1234", b"56789"], status=200, content_type="application/json")
