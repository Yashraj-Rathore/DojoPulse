"""Identity, metadata and replay representations are distinct from gameplay judgments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class ProviderClass(StrEnum):
    OFFICIAL = "OFFICIAL"
    COMMUNITY_PUBLIC_API = "COMMUNITY_PUBLIC_API"
    REVERSE_ENGINEERED = "REVERSE_ENGINEERED"
    USER_UPLOAD = "USER_UPLOAD"


class Operation(StrEnum):
    RESOLVE_NAME = "RESOLVE_NAME"
    RESOLVE_ID = "RESOLVE_ID"
    DISCOVER_MATCHES = "DISCOVER_MATCHES"
    FETCH_REPLAY = "FETCH_REPLAY"
    IMPORT_VIDEO = "IMPORT_VIDEO"


class Representation(StrEnum):
    MATCH_METADATA = "MATCH_METADATA"
    VIDEO = "VIDEO"
    NATIVE_REPLAY = "NATIVE_REPLAY"
    STRUCTURED_EVENTS = "STRUCTURED_EVENTS"


class Availability(StrEnum):
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    NOT_FOUND = "NOT_FOUND"
    EXPIRED = "EXPIRED"
    VERSION_UNSUPPORTED = "VERSION_UNSUPPORTED"


class MatchMode(StrEnum):
    UNKNOWN = "unknown"
    RANKED = "ranked"
    QUICK = "quick"
    PLAYER = "player"
    GROUP = "group"
    PRACTICE = "practice"
    TAKEOVER = "takeover"
    OTHER = "other"


def require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware")


@dataclass(frozen=True)
class ExternalId:
    namespace: str
    value: str

    def __post_init__(self) -> None:
        if not self.namespace or not self.value or self.value != self.value.strip():
            raise ValueError("External ID requires namespace and exact nonempty value")
        if len(self.value) > 200:
            raise ValueError("External ID too long")


@dataclass(frozen=True)
class Provenance:
    provider: str
    access_class: ProviderClass
    adapter_version: str
    schema_version: str
    retrieved_at: datetime
    record_digest: str
    digest_kind: str = "canonical-json-sha256"
    dataset_kind: str = "real"

    def __post_init__(self) -> None:
        require_aware(self.retrieved_at)
        if self.dataset_kind not in {"real", "synthetic"}:
            raise ValueError("Invalid dataset kind")
        if len(self.record_digest) != 64 or any(
            c not in "0123456789abcdef" for c in self.record_digest
        ):
            raise ValueError("Invalid source record digest")


@dataclass(frozen=True)
class IdentityCandidate:
    canonical_id: ExternalId
    bindings: tuple[ExternalId, ...]
    display_name: str | None
    source: Provenance

    # Public profile selection is explicitly not authentication.
    @property
    def ownership_verified(self) -> bool:
        return False


def select_candidate(
    candidates: tuple[IdentityCandidate, ...], selected: ExternalId | None
) -> IdentityCandidate:
    if selected is None:
        raise ValueError("Explicit player selection required; names are not unique")
    matches = [candidate for candidate in candidates if candidate.canonical_id == selected]
    if len(matches) != 1:
        raise ValueError("Identity missing or ambiguous")
    return matches[0]


@dataclass(frozen=True)
class PlayerSnapshot:
    slot: int
    identities: tuple[ExternalId, ...]
    display_name: str | None
    name_semantics: str
    character_code: str
    rank_code: str | None
    power: int | None
    rounds_won: int | None

    def __post_init__(self) -> None:
        if self.slot not in {1, 2} or not self.identities:
            raise ValueError("Participant needs a slot and namespaced identity")


@dataclass(frozen=True)
class MatchMetadata:
    game: str
    external_id: ExternalId
    played_at: datetime
    raw_game_version: str
    canonical_game_build: str | None
    version_mapping_revision: str | None
    raw_mode: str
    mode: MatchMode
    mode_mapping_revision: str | None
    participants: tuple[PlayerSnapshot, PlayerSnapshot]
    winner_slot: int | None
    raw_winner: str
    stage_code: str | None
    provenance: Provenance
    representation: Representation = Representation.MATCH_METADATA
    replay_availability: Availability = Availability.UNKNOWN

    def __post_init__(self) -> None:
        require_aware(self.played_at)
        if {p.slot for p in self.participants} != {1, 2}:
            raise ValueError("Exactly one participant per slot required")
        if self.winner_slot not in {None, 1, 2}:
            raise ValueError("Invalid winner slot")
        if self.canonical_game_build is not None and not self.version_mapping_revision:
            raise ValueError("Mapped build requires a mapping revision")
        if self.mode != MatchMode.UNKNOWN and not self.mode_mapping_revision:
            raise ValueError("Mapped mode requires a mapping revision")
        if self.representation != Representation.MATCH_METADATA:
            raise ValueError("Match metadata cannot claim to be gameplay evidence")

    @property
    def event_evidence_sufficient(self) -> bool:
        return False


@dataclass(frozen=True)
class DiscoveryPage:
    matches: tuple[MatchMetadata, ...]
    next_cursor: str | None
    requested_start: datetime
    requested_end: datetime
    coverage: str  # COMPLETE_FOR_QUERY / PARTIAL / UNKNOWN; not completeness of player's history
    gaps: tuple[str, ...] = ()
    truncated: bool = False


@dataclass(frozen=True)
class ReplayReference:
    source: Provenance
    external_match_id: ExternalId
    representation: Representation
    availability: Availability
    external_replay_id: ExternalId | None = None
    upstream_expires_at: datetime | None = None
    canonical_game_build: str | None = None


@dataclass(frozen=True)
class PayloadReceipt:
    reference: ReplayReference
    private_object_key: str
    content_sha256: str
    byte_count: int
    local_retain_until: datetime
    # Parser validation is separate from a successful download.


class ProviderAdapter(Protocol):
    """Future transports implement this interface after purpose-specific approval."""

    def resolve_player(self, query: str, kind: Operation) -> tuple[IdentityCandidate, ...]: ...

    def discover_matches(
        self, identity: ExternalId, cursor: str | None, start: datetime, end: datetime
    ) -> DiscoveryPage: ...

    def fetch_replay(self, reference: ReplayReference) -> PayloadReceipt: ...
